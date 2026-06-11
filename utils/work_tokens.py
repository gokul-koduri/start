"""Work tokens — blocked work that auto-releases when the ongoing section completes.

When you're working on a parallel task and hit an obstruction, you don't stop.
You create a token: "I need X to finish before I can do Y". The token sits in
the queue, blocked. When X completes, the token auto-releases to "ready".
Then you (or another task) claim it and do the remaining work.

Lifecycle:
    blocked → ready → claimed → done
                 ↘ expired

Usage:
    # While working on task #3, hit an obstruction
    python -m agents.parallel_spawner token create \
        --name "add-email-templates-to-worker" \
        --description "Worker needs template paths from email-queue task" \
        --blocked-by 2 \
        --created-by 3

    # When task #2 completes, tokens blocked by it auto-release
    python -m agents.parallel_spawner complete --id 2 --result "Email queue done"

    # Check for ready tokens
    python -m agents.parallel_spawner token list --status ready

    # Claim and do the work
    python -m agents.parallel_spawner token claim --id 1 --claimed-by 3

    # Complete the token
    python -m agents.parallel_spawner token complete --id 1 --result "Templates wired up"

Design:
    - Tokens live in `work_tokens` table (survives restarts)
    - Auto-release: when a parallel_task completes, all tokens it blocks become "ready"
    - A token can be blocked by multiple tasks (ALL must complete)
    - Tokens have their own artifact tracking (files, tests)
    - Token log tracks every state transition
"""

import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from db.connection import get_connection

_logger = logging.getLogger(__name__)


# ── Enums ────────────────────────────────────────────────────────────────────


class TokenStatus(str, Enum):
    BLOCKED = "blocked"  # Waiting for blocking task(s) to complete
    READY = "ready"  # Blocking task(s) done, ready to be picked up
    CLAIMED = "claimed"  # Someone is working on it
    DONE = "done"  # Work complete
    EXPIRED = "expired"  # Timed out or no longer relevant


# ── DB tables ────────────────────────────────────────────────────────────────

