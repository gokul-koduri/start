#!/usr/bin/env python3
"""
Sprint Cycle CLI - Entry point for the continuous cycle agent

Usage:
    python scripts/run_sprint_cycle.py              # Run continuous cycle
    python scripts/run_sprint_cycle.py --once       # Run single cycle
    python scripts/run_sprint_cycle.py --daemon    # Run as background daemon
    python scripts/run_sprint_cycle.py --status    # Show cycle status
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import load_config
from agents.cycle_agent import run_daemon, run_once

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_logger = logging.getLogger(__name__)


def show_status():
    """Show current sprint cycle status."""
    try:
        # Check for state file
        state_file = Path("sprint_state.json")
        if state_file.exists():
            state = json.loads(state_file.read_text())
            print("=== Sprint Cycle Status ===")
            print(f"  Last Run: {state.get('last_run', 'Never')}")
            print(f"  Tasks Processed: {state.get('tasks_processed', 0)}")
            print(f"  Cycle Count: {state.get('cycle_count', 0)}")
        else:
            print("=== Sprint Cycle Status ===")
            print("  No state file found (not yet run)")

        # Check database for pending tasks
        try:
            from db.connection import get_connection
            conn = get_connection()
            cursor = conn.cursor()

            # Count tasks by state
            cursor.execute("""
                SELECT state, COUNT(*) as cnt
                FROM sprint_tasks
                GROUP BY state
            """)
            # DictCursor returns list of dicts: [{'state': 'planned', 'cnt': 5}, ...]
            rows = cursor.fetchall()
            states = {}
            for row in rows:
                state_name = row["state"] if isinstance(row, dict) else row[0]
                count = row["cnt"] if isinstance(row, dict) else row[1]
                states[state_name] = count

            print("\n=== Task Queue ===")
            print(f"  Planned/Pending Approval: {states.get('planned', 0)}")
            print(f"  Approved: {states.get('approved', 0)}")
            print(f"  In Progress: {states.get('in_progress', 0)}")
            print(f"  Done: {states.get('done', 0)}")
            print(f"  Failed: {states.get('failed', 0)}")

            cursor.close()
            conn.close()

        except Exception as e:
            print(f"\n  (Could not fetch DB status: {e})")

        # Check for approvals
        try:
            from db.connection import get_connection
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT COUNT(*)
                FROM pending_approvals
                WHERE decision IS NULL
            """)
            pending_approvals = cursor.fetchone()[0]

            print("\n=== Pending Approvals ===")
            print(f"  Awaiting Decision: {pending_approvals}")

            cursor.close()
            conn.close()

        except Exception as e:
            print(f"\n  (Could not fetch pending approvals: {e})")

    except Exception as e:
        _logger.error("Error fetching status: %s", e)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Sprint Cycle CLI - Continuous Claude ↔ Codex cycle",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run_sprint_cycle.py              # Run continuous cycle
  python scripts/run_sprint_cycle.py --once       # Run single cycle
  python scripts/run_sprint_cycle.py --daemon     # Run as daemon
  python scripts/run_sprint_cycle.py --status     # Show status
  python scripts/run_sprint_cycle.py --pending    # List pending tasks
        """
    )

    parser.add_argument("--once", action="store_true", help="Run a single cycle and exit")
    parser.add_argument("--daemon", action="store_true", help="Run as continuous daemon")
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument("--pending", action="store_true", help="List pending tasks")

    args = parser.parse_args()

    if args.status:
        show_status()
        return

    if args.pending:
        from agents.sprint_execution_agent import get_pending_tasks
        tasks = get_pending_tasks()
        print(f"\nPending Tasks ({len(tasks)}):")
        print("-" * 80)
        for task in tasks:
            print(f"  [{task['state']:<15}] {task['task_id']}: {task['title'][:50]}")
        return

    # Load settings
    config = load_config()
    sprint_config = config.get("sprint_cycle", {}) if config else {}
    run_config = {
        "scan_interval_seconds": sprint_config.get("scan_interval_seconds", 300),
        "auto_approve_score": sprint_config.get("thresholds", {}).get("auto_approve_score", 40),
        "auto_approve_effort_min": sprint_config.get("thresholds", {}).get("auto_approve_effort_min", 30),
    }

    if args.daemon:
        print("Starting Sprint Cycle daemon...")
        print(f"  Scan interval: {run_config['scan_interval_seconds']}s")
        print(f"  Auto-approve threshold: score < {run_config['auto_approve_score']}, effort < {run_config['auto_approve_effort_min']}min")
        print("  Press Ctrl+C to stop gracefully\n")
        run_daemon(run_config)

    elif args.once:
        print("Running single cycle...")
        result = run_once(run_config)
        print(f"Cycle completed: {result.data}")

    else:
        # Default: run continuous
        print("Starting Sprint Cycle (continuous mode)...")
        print(f"  Scan interval: {run_config['scan_interval_seconds']}s")
        print("  Press Ctrl+C to stop\n")
        run_daemon(run_config)


if __name__ == "__main__":
    main()