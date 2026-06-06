"""Tests for tenant manager."""

import unittest
from unittest.mock import patch, MagicMock, call
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestTenantManager(unittest.TestCase):
    """Test tenant management and isolation."""

    def setUp(self):
        """Set up test fixtures."""
        from auth.tenant_manager import TenantManager
        self.manager = TenantManager({"tenant_id": "default"})

    def test_current_tenant(self):
        """Test getting current tenant ID."""
        self.assertEqual(self.manager.current_tenant, "default")

    def test_switch_tenant_context(self):
        """Test switching tenant with context manager."""
        self.assertEqual(self.manager.current_tenant, "default")

        with self.manager.switch_tenant("acme-corp"):
            self.assertEqual(self.manager.current_tenant, "acme-corp")

        # Should restore after context
        self.assertEqual(self.manager.current_tenant, "default")

    def test_nested_tenant_switch(self):
        """Test nested tenant context switches."""
        self.assertEqual(self.manager.current_tenant, "default")

        with self.manager.switch_tenant("tenant-a"):
            self.assertEqual(self.manager.current_tenant, "tenant-a")
            with self.manager.switch_tenant("tenant-b"):
                self.assertEqual(self.manager.current_tenant, "tenant-b")
            self.assertEqual(self.manager.current_tenant, "tenant-a")

        self.assertEqual(self.manager.current_tenant, "default")

    def test_get_tenant_filter_row_level(self):
        """Test tenant filter generation for row-level isolation."""
        self.manager.isolation_level = "row"
        filter_clause = self.manager.get_tenant_filter("failed_startups")
        self.assertEqual(filter_clause, "tenant_id = 'default'")

        with self.manager.switch_tenant("acme"):
            filter_clause = self.manager.get_tenant_filter("news_articles")
            self.assertEqual(filter_clause, "tenant_id = 'acme'")

    def test_get_tenant_filter_schema_level(self):
        """Test tenant filter for schema-level isolation."""
        self.manager.isolation_level = "schema"
        filter_clause = self.manager.get_tenant_filter("failed_startups")
        self.assertIn("Schema isolation", filter_clause)
        self.assertIn("default_failed_startups", filter_clause)

    def test_apply_tenant_filter_simple_query(self):
        """Test applying tenant filter to simple SELECT."""
        self.manager.isolation_level = "row"
        query = "SELECT * FROM failed_startups"
        filtered = self.manager.apply_tenant_filter(query, "failed_startups")

        self.assertIn("WHERE", filtered)
        self.assertIn("tenant_id = 'default'", filtered)

    def test_apply_tenant_filter_with_existing_where(self):
        """Test applying tenant filter to query with existing WHERE."""
        self.manager.isolation_level = "row"
        query = "SELECT * FROM failed_startups WHERE year_shutdown > 2020"
        filtered = self.manager.apply_tenant_filter(query, "failed_startups")

        self.assertIn("AND tenant_id = 'default'", filtered)
        self.assertIn("year_shutdown", filtered)

    def test_apply_tenant_filter_with_group_by(self):
        """Test applying tenant filter to query with GROUP BY."""
        self.manager.isolation_level = "row"
        query = "SELECT sector, COUNT(*) FROM failed_startups GROUP BY sector"
        filtered = self.manager.apply_tenant_filter(query, "failed_startups")

        self.assertIn("WHERE tenant_id = 'default'", filtered)
        self.assertIn("GROUP BY", filtered)

    def test_check_table_access(self):
        """Test table access checking."""
        self.assertTrue(self.manager.check_table_access("failed_startups"))
        self.assertTrue(self.manager.check_table_access("news_articles"))

    def test_get_tenant_config(self):
        """Test getting tenant configuration."""
        config = self.manager.get_tenant_config()
        self.assertEqual(config["tenant_id"], "default")
        self.assertIn("features", config)

        with self.manager.switch_tenant("acme"):
            config = self.manager.get_tenant_config()
            self.assertEqual(config["tenant_id"], "acme")

    @patch("auth.tenant_manager.get_connection")
    @patch("auth.tenant_manager.schema")
    def test_list_tenants(self, mock_schema, mock_get_connection):
        """Test listing all tenants."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            {"id": 1, "name": "Default", "slug": "default", "is_active": 1},
            {"id": 2, "name": "ACME Corp", "slug": "acme", "is_active": 1},
        ]
        mock_get_connection.return_value = mock_conn

        tenants = self.manager.list_tenants()

        self.assertEqual(len(tenants), 2)
        self.assertEqual(tenants[0]["name"], "Default")
        self.assertEqual(tenants[1]["slug"], "acme")

    @patch("auth.tenant_manager.get_connection")
    @patch("auth.tenant_manager.schema")
    def test_create_tenant(self, mock_schema, mock_get_connection):
        """Test creating a new tenant."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 42
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        tenant_id = self.manager.create_tenant("New Tenant", "new-tenant", {"feature": "premium"})

        self.assertEqual(tenant_id, 42)
        mock_cursor.execute.assert_called_once()
        self.assertIn("INSERT INTO tenants", str(mock_cursor.execute.call_args))

    @patch("auth.tenant_manager.get_connection")
    @patch("auth.tenant_manager.schema")
    def test_activate_tenant(self, mock_schema, mock_get_connection):
        """Test activating a tenant."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        result = self.manager.activate_tenant(42)

        self.assertTrue(result)
        mock_cursor.execute.assert_called_once()
        call_args = str(mock_cursor.execute.call_args)
        self.assertIn("UPDATE tenants", call_args)
        self.assertIn("is_active = 1", call_args)


if __name__ == "__main__":
    unittest.main()
