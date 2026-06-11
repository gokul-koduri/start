"""Parallel task spawner — spawn independent work as a parallel agent during sprints.

When a problem comes up mid-sprint (e.g., "email template design", "auth system",
"rate limiting"), you don't want it to block the main pipeline. This module lets
you spawn a parallel workstream that designs, builds, and completes independently.

Usage:
    # Spawn a parallel task
    python -m agents.parallel_spawner spawn \\
        --name "email-queue" \\
        --description "Design and build email queue with templates, retry, and worker" \\
        --type build \\
        --priority P1

    # Check status of all spawned tasks
    python -m agents.parallel_spawner status

    # Complete a task
    python -m agents.parallel_spawner complete --id 1 --result "Built email queue, 19 tests pass"

    # List all active tasks
    python -m agents.parallel_spawner list

Design:
    - Tasks live in the `parallel_tasks` DB table (survives restarts)
    - Each task has: status, design_doc, files_created, files_modified, tests_added
    - The spawner creates a work log so nothing is lost
    - Tasks are independent — no blocking between them or the main pipeline
"""

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

from db.connection import get_connection
from utils.work_tokens import (
    create_token as _create_token,
    release_completed_blockers,
    claim_token as _claim_token,
    complete_token as _complete_token,
    expire_token as _expire_token,
    get_token as _get_token,
    list_tokens as _list_tokens,
    get_ready_tokens,
    get_token_log as _get_token_log,
    print_token_dashboard,
    TokenStatus as _TokenStatus,
)

_logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TaskStatus(str, Enum):
    QUEUED = "queued"
    DESIGNING = "designing"
    BUILDING = "building"
    TESTING = "testing"
    COMPLETING = "completing"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    BUILD = "build"  # New feature
    FIX = "fix"  # Bug fix
    REFACTOR = "refactor"  # Code improvement
    DESIGN = "design"  # Design document only
    TEST = "test"  # Add tests
    DOCS = "docs"  # Documentation


# ── Ensure DB table exists ──────────────────────────────────────────────────

_PARALLEL_TASKS_TABLE = """
CREATE TABLE IF NOT EXISTS parallel_tasks (
    id                  INT PRIMARY KEY AUTO_INCREMENT,
    task_name           VARCHAR(255) NOT NULL UNIQUE,
    description         TEXT NOT NULL,
    task_type           VARCHAR(50) NOT NULL DEFAULT 'build',
    priority            VARCHAR(10) NOT NULL DEFAULT 'P2',
    status              VARCHAR(20) NOT NULL DEFAULT 'queued',
    spawned_by          VARCHAR(100) DEFAULT 'manual',
    parent_sprint       VARCHAR(50),
    design_doc          TEXT COMMENT 'JSON: design decisions, approach, files affected',
    files_created       TEXT COMMENT 'JSON: list of file paths created',
    files_modified      TEXT COMMENT 'JSON: list of file paths modified',
    tests_added         INT DEFAULT 0,
    tests_passing       INT DEFAULT 0,
    result_summary      TEXT,
    error_message       TEXT,
    wall_clock_minutes  FLOAT DEFAULT 0,
    started_at          DATETIME,
    completed_at        DATETIME,
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_pt_status (status),
    INDEX idx_pt_priority (priority, status),
    INDEX idx_pt_type (task_type),
    INDEX idx_pt_created (created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

_PARALLEL_TASK_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS parallel_task_log (
    id                  BIGINT PRIMARY KEY AUTO_INCREMENT,
    task_id             INT NOT NULL,
    phase               VARCHAR(30) NOT NULL COMMENT 'spawn, design, build, test, complete, fail',
    message             TEXT NOT NULL,
    data_json           TEXT COMMENT 'JSON: structured data for this log entry',
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES parallel_tasks(id) ON DELETE CASCADE,
    INDEX idx_ptl_task (task_id, created_at),
    INDEX idx_ptl_phase (phase)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


def _ensure_tables():
    """Create parallel_tasks tables if they don't exist."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(_PARALLEL_TASKS_TABLE)
            cur.execute(_PARALLEL_TASK_LOG_TABLE)
        conn.commit()
    finally:
        conn.close()


# ── Core operations ──────────────────────────────────────────────────────────


