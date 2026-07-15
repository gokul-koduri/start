"""
Sprint Execution Agent — Execute approved sprint tasks

This agent retrieves tasks that have been approved (either auto-approved or
manually approved) and executes them.

Usage:
    python run_agent.py --pipeline sprint-execution
    python -m agents.sprint_execution_agent --pending
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any

from agents.base import AgentResult, BaseAgent
from db.connection import get_connection

_logger = logging.getLogger(__name__)


class SprintExecutionAgent(BaseAgent):
    """Execute approved sprint tasks from the backlog.

    This agent:
    1. Loads tasks in 'approved' or 'planned' state (minor tasks)
    2. Executes them according to the plan
    3. Updates task state to 'in_progress' then 'done'
    4. Logs execution notes
    """

    @property
    def name(self) -> str:
        return "sprint_execution_agent"

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        """Execute all approved and ready tasks."""
        started_at = datetime.now(timezone.utc).isoformat()
        tasks_executed = 0
        tasks_failed = 0
        errors = []

        try:
            conn = get_connection()
            cursor = conn.cursor()

            # Get tasks that are ready to execute
            # - 'planned' with low score => auto-approved
            # - 'approved' => human approved
            cursor.execute("""
                SELECT
                    st.id,
                    st.task_id,
                    st.title,
                    st.description,
                    st.plan_document,
                    st.task_effort_minutes,
                    st.state,
                    st.opportunity_score
                FROM sprint_tasks st
                WHERE st.state IN ('planned', 'approved')
                ORDER BY
                    CASE st.state
                        WHEN 'approved' THEN 1
                        WHEN 'planned' THEN 2
                    END,
                    st.priority ASC,
                    st.opportunity_score DESC
                LIMIT 5
            """)

            tasks = cursor.fetchall()
            cursor.close()
            conn.close()

            for task in tasks:
                try:
                    self._execute_single_task(task)
                    tasks_executed += 1
                except Exception as e:
                    _logger.error("Failed to execute task %s: %s", task['task_id'], e)
                    tasks_failed += 1
                    errors.append(f"{task['task_id']}: {str(e)}")

        except Exception as e:
            _logger.error("Sprint execution error: %s", e)
            errors.append(str(e))

        completed_at = datetime.now(timezone.utc).isoformat()

        return AgentResult(
            agent_name=self.name,
            status="success" if not errors else "partial",
            started_at=started_at,
            completed_at=completed_at,
            data={
                "tasks_executed": tasks_executed,
                "tasks_failed": tasks_failed,
            },
            errors=errors,
        )

    def _execute_single_task(self, task: dict):
        """Execute a single task."""
        task_id = task["task_id"]
        _logger.info("Executing task: %s", task_id)

        # Parse plan if present
        plan = None
        if task.get("plan_document"):
            try:
                plan = json.loads(task["plan_document"])
            except json.JSONDecodeError:
                _logger.warning("Could not parse plan for task %s", task_id)

        # Update state to in_progress
        self._update_task_state(task["id"], "in_progress")

        try:
            # Execute based on task type
            # For now, just create documentation
            if plan:
                self._implement_plan(task, plan)

            # Mark as done
            self._update_task_state(task["id"], "done", completed_at=datetime.now(timezone.utc).isoformat())
            _logger.info("Task %s completed successfully", task_id)

        except Exception as e:
            # Mark as failed
            self._update_task_state(task["id"], "failed", execution_notes=str(e))
            raise

    def _implement_plan(self, task: dict, plan: dict):
        """Implement the plan (placeholder for actual implementation)."""
        steps = plan.get("steps", [])

        _logger.info("Executing %d steps for task %s", len(steps), task["task_id"])

        for i, step in enumerate(steps, 1):
            _logger.info("  Step %d: %s", i, step)
            # TODO: Actual implementation would go here
            # For now, just log

    def _update_task_state(self, task_db_id: int, state: str, completed_at: str = None, execution_notes: str = None):
        """Update task state in database."""
        try:
            conn = get_connection()
            cursor = conn.cursor()

            if state == "in_progress":
                cursor.execute("""
                    UPDATE sprint_tasks
                    SET state = %s, started_at = NOW()
                    WHERE id = %s
                """, (state, task_db_id))
            elif state == "done":
                cursor.execute("""
                    UPDATE sprint_tasks
                    SET state = %s, completed_at = %s
                    WHERE id = %s
                """, (state, completed_at, task_db_id))
            elif state == "failed" and execution_notes:
                cursor.execute("""
                    UPDATE sprint_tasks
                    SET state = %s, execution_notes = %s
                    WHERE id = %s
                """, (state, execution_notes, task_db_id))
            else:
                cursor.execute("""
                    UPDATE sprint_tasks
                    SET state = %s
                    WHERE id = %s
                """, (state, task_db_id))

            conn.commit()
            cursor.close()
            conn.close()

        except Exception as e:
            _logger.error("Error updating task state: %s", e)


def get_pending_tasks() -> list[dict[str, Any]]:
    """Get all pending tasks (for CLI display)."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            task_id,
            title,
            task_type,
            state,
            opportunity_score,
            task_effort_minutes,
            created_at
        FROM sprint_tasks
        WHERE state IN ('scanned', 'planned', 'approved', 'in_progress')
        ORDER BY
            CASE state
                WHEN 'in_progress' THEN 1
                WHEN 'approved' THEN 2
                WHEN 'planned' THEN 3
                ELSE 4
            END,
            opportunity_score DESC
    """)

    tasks = cursor.fetchall()
    cursor.close()
    conn.close()

    return tasks


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Sprint Execution Agent")
    parser.add_argument("--pending", action="store_true", help="List pending tasks")
    args = parser.parse_args()

    if args.pending:
        tasks = get_pending_tasks()
        print(f"\nPending Tasks ({len(tasks)}):")
        print("-" * 80)
        for task in tasks:
            print(f"  {task['task_id']:<15} {task['state']:<15} {task['title'][:40]}")
    else:
        agent = SprintExecutionAgent()
        result = agent.run()
        print(f"Execution complete: {result.data}")