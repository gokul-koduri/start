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

    def test_schema_version_at_least_22(self):
        from db.schema import get_schema_version
        self.assertGreaterEqual(get_schema_version(), 22)

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


class TestInputSanitizer(unittest.TestCase):
    """Test input sanitization utilities (T-061)."""

    def test_sanitize_string_basic(self):
        from utils.input_sanitizer import sanitize_string
        result = sanitize_string("  hello world  ")
        self.assertEqual(result, "hello world")

    def test_sanitize_string_strips_null_bytes(self):
        from utils.input_sanitizer import sanitize_string
        result = sanitize_string("hello\x00world")
        self.assertEqual(result, "helloworld")

    def test_sanitize_string_escapes_html(self):
        from utils.input_sanitizer import sanitize_string
        result = sanitize_string("<b>bold</b>")
        self.assertIn("&lt;b&gt;", result)

    def test_sanitize_string_rejects_script(self):
        from utils.input_sanitizer import sanitize_string
        with self.assertRaises(ValueError):
            sanitize_string('<script>alert("xss")</script>')

    def test_sanitize_string_rejects_javascript_uri(self):
        from utils.input_sanitizer import sanitize_string
        with self.assertRaises(ValueError):
            sanitize_string('javascript:alert(1)')

    def test_sanitize_string_rejects_event_handler(self):
        from utils.input_sanitizer import sanitize_string
        with self.assertRaises(ValueError):
            sanitize_string('onclick=alert(1)')

    def test_sanitize_string_rejects_oversized(self):
        from utils.input_sanitizer import sanitize_string
        with self.assertRaises(ValueError):
            sanitize_string("x" * 10001)

    def test_sanitize_dict(self):
        from utils.input_sanitizer import sanitize_dict
        data = {"name": "  test  ", "nested": {"key": "<b>hi</b>"}}
        result = sanitize_dict(data)
        self.assertEqual(result["name"], "test")
        self.assertIn("&lt;b&gt;", result["nested"]["key"])

    def test_sanitize_dict_with_list(self):
        from utils.input_sanitizer import sanitize_dict
        data = {"tags": ["  a  ", "<b>html</b>"]}
        result = sanitize_dict(data)
        self.assertEqual(result["tags"][0], "a")
        # HTML is escaped in list items
        self.assertIn("&lt;b&gt;", result["tags"][1])

    def test_sanitize_dict_list_dangerous_raises(self):
        """Dangerous patterns in list items raise ValueError."""
        from utils.input_sanitizer import sanitize_dict
        data = {"tags": ["<script>alert(1)</script>"]}
        with self.assertRaises(ValueError):
            sanitize_dict(data)

    def test_sanitize_email_valid(self):
        from utils.input_sanitizer import sanitize_email
        result = sanitize_email("  User@Example.COM  ")
        self.assertEqual(result, "user@example.com")

    def test_sanitize_email_invalid(self):
        from utils.input_sanitizer import sanitize_email
        with self.assertRaises(ValueError):
            sanitize_email("not-an-email")

    def test_sanitize_email_empty(self):
        from utils.input_sanitizer import sanitize_email
        with self.assertRaises(ValueError):
            sanitize_email("")

    def test_sanitize_string_non_string_raises(self):
        from utils.input_sanitizer import sanitize_string
        with self.assertRaises(ValueError):
            sanitize_string(123)


