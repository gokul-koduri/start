"""API v2 Auth router — registration, login, API key management."""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field

from auth.jwt_handler import JWTHandler
from auth.password_hasher import hash_password, verify_password, validate_password_strength
from auth.api_key_manager import generate_api_key
from auth.auth_middleware import get_current_user

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v2/auth", tags=["auth"])

_jwt_handler = JWTHandler()


# ── Pydantic Models ──────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    display_name: Optional[str] = Field(None, max_length=255)
    role: str = Field(default="viewer", pattern=r"^(viewer|analyst|admin)$")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class APIKeyCreate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    permissions: list[str] = Field(default=["*"])


# ── Registration (T-054) ──────────────────────────────────

@router.post("/register")
def register(body: RegisterRequest):
    """Register a new user account.

    Creates a user with bcrypt-hashed password. Default role is 'viewer'.
    """
    is_valid, error_msg = validate_password_strength(body.password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    try:
        from db.connection import get_connection
        from db import schema
        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE email = %s", (body.email,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            raise HTTPException(status_code=409, detail="Email already registered")

        password_hash = hash_password(body.password)
        cursor.execute(
            """INSERT INTO users (email, password_hash, display_name, role)
               VALUES (%s, %s, %s, %s)""",
            (body.email, password_hash, body.display_name, body.role),
        )
        user_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()

        _logger.info("User registered: %s (ID: %d, role: %s)", body.email, user_id, body.role)

        return {
            "status": "registered",
            "user_id": user_id,
            "email": body.email,
            "role": body.role,
        }
    except HTTPException:
        raise
    except Exception as e:
        _logger.error("Registration failed: %s", e)
        raise HTTPException(status_code=500, detail="Registration failed")


# ── Login (T-055) ──────────────────────────────────────────

@router.post("/login")
def login(body: LoginRequest):
    """Authenticate user and return JWT token."""
    try:
        from db.connection import get_connection
        from db import schema
        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, email, password_hash, display_name, role, is_active FROM users WHERE email = %s",
            (body.email,),
        )
        user = cursor.fetchone()

        if not user or not verify_password(body.password, user["password_hash"]):
            cursor.close()
            conn.close()
            raise HTTPException(status_code=401, detail="Invalid email or password")

        if not user["is_active"]:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=403, detail="Account is deactivated")

        # Update last login
        cursor.execute(
            "UPDATE users SET last_login_at = %s WHERE id = %s",
            (datetime.now(timezone.utc).isoformat(), user["id"]),
        )
        conn.commit()
        cursor.close()
        conn.close()

        # Create JWT token
        token_payload = {
            "user_id": user["id"],
            "email": user["email"],
            "role": user["role"],
        }
        access_token = _jwt_handler.create_token(token_payload)

        _logger.info("User logged in: %s (role: %s)", body.email, user["role"])

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user["id"],
                "email": user["email"],
                "display_name": user["display_name"],
                "role": user["role"],
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        _logger.error("Login failed: %s", e)
        raise HTTPException(status_code=500, detail="Login failed")


# ── API Key Management (T-057) ──────────────────────────────

@router.post("/api-keys")
def create_api_key(body: APIKeyCreate, current_user: dict = Depends(get_current_user)):
    """Create a new API key for the authenticated user."""
    user_id = current_user["user_id"]
    raw_key, key_prefix, key_hash = generate_api_key()

    try:
        from db.connection import get_connection
        from db import schema
        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()

        cursor.execute(
            """INSERT INTO api_keys (user_id, key_prefix, key_hash, name, permissions)
               VALUES (%s, %s, %s, %s, %s)""",
            (user_id, key_prefix, key_hash, body.name, json.dumps(body.permissions)),
        )
        key_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()

        _logger.info("API key created: prefix=%s, user=%s", key_prefix, current_user.get("email"))

        return {
            "id": key_id,
            "name": body.name,
            "key_prefix": key_prefix,
            "raw_key": raw_key,
            "permissions": body.permissions,
            "warning": "Store this key securely. It will not be shown again.",
        }
    except Exception as e:
        _logger.error("API key creation failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to create API key")


@router.get("/api-keys")
def list_api_keys(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    """List API keys for the authenticated user."""
    user_id = current_user["user_id"]

    try:
        from db.connection import get_connection
        from db import schema
        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()

        cursor.execute(
            """SELECT id, key_prefix, name, permissions, last_used_at, is_active, created_at
               FROM api_keys WHERE user_id = %s ORDER BY created_at DESC LIMIT %s OFFSET %s""",
            (user_id, limit, offset),
        )
        keys = []
        for row in cursor.fetchall():
            k = dict(row)
            try:
                k["permissions"] = json.loads(k.get("permissions", "[]"))
            except (TypeError, ValueError):
                k["permissions"] = []
            keys.append(k)

        cursor.close()
        conn.close()
        return {"api_keys": keys, "limit": limit, "offset": offset}
    except Exception as e:
        _logger.error("List API keys failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to list API keys")


@router.delete("/api-keys/{key_id}")
def delete_api_key(key_id: int, current_user: dict = Depends(get_current_user)):
    """Delete (revoke) an API key."""
    user_id = current_user["user_id"]

    try:
        from db.connection import get_connection
        from db import schema
        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id FROM api_keys WHERE id = %s AND user_id = %s",
            (key_id, user_id),
        )
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail="API key not found")

        cursor.execute("UPDATE api_keys SET is_active = 0 WHERE id = %s", (key_id,))
        conn.commit()
        cursor.close()
        conn.close()

        return {"status": "revoked", "key_id": key_id}
    except HTTPException:
        raise
    except Exception as e:
        _logger.error("API key deletion failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to delete API key")
