"""
Sprint Execution Cycle Agent — Continuous Claude ↔ Codex Loop

This agent implements a never-ending SCAN → PLAN (Codex) → APPROVE → EXECUTE cycle
that continuously identifies opportunities, plans via Codex, and executes tasks.

Architecture:
    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────────┐
    │  SCAN   │───▶│  PLAN   │───▶│ APPROVE │───▶│  EXECUTE    │
    │ (Opps)  │    │(Codex)  │    │(Hybrid) │    │  (Tasks)    │
    └─────────┘    └─────────┘    └─────────┘    └─────────────┘
         │                                               │
         └───────────────────────────────────────────────┘
                      (Repeat forever)

Usage:
    python run_agent.py --pipeline sprint-cycle  # Run continuous cycle
    python -m agents.cycle_agent --once           # Run one cycle only
    python -m agents.cycle_agent --daemon         # Run as daemon

Configuration in config/settings.yaml:
    sprint_cycle:
        enabled: true
        scan_interval_seconds: 300
        thresholds:
            auto_approve_score: 40
            auto_approve_effort_min: 30
"""

import json
import logging
import signal
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agents.base import AgentResult, BaseAgent
from db.connection import get_connection

_logger = logging.getLogger(__name__)

# Threshold constants
AUTO_APPROVE_SCORE_THRESHOLD = 40
AUTO_APPROVE_EFFORT_MINUTES = 30
DEFAULT_SCAN_INTERVAL = 300  # 5 minutes


