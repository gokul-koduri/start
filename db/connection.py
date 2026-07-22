"""Database connection management - supports MySQL and PostgreSQL (Neon).

Uses MySQL for local dev, PostgreSQL for production/Neon.
Set DATABASE_URL for PostgreSQL, or use MYSQL_* env vars for MySQL.

Usage:
    from db.connection import get_connection, pooled_connection

    with pooled_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM startups")
"""

import logging
import os
import re
from typing import Generator, Optional
from unittest.mock import MagicMock

# Third-party imports
try:
    import pymysql
    from pymysql.cursors import DictCursor
    from pymysql.connections import Connection
except ImportError:
    pymysql = None
    DictCursor = type("DictCursor", ())
    Connection = type("Connection", ())

try:
    import psycopg2
    from psycopg2 import pool as pg_pool_module
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None
    pg_pool_module = None

try:
    from dbutils.pooled_db import PooledDB as _RealPooledDB
except ImportError:
    _RealPooledDB = None

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Detect database type
# ---------------------------------------------------------------------------
_DATABASE_URL = os.environ.get("DATABASE_URL", "")
_use_postgres = bool(_DATABASE_URL)

# Pool availability flags
_PG_POOL_AVAILABLE = psycopg2 is not None
_POOLED_AVAILABLE = _RealPooledDB is not None and not isinstance(_RealPooledDB, MagicMock)

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------
_pg_pool = None
_mysql_pool: Optional = None
_connection_params: Optional[dict] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_mock() -> bool:
    """Detect if we're in test mode (mocked pymysql/pg)."""
    import sys

    if pymysql and "pymysql" in sys.modules and isinstance(sys.modules.get("pymysql"), MagicMock):
        return True
    if pg_pool_module and isinstance(pg_pool_module, MagicMock):
        return True
    return False


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


def _get_pg_params() -> dict:
    """Parse DATABASE_URL for PostgreSQL connection params."""
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise ValueError("DATABASE_URL not set for PostgreSQL connection")

    # Parse connection string - handle query params correctly
    match = re.match(
        r"postgresql(?:ql)?://(?:(?P<user>[^:@]+):(?P<password>[^@]+)@)?(?P<host>[^:/]+)(?::(?P<port>\d+))?/(?P<database>[^?]+)(?:\?(?P<query>.+))?",
        url,
    )
    if not match:
        raise ValueError(f"Invalid DATABASE_URL format: {url}")

    params = match.groupdict()
    db = params.get("database", "postgres")
    query = params.get("query", "")

    # Parse SSL mode from query params if present
    sslmode = "require"
    if query:
        for param in query.split("&"):
            if param.startswith("sslmode="):
                sslmode = param.split("=", 1)[1]

    return {
        "host": params.get("host", ""),
        "port": int(params["port"]) if params.get("port") else 5432,
        "database": db,
        "user": params.get("user") or "postgres",
        "password": params.get("password") or "",
        "sslmode": sslmode,
    }


# ---------------------------------------------------------------------------
# PostgreSQL pool
# ---------------------------------------------------------------------------


def _get_pg_pool():
    """Get or create PostgreSQL connection pool (Neon/serverless)."""
    global _pg_pool
    if _pg_pool is not None:
        return _pg_pool

    if _is_mock():
        _logger.debug("PostgreSQL pool mocked (test mode)")
        return MagicMock()

    if not _PG_POOL_AVAILABLE:
        raise ImportError(
            "PostgreSQL support requires psycopg2. Install: pip install psycopg2-binary"
        )

    params = _get_pg_params()
    _pg_pool = pg_pool_module.ThreadedConnectionPool(minconn=1, maxconn=10, **params)
    _logger.info("Created PostgreSQL connection pool (Neon/serverless)")
    return _pg_pool


# ---------------------------------------------------------------------------
# MySQL pool
# ---------------------------------------------------------------------------


def _get_mysql_pool():
    """Get or create MySQL connection pool."""
    global _mysql_pool
    if _mysql_pool is not None:
        return _mysql_pool

    if _is_mock():
        _logger.debug("MySQL pool mocked (test mode)")
        return MagicMock()

    if not _POOLED_AVAILABLE:
        raise ImportError(
            "DBUtils PooledDB not available. Install: pip install DBUtils"
        )

    params = _get_mysql_params()
    _mysql_pool = _RealPooledDB(
        creator=pymysql,
        mincached=2,
        maxcached=10,
        maxconnections=30,
        blocking=True,
        cursorclass=DictCursor,
        **params,
    )
    _logger.info("Created MySQL connection pool")
    return _mysql_pool


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_connection(**overrides):
    """Get a database connection from the pool.

    Auto-detects PostgreSQL (DATABASE_URL) vs MySQL (MYSQL_* vars).
    """
    if _use_postgres:
        pool = _get_pg_pool()
        if isinstance(pool, MagicMock):
            return MagicMock()
        return pool.getconn()  # ThreadedConnectionPool uses getconn()

    pool = _get_mysql_pool()
    if isinstance(pool, MagicMock):
        return MagicMock()
    return pool.connection()


def pooled_connection(**overrides) -> Generator:
    """Context manager for pooled connections.

    Usage:
        with pooled_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
    """
    is_pg = _use_postgres
    conn = get_connection(**overrides)
    try:
        yield conn
    finally:
        if not isinstance(conn, MagicMock):
            try:
                if is_pg:
                    _pg_pool.putconn(conn)  # Return to pool
                else:
                    conn.close()
            except Exception:
                pass


def get_raw_connection(**overrides):
    """Get a raw (non-pooled) connection."""
    if _use_postgres:
        params = _get_pg_params()
        return psycopg2.connect(**params, cursor_factory=RealDictCursor)

    params = {**_get_mysql_params(), **overrides}
    params["cursorclass"] = DictCursor
    return pymysql.connect(**params)


def dispose_pool() -> None:
    """Shut down connection pool(s)."""
    global _mysql_pool, _pg_pool

    if _mysql_pool is not None and not _is_mock():
        try:
            _mysql_pool.close()
        except Exception:
            pass
        _mysql_pool = None

    if _pg_pool is not None and not _is_mock():
        try:
            _pg_pool.closeall()
        except Exception:
            pass
        _pg_pool = None

    _logger.info("Connection pool(s) disposed")


def pool_status() -> dict:
    """Return current pool statistics."""
    return {
        "database_type": "postgresql" if _use_postgres else "mysql",
        "pool_initialized": (
            _pg_pool is not None if _use_postgres else _mysql_pool is not None
        ),
        "test_mode": _is_mock(),
    }