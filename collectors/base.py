"""Abstract base collector class for all data collectors."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import logging
import traceback

from db.connection import get_connection
from db import schema

_logger = logging.getLogger(__name__)


@dataclass
class CollectionResult:
    """Result of a collection run."""
    collector_name: str
    records_collected: int = 0
    records_inserted: int = 0
    records_skipped: int = 0
    errors: list[str] = field(default_factory=list)
    status: str = "success"  # success, partial, failed


class BaseCollector(ABC):
    """Abstract base class that all collectors inherit from.

    Subclasses must implement:
        - collect() -> CollectionResult
        - name property

    The base class manages:
        - Database connection and schema initialization
        - collection_runs audit trail (start/update/end)
        - Error handling and logging
    """

    def __init__(self, config: dict | None = None, dry_run: bool = False):
        self.config = config or {}
        self.dry_run = dry_run
        self._run_id = None

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name for this collector (used in collection_runs and logging)."""
        ...

    @abstractmethod
    def collect(self, conn) -> CollectionResult:
        """Collect data and return results.

        This is the main method subclasses implement. The base class
        wraps it with error handling, logging, and run tracking.

        Args:
            conn: Active database connection.

        Returns:
            CollectionResult with counts and status.
        """
        ...

    def run(self) -> CollectionResult:
        """Execute the full collection lifecycle.

        1. Open DB connection
        2. Ensure schema exists
        3. Insert 'running' into collection_runs
        4. Call collect()
        5. Update collection_runs with final status
        """
        _logger.info("=== %s: Starting collection ===", self.name)

        try:
            conn = get_connection()
            schema.init_schema(conn)
        except Exception as e:
            _logger.critical("%s: Cannot connect to database: %s", self.name, e)
            return CollectionResult(
                collector_name=self.name,
                status="failed",
                errors=[f"Database connection failed: {e}"],
            )

        try:
            # Insert running record
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO collection_runs (collector_name, started_at, status, parameters) VALUES (%s, %s, 'running', %s)",
                (self.name, datetime.now(timezone.utc).isoformat(), json.dumps({})),
            )
            self._run_id = cursor.lastrowid
            cursor.close()
            conn.commit()

            # Run the actual collection
            result = self.collect(conn)

            # Update run record
            status = result.status
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE collection_runs
                   SET completed_at = %s, status = %s,
                       records_collected = %s, records_deduped = %s,
                       error_message = %s
                   WHERE id = %s""",
                (
                    datetime.now(timezone.utc).isoformat(),
                    status,
                    result.records_collected,
                    result.records_skipped,
                    "; ".join(result.errors[:5]) if result.errors else None,
                    self._run_id,
                ),
            )
            cursor.close()
            conn.commit()

            _logger.info(
                "=== %s: Complete — %d collected, %d inserted, %d skipped, status=%s ===",
                self.name, result.records_collected, result.records_inserted,
                result.records_skipped, status,
            )
            return result

        except Exception as e:
            tb = traceback.format_exc()
            _logger.error("%s: Unhandled exception: %s\n%s", self.name, e, tb)

            # Update run record as failed
            if self._run_id:
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        """UPDATE collection_runs
                           SET completed_at = %s, status = 'failed', error_message = %s
                           WHERE id = %s""",
                        (datetime.now(timezone.utc).isoformat(), f"{e}\n{tb}", self._run_id),
                    )
                    cursor.close()
                    conn.commit()
                except Exception:
                    pass

            return CollectionResult(
                collector_name=self.name,
                status="failed",
                errors=[str(e)],
            )
        finally:
            conn.close()

    def get_last_run_time(self, conn) -> datetime | None:
        """Get the timestamp of the last successful run for this collector."""
        cursor = conn.cursor()
        cursor.execute(
            "SELECT started_at FROM collection_runs WHERE collector_name = %s AND status IN ('success', 'partial') ORDER BY started_at DESC LIMIT 1",
            (self.name,),
        )
        row = cursor.fetchone()
        cursor.close()
        if row:
            try:
                return datetime.fromisoformat(row["started_at"])
            except (ValueError, TypeError):
                return None
        return None
