"""Abstract base agent class for the research automation pipeline."""

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
class AgentResult:
    """Result of an agent execution."""

    agent_name: str
    status: str = "pending"  # pending, running, success, partial, failed
    started_at: str | None = None
    completed_at: str | None = None
    data: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    upstream_results: list = field(default_factory=list)  # list[AgentResult]


class BaseAgent(ABC):
    """Abstract base class that all agents inherit from.

    Subclasses must implement:
        - execute(upstream_results) -> AgentResult
        - name property

    The base class manages:
        - Timing and status tracking
        - Error handling and logging
        - agent_runs audit trail in the database
        - Configuration-driven enable/disable
    """

    def __init__(self, config: dict | None = None, dry_run: bool = False):
        self.config = config or {}
        self.dry_run = dry_run

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name for this agent (used in logging and agent_runs)."""
        ...

    @property
    def enabled(self) -> bool:
        """Check if this agent is enabled in config."""
        return self.config.get("enabled", True)

    @abstractmethod
    def execute(self, upstream_results: list | None = None) -> AgentResult:
        """Execute the agent's main logic.

        Args:
            upstream_results: Results from previous agents in the pipeline.

        Returns:
            AgentResult with status, data, and any errors.
        """
        ...

    def run(self, upstream_results: list | None = None) -> AgentResult:
        """Execute the full agent lifecycle.

        Wraps execute() with:
        1. Timing (started_at, completed_at)
        2. Error handling (catches exceptions, marks as failed)
        3. Logging (start/complete messages)
        4. Database audit trail (agent_runs table)
        """
        if not self.enabled:
            _logger.info("%s: Skipping (disabled in config)", self.name)
            return AgentResult(
                agent_name=self.name,
                status="success",
                data={"skipped": True, "reason": "disabled"},
            )

        _logger.info("=== %s: Starting ===", self.name)

        result = AgentResult(
            agent_name=self.name,
            status="running",
            upstream_results=upstream_results or [],
        )
        result.started_at = datetime.now(timezone.utc).isoformat()

        try:
            conn = get_connection()
            schema.init_schema(conn)
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO agent_runs
                   (pipeline_name, agent_name, started_at, status, trigger_type)
                   VALUES (%s, %s, %s, 'running', %s)""",
                (
                    self.config.get("_pipeline_name", "manual"),
                    self.name,
                    result.started_at,
                    "manual" if not self.config.get("_scheduled") else "scheduled",
                ),
            )
            run_id = cursor.lastrowid
            conn.commit()
            cursor.close()
        except Exception:
            run_id = None
            conn = None

        try:
            result = self.execute(upstream_results)
            result.agent_name = self.name
            if result.status not in ("failed", "partial"):
                result.status = result.status or "success"
        except Exception as e:
            tb = traceback.format_exc()
            _logger.error("%s: Unhandled exception: %s\n%s", self.name, e, tb)
            result = AgentResult(
                agent_name=self.name,
                status="failed",
                errors=[f"{e}\n{tb}"],
                upstream_results=upstream_results or [],
            )
        finally:
            result.started_at = (
                result.started_at or datetime.now(timezone.utc).isoformat()
            )
            result.completed_at = datetime.now(timezone.utc).isoformat()

            # Update agent_runs record
            if run_id and conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        """UPDATE agent_runs
                           SET completed_at = %s, status = %s,
                               records_affected = %s, error_message = %s,
                               result_data = %s
                           WHERE id = %s""",
                        (
                            result.completed_at,
                            result.status,
                            result.data.get("records_affected", 0),
                            "; ".join(result.errors[:5]) if result.errors else None,
                            json.dumps(result.data, default=str)[:5000],
                            run_id,
                        ),
                    )
                    conn.commit()
                    cursor.close()
                except Exception:
                    pass
                finally:
                    conn.close()

        _logger.info(
            "=== %s: %s (errors=%d) ===",
            self.name,
            result.status,
            len(result.errors),
        )
        return result
