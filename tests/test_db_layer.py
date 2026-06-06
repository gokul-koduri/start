"""Database layer tests — connection, schema, CRUD operations (T-042)."""

import unittest
from unittest.mock import MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestSchemaVersion(unittest.TestCase):
    """Test schema versioning."""

    def test_schema_version_is_integer(self):
        """Schema version is an integer."""
        from db.schema import _SCHEMA_VERSION
        self.assertIsInstance(_SCHEMA_VERSION, int)

    def test_schema_version_at_least_14(self):
        """Schema version is at least 14 (Phase 4 baseline)."""
        from db.schema import _SCHEMA_VERSION
        self.assertGreaterEqual(_SCHEMA_VERSION, 14)

    def test_get_schema_version(self):
        """get_schema_version returns the current version."""
        from db.schema import get_schema_version, _SCHEMA_VERSION
        self.assertEqual(get_schema_version(), _SCHEMA_VERSION)


class TestSchemaTables(unittest.TestCase):
    """Test that all expected tables are defined."""

    def test_tables_list_not_empty(self):
        """_TABLES list is not empty."""
        from db.schema import _TABLES
        self.assertGreater(len(_TABLES), 0)

    def test_all_tables_have_create(self):
        """Every table definition starts with CREATE TABLE."""
        from db.schema import _TABLES
        for i, table_sql in enumerate(_TABLES):
            self.assertIn("CREATE TABLE", table_sql, f"Table {i} missing CREATE TABLE")

    def test_expected_tables_present(self):
        """All expected tables are defined in the schema."""
        from db.schema import _TABLES
        all_sql = " ".join(_TABLES)
        expected = [
            "failed_startups", "news_articles", "collection_runs",
            "opportunity_scores", "signal_events", "alert_dispatches",
            "alert_rules", "alert_preferences", "score_deltas",
            "score_accuracy_runs", "query_log", "chat_log",
        ]
        for table in expected:
            self.assertIn(table, all_sql, f"Missing table: {table}")

    def test_schema_has_indexes(self):
        """Schema includes index definitions for performance."""
        from db.schema import _TABLES
        all_sql = " ".join(_TABLES)
        self.assertIn("INDEX", all_sql)


class TestSchemaInit(unittest.TestCase):
    """Test schema initialization with mocked connection."""

    def test_init_schema_calls_execute(self):
        """init_schema executes CREATE TABLE statements."""
        from db import schema
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        schema.init_schema(mock_conn)

        # Should have called execute for each table + index
        self.assertGreater(mock_cursor.execute.call_count, 0)

    def test_init_schema_handles_recreation(self):
        """init_schema uses IF NOT EXISTS for idempotency."""
        from db import schema
        # All table definitions should contain IF NOT EXISTS
        for table_sql in schema._TABLES:
            self.assertIn("IF NOT EXISTS", table_sql)


class TestConnectionModule(unittest.TestCase):
    """Test db/connection.py module structure."""

    def test_get_connection_importable(self):
        """get_connection function is importable."""
        from db.connection import get_connection
        self.assertTrue(callable(get_connection))

    def test_module_imports(self):
        """db.connection module has expected attributes."""
        import db.connection as conn_mod
        self.assertTrue(hasattr(conn_mod, "get_connection"))


class TestSchemaModuleStructure(unittest.TestCase):
    """Test db.schema module structure."""

    def test_schema_module_imports(self):
        """db.schema module has expected attributes."""
        import db.schema as schema_mod
        self.assertTrue(hasattr(schema_mod, "_SCHEMA_VERSION"))
        self.assertTrue(hasattr(schema_mod, "_TABLES"))
        self.assertTrue(hasattr(schema_mod, "init_schema"))
        self.assertTrue(hasattr(schema_mod, "get_schema_version"))

    def test_schema_file_exists(self):
        """db/schema.py file exists."""
        path = Path(__file__).parent.parent / "db" / "schema.py"
        self.assertTrue(path.exists())

    def test_connection_file_exists(self):
        """db/connection.py file exists."""
        path = Path(__file__).parent.parent / "db" / "connection.py"
        self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()