_WORK_TOKENS_TABLE = """
CREATE TABLE IF NOT EXISTS work_tokens (
    id                  INT PRIMARY KEY AUTO_INCREMENT,
    token_name          VARCHAR(255) NOT NULL,
    description         TEXT NOT NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'blocked',
    priority            VARCHAR(10) NOT NULL DEFAULT 'P2',
    created_by_task_id  INT COMMENT 'FK: parallel_tasks.id — who created this token',
    claimed_by_task_id  INT COMMENT 'FK: parallel_tasks.id — who is doing the work',
    work_summary        TEXT COMMENT 'What needs to be done once unblocked',
    result_summary      TEXT COMMENT 'What was actually done',
    files_created       TEXT COMMENT 'JSON: list of file paths created',
    files_modified      TEXT COMMENT 'JSON: list of file paths modified',
    tests_added         INT DEFAULT 0,
    tests_passing       INT DEFAULT 0,
    metadata_json       TEXT COMMENT 'JSON: arbitrary metadata',
    released_at         DATETIME COMMENT 'When token became ready',
    claimed_at          DATETIME COMMENT 'When token was claimed',
    completed_at        DATETIME COMMENT 'When token work was done',
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_wt_status (status),
    INDEX idx_wt_blocked (created_by_task_id),
    INDEX idx_wt_claimed (claimed_by_task_id),
    INDEX idx_wt_ready_priority (status, priority),
    INDEX idx_wt_created (created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

_TOKEN_BLOCKERS_TABLE = """
CREATE TABLE IF NOT EXISTS token_blockers (
    id                  INT PRIMARY KEY AUTO_INCREMENT,
    token_id            INT NOT NULL,
    blocking_task_id    INT NOT NULL COMMENT 'FK: parallel_tasks.id — task that must complete',
    blocker_description TEXT COMMENT 'Why this blocks the token',
    satisfied           TINYINT NOT NULL DEFAULT 0 COMMENT '1 = blocking task is done',
    satisfied_at        DATETIME,
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (token_id) REFERENCES work_tokens(id) ON DELETE CASCADE,
    INDEX idx_tb_token (token_id),
    INDEX idx_tb_blocker (blocking_task_id),
    INDEX idx_tb_satisfied (satisfied)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

_TOKEN_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS token_log (
    id                  BIGINT PRIMARY KEY AUTO_INCREMENT,
    token_id            INT NOT NULL,
    event               VARCHAR(30) NOT NULL COMMENT 'created, released, claimed, completed, expired',
    message             TEXT NOT NULL,
    data_json           TEXT COMMENT 'JSON: structured data',
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (token_id) REFERENCES work_tokens(id) ON DELETE CASCADE,
    INDEX idx_tl_token (token_id, created_at),
    INDEX idx_tl_event (event)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


def _ensure_tables():
    """Create work_tokens tables if they don't exist."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(_WORK_TOKENS_TABLE)
            cur.execute(_TOKEN_BLOCKERS_TABLE)
            cur.execute(_TOKEN_LOG_TABLE)
        conn.commit()
    finally:
        conn.close()


# ── Core API ─────────────────────────────────────────────────────────────────


def create_token(
    name: str,
    description: str,
    blocked_by: list[int],
    *,
    created_by: Optional[int] = None,
    priority: str = "P2",
    work_summary: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> int:
    """Create a blocked work token.

    Args:
        name: Unique token name
        description: What this token represents
        blocked_by: List of parallel_task IDs that must complete before this token is ready
        created_by: The parallel_task that created this token (the one that hit the obstruction)
        priority: P0-P3
        work_summary: What work needs to be done once unblocked
        metadata: Arbitrary JSON metadata

    Returns:
        token_id

    Raises:
        ValueError if no blockers provided (use a regular task instead)
    """
    if not blocked_by:
        raise ValueError(
            "Tokens must be blocked by at least one task. "
            "If nothing blocks you, use a regular parallel task."
        )

    _ensure_tables()
    conn = get_connection()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    try:
        with conn.cursor() as cur:
            # Check if any blockers are already done
            already_done = set()
            for task_id in blocked_by:
                cur.execute(
                    "SELECT id, status FROM parallel_tasks WHERE id = %s", (task_id,)
                )
                row = cur.fetchone()
                if row and row["status"] in ("done", "cancelled"):
                    already_done.add(task_id)

            # If ALL blockers are done, token starts as "ready"
            initial_status = (
                "ready" if len(already_done) == len(blocked_by) else "blocked"
            )

            cur.execute(
                """INSERT INTO work_tokens
                   (token_name, description, status, priority,
                    created_by_task_id, work_summary, metadata_json,
                    released_at, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    name,
                    description,
                    initial_status,
                    priority,
                    created_by,
                    work_summary,
                    json.dumps(metadata) if metadata else None,
                    now if initial_status == "ready" else None,
                    now,
                    now,
                ),
            )
            token_id = cur.lastrowid

            # Create blocker records
            for task_id in blocked_by:
                is_satisfied = task_id in already_done
                cur.execute(
                    """INSERT INTO token_blockers
                       (token_id, blocking_task_id, satisfied, satisfied_at, created_at)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (
                        token_id,
                        task_id,
                        1 if is_satisfied else 0,
                        now if is_satisfied else None,
                        now,
                    ),
                )

            # Log the creation
            cur.execute(
                """INSERT INTO token_log
                   (token_id, event, message, data_json, created_at)
                   VALUES (%s, 'created', %s, %s, %s)""",
                (
                    token_id,
                    f"Token created (blocked by {len(blocked_by)} task(s), "
                    f"{len(already_done)} already done)",
                    json.dumps(
                        {
                            "blocked_by": blocked_by,
                            "already_done": list(already_done),
                            "initial_status": initial_status,
                        }
                    ),
                    now,
                ),
            )

        conn.commit()
        _logger.info(
            "create_token: Token #%d '%s' created (status=%s, blocked_by=%s)",
            token_id,
            name,
            initial_status,
            blocked_by,
        )
        return token_id
    finally:
        conn.close()


def release_completed_blockers(task_id: int) -> list[int]:
    """Release all tokens blocked by a now-completed task.

    Called automatically when a parallel_task completes. Checks each token
    blocked by this task. If ALL blockers for a token are now satisfied,
    the token status becomes "ready".

    Returns list of token IDs that became ready.
    """
    _ensure_tables()
    conn = get_connection()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    released_tokens = []

    try:
        with conn.cursor() as cur:
            # Mark this blocker as satisfied for all tokens it blocks
            cur.execute(
                """UPDATE token_blockers
                   SET satisfied = 1, satisfied_at = %s
                   WHERE blocking_task_id = %s AND satisfied = 0""",
                (now, task_id),
            )
            conn.commit()

            # Find tokens where ALL blockers are now satisfied but token is still "blocked"
            cur.execute(
                """SELECT t.id, t.token_name
                   FROM work_tokens t
                   WHERE t.status = 'blocked'
                     AND NOT EXISTS (
                       SELECT 1 FROM token_blockers tb
                       WHERE tb.token_id = t.id AND tb.satisfied = 0
                     )"""
            )
            ready_tokens = cur.fetchall()

            for rt in ready_tokens:
                cur.execute(
                    """UPDATE work_tokens
                       SET status = 'ready', released_at = %s, updated_at = %s
                       WHERE id = %s AND status = 'blocked'""",
                    (now, now, rt["id"]),
                )

                cur.execute(
                    """INSERT INTO token_log
                       (token_id, event, message, data_json, created_at)
                       VALUES (%s, 'released', 'All blockers done — token ready', %s, %s)""",
                    (
                        rt["id"],
                        json.dumps({"released_by_task": task_id}),
                        now,
                    ),
                )

                released_tokens.append(rt["id"])
                _logger.info(
                    "release_completed_blockers: Token #%d '%s' → ready (task #%d completed)",
                    rt["id"],
                    rt["token_name"],
                    task_id,
                )

        conn.commit()
    finally:
        conn.close()

    return released_tokens


def claim_token(token_id: int, claimed_by: int) -> None:
    """Claim a ready token. The claiming task will do the work.

    Raises ValueError if token is not in "ready" status.
    """
    conn = get_connection()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT status FROM work_tokens WHERE id = %s", (token_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Token #{token_id} not found")
            if row["status"] != "ready":
                raise ValueError(
                    f"Token #{token_id} is '{row['status']}', not 'ready'. "
                    f"Only ready tokens can be claimed."
                )

            cur.execute(
                """UPDATE work_tokens
                   SET status = 'claimed', claimed_by_task_id = %s,
                       claimed_at = %s, updated_at = %s
                   WHERE id = %s""",
                (claimed_by, now, now, token_id),
            )

            cur.execute(
                """INSERT INTO token_log
                   (token_id, event, message, data_json, created_at)
                   VALUES (%s, 'claimed', %s, %s, %s)""",
                (
                    token_id,
                    f"Claimed by task #{claimed_by}",
                    json.dumps({"claimed_by": claimed_by}),
                    now,
                ),
            )
        conn.commit()
        _logger.info("claim_token: Token #%d claimed by task #%d", token_id, claimed_by)
    finally:
        conn.close()


def complete_token(
    token_id: int,
    result: str,
    *,
    files_created: Optional[list[str]] = None,
    files_modified: Optional[list[str]] = None,
    tests_added: int = 0,
    tests_passing: int = 0,
) -> None:
    """Mark a token as done with results.

    Raises ValueError if token is not in "claimed" status.
    """
    conn = get_connection()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT status FROM work_tokens WHERE id = %s", (token_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Token #{token_id} not found")
            if row["status"] != "claimed":
                raise ValueError(
                    f"Token #{token_id} is '{row['status']}', not 'claimed'. "
                    f"Only claimed tokens can be completed."
                )

            cur.execute(
                """UPDATE work_tokens
                   SET status = 'done', result_summary = %s,
                       files_created = %s, files_modified = %s,
                       tests_added = %s, tests_passing = %s,
                       completed_at = %s, updated_at = %s
                   WHERE id = %s""",
                (
                    result,
                    json.dumps(files_created) if files_created else None,
                    json.dumps(files_modified) if files_modified else None,
                    tests_added,
                    tests_passing,
                    now,
                    now,
                    token_id,
                ),
            )

            cur.execute(
                """INSERT INTO token_log
                   (token_id, event, message, data_json, created_at)
                   VALUES (%s, 'completed', %s, %s, %s)""",
                (
                    token_id,
                    f"Token completed: {result[:200]}",
                    json.dumps(
                        {
                            "result": result,
                            "files_created": files_created or [],
                            "files_modified": files_modified or [],
                            "tests_added": tests_added,
                            "tests_passing": tests_passing,
                        }
                    ),
                    now,
                ),
            )
        conn.commit()
        _logger.info("complete_token: Token #%d completed: %s", token_id, result[:100])
    finally:
        conn.close()


def expire_token(token_id: int, reason: str = "") -> None:
    """Mark a token as expired (no longer relevant)."""
    conn = get_connection()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE work_tokens
                   SET status = 'expired', result_summary = %s,
                       completed_at = %s, updated_at = %s
                   WHERE id = %s""",
                (reason or "Expired", now, now, token_id),
            )

            cur.execute(
                """INSERT INTO token_log
                   (token_id, event, message, data_json, created_at)
                   VALUES (%s, 'expired', %s, NULL, %s)""",
                (token_id, f"Token expired: {reason}", now),
            )
        conn.commit()
    finally:
        conn.close()


# ── Query API ────────────────────────────────────────────────────────────────


def get_token(token_id: int) -> Optional[dict]:
    """Get a token by ID with its blockers."""
    _ensure_tables()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM work_tokens WHERE id = %s", (token_id,))
            token = cur.fetchone()
            if not token:
                return None

            cur.execute(
                """SELECT tb.*, pt.task_name, pt.status as task_status
                   FROM token_blockers tb
                   JOIN parallel_tasks pt ON pt.id = tb.blocking_task_id
                   WHERE tb.token_id = %s
                   ORDER BY tb.id""",
                (token_id,),
            )
            token["blockers"] = cur.fetchall()
            return token
    finally:
        conn.close()


def list_tokens(
    status: Optional[str] = None, task_id: Optional[int] = None
) -> list[dict]:
    """List tokens, optionally filtered by status or related task."""
    _ensure_tables()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            query = "SELECT * FROM work_tokens"
            conditions = []
            params = []

            if status:
                conditions.append("status = %s")
                params.append(status)
            if task_id:
                conditions.append(
                    "(created_by_task_id = %s OR claimed_by_task_id = %s)"
                )
                params.extend([task_id, task_id])

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY FIELD(status, 'blocked', 'ready', 'claimed', 'done', 'expired'), priority, created_at DESC"
            cur.execute(query, params)
            return cur.fetchall()
    finally:
        conn.close()


def get_tokens_blocked_by(task_id: int) -> list[dict]:
    """Get all tokens blocked by a specific task."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT wt.* FROM work_tokens wt
                   JOIN token_blockers tb ON tb.token_id = wt.id
                   WHERE tb.blocking_task_id = %s AND tb.satisfied = 0
                   ORDER BY wt.priority""",
                (task_id,),
            )
            return cur.fetchall()
    finally:
        conn.close()


