"""Shared test fixtures and configuration."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(autouse=True)
def mock_pymysql(monkeypatch):
    """Auto-mock pymysql for all tests to prevent real DB connections.

    Tests that need the real dedup module should import it BEFORE
    this fixture runs, or use the explicit module cleanup pattern.
    """
    mock_pymysql = MagicMock()
    mock_pymysql.cursors = MagicMock()
    mock_pymysql.cursors.DictCursor = MagicMock
    # Required by DBUtils PooledDB
    mock_pymysql.threadsafety = 1
    mock_pymysql.paramstyle = "pyformat"

    # Mock connect function that returns a proper connection-like object
    mock_cursor = MagicMock()
    mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
    mock_cursor.__exit__ = MagicMock(return_value=False)
    mock_cursor.fetchone.return_value = None
    mock_cursor.fetchall.return_value = []

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.cursor.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.__exit__ = MagicMock(return_value=False)

    def mock_connect(*args, **kwargs):
        return mock_conn

    mock_pymysql.connect = mock_connect

    monkeypatch.setitem(sys.modules, "pymysql", mock_pymysql)
    monkeypatch.setitem(sys.modules, "pymysql.cursors", mock_pymysql.cursors)
    # Required for db/connection.py: from pymysql.connections import Connection
    mock_pymysql.connections = MagicMock()
    mock_pymysql.connections.Connection = MagicMock
    monkeypatch.setitem(sys.modules, "pymysql.connections", mock_pymysql.connections)
