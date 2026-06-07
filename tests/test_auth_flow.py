"""Tests for Sprint 4 Epic 4.1 — Auth flow (T-054 to T-058)."""

import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestPasswordHasher(unittest.TestCase):
    """Test password hashing and verification (T-054)."""

    def test_hash_password_returns_string(self):
        from auth.password_hasher import hash_password
        result = hash_password("SecurePass123")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_verify_password_correct(self):
        from auth.password_hasher import hash_password, verify_password
        hashed = hash_password("MyPassword1")
        self.assertTrue(verify_password("MyPassword1", hashed))

    def test_verify_password_incorrect(self):
        from auth.password_hasher import hash_password, verify_password
        hashed = hash_password("MyPassword1")
        self.assertFalse(verify_password("WrongPassword1", hashed))

    def test_validate_password_strength_valid(self):
        from auth.password_hasher import validate_password_strength
        valid, msg = validate_password_strength("SecurePass123")
        self.assertTrue(valid)

    def test_validate_password_strength_too_short(self):
        from auth.password_hasher import validate_password_strength
        valid, msg = validate_password_strength("Short1")
        self.assertFalse(valid)
        self.assertIn("8 characters", msg)

    def test_validate_password_strength_no_upper(self):
        from auth.password_hasher import validate_password_strength
        valid, msg = validate_password_strength("lowercase123")
        self.assertFalse(valid)

    def test_validate_password_strength_no_digit(self):
        from auth.password_hasher import validate_password_strength
        valid, msg = validate_password_strength("NoDigitsHere")
        self.assertFalse(valid)


class TestAPIKeyManager(unittest.TestCase):
    """Test API key generation and hashing (T-057)."""

    def test_generate_api_key_format(self):
        from auth.api_key_manager import generate_api_key, KEY_PREFIX
        raw_key, prefix, key_hash = generate_api_key()
        self.assertTrue(raw_key.startswith(KEY_PREFIX))
        self.assertEqual(len(key_hash), 64)  # SHA-256 hex

    def test_hash_api_key_deterministic(self):
        from auth.api_key_manager import hash_api_key
        h1 = hash_api_key("oip_live_test123")
        h2 = hash_api_key("oip_live_test123")
        self.assertEqual(h1, h2)

    def test_hash_api_key_different_keys(self):
        from auth.api_key_manager import hash_api_key
        h1 = hash_api_key("oip_live_key1")
        h2 = hash_api_key("oip_live_key2")
        self.assertNotEqual(h1, h2)

    def test_validate_api_key_format_valid(self):
        from auth.api_key_manager import validate_api_key_format
        self.assertTrue(validate_api_key_format("oip_live_something123"))

    def test_validate_api_key_format_invalid(self):
        from auth.api_key_manager import validate_api_key_format
        self.assertFalse(validate_api_key_format("invalid_key"))
        self.assertFalse(validate_api_key_format(""))
        self.assertFalse(validate_api_key_format(None))


class TestAuthMiddleware(unittest.TestCase):
    """Test auth middleware dependency functions (T-056)."""

    def test_require_role_returns_callable(self):
        from auth.auth_middleware import require_role
        checker = require_role("admin")
        self.assertTrue(callable(checker))

    def test_require_permission_returns_callable(self):
        from auth.auth_middleware import require_permission
        checker = require_permission("startups:write")
        self.assertTrue(callable(checker))


class TestAuthRouterRegistration(unittest.TestCase):
    """Test that auth routes are registered in the app."""

    @classmethod
    def setUpClass(cls):
        try:
            import api_server
            if not api_server.HAS_FASTAPI:
                raise unittest.SkipTest("FastAPI not installed")
            cls.app = api_server.app
        except ImportError:
            raise unittest.SkipTest("api_server not importable")

    def test_register_route_exists(self):
        routes = [r.path for r in self.app.routes if hasattr(r, "path")]
        self.assertIn("/api/v2/auth/register", routes)

    def test_login_route_exists(self):
        routes = [r.path for r in self.app.routes if hasattr(r, "path")]
        self.assertIn("/api/v2/auth/login", routes)

    def test_api_keys_route_exists(self):
        routes = [r.path for r in self.app.routes if hasattr(r, "path")]
        self.assertIn("/api/v2/auth/api-keys", routes)


class TestSchemaV22(unittest.TestCase):
    """Test schema version 22 changes."""

    def test_schema_version_is_22(self):
        from db.schema import get_schema_version
        self.assertEqual(get_schema_version(), 22)

    def test_users_table_in_schema(self):
        from db.schema import _TABLES
        table_sql = " ".join(_TABLES)
        self.assertIn("users", table_sql)

    def test_api_keys_table_in_schema(self):
        from db.schema import _TABLES
        table_sql = " ".join(_TABLES)
        self.assertIn("api_keys", table_sql)

    def test_users_table_has_required_columns(self):
        from db.schema import _TABLES
        for t in _TABLES:
            if "CREATE TABLE" in t and "users (" in t:
                self.assertIn("email", t)
                self.assertIn("password_hash", t)
                self.assertIn("role", t)
                self.assertIn("is_active", t)
                break

    def test_api_keys_table_has_required_columns(self):
        from db.schema import _TABLES
        for t in _TABLES:
            if "CREATE TABLE" in t and "api_keys" in t:
                self.assertIn("key_hash", t)
                self.assertIn("user_id", t)
                self.assertIn("is_active", t)
                self.assertIn("FOREIGN KEY", t)
                break

    def test_users_table_has_indexes(self):
        from db.schema import _TABLES
        for t in _TABLES:
            if "CREATE TABLE" in t and "users (" in t:
                self.assertIn("idx_users_email", t)
                self.assertIn("idx_users_role", t)
                break


if __name__ == "__main__":
    unittest.main()
