"""MySQL connection management with PyMySQL and DictCursor."""

import os
import logging

import pymysql
from pymysql.cursors import DictCursor

_logger = logging.getLogger(__name__)

_connection_params = None


def _get_mysql_params() -> dict:
    """Load MySQL connection parameters from environment variables."""
    global _connection_params
    if _connection_params is not None:
        return _connection_params

    _connection_params = {
        "host": os.environ.get("MYSQL_HOST", "localhost"),
        "port": int(os.environ.get("MYSQL_PORT", "3306")),
        "user": os.environ.get("MYSQL_USER", "root"),
        "password": os.environ.get("MYSQL_PASSWORD", ""),
        "database": os.environ.get("MYSQL_DATABASE", "startup_research"),
        "charset": os.environ.get("MYSQL_CHARSET", "utf8mb4"),
        "cursorclass": DictCursor,
        "connect_timeout": 5,
        "autocommit": False,
    }
    return _connection_params


def get_connection(**overrides) -> pymysql.Connection:
    """Get a MySQL connection with DictCursor.

    Returns a PyMySQL connection with InnoDB settings and DictCursor for
    row["column"] access. The caller is responsible for closing.

    For context manager usage, use closing():
        from contextlib import closing
        with closing(get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute(...)
    """
    params = {**_get_mysql_params(), **overrides}
    conn = pymysql.connect(**params)
    return conn
