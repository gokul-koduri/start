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
    monkeypatch.setitem(sys.modules, "pymysql", mock_pymysql)
    monkeypatch.setitem(sys.modules, "pymysql.cursors", mock_pymysql.cursors)
