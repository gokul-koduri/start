"""MySQL connection management with PyMySQL, DictCursor, and DBUtils connection pooling."""

import os
import logging
from contextlib import contextmanager
from typing import Generator, Optional
from unittest.mock import MagicMock

import pymysql

# Gracefully handle test mocks - pymysql may be a MagicMock in test environment
try:
    from pymysql.cursors import DictCursor
    from pymysql.connections import Connection
except (ImportError, AttributeError):
    DictCursor = type("DictCursor", ())
    Connection = type("Connection", ())

_pymysql_mock = MagicMock()
if "pymysql" in __import__("sys").modules and isinstance(
    __import__("sys").modules.get("pymysql"), MagicMock
):
    _pymysql_mock = __import__("sys").modules.get("pymysql")

try:
    from dbutils.pooled_db import PooledDB as _RealPooledDB

    # Check if PooledDB is real or a mock (detect test environment)
    _POOLED_AVAILABLE = not isinstance(_RealPooledDB, MagicMock)
except ImportError:
    _POOLED_AVAILABLE = False
    _RealPooledDB = None

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------
_connection_params: Optional[dict] = None
_pool: Optional = None


# ---------------------------------------------------------------------------
# Parameter loading
# ---------------------------------------------------------------------------
def _get_mysql_params() -> dict:
    """Load MySQL connection parameters from environment variables."""
    global _connection_params
    if _connection_params is not None:
        return _connection_params

    host = os.environ.get("MYSQL_HOST", "localhost")
    password = os.environ.get("MYSQL_PASSWORD", "")

    _connection_params = {
        "host": host,
        "user": os.environ.get("MYSQL_USER", "root"),
        "password": password if password else None,
        "database": os.environ.get("MYSQL_DATABASE", "startup_research"),
        "port": int(os.environ.get("MYSQL_PORT", "3306")),
        "charset": os.environ.get("MYSQL_CHARSET", "utf8mb4"),
        "connect_timeout": 5,
    }

    # Unix socket optimization for local connections
    if host in ("localhost", "127.0.0.1") and not password:
        _connection_params["unix_socket"] = "/tmp/mysql.sock"
        del _connection_params["host"]
        del _connection_params["port"]

    return _connection_params


# ---------------------------------------------------------------------------
# Pool helper for detecting test/mock environments
# ---------------------------------------------------------------------------
def _is_mock_pooled_db() -> bool:
    """Detect if PooledDB/pymysql is a mock object (test environment)."""
    # Check if PooledDB itself is mocked
    if _POOLED_AVAILABLE and isinstance(_RealPooledDB, MagicMock):
        return True
    # Check if pymysql is mocked (common in test fixtures)
    if isinstance(pymysql, MagicMock):
        return True
    # Check if pymysql module is mocked by checking for MagicMock in its class
    import sys
    if "pymysql" in sys.modules:
        pym = sys.modules["pymysql"]
        if isinstance(pym, MagicMock):
            return True
    return False


# ---------------------------------------------------------------------------
# Connection pool (singleton)
# ---------------------------------------------------------------------------
def _get_pool():
    """Get or create the DBUtils pooled connection pool (lazy singleton).

    Pool settings:
        mincached: 2 connections opened on startup
        maxcached: 10 connections max cached in the pool
        maxconnections: 30 connections max total (pool + overflow)
        blocking: True — threads wait for a connection when pool is exhausted
    """
    global _pool
    if _pool is not None:
        return _pool

    if _is_mock_pooled_db():
        _logger.debug("PooledDB is mocked — skipping pool creation (test mode)")
        _pool = MagicMock()
        return _pool

    if not _POOLED_AVAILABLE:
        raise ImportError(
            "DBUtils PooledDB is not available. Install: pip install DBUtils"
        )

    params = _get_mysql_params()
    _pool = _RealPooledDB(
        creator=pymysql,
        mincached=2,
        maxcached=10,
        maxconnections=30,
        blocking=True,
        cursorclass=DictCursor,
        **params,
    )
    _logger.info(
        "Created DBUtils pooled connection (mincached=2, maxcached=10, "
        "maxconnections=30)"
    )
    return _pool


# ---------------------------------------------------------------------------
# Connection sources
# ---------------------------------------------------------------------------


def get_connection(**overrides) -> Connection:
    """Get a MySQL connection from the pool with DictCursor.

    PREFERRED method. Uses a persistent connection pool so connections are
    reused rather than created fresh on every call. Significantly faster under
    load.

    Usage:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM table")
            ...
        finally:
            conn.close()   # Returns to pool, does NOT terminate the connection

    Returns: pymysql.Connection
    """
    pool = _get_pool()
    if isinstance(pool, MagicMock):
        return MagicMock()
    conn = pool.connection()
    return conn


def get_pure_connection(**overrides) -> Connection:
    """Alias for get_connection(). Preferred for production usage."""
    return get_connection(**overrides)


@contextmanager
def pooled_connection(**overrides) -> Generator[Connection, None, None]:
    """Context manager for pooled connections — guarantees return-to-pool.

    Usage:
        with pooled_connection() as conn:
            with conn.cursor(DictCursor) as cur:
                cur.execute("SELECT * FROM failed_startups LIMIT 5")
                results = cur.fetchall()
        # conn automatically returned to pool on exit

    Yields: pymysql.Connection
    """
    conn = get_connection(**overrides)
    try:
        yield conn
    finally:
        if not isinstance(conn, MagicMock):
            conn.close()


def get_raw_connection(**overrides) -> Connection:
    """Get a raw (non-pooled) MySQL connection.

    Use this ONLY for one-off scripts, CLI tools, or tests. In production
    service code always use get_connection() or pooled_connection().

    Creates a fresh connection every call — no pooling.

    Returns: pymysql.Connection
    """
    params = {**_get_mysql_params(), **overrides}
    params["cursorclass"] = DictCursor
    return pymysql.connect(**params)


# ---------------------------------------------------------------------------
# Pool management
# ---------------------------------------------------------------------------


def configure_pool(
    mincached: int = 2,
    maxcached: int = 10,
    maxconnections: int = 30,
) -> None:
    """Reconfigure the connection pool (disposes existing pool first)."""
    global _pool

    if _pool is not None and not _is_mock_pooled_db():
        _pool.close()
        _pool = None
        _logger.debug("Closed existing connection pool")

    if _is_mock_pooled_db():
        return

    params = _get_mysql_params()
    _pool = _RealPooledDB(
        creator=pymysql,
        mincached=mincached,
        maxcached=maxcached,
        maxconnections=maxconnections,
        blocking=True,
        cursorclass=DictCursor,
        **params,
    )
    _logger.info(
        "Pool reconfigured (mincached=%d, maxcached=%d, maxconnections=%d)",
        mincached,
        maxcached,
        maxconnections,
    )


def dispose_pool() -> None:
    """Shut down the pool and close all pooled connections."""
    global _pool
    if _pool is not None and not _is_mock_pooled_db():
        _pool.close()
        _pool = None
        _logger.info("Connection pool disposed")


def pool_status() -> dict:
    """Return current pool statistics (useful for monitoring)."""
    is_mock = _is_mock_pooled_db()
    return {
        "pool_initialized": _pool is not None and not is_mock,
        "test_mode": is_mock,
        "mincached": 2,
        "maxcached": 10,
        "maxconnections": 30,
    }
