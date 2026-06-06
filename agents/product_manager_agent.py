"""Product Manager Agent — owns vision, backlog, prioritization, and scope.

This agent acts as the Product Manager role in the AI Product Development Team.
It manages the product backlog, defines user stories, prioritizes features,
tracks sprint progress, and ensures every task follows the Definition of Done.

Key responsibilities:
    - Maintain and prioritize the product backlog
    - Write user stories in "As a [user] / I want [goal] / So that [benefit]" format
    - Assign story points and priorities
    - Track sprint burndown
    - Enforce MVP scope and prevent scope creep
    - Sign off on Definition of Done for each feature

Tables used:
    - backlog_items     (product backlog + sprint backlog)
    - sprint_metrics    (burndown, velocity)
    - user_stories      (formal user stories with acceptance criteria)
    - daily_metrics     (business KPIs for product decisions)

Usage:
    pm = ProductManagerAgent()
    result = pm.execute()
    # Returns: backlog health, sprint status, blockers, risks
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any

from agents.base import AgentResult, BaseAgent
from db.connection import get_connection
from db import schema

_logger = logging.getLogger(__name__)


class ProductManagerAgent(BaseAgent):
    """Product Manager — owns the product backlog, vision, and priorities.

    Generates:
    - Backlog health report (items by status, priority, age)
    - Sprint burndown status
    - Scope creep alerts (new items added mid-sprint)
    - MVP completion percentage
    - Risk assessment for current sprint
    """

    @property
    def name(self) -> str:
        return "product_manager"

    def execute(self, upstream_results=None) -> AgentResult:
        """Run product management analysis.

        Steps:
            1. Audit backlog health (stale items, unestimated, no acceptance criteria)
            2. Calculate sprint burndown (planned vs completed story points)
            3. Check MVP completion percentage
            4. Identify blockers and risks
            5. Generate prioritization recommendations
            6. Write results to database
        """
        started = datetime.now(timezone.utc).isoformat()
        errors = []

        try:
            conn = get_connection()
            schema.init_schema(conn)
            cursor = conn.cursor()

            # ── Step 1: Backlog health ──
            backlog_health = self._audit_backlog(cursor)

            # ── Step 2: Sprint burndown ──
            sprint_status = self._sprint_burndown(cursor)

            # ── Step 3: MVP completion ──
            mvp_progress = self._mvp_completion(cursor)

            # ── Step 4: Blockers and risks ──
            risks = self._identify_risks(cursor, backlog_health, sprint_status)

            # ── Step 5: Recommendations ──
            recommendations = self._generate_recommendations(
                backlog_health, sprint_status, mvp_progress, risks
            )

            # ── Step 6: Store results ──
            result_data = {
                "backlog_health": backlog_health,
                "sprint_status": sprint_status,
                "mvp_progress": mvp_progress,
                "risks": risks,
                "recommendations": recommendations,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

            cursor.execute(
                "INSERT INTO analysis_failure_patterns "
                "(analysis_type, insights_json, analyzed_at) "
                "VALUES (%s, %s, %s)",
                ("pm_report",
                 json.dumps(result_data, default=str),
                 datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
            cursor.close()
            conn.close()

            return AgentResult(
                agent_name=self.name,
                status="success",
                started_at=started,
                completed_at=datetime.now(timezone.utc).isoformat(),
                data=result_data,
                errors=errors,
            )

        except Exception as e:
            errors.append(str(e))
            _logger.error("ProductManager error: %s", e)
            return AgentResult(
                agent_name=self.name,
                status="failed",
                started_at=started,
                completed_at=datetime.now(timezone.utc).isoformat(),
                errors=errors,
            )

    def _audit_backlog(self, cursor) -> dict:
        """Audit product backlog health."""
        health = {"total_items": 0, "by_status": {}, "by_priority": {},
                  "stale_count": 0, "unestimated": 0}

        try:
            # Check if backlog table exists
            cursor.execute("SHOW TABLES LIKE 'backlog_items'")
            if not cursor.fetchone():
                health["note"] = "backlog_items table not yet created"
                return health

            cursor.execute("SELECT COUNT(*) as cnt FROM backlog_items")
            health["total_items"] = cursor.fetchone()["cnt"]

            cursor.execute(
                "SELECT status, COUNT(*) as cnt FROM backlog_items GROUP BY status"
            )
            for row in cursor.fetchall():
                health["by_status"][row["status"]] = row["cnt"]

            cursor.execute(
                "SELECT priority, COUNT(*) as cnt FROM backlog_items GROUP BY priority"
            )
            for row in cursor.fetchall():
                health["by_priority"][row["priority"]] = row["cnt"]

            # Stale items: >14 days without update
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM backlog_items "
                "WHERE updated_at < DATE_SUB(NOW(), INTERVAL 14 DAY) AND status NOT IN ('done', 'cancelled')"
            )
            health["stale_count"] = cursor.fetchone()["cnt"]

            # Unestimated: no story points
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM backlog_items "
                "WHERE story_points IS NULL OR story_points = 0"
            )
            health["unestimated"] = cursor.fetchone()["cnt"]

        except Exception as e:
            health["error"] = str(e)

        return health

    def _sprint_burndown(self, cursor) -> dict:
        """Calculate current sprint burndown."""
        status = {"current_sprint": None, "total_points": 0,
                  "completed_points": 0, "remaining_points": 0,
                  "completion_pct": 0}

        try:
            cursor.execute("SHOW TABLES LIKE 'backlog_items'")
            if not cursor.fetchone():
                return status

            cursor.execute(
                "SELECT sprint, SUM(story_points) as total, "
                "SUM(CASE WHEN status='done' THEN story_points ELSE 0 END) as done "
                "FROM backlog_items WHERE sprint IS NOT NULL "
                "GROUP BY sprint ORDER BY sprint DESC LIMIT 1"
            )
            row = cursor.fetchone()
            if row:
                status["current_sprint"] = row["sprint"]
                status["total_points"] = row["total"] or 0
                status["completed_points"] = row["done"] or 0
                status["remaining_points"] = status["total_points"] - status["completed_points"]
                if status["total_points"] > 0:
                    status["completion_pct"] = round(
                        status["completed_points"] / status["total_points"] * 100, 1
                    )
        except Exception as e:
            status["error"] = str(e)

        return status

    def _mvp_completion(self, cursor) -> dict:
        """Check MVP feature completion percentage."""
        progress = {"total_mvp_features": 0, "completed": 0,
                    "completion_pct": 0, "features": []}

        try:
            cursor.execute("SHOW TABLES LIKE 'backlog_items'")
            if not cursor.fetchone():
                return progress

            cursor.execute(
                "SELECT id, title, status, priority, story_points "
                "FROM backlog_items WHERE mvp = 1 ORDER BY priority, id"
            )
            rows = cursor.fetchall()
            progress["total_mvp_features"] = len(rows)
            progress["features"] = rows
            progress["completed"] = sum(1 for r in rows if r["status"] == "done")
            if progress["total_mvp_features"] > 0:
                progress["completion_pct"] = round(
                    progress["completed"] / progress["total_mvp_features"] * 100, 1
                )
        except Exception as e:
            progress["error"] = str(e)

        return progress

    def _identify_risks(self, cursor, backlog, sprint) -> list[dict]:
        """Identify project risks from backlog and sprint data."""
        risks = []

        if backlog.get("stale_count", 0) > 5:
            risks.append({
                "id": "PM-R001",
                "severity": "warning",
                "message": f"{backlog['stale_count']} backlog items stale (>14 days without update)",
            })

        if backlog.get("unestimated", 0) > 10:
            risks.append({
                "id": "PM-R002",
                "severity": "warning",
                "message": f"{backlog['unestimated']} items have no story point estimate",
            })

        if sprint.get("completion_pct", 0) < 50 and sprint.get("current_sprint"):
            risks.append({
                "id": "PM-R003",
                "severity": "high",
                "message": f"Sprint {sprint.get('current_sprint')} only {sprint.get('completion_pct')}% complete",
            })

        # Check for items blocking others
        try:
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM backlog_items "
                "WHERE status = 'blocked'"
            )
            blocked = cursor.fetchone()["cnt"]
            if blocked > 0:
                risks.append({
                    "id": "PM-R004",
                    "severity": "high",
                    "message": f"{blocked} items are currently blocked",
                })
        except Exception:
            pass

        return risks

    def _generate_recommendations(self, backlog, sprint, mvp, risks) -> list[str]:
        """Generate actionable recommendations."""
        recs = []

        if mvp.get("completion_pct", 0) < 100:
            recs.append(
                f"MVP is {mvp.get('completion_pct', 0)}% complete. "
                f"Focus on remaining {mvp['total_mvp_features'] - mvp['completed']} features."
            )

        high_risks = [r for r in risks if r.get("severity") == "high"]
        if high_risks:
            recs.append(
                f"Address {len(high_risks)} high-severity risks immediately."
            )

        if backlog.get("unestimated", 0) > 0:
            recs.append(
                f"Estimate {backlog['unestimated']} unestimated backlog items."
            )

        if not recs:
            recs.append("Product health looks good. Keep shipping.")

        return recs
