"""FastAPI authentication dependencies for JWT and API key validation."""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auth.jwt_handler import JWTHandler
from auth.api_key_manager import hash_api_key

_logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)
_jwt_handler = JWTHandler()


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> dict:
    """FastAPI dependency that extracts and validates the current user.

    Checks two auth methods in order:
    1. Authorization: Bearer <jwt-token>  (JWT auth)
    2. X-API-Key: <api-key>              (API key auth)

    Returns:
        Dict with user_id, email, role, auth_method

    Raises:
        HTTPException 401 if no valid auth provided
    """
    # Method 1: JWT Bearer token
    if credentials and credentials.scheme.lower() == "bearer":
        try:
            payload = _jwt_handler.validate_token(credentials.credentials)
            return {
                "user_id": payload.get("user_id"),
                "email": payload.get("email", ""),
                "role": payload.get("role", "viewer"),
                "auth_method": "jwt",
            }
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Method 2: API Key in X-API-Key header
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return await _validate_api_key(api_key)

    # No auth provided
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide Authorization: Bearer <token> or X-API-Key header.",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def _validate_api_key(raw_key: str) -> dict:
    """Validate an API key and return user info."""
    key_hash = hash_api_key(raw_key)

    try:
        from db.connection import get_connection
        from db import schema
        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()

        cursor.execute(
            """SELECT ak.id, ak.user_id, ak.permissions, ak.is_active,
                      u.email, u.role, u.is_active as user_active
               FROM api_keys ak
               JOIN users u ON ak.user_id = u.id
               WHERE ak.key_hash = %s""",
            (key_hash,),
        )
        row = cursor.fetchone()

        if not row:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=401, detail="Invalid API key")

        if not row["is_active"] or not row["user_active"]:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=401, detail="API key or account is deactivated")

        # Update last_used_at (best-effort)
        try:
            cursor.execute(
                "UPDATE api_keys SET last_used_at = NOW() WHERE id = %s",
                (row["id"],),
            )
            conn.commit()
        except Exception:
            pass

        cursor.close()
        conn.close()

        return {
            "user_id": row["user_id"],
            "email": row["email"],
            "role": row["role"],
            "auth_method": "api_key",
        }
    except HTTPException:
        raise
    except Exception as e:
        _logger.error("API key validation failed: %s", e)
        raise HTTPException(status_code=401, detail="API key validation failed")


def require_role(*roles: str):
    """Create a dependency that requires one of the specified roles.

    Usage:
        @router.post("/admin-only")
        async def admin_endpoint(user: dict = Depends(require_role("admin"))):
            ...
    """
    async def role_checker(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user.get("role") not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.get('role')}' not permitted. Required: {', '.join(roles)}",
            )
        return current_user
    return role_checker


def require_permission(permission: str):
    """Create a dependency that requires a specific permission.

    Usage:
        @router.post("/generate")
        async def generate(user: dict = Depends(require_permission("system:write"))):
            ...
    """
    from auth.rbac import RBAC
    _rbac = RBAC()

    async def permission_checker(current_user: dict = Depends(get_current_user)) -> dict:
        role = current_user.get("role", "viewer")
        if not _rbac.check_permission(role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' denied for role '{role}'",
            )
        return current_user
    return permission_checker