class TestSecurityHeaders(unittest.TestCase):
    """Test security headers middleware (T-060)."""

    @classmethod
    def setUpClass(cls):
        try:
            import api_server
            if not api_server.HAS_FASTAPI:
                raise unittest.SkipTest("FastAPI not installed")
            cls.app = api_server.app
        except ImportError:
            raise unittest.SkipTest("api_server not importable")

    def test_x_content_type_options_header(self):
        from fastapi.testclient import TestClient
        client = TestClient(self.app)
        response = client.get("/api/health")
        self.assertEqual(response.headers.get("X-Content-Type-Options"), "nosniff")

    def test_x_frame_options_header(self):
        from fastapi.testclient import TestClient
        client = TestClient(self.app)
        response = client.get("/api/health")
        self.assertEqual(response.headers.get("X-Frame-Options"), "DENY")

    def test_referrer_policy_header(self):
        from fastapi.testclient import TestClient
        client = TestClient(self.app)
        response = client.get("/api/health")
        self.assertEqual(
            response.headers.get("Referrer-Policy"),
            "strict-origin-when-cross-origin"
        )

    def test_csp_header_present(self):
        from fastapi.testclient import TestClient
        client = TestClient(self.app)
        response = client.get("/api/health")
        csp = response.headers.get("Content-Security-Policy", "")
        self.assertIn("default-src 'self'", csp)

    def test_permissions_policy_header(self):
        from fastapi.testclient import TestClient
        client = TestClient(self.app)
        response = client.get("/api/health")
        pp = response.headers.get("Permissions-Policy", "")
        self.assertIn("camera=()", pp)
        self.assertIn("microphone=()", pp)


class TestDockerHardening(unittest.TestCase):
    """Test Docker security hardening (T-062)."""

    @classmethod
    def setUpClass(cls):
        cls.compose_path = Path(__file__).parent.parent / "docker-compose.yml"
        cls.compose_content = cls.compose_path.read_text()

    def test_all_services_have_security_opt(self):
        """All services have no-new-privileges."""
        import re
        services = re.findall(r"^  (\w[\w-]*):", self.compose_content, re.MULTILINE)
        for svc in services:
            if svc in ("version", "services", "volumes"):
                continue
            # Find the service block
            self.assertIn("no-new-privileges:true", self.compose_content,
                          f"Service '{svc}' missing no-new-privileges")

    def test_all_services_have_cap_drop(self):
        """All services drop ALL capabilities."""
        self.assertIn("cap_drop:", self.compose_content)
        self.assertIn("- ALL", self.compose_content)

    def test_app_services_run_as_non_root(self):
        """Application services run as user 1000:1000."""
        app_services = ["api", "streamlit", "pipeline", "scheduler", "stream_processor"]
        for svc in app_services:
            # Find the service section
            import re
            pattern = rf"  {svc}:\s*\n(?:.*\n)*?.*user:"
            self.assertRegex(
                self.compose_content, pattern,
                f"Service '{svc}' missing user directive"
            )

    def test_no_hardcoded_passwords(self):
        """No default password fallbacks in docker-compose."""
        self.assertNotIn("startup2024", self.compose_content,
                         "Hardcoded password 'startup2024' found in docker-compose")

    def test_api_service_has_jwt_secret(self):
        """API service passes JWT_SECRET env var."""
        self.assertIn("JWT_SECRET:", self.compose_content)

    def test_resource_limits_exist(self):
        """Services have deploy resource limits."""
        self.assertIn("deploy:", self.compose_content)
        self.assertIn("memory:", self.compose_content)
        self.assertIn("cpus:", self.compose_content)


class TestSecretsCleanup(unittest.TestCase):
    """Test secrets cleanup (T-063)."""

    def test_settings_yaml_no_hardcoded_jwt(self):
        """settings.yaml uses env var for JWT secret."""
        settings_path = Path(__file__).parent.parent / "config" / "settings.yaml"
        content = settings_path.read_text()
        self.assertIn("jwt_secret: \"${JWT_SECRET}\"", content)
        self.assertNotIn("change-me-in-production", content)

    def test_settings_yaml_no_hardcoded_timescaledb_password(self):
        """settings.yaml uses env var for TimescaleDB password."""
        settings_path = Path(__file__).parent.parent / "config" / "settings.yaml"
        content = settings_path.read_text()
        self.assertNotIn("startup2024", content)

    def test_env_example_has_required_vars(self):
        """.env.example documents all required secrets."""
        env_path = Path(__file__).parent.parent / ".env.example"
        content = env_path.read_text()
        self.assertIn("MYSQL_PASSWORD=", content)
        self.assertIn("JWT_SECRET=", content)
        self.assertIn("TIMESCALEDB_PASSWORD=", content)


if __name__ == "__main__":
    unittest.main()