def get_ready_tokens() -> list[dict]:
    """Get all tokens ready to be claimed."""
    return list_tokens(status="ready")


def token_stats() -> dict:
    """Get token queue statistics."""
    _ensure_tables()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT status, COUNT(*) as cnt FROM work_tokens GROUP BY status"
            )
            by_status = {r["status"]: r["cnt"] for r in cur.fetchall()}
        return {
            "blocked": by_status.get("blocked", 0),
            "ready": by_status.get("ready", 0),
            "claimed": by_status.get("claimed", 0),
            "done": by_status.get("done", 0),
            "expired": by_status.get("expired", 0),
        }
    finally:
        conn.close()


def get_token_log(token_id: int) -> list[dict]:
    """Get the log entries for a token."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM token_log WHERE token_id = %s ORDER BY created_at",
                (token_id,),
            )
            return cur.fetchall()
    finally:
        conn.close()


# ── Dashboard ────────────────────────────────────────────────────────────────


def print_token_dashboard():
    """Print a formatted view of all work tokens."""
    tokens = list_tokens()
    if not tokens:
        print("\n  No work tokens found.\n")
        return

    status_icons = {
        "blocked": "🔒",
        "ready": "🟢",
        "claimed": "🔧",
        "done": "✅",
        "expired": "⏰",
    }

    print("\n" + "=" * 90)
    print("  WORK TOKENS — BLOCKED WORK WAITING FOR SECTIONS TO COMPLETE")
    print("=" * 90)
    print()
    print(
        f"  {'ID':<4} {'STATUS':<10} {'PRI':<5} {'NAME':<35} {'BLOCKED BY':<20} {'CREATED BY':>10}"
    )
    print(f"  {'─'*4} {'─'*10} {'─'*5} {'─'*35} {'─'*20} {'─'*10}")

    for t in tokens:
        icon = status_icons.get(t["status"], "?")
        name = (
            t["token_name"][:33] + ".."
            if len(t["token_name"]) > 35
            else t["token_name"]
        )
        blocked = f"task #{t.get('created_by_task_id') or '?'}"
        created = (
            f"task #{t['created_by_task_id']}"
            if t.get("created_by_task_id")
            else "manual"
        )
        claimed = (
            f"→ task #{t['claimed_by_task_id']}" if t.get("claimed_by_task_id") else ""
        )
        print(
            f"  {t['id']:<4} {icon} {t['status']:<8} {t['priority']:<5} {name:<35} {blocked:<20} {created:>10} {claimed}"
        )

    stats = token_stats()
    print()
    print(
        f"  🔒 Blocked: {stats['blocked']}  🟢 Ready: {stats['ready']}  "
        f"🔧 Claimed: {stats['claimed']}  ✅ Done: {stats['done']}  ⏰ Expired: {stats['expired']}"
    )
    print("=" * 90)
    print()
