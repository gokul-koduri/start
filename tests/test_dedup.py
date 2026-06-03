"""Tests for database deduplication logic."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock pymysql before importing db modules
mock_pymysql = MagicMock()
sys.modules['pymysql'] = mock_pymysql
sys.modules['pymysql.cursors'] = mock_pymysql.cursors

# Ensure we get the REAL db.dedup, not a leftover mock from test_collectors
if 'db.dedup' in sys.modules and isinstance(sys.modules['db.dedup'], MagicMock):
    del sys.modules['db.dedup']
if 'db' in sys.modules and isinstance(sys.modules['db'], MagicMock):
    del sys.modules['db']
if 'db.connection' in sys.modules and isinstance(sys.modules.get('db.connection'), MagicMock):
    del sys.modules['db.connection']

from db.dedup import dedup_startup


class TestDedup:
    def test_new_startup(self):
        """A startup not in the DB should return False (not a duplicate)."""
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        conn.cursor.return_value = cursor

        result = dedup_startup(conn, "Brand New Startup", "US & Global")
        assert result is False

    def test_existing_startup(self):
        """A startup already in the DB should return True (is a duplicate)."""
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = (1,)
        conn.cursor.return_value = cursor

        result = dedup_startup(conn, "Existing Startup", "US & Global")
        assert result is True

    def test_same_name_different_region(self):
        """Same name in different region should not be a duplicate."""
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        conn.cursor.return_value = cursor

        result = dedup_startup(conn, "Some Startup", "Europe")
        assert result is False
