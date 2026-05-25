"""SQLite connection management with WAL mode and context manager."""

import sqlite3
import logging
from pathlib import Path

from config import get_project_root

_logger = logging.getLogger(__name__)

_connection_cache = None


def get_db_path() -> Path:
    """Return the path to the SQLite database file."""
    import os
    db_path = os.environ.get("DATABASE_PATH", "data/startup_research.db")
    path = Path(db_path)
    if not path.is_absolute():
        path = get_project_root() / path
    return path


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Get a SQLite connection with optimized settings.

    Returns a connection with WAL mode, foreign keys enabled, and
    a 5-second busy timeout. The caller is responsible for closing.

    For context manager usage:
        with get_connection() as conn:
            conn.execute(...)
    """
    if db_path is None:
        db_path = str(get_db_path())

    # Ensure parent directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    conn.row_factory = sqlite3.Row

    # Monkey-patch __exit__ for context manager support
    _original_exit = type(conn).__exit__

    def _exit(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        self.close()
        return False

    type(conn).__exit__ = _exit

    return conn