def spawn_task(
    name: str,
    description: str,
    task_type: str = "build",
    priority: str = "P2",
    parent_sprint: Optional[str] = None,
    spawned_by: str = "manual",
    design_doc: Optional[dict] = None,
) -> int:
    """Spawn a new parallel task. Returns the task ID.

    Raises ValueError if a task with this name already exists and is not done/failed/cancelled.
    """
    _ensure_tables()
    conn = get_connection()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    try:
        with conn.cursor() as cur:
            # Check for existing active task with same name
            cur.execute(
                "SELECT id, status FROM parallel_tasks WHERE task_name = %s", (name,)
            )
            existing = cur.fetchone()
            if existing and existing["status"] not in ("done", "failed", "cancelled"):
                raise ValueError(
                    f"Task '{name}' already exists (id={existing['id']}, status={existing['status']})"
                )

            cur.execute(
                """INSERT INTO parallel_tasks
                   (task_name, description, task_type, priority, status,
                    spawned_by, parent_sprint, design_doc, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, 'queued',
                           %s, %s, %s, %s, %s)""",
                (
                    name,
                    description,
                    task_type,
                    priority,
                    spawned_by,
                    parent_sprint,
                    json.dumps(design_doc) if design_doc else None,
                    now,
                    now,
                ),
            )
            task_id = cur.lastrowid

            cur.execute(
                """INSERT INTO parallel_task_log
                   (task_id, phase, message, data_json, created_at)
                   VALUES (%s, 'spawn', 'Task spawned', %s, %s)""",
                (
                    task_id,
                    json.dumps({"name": name, "type": task_type, "priority": priority}),
                    now,
                ),
            )
        conn.commit()
        _logger.info("spawn_task: Created parallel task id=%d name='%s'", task_id, name)
        return task_id
    finally:
        conn.close()


def update_task_status(
    task_id: int,
    status: str,
    message: Optional[str] = None,
    data: Optional[dict] = None,
) -> None:
    """Update a task's status and log the transition."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Calculate wall clock time if completing
            wall_minutes = None
            if status in ("done", "failed"):
                cur.execute(
                    "SELECT started_at FROM parallel_tasks WHERE id = %s", (task_id,)
                )
                row = cur.fetchone()
                if row and row.get("started_at"):
                    started = row["started_at"]
                    if isinstance(started, str):
                        started = datetime.fromisoformat(started)
                    wall_minutes = (
                        datetime.now(timezone.utc)
                        - started.replace(tzinfo=timezone.utc)
                        if hasattr(started, "tzinfo") and started.tzinfo
                        else (datetime.now(timezone.utc) - started)
                    ).total_seconds() / 60

            updates = ["status = %s", "updated_at = %s"]
            params = [status, now]

            if (
                status in ("designing", "building", "testing")
                and message != "set_started"
            ):
                # Don't overwrite started_at on intermediate status changes
                pass
            elif status in ("designing", "building", "testing"):
                updates.append("started_at = %s")
                params.append(now)

            if status == "done":
                updates.append("completed_at = %s")
                params.append(now)

            if wall_minutes is not None:
                updates.append("wall_clock_minutes = %s")
                params.append(wall_minutes)

            params.append(task_id)
            cur.execute(
                f"UPDATE parallel_tasks SET {', '.join(updates)} WHERE id = %s",
                params,
            )

            cur.execute(
                """INSERT INTO parallel_task_log
                   (task_id, phase, message, data_json, created_at)
                   VALUES (%s, %s, %s, %s, %s)""",
                (
                    task_id,
                    status,
                    message or f"Status → {status}",
                    json.dumps(data) if data else None,
                    now,
                ),
            )
        conn.commit()
    finally:
        conn.close()


def record_artifacts(
    task_id: int,
    files_created: Optional[list[str]] = None,
    files_modified: Optional[list[str]] = None,
    tests_added: int = 0,
    tests_passing: int = 0,
    design_doc: Optional[dict] = None,
    result_summary: Optional[str] = None,
) -> None:
    """Record what was built during this task."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM parallel_tasks WHERE id = %s", (task_id,))
            task = cur.fetchone()
            if not task:
                raise ValueError(f"Task {task_id} not found")

            updates = []
            params = []

            if files_created is not None:
                existing = json.loads(task.get("files_created") or "[]")
                existing.extend(files_created)
                updates.append("files_created = %s")
                params.append(json.dumps(existing))

            if files_modified is not None:
                existing = json.loads(task.get("files_modified") or "[]")
                existing.extend(files_modified)
                updates.append("files_modified = %s")
                params.append(json.dumps(existing))

            if tests_added:
                updates.append("tests_added = %s")
                params.append((task.get("tests_added") or 0) + tests_added)

            if tests_passing:
                updates.append("tests_passing = %s")
                params.append((task.get("tests_passing") or 0) + tests_passing)

            if design_doc is not None:
                updates.append("design_doc = %s")
                params.append(json.dumps(design_doc))

            if result_summary is not None:
                updates.append("result_summary = %s")
                params.append(result_summary)

            if not updates:
                return

            params.append(task_id)
            cur.execute(
                f"UPDATE parallel_tasks SET {', '.join(updates)} WHERE id = %s",
                params,
            )
        conn.commit()
    finally:
        conn.close()


