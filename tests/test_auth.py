"""Tests for auth package (JWT + RBAC)."""

import unittest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestJWTHandler(unittest.TestCase):
    """Test JWT token creation and validation."""

    def setUp(self):
        """Set up test fixtures."""
        from auth.jwt_handler import JWTHandler

        self.handler = JWTHandler({"jwt_secret": "test-secret", "jwt_expiry_hours": 24})

    def test_create_token(self):
        """Test token creation with payload."""
        payload = {"user_id": 123, "role": "analyst"}
        token = self.handler.create_token(payload)

        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 0)
        # Token should be non-empty and can be validated
        validated = self.handler.validate_token(token)
        self.assertEqual(validated["user_id"], 123)
        self.assertEqual(validated["role"], "analyst")

    def test_validate_token(self):
        """Test token validation."""
        payload = {"user_id": 456, "role": "admin"}
        token = self.handler.create_token(payload)
        validated = self.handler.validate_token(token)

        self.assertEqual(validated["user_id"], 456)
        self.assertEqual(validated["role"], "admin")
        self.assertIn("user_id", validated)
        self.assertIn("role", validated)

    def test_validate_expired_token(self):
        """Test that expired tokens are rejected."""
        # Create handler with very short expiry
        handler = self.handler.__class__({"jwt_secret": "test", "jwt_expiry_hours": -1})
        payload = {"user_id": 789}
        token = handler.create_token(payload)

        with self.assertRaises(ValueError) as ctx:
            handler.validate_token(token)
        self.assertIn("expired", str(ctx.exception).lower())

    def test_validate_invalid_token(self):
        """Test that invalid tokens are rejected."""
        with self.assertRaises(ValueError) as ctx:
            self.handler.validate_token("not-a-valid-token")
        self.assertIn("invalid", str(ctx.exception).lower())

    def test_refresh_token(self):
        """Test token refresh extends expiry."""
        payload = {"user_id": 999, "role": "viewer"}
        old_token = self.handler.create_token(payload)
        new_token = self.handler.refresh_token(old_token)

        # New token should validate successfully
        validated = self.handler.validate_token(new_token)
        self.assertEqual(validated["user_id"], 999)
        self.assertEqual(validated["role"], "viewer")


class TestRBAC(unittest.TestCase):
    """Test role-based access control."""

    def setUp(self):
        """Set up test fixtures."""
        from auth.rbac import RBAC

        self.rbac = RBAC()

    def test_check_permission_viewer(self):
        """Test viewer permissions (read-only)."""
        self.assertTrue(self.rbac.check_permission("viewer", "startups:read"))
        self.assertTrue(self.rbac.check_permission("viewer", "news:read"))
        self.assertFalse(self.rbac.check_permission("viewer", "startups:write"))
        self.assertFalse(self.rbac.check_permission("viewer", "pipelines:run"))

    def test_check_permission_analyst(self):
        """Test analyst permissions (read + write)."""
        self.assertTrue(self.rbac.check_permission("analyst", "startups:read"))
        self.assertTrue(self.rbac.check_permission("analyst", "startups:write"))
        self.assertFalse(self.rbac.check_permission("analyst", "startups:delete"))
        self.assertTrue(self.rbac.check_permission("analyst", "pipelines:run"))

    def test_check_permission_admin(self):
        """Test admin permissions (full access)."""
        self.assertTrue(self.rbac.check_permission("admin", "startups:read"))
        self.assertTrue(self.rbac.check_permission("admin", "startups:write"))
        self.assertTrue(self.rbac.check_permission("admin", "startups:delete"))
        self.assertTrue(self.rbac.check_permission("admin", "system:write"))

    def test_check_permission_invalid_role(self):
        """Test that invalid roles return False."""
        self.assertFalse(self.rbac.check_permission("hacker", "startups:read"))

    def test_check_permission_invalid_permission(self):
        """Test that invalid permissions return False."""
        self.assertFalse(self.rbac.check_permission("admin", "hack:planet"))

    def test_get_permissions_viewer(self):
        """Test get all viewer permissions."""
        perms = self.rbac.get_permissions("viewer")
        self.assertIn("startups:read", perms)
        self.assertIn("news:read", perms)
        self.assertNotIn("startups:write", perms)
        self.assertNotIn("system:write", perms)

    def test_get_permissions_admin(self):
        """Test get all admin permissions."""
        perms = self.rbac.get_permissions("admin")
        self.assertIn("startups:read", perms)
        self.assertIn("startups:write", perms)
        self.assertIn("startups:delete", perms)
        self.assertIn("system:write", perms)

    def test_get_role_level(self):
        """Test role hierarchy levels."""
        self.assertEqual(self.rbac.get_role_level("viewer"), 1)
        self.assertEqual(self.rbac.get_role_level("analyst"), 2)
        self.assertEqual(self.rbac.get_role_level("admin"), 3)
        self.assertEqual(self.rbac.get_role_level("unknown"), 0)

    def test_is_higher_role(self):
        """Test role comparison."""
        self.assertTrue(self.rbac.is_higher_role("admin", "analyst"))
        self.assertTrue(self.rbac.is_higher_role("analyst", "viewer"))
        self.assertFalse(self.rbac.is_higher_role("viewer", "admin"))
        self.assertFalse(self.rbac.is_higher_role("admin", "admin"))

    def test_filter_roles_by_level(self):
        """Test filtering roles by minimum level."""
        roles = self.rbac.filter_roles_by_level(min_level=2)
        self.assertIn("analyst", roles)
        self.assertIn("admin", roles)
        self.assertNotIn("viewer", roles)

    def test_add_permission(self):
        """Test adding a custom permission."""
        self.rbac.add_permission("custom:action", ["admin", "analyst"])
        self.assertTrue(self.rbac.check_permission("admin", "custom:action"))
        self.assertTrue(self.rbac.check_permission("analyst", "custom:action"))
        self.assertFalse(self.rbac.check_permission("viewer", "custom:action"))

    def test_add_role(self):
        """Test adding a custom role."""
        self.rbac.add_role("superuser", 100)
        self.assertEqual(self.rbac.get_role_level("superuser"), 100)
        self.assertTrue(self.rbac.is_higher_role("superuser", "admin"))


if __name__ == "__main__":
    unittest.main()