class CycleAgent(BaseAgent):
    """Continuous cycle agent that scans, plans, approves, and executes.

    The agent follows this loop:
    1. SCAN: Find new opportunities from the opportunity pipeline
    2. PLAN: Generate implementation plan via Codex/Plan Agent
    3. APPROVE: Auto-approve minor tasks, queue major for human approval
    4. EXECUTE: Run approved tasks
    5. Repeat
    """

    def __init__(self, config: dict | None = None, dry_run: bool = False):
        super().__init__(config, dry_run)
        self.scan_interval = config.get("scan_interval_seconds", DEFAULT_SCAN_INTERVAL)
        self.auto_approve_score = config.get("auto_approve_score", AUTO_APPROVE_SCORE_THRESHOLD)
        self.auto_approve_effort = config.get("auto_approve_effort_min", AUTO_APPROVE_EFFORT_MINUTES)
        self._shutdown_requested = False

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    @property
    def name(self) -> str:
        return "cycle_agent"

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        _logger.info("Shutdown signal received, finishing current cycle...")
        self._shutdown_requested = True

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        """Execute one cycle of the loop."""
        cycle_id = str(uuid.uuid4())[:8]
        started_at = datetime.now(timezone.utc).isoformat()
        _logger.info("=== Cycle %s STARTED ===", cycle_id)

        tasks_processed = 0
        tasks_auto_approved = 0
        tasks_pending_approval = 0
        errors = []

        try:
            # Step 1: Scan for opportunities
            opportunities = self.scan_opportunities()
            _logger.info("Cycle %s: Found %d opportunities", cycle_id, len(opportunities))

            for opp in opportunities:
                if self._shutdown_requested:
                    _logger.info("Shutdown requested, stopping cycle")
                    break

                try:
                    # Step 2: Plan via Codex
                    plan = self.plan_via_codex(opp)
                    if not plan:
                        _logger.warning("Cycle %s: No plan generated for opportunity %s",
                                        cycle_id, opp.get("title", "unknown"))
                        continue

                    # Step 3: Determine approval path
                    if self.is_minor_task(opp, plan):
                        self.execute_task(opp, plan)
                        tasks_auto_approved += 1
                    else:
                        self.queue_for_approval(opp, plan)
                        tasks_pending_approval += 1

                    # Step 4: Check pending approvals and execute if ready
                    self.process_pending_approvals()
                    tasks_processed += 1

                    # Log to audit trail
                    self.log_audit(cycle_id, opp, "processed", {
                        "auto_approved": tasks_auto_approved > 0,
                        "pending_approval": tasks_pending_approval > 0,
                    })

                except Exception as e:
                    _logger.error("Cycle %s: Error processing opportunity: %s", cycle_id, e)
                    errors.append(str(e))

        except Exception as e:
            _logger.error("Cycle %s: Fatal error: %s", cycle_id, e)
            errors.append(str(e))

        completed_at = datetime.now(timezone.utc).isoformat()

        return AgentResult(
            agent_name=self.name,
            status="success" if not errors else "partial",
            started_at=started_at,
            completed_at=completed_at,
            data={
                "cycle_id": cycle_id,
                "tasks_processed": tasks_processed,
                "tasks_auto_approved": tasks_auto_approved,
                "tasks_pending_approval": tasks_pending_approval,
            },
            errors=errors if errors else [],
        )

    def run_continuous(self):
        """Run the cycle continuously until shutdown is requested."""
        _logger.info("Starting continuous cycle loop (interval: %ds)", self.scan_interval)
        _logger.info("Press Ctrl+C to stop gracefully")

        while not self._shutdown_requested:
            self.run()
            if not self._shutdown_requested:
                _logger.info("Sleeping for %d seconds...", self.scan_interval)
                for _ in range(self.scan_interval):
                    if self._shutdown_requested:
                        break
                    time.sleep(1)

        _logger.info("Cycle loop stopped gracefully")

    # ─── SCAN PHASE ───────────────────────────────────────────────────────────

    def scan_opportunities(self) -> list[dict[str, Any]]:
        """Scan for new opportunities to process.

        Returns:
            List of opportunity dicts with at least: id, title, description, opportunity_score
        """
        opportunities = []

        try:
            conn = get_connection()
            cursor = conn.cursor()

            # Query high-scoring opportunities that haven't been processed yet
            query = """
                SELECT
                    mo.id,
                    mo.title,
                    mo.description,
                    mo.opportunity_score,
                    mo.confidence_score,
                    mo.sector,
                    mo.sub_sector
                FROM manufacturing_opportunities mo
                LEFT JOIN sprint_tasks st ON st.related_opp_id = mo.id
                WHERE mo.status = 'active'
                  AND mo.opportunity_score >= 30
                  AND st.id IS NULL
                ORDER BY mo.opportunity_score DESC, mo.created_at DESC
                LIMIT 10
            """
            cursor.execute(query)
            results = cursor.fetchall()
            cursor.close()
            conn.close()

            for row in results:
                # Results are Dicts (DictCursor) - access by key
                opportunities.append({
                    "id": row["id"],
                    "title": row["title"],
                    "description": row["description"],
                    "opportunity_score": row["opportunity_score"] or 0,
                    "confidence_score": row["confidence_score"] or 0.5,
                    "sector": row["sector"],
                    "sub_sector": row["sub_sector"],
                })

        except Exception as e:
            _logger.error("Error scanning opportunities: %s", e)

        return opportunities

    # ─── PLAN PHASE (Codex) ──────────────────────────────────────────────────

    def plan_via_codex(self, opportunity: dict) -> dict | None:
        """Generate implementation plan via Codex/Plan Agent.

        Args:
            opportunity: Dict with title, description, etc.

        Returns:
            Plan dict with steps, files, effort estimate, or None on failure
        """
        _logger.info("Planning for: %s", opportunity.get("title", "unknown"))

        try:
            # Construct plan prompt for Codex
            prompt = f"""Create an implementation plan for the following opportunity:

Title: {opportunity.get('title', 'N/A')}
Description: {opportunity.get('description', 'N/A')}
Sector: {opportunity.get('sector', 'N/A')}
Opportunity Score: {opportunity.get('opportunity_score', 0)}
Confidence: {opportunity.get('confidence_score', 0.5)}

Generate a structured plan with:
1. Implementation steps (numbered list)
2. Estimated effort in minutes
3. Critical files to create/modify
4. Dependencies
5. Risks and mitigation
6. Validation criteria

Return as JSON with keys: steps (array), estimated_minutes (int),
critical_files (array), dependencies (array), risks (array), validation (array)
"""

            # TODO: Integrate with actual Codex/Plan Agent when available
            # For now, generate a simple plan structure
            plan = self._generate_fallback_plan(opportunity)
            return plan

        except Exception as e:
            _logger.error("Error planning via Codex: %s", e)
            return None

    def _generate_fallback_plan(self, opportunity: dict) -> dict:
        """Generate a simple fallback plan when Codex isn't available."""
        title = opportunity.get("title", "Untitled")
        score = opportunity.get("opportunity_score", 50)

        # Estimate effort based on score (higher score = bigger task)
        if score >= 70:
            estimated_minutes = 120  # 2 hours
        elif score >= 50:
            estimated_minutes = 60   # 1 hour
        else:
            estimated_minutes = 30  # 30 minutes

        return {
            "steps": [
                f"Analyze {title} opportunity",
                "Create implementation plan document",
                "Implement changes",
                "Validate and test",
            ],
            "estimated_minutes": estimated_minutes,
            "critical_files": [
                "docs/plans/TEMPLATE.md",
            ],
            "dependencies": [],
            "risks": [
                "Scope may change during implementation",
            ],
            "validation": [
                "All tests pass",
                "Documentation updated",
            ],
        }

    # ─── APPROVE PHASE ────────────────────────────────────────────────────────

    def is_minor_task(self, opportunity: dict, plan: dict) -> bool:
        """Determine if this is a minor task (auto-approve) or major (require approval).

        Rules:
        - Minor if: score < threshold AND effort < effort_threshold
        - Major if: score >= threshold OR effort >= effort_threshold
        """
        score = opportunity.get("opportunity_score", 0)
        effort = plan.get("estimated_minutes", 60)

        # Minor if BOTH conditions are met
        is_minor = score < self.auto_approve_score and effort < self.auto_approve_effort

        _logger.info(
            "Task classification: score=%d (<%d?), effort=%d (<%d?) → %s",
            score, self.auto_approve_score,
            effort, self.auto_approve_effort,
            "MINOR (auto)" if is_minor else "MAJOR (approval required)"
        )

        return is_minor

    def queue_for_approval(self, opportunity: dict, plan: dict):
        """Queue a task for human approval."""
        _logger.info("Queuing for approval: %s", opportunity.get("title"))

        try:
            conn = get_connection()
            cursor = conn.cursor()

            # Generate task ID
            cursor.execute("SELECT COUNT(*) as cnt FROM sprint_tasks")
            result = cursor.fetchone()
            count = result["cnt"] if isinstance(result, dict) else result[0]
            task_id = f"SPRINT-2026-{count + 1:03d}"

            # Insert sprint task
            cursor.execute("""
                INSERT INTO sprint_tasks
                (task_id, title, description, task_type, opportunity_score,
                 task_effort_minutes, state, plan_document, source, related_opp_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                task_id,
                opportunity.get("title"),
                opportunity.get("description"),
                "feature",
                opportunity.get("opportunity_score"),
                plan.get("estimated_minutes", 60),
                "planned",
                json.dumps(plan),
                "opportunity_pipeline",
                opportunity.get("id"),
            ))

            task_db_id = cursor.lastrowid

            # Create pending approval record
            cursor.execute("""
                INSERT INTO pending_approvals
                (sprint_task_id, approval_type, request_summary, plan_preview, expires_at)
                VALUES (%s, %s, %s, %s, DATE_ADD(NOW(), INTERVAL 24 HOUR))
            """, (
                task_db_id,
                "major_task",
                f"Approval needed for: {opportunity.get('title')}",
                json.dumps(plan)[:1000],
            ))

            conn.commit()
            cursor.close()
            conn.close()

            _logger.info("Task %s queued for approval", task_id)

        except Exception as e:
            _logger.error("Error queueing for approval: %s", e)

    def process_pending_approvals(self):
        """Process any tasks that have been approved and are ready to execute."""
        # TODO: Check for approval responses and execute approved tasks
        pass

    # ─── EXECUTE PHASE ───────────────────────────────────────────────────────

    def execute_task(self, opportunity: dict, plan: dict):
        """Execute an approved/auto-approved task."""
        _logger.info("Executing: %s", opportunity.get("title"))

        try:
            # Create plan document
            plan_file = self.create_plan_document(opportunity, plan)

            # Log execution
            _logger.info("Task completed: %s", opportunity.get("title"))
            _logger.info("Plan saved to: %s", plan_file)

        except Exception as e:
            _logger.error("Error executing task: %s", e)

    def create_plan_document(self, opportunity: dict, plan: dict) -> Path:
        """Create a plan document in docs/plans/.

        Returns:
            Path to the created plan file
        """
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        title_slug = opportunity.get("title", "unknown")[:50].lower().replace(" ", "-")
        filename = f"{today}-{title_slug}.md"
        plan_path = Path("docs/plans") / filename

        # Ensure directory exists
        plan_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate plan content
        content = f"""# Plan: {opportunity.get('title', 'Untitled')}

**Created:** {today}
**Status:** APPROVED
**Type:** Auto-generated from Opportunity Pipeline
**Source:** manufacturing_opportunities.id={opportunity.get('id')}

---

## Context

### Opportunity
- **Title:** {opportunity.get('title', 'N/A')}
- **Sector:** {opportunity.get('sector', 'N/A')}
- **Opportunity Score:** {opportunity.get('opportunity_score', 'N/A')}
- **Confidence:** {opportunity.get('confidence_score', 'N/A')}

### Description
{opportunity.get('description', 'No description provided.')}

---

## Implementation Plan

### Estimated Effort
{plan.get('estimated_minutes', 'N/A')} minutes

### Steps
"""

        for i, step in enumerate(plan.get("steps", []), 1):
            content += f"{i}. {step}\n"

        content += """

### Critical Files
"""
        for f in plan.get("critical_files", []):
            content += f"- `{f}`\n"

        content += """

### Dependencies
"""
        for dep in plan.get("dependencies", []):
            content += f"- {dep}\n"

        content += """

### Risks
"""
        for risk in plan.get("risks", []):
            content += f"- {risk}\n"

        content += """

### Validation
"""
        for val in plan.get("validation", []):
            content += f"- {val}\n"

        content += """

---

## Approval

| Reviewer | Status | Date | Notes |
|----------|--------|------|-------|
| CycleAgent | AUTO-APPROVED | {} | Auto-approved (minor task) |

*This plan was auto-generated by the Sprint Cycle Agent*
""".format(datetime.now(timezone.utc).strftime("%Y-%m-%d"))

        # Write file
        plan_path.write_text(content)
        return plan_path

    # ─── AUDIT LOGGING ───────────────────────────────────────────────────────

    def log_audit(self, cycle_id: str, opportunity: dict, action: str, details: dict):
        """Log an audit entry for this cycle."""
        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO cycle_audit_log
                (cycle_id, action, opportunity_data, details_json)
                VALUES (%s, %s, %s, %s)
            """, (
                cycle_id,
                action,
                json.dumps({
                    "id": opportunity.get("id"),
                    "title": opportunity.get("title"),
                    "score": opportunity.get("opportunity_score"),
                }),
                json.dumps(details),
            ))

            conn.commit()
            cursor.close()
            conn.close()

        except Exception as e:
            _logger.error("Error logging audit: %s", e)


def run_daemon(config: dict | None = None):
    """Run the cycle agent as a continuous daemon."""
    agent = CycleAgent(config)
    agent.run_continuous()


def run_once(config: dict | None = None):
    """Run a single cycle."""
    agent = CycleAgent(config)
    return agent.run()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Sprint Cycle Agent")
    parser.add_argument("--daemon", action="store_true", help="Run as continuous daemon")
    parser.add_argument("--once", action="store_true", help="Run a single cycle")
    parser.add_argument("--config", type=str, help="Path to config file")
    args = parser.parse_args()

    # Load config
    config = {}
    if args.config:
        config = json.loads(Path(args.config).read_text())

    if args.daemon:
        run_daemon(config)
    elif args.once:
        result = run_once(config)
        print(f"Cycle completed: {result}")
    else:
        # Default: run once
        result = run_once(config)
        print(f"Cycle completed: {result}")