def get_task(task_id: int) -> Optional[dict]:
    """Get a task by ID."""
    _ensure_tables()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM parallel_tasks WHERE id = %s", (task_id,))
            return cur.fetchone()
    finally:
        conn.close()


def find_task(name: str) -> Optional[dict]:
    """Find a task by name."""
    _ensure_tables()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM parallel_tasks WHERE task_name = %s", (name,))
            return cur.fetchone()
    finally:
        conn.close()


def list_tasks(status: Optional[str] = None) -> list[dict]:
    """List all tasks, optionally filtered by status."""
    _ensure_tables()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if status:
                cur.execute(
                    "SELECT * FROM parallel_tasks WHERE status = %s ORDER BY priority, created_at DESC",
                    (status,),
                )
            else:
                cur.execute(
                    "SELECT * FROM parallel_tasks ORDER BY FIELD(status, 'queued', 'designing', 'building', 'testing', 'completing', 'done', 'failed', 'cancelled'), priority, created_at DESC"
                )
            return cur.fetchall()
    finally:
        conn.close()


def get_task_log(task_id: int) -> list[dict]:
    """Get the log entries for a task."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM parallel_task_log WHERE task_id = %s ORDER BY created_at",
                (task_id,),
            )
            return cur.fetchall()
    finally:
        conn.close()


# ── Run tests for a task ────────────────────────────────────────────────────


def run_tests(test_path: Optional[str] = None) -> dict:
    """Run pytest and return results. Used by tasks to verify their work."""
    cmd = [sys.executable, "-m", "pytest", "-v", "--tb=short", "-q"]
    if test_path:
        cmd.append(test_path)
    else:
        cmd.append("tests/")

    result = subprocess.run(
        cmd,
        cwd=str(_PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )

    # Parse output for counts
    output = result.stdout + result.stderr
    passed = output.count(" PASSED")
    failed = output.count(" FAILED")

    return {
        "returncode": result.returncode,
        "passed": passed,
        "failed": failed,
        "output": output[-2000:],  # Last 2000 chars
    }


# ── Status dashboard ────────────────────────────────────────────────────────


def print_status():
    """Print a formatted status dashboard of all parallel tasks."""
    tasks = list_tasks()
    if not tasks:
        print("No parallel tasks found.")
        return

    status_icons = {
        "queued": "⏳",
        "designing": "📐",
        "building": "🔨",
        "testing": "🧪",
        "completing": "✅",
        "done": "✅",
        "failed": "❌",
        "cancelled": "🚫",
    }

    print("\n" + "=" * 80)
    print("  PARALLEL TASKS — SPAWNED DURING SPRINT")
    print("=" * 80)
    print()
    print(
        f"  {'ID':<4} {'STATUS':<14} {'PRIORITY':<8} {'TYPE':<10} {'NAME':<30} {'TIME':>8}"
    )
    print(f"  {'─'*4} {'─'*14} {'─'*8} {'─'*10} {'─'*30} {'─'*8}")

    for t in tasks:
        icon = status_icons.get(t["status"], "?")
        wall = f"{t['wall_clock_minutes']:.1f}m" if t.get("wall_clock_minutes") else "—"
        name = (
            t["task_name"][:28] + ".." if len(t["task_name"]) > 30 else t["task_name"]
        )
        print(
            f"  {t['id']:<4} {icon} {t['status']:<12} {t['priority']:<8} {t['task_type']:<10} {name:<30} {wall:>8}"
        )

    # Summary
    active = sum(1 for t in tasks if t["status"] not in ("done", "failed", "cancelled"))
    done = sum(1 for t in tasks if t["status"] == "done")
    failed = sum(1 for t in tasks if t["status"] == "failed")
    total_files = sum(len(json.loads(t.get("files_created") or "[]")) for t in tasks)
    total_tests = sum(t.get("tests_passing") or 0 for t in tasks)

    print()
    print(
        f"  Active: {active}  Done: {done}  Failed: {failed}  "
        f"Files created: {total_files}  Tests passing: {total_tests}"
    )
    print("=" * 80)
    print()


# ── Convenience: spawn + run ─────────────────────────────────────────────────


def spawn_and_track(
    name: str,
    description: str,
    task_type: str = "build",
    priority: str = "P2",
    parent_sprint: Optional[str] = None,
) -> int:
    """Spawn a task and print guidance for next steps.

    This is the main entry point for 'I hit a problem during sprint,
    spawn an agent to handle it in parallel.'
    """
    task_id = spawn_task(
        name=name,
        description=description,
        task_type=task_type,
        priority=priority,
        parent_sprint=parent_sprint,
    )

    print(f"\n✅ Spawned parallel task #{task_id}: {name}")
    print(f"   Type: {task_type}  Priority: {priority}")
    print("   Status: queued")
    print()
    print("   Next steps:")
    print(
        f"   1. Update status:  python -m agents.parallel_spawner update --id {task_id} --status designing"
    )
    print(
        f'   2. Record design:  python -m agents.parallel_spawner design --id {task_id} --doc \'{{"approach": "..."}}\''
    )
    print(
        f"   3. Start building: python -m agents.parallel_spawner update --id {task_id} --status building"
    )
    print(
        f"   4. Record files:   python -m agents.parallel_spawner artifacts --id {task_id} --created 'file1.py,file2.py'"
    )
    print(
        f"   5. Run tests:      python -m agents.parallel_spawner test --id {task_id}"
    )
    print(
        f"   6. Complete:       python -m agents.parallel_spawner complete --id {task_id} --result 'Done, all tests pass'"
    )
    print()

    return task_id


def _handle_token_command(args):
    """Dispatch token subcommands."""
    if args.token_command == "create":
        blocked_by = [int(x.strip()) for x in args.blocked_by.split(",")]
        token_id = _create_token(
            name=args.name,
            description=args.description,
            blocked_by=blocked_by,
            created_by=args.created_by,
            priority=args.priority,
            work_summary=args.work_summary,
        )
        print(f"\n🔒 Created token #{token_id}: {args.name}")
        print(f"   Blocked by: {blocked_by}")
        print("   Status: blocked")
        print()
        print(f"   This token will auto-release when task(s) {blocked_by} complete.")
        print(
            f"   Check:  python -m agents.parallel_spawner token show --id {token_id}"
        )
        print("   Ready:  python -m agents.parallel_spawner token list --status ready")
        print()

    elif args.token_command == "list":
        tokens = _list_tokens(status=args.status, task_id=args.task)
        if not tokens:
            print("  No tokens found.")
        for t in tokens:
            blocked = (
                f"→ task #{t['claimed_by_task_id']}"
                if t.get("claimed_by_task_id")
                else ""
            )
            print(
                f"  #{t['id']:<4} {t['status']:<10} {t['priority']:<5} {t['token_name']} {blocked}"
            )

    elif args.token_command == "show":
        token = _get_token(args.id)
        if not token:
            print(f"Token #{args.id} not found")
            return
        print(f"\n  Token #{token['id']}: {token['token_name']}")
        print(f"  Status:      {token['status']}")
        print(f"  Priority:    {token['priority']}")
        print(f"  Description: {token['description']}")
        if token.get("work_summary"):
            print(f"  Work:        {token['work_summary']}")
        if token.get("created_by_task_id"):
            print(f"  Created by:  task #{token['created_by_task_id']}")
        if token.get("claimed_by_task_id"):
            print(f"  Claimed by:  task #{token['claimed_by_task_id']}")
        if token.get("result_summary"):
            print(f"  Result:      {token['result_summary']}")
        print(f"  Created:     {token['created_at']}")
        if token.get("released_at"):
            print(f"  Released:    {token['released_at']}")
        if token.get("claimed_at"):
            print(f"  Claimed:     {token['claimed_at']}")
        if token.get("completed_at"):
            print(f"  Completed:   {token['completed_at']}")
        # Blockers
        if token.get("blockers"):
            print("\n  Blockers:")
            for b in token["blockers"]:
                sat = "✅" if b["satisfied"] else "🔒"
                print(
                    f"    {sat} task #{b['blocking_task_id']} ({b['task_name']}) — {b['task_status']}"
                )
        # Artifacts
        if token.get("files_created"):
            files = json.loads(token["files_created"])
            print(f"\n  Files created: {len(files)}")
            for f in files:
                print(f"    + {f}")
        if token.get("files_modified"):
            files = json.loads(token["files_modified"])
            print(f"  Files modified: {len(files)}")
            for f in files:
                print(f"    ~ {f}")
        print(
            f"  Tests: {token.get('tests_passing') or 0} passing / {token.get('tests_added') or 0} added"
        )
        print()

    elif args.token_command == "claim":
        _claim_token(args.id, claimed_by=args.claimed_by)
        print(f"🔧 Token #{args.id} claimed by task #{args.claimed_by}")

    elif args.token_command == "complete":
        created = args.created.split(",") if args.created else None
        modified = args.modified.split(",") if args.modified else None
        _complete_token(
            args.id,
            result=args.result,
            files_created=created,
            files_modified=modified,
            tests_added=args.tests_added,
            tests_passing=args.tests_passing,
        )
        print(f"✅ Token #{args.id} completed: {args.result}")

    elif args.token_command == "expire":
        _expire_token(args.id, reason=args.reason)
        print(f"⏰ Token #{args.id} expired: {args.reason}")

    elif args.token_command == "log":
        entries = _get_token_log(args.id)
        if not entries:
            print(f"No log entries for token #{args.id}")
        for e in entries:
            print(f"  [{e['created_at']}] {e['event']}: {e['message']}")

    elif args.token_command == "ready":
        tokens = get_ready_tokens()
        if not tokens:
            print("  No ready tokens.")
        for t in tokens:
            print(f"  🟢 #{t['id']:<4} {t['priority']:<5} {t['token_name']}")
            if t.get("work_summary"):
                print(f"         {t['work_summary']}")

    elif args.token_command == "blocked":
        from utils.work_tokens import list_tokens as _lt

        tokens = _lt(status="blocked")
        if not tokens:
            print("  No blocked tokens.")
        for t in tokens:
            print(f"  🔒 #{t['id']:<4} {t['priority']:<5} {t['token_name']}")

    else:
        print(
            "  Usage: python -m agents.parallel_spawner token <create|list|show|claim|complete|expire|log|ready|blocked>"
        )


# ── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Parallel task spawner for sprint work"
    )
    sub = parser.add_subparsers(dest="command")

    # spawn
    p_spawn = sub.add_parser("spawn", help="Spawn a new parallel task")
    p_spawn.add_argument("--name", required=True, help="Task name (unique)")
    p_spawn.add_argument("--description", required=True, help="What needs to be done")
    p_spawn.add_argument(
        "--type",
        default="build",
        choices=["build", "fix", "refactor", "design", "test", "docs"],
    )
    p_spawn.add_argument("--priority", default="P2", choices=["P0", "P1", "P2", "P3"])
    p_spawn.add_argument("--sprint", default=None, help="Parent sprint name")

    # update
    p_update = sub.add_parser("update", help="Update task status")
    p_update.add_argument("--id", type=int, required=True)
    p_update.add_argument(
        "--status", required=True, choices=[s.value for s in TaskStatus]
    )
    p_update.add_argument("--message", default=None)

    # design
    p_design = sub.add_parser("design", help="Record design document")
    p_design.add_argument("--id", type=int, required=True)
    p_design.add_argument("--doc", required=True, help="JSON design document")

    # artifacts
    p_art = sub.add_parser("artifacts", help="Record files created/modified")
    p_art.add_argument("--id", type=int, required=True)
    p_art.add_argument(
        "--created", default=None, help="Comma-separated list of files created"
    )
    p_art.add_argument(
        "--modified", default=None, help="Comma-separated list of files modified"
    )
    p_art.add_argument("--tests-added", type=int, default=0)
    p_art.add_argument("--tests-passing", type=int, default=0)

    # test
    p_test = sub.add_parser("test", help="Run tests and record results")
    p_test.add_argument("--id", type=int, required=True)
    p_test.add_argument(
        "--path",
        default=None,
        help="Specific test path (e.g., tests/test_email_queue.py)",
    )

    # complete
    p_complete = sub.add_parser("complete", help="Mark task as done")
    p_complete.add_argument("--id", type=int, required=True)
    p_complete.add_argument("--result", required=True, help="Result summary")

    # fail
    p_fail = sub.add_parser("fail", help="Mark task as failed")
    p_fail.add_argument("--id", type=int, required=True)
    p_fail.add_argument("--error", required=True, help="Error description")

    # status / list
    sub.add_parser("status", help="Show parallel tasks dashboard")
    p_list = sub.add_parser("list", help="List tasks")
    p_list.add_argument("--status", default=None, help="Filter by status")

    # log
    p_log = sub.add_parser("log", help="Show task log")
    p_log.add_argument("--id", type=int, required=True)

    # show
    p_show = sub.add_parser("show", help="Show task details")
    p_show.add_argument("--id", type=int, required=True)

    # token (with subcommands)
    p_token = sub.add_parser("token", help="Manage work tokens (blocked work)")
    token_sub = p_token.add_subparsers(dest="token_command")

    # token create
    tc = token_sub.add_parser("create", help="Create a blocked work token")
    tc.add_argument("--name", required=True, help="Token name")
    tc.add_argument("--description", required=True, help="What work needs doing")
    tc.add_argument(
        "--blocked-by",
        required=True,
        help="Comma-separated task IDs that must complete first",
    )
    tc.add_argument("--created-by", type=int, default=None, help="Your current task ID")
    tc.add_argument("--priority", default="P2", choices=["P0", "P1", "P2", "P3"])
    tc.add_argument("--work-summary", default=None, help="What to do once unblocked")

    # token list
    tl = token_sub.add_parser("list", help="List tokens")
    tl.add_argument("--status", default=None, choices=[s.value for s in _TokenStatus])
    tl.add_argument("--task", type=int, default=None, help="Filter by related task ID")

    # token show
    ts = token_sub.add_parser("show", help="Show token details with blockers")
    ts.add_argument("--id", type=int, required=True)

    # token claim
    tcl = token_sub.add_parser("claim", help="Claim a ready token")
    tcl.add_argument("--id", type=int, required=True)
    tcl.add_argument("--claimed-by", type=int, required=True, help="Your task ID")

    # token complete
    tco = token_sub.add_parser("complete", help="Complete a claimed token")
    tco.add_argument("--id", type=int, required=True)
    tco.add_argument("--result", required=True, help="What was done")
    tco.add_argument("--created", default=None, help="Comma-separated files created")
    tco.add_argument("--modified", default=None, help="Comma-separated files modified")
    tco.add_argument("--tests-added", type=int, default=0)
    tco.add_argument("--tests-passing", type=int, default=0)

    # token expire
    te = token_sub.add_parser("expire", help="Expire a token")
    te.add_argument("--id", type=int, required=True)
    te.add_argument("--reason", default="No longer relevant")

    # token log
    tlg = token_sub.add_parser("log", help="Show token log")
    tlg.add_argument("--id", type=int, required=True)

    # token ready (shortcut)
    token_sub.add_parser("ready", help="List all ready tokens")

    # token blocked (shortcut)
    token_sub.add_parser("blocked", help="List all blocked tokens")

    args = parser.parse_args()

    if args.command == "spawn":
        spawn_and_track(
            name=args.name,
            description=args.description,
            task_type=args.type,
            priority=args.priority,
            parent_sprint=args.sprint,
        )

    elif args.command == "update":
        update_task_status(args.id, args.status, message=args.message)

    elif args.command == "design":
        update_task_status(args.id, "designing", message="Design recorded")
        record_artifacts(args.id, design_doc=json.loads(args.doc))
        print(f"✅ Design recorded for task #{args.id}")

    elif args.command == "artifacts":
        created = args.created.split(",") if args.created else None
        modified = args.modified.split(",") if args.modified else None
        record_artifacts(
            args.id,
            files_created=created,
            files_modified=modified,
            tests_added=args.tests_added,
            tests_passing=args.tests_passing,
        )
        print(f"✅ Artifacts recorded for task #{args.id}")

    elif args.command == "test":
        update_task_status(args.id, "testing", message="Running tests")
        results = run_tests(args.path)
        record_artifacts(args.id, tests_passing=results["passed"])
        if results["failed"] == 0:
            print(f"✅ All tests pass: {results['passed']} passed")
        else:
            print(f"⚠️  Tests: {results['passed']} passed, {results['failed']} failed")
            print(results["output"][-500:])

    elif args.command == "complete":
        update_task_status(args.id, "done", message=args.result)
        record_artifacts(args.id, result_summary=args.result)
        # Auto-release any tokens blocked by this task
        released = release_completed_blockers(args.id)
        if released:
            print(f"✅ Task #{args.id} completed: {args.result}")
            print(f"🔓 Released {len(released)} token(s): {released}")
            print(
                "   Run 'python -m agents.parallel_spawner token list --status ready' to see them"
            )
        else:
            print(f"✅ Task #{args.id} completed: {args.result}")

    elif args.command == "fail":
        update_task_status(args.id, "failed", message=args.error)
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE parallel_tasks SET error_message = %s WHERE id = %s",
                    (args.error, args.id),
                )
            conn.commit()
        finally:
            conn.close()
        print(f"❌ Task #{args.id} failed: {args.error}")

    elif args.command == "status":
        print_status()
        print_token_dashboard()

    elif args.command == "list":
        tasks = list_tasks(status=args.status)
        for t in tasks:
            print(
                f"  #{t['id']:>3}  {t['status']:<14} {t['priority']:<6} {t['task_name']}"
            )

    elif args.command == "log":
        entries = get_task_log(args.id)
        if not entries:
            print(f"No log entries for task #{args.id}")
        for e in entries:
            print(f"  [{e['created_at']}] {e['phase']}: {e['message']}")

    elif args.command == "show":
        task = get_task(args.id)
        if not task:
            print(f"Task #{args.id} not found")
        else:
            print(f"\n  Task #{task['id']}: {task['task_name']}")
            print(f"  Status:     {task['status']}")
            print(f"  Type:       {task['task_type']}")
            print(f"  Priority:   {task['priority']}")
            print(f"  Sprint:     {task.get('parent_sprint') or '—'}")
            print(f"  Created:    {task['created_at']}")
            print(f"  Wall time:  {task.get('wall_clock_minutes', 0):.1f} min")
            print(f"  Description: {task['description']}")
            if task.get("result_summary"):
                print(f"  Result:     {task['result_summary']}")
            if task.get("files_created"):
                files = json.loads(task["files_created"])
                print(f"  Files created: {len(files)}")
                for f in files:
                    print(f"    + {f}")
            if task.get("files_modified"):
                files = json.loads(task["files_modified"])
                print(f"  Files modified: {len(files)}")
                for f in files:
                    print(f"    ~ {f}")
            print(
                f"  Tests: {task.get('tests_passing') or 0} passing / {task.get('tests_added') or 0} added"
            )
            if task.get("error_message"):
                print(f"  Error: {task['error_message']}")
            print()

    # ── Token subcommands ──
    elif args.command == "token":
        _handle_token_command(args)

    else:
        parser.print_help()


# ── Orchestrated agent wrapper ───────────────────────────────────────────────

# This lets the parallel spawner run inside the orchestrator pipeline
# as a regular agent. It checks for queued tasks and runs them.


class OrchestratedParallelSpawner:
    """Agent wrapper that the orchestrator can call to process queued parallel tasks."""

    def __init__(self, config=None, dry_run=False):
        self.config = config or {}
        self.dry_run = dry_run

    @property
    def name(self):
        return "parallel_spawner"

    @property
    def enabled(self):
        return self.config.get("enabled", True)

    def run(self, upstream_results=None):
        from agents.base import AgentResult

        if not self.enabled:
            return AgentResult(
                agent_name=self.name, status="success", data={"skipped": True}
            )

        tasks = list_tasks(status="queued")
        if not tasks:
            return AgentResult(
                agent_name=self.name,
                status="success",
                data={"message": "No queued parallel tasks"},
            )

        return AgentResult(
            agent_name=self.name,
            status="success",
            data={
                "queued_tasks": len(tasks),
                "task_names": [t["task_name"] for t in tasks],
                "message": f"{len(tasks)} parallel tasks queued — run 'python -m agents.parallel_spawner status' to track",
            },
        )
