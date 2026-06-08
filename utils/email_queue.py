"""Email queue — database-backed email delivery with retry and suppression.

All email sending goes through the outbound_emails table. Agents queue emails;
the EmailWorker drains the queue with exponential backoff, rate limiting,
and bounce/complaint tracking via email_suppressions.

Design choices:
  - HTML + plain text (multipart/alternative) — maximizes deliverability
  - Database queue, not Redis — survives restarts, queryable, auditable
  - Exponential backoff — 2^attempt minutes (1, 2, 4, 8, 16 min)
  - Suppression list — bounces and complaints auto-suppress future sends
  - Jinja2 templates with fallback — graceful degradation if template missing
"""

import json
import logging
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Iterable

from db.connection import get_connection

_logger = logging.getLogger(__name__)

# Exponential backoff: 2^attempt minutes
_RETRY_DELAYS = {
    0: timedelta(minutes=1),
    1: timedelta(minutes=2),
    2: timedelta(minutes=4),
    3: timedelta(minutes=8),
    4: timedelta(minutes=16),
}
_DEFAULT_RETRY = timedelta(minutes=16)

# ── Public API ──────────────────────────────────────────────────────────────


def queue_email(
    recipient: str,
    subject: str,
    email_type: str,
    plain_body: str,
    html_body: str,
    *,
    recipient_name: str | None = None,
    from_address: str | None = None,
    reply_to: str | None = None,
    priority: int = 5,
    related_id: str | None = None,
    metadata: dict | None = None,
) -> int:
    """Insert an email into the outbound_emails queue.

    Returns the outbound_email_id.
    Raises ValueError if recipient is suppressed.
    """
    if _is_suppressed(recipient):
        raise ValueError(f"Recipient {recipient} is suppressed (bounce/complaint/unsubscribe)")

    from_addr = from_address or os.environ.get("SMTP_FROM", "noreply@localhost")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            now = datetime.now(timezone.utc)
            cur.execute(
                """INSERT INTO outbound_emails
                   (recipient, recipient_name, subject, email_type,
                    plain_body, html_body, from_address, reply_to,
                    status, priority, attempts, max_attempts,
                    next_retry_at, related_id, metadata_json, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s,
                           'queued', %s, 0, 5,
                           %s, %s, %s, %s)""",
                (
                    recipient,
                    recipient_name,
                    subject,
                    email_type,
                    plain_body,
                    html_body,
                    from_addr,
                    reply_to,
                    priority,
                    now.strftime("%Y-%m-%d %H:%M:%S"),  # next_retry_at = now
                    related_id,
                    json.dumps(metadata) if metadata else None,
                    now.strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            email_id = cur.lastrowid

            # Log the queue event
            cur.execute(
                """INSERT INTO email_delivery_log
                   (outbound_email_id, event_type, detail, created_at)
                   VALUES (%s, 'queued', 'Email queued for delivery', %s)""",
                (email_id, now.strftime("%Y-%m-%d %H:%M:%S")),
            )
        conn.commit()
        _logger.info("queue_email: Queued %s email id=%d to %s", email_type, email_id, recipient)
        return email_id
    finally:
        conn.close()


def queue_bulk(recipients: Iterable[str], subject: str, email_type: str,
               plain_body: str, html_body: str, **kwargs) -> list[int]:
    """Queue the same email to multiple recipients.

    Skips suppressed addresses silently. Returns list of queued email IDs.
    """
    ids = []
    for r in recipients:
        try:
            eid = queue_email(r, subject, email_type, plain_body, html_body, **kwargs)
            ids.append(eid)
        except ValueError:
            _logger.info("queue_bulk: Skipping suppressed recipient %s", r)
    return ids


def get_active_recipients() -> list[dict]:
    """Get Pro/Enterprise users with emails for report delivery."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT u.id, u.email, u.display_name, ul.tier
                   FROM users u
                   JOIN user_licenses ul ON ul.user_id = u.id
                   WHERE ul.status = 'active'
                     AND ul.tier IN ('pro', 'enterprise')
                     AND u.is_active = 1
                     AND u.email IS NOT NULL"""
            )
            return cur.fetchall()
    finally:
        conn.close()


# ── Suppression ──────────────────────────────────────────────────────────────


def _is_suppressed(email: str) -> bool:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM email_suppressions WHERE email = %s LIMIT 1",
                (email,),
            )
            return cur.fetchone() is not None
    finally:
        conn.close()


def add_suppression(email: str, reason: str, detail: str | None = None) -> None:
    """Add email to suppression list (bounce, complaint, unsubscribe)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO email_suppressions (email, reason, detail)
                   VALUES (%s, %s, %s)
                   ON DUPLICATE KEY UPDATE reason = VALUES(reason), detail = VALUES(detail)""",
                (email, reason, detail),
            )
        conn.commit()
        _logger.info("add_suppression: Suppressed %s (%s)", email, reason)
    finally:
        conn.close()


def remove_suppression(email: str) -> None:
    """Remove email from suppression list (e.g., user re-subscribes)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM email_suppressions WHERE email = %s", (email,))
        conn.commit()
    finally:
        conn.close()


# ── Template rendering ──────────────────────────────────────────────────────

_template_dir = Path(__file__).resolve().parent.parent / "templates" / "email"


def render_template(template_name: str, context: dict) -> str:
    """Render an email HTML template using Jinja2 (with fallback).

    Falls back to basic variable substitution if Jinja2 is not installed.
    """
    template_path = _template_dir / template_name
    if not template_path.exists():
        _logger.warning("render_template: Template %s not found at %s", template_name, template_path)
        return f"<html><body><p>Template '{template_name}' not found.</p></body></html>"

    template_text = template_path.read_text(encoding="utf-8")

    try:
        import jinja2
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(_template_dir)),
            autoescape=True,
            undefined=jinja2.Undefined,
        )
        tpl = env.get_template(template_name)
        return tpl.render(**context)
    except ImportError:
        _logger.debug("render_template: Jinja2 not installed, using basic substitution")
        # Basic {{ var }} substitution only
        result = template_text
        for key, val in context.items():
            if isinstance(val, str):
                result = result.replace("{{ " + key + " }}", val)
        return result


def plain_from_html(html: str) -> str:
    """Extract a reasonable plain text version from HTML.

    Strips tags, collapses whitespace, returns readable text.
    For important emails, provide a hand-written plain_body instead.
    """
    import re
    text = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</h[1-6]>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</tr>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</td>", " | ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ── Queue statistics ────────────────────────────────────────────────────────


def queue_stats() -> dict:
    """Get email queue statistics for monitoring."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT status, COUNT(*) as cnt FROM outbound_emails
                   GROUP BY status"""
            )
            by_status = {r["status"]: r["cnt"] for r in cur.fetchall()}

            cur.execute(
                """SELECT COUNT(*) as cnt FROM email_suppressions"""
            )
            suppressed = cur.fetchone()["cnt"]

            cur.execute(
                """SELECT COUNT(*) as cnt FROM email_delivery_log
                   WHERE event_type = 'sent'
                     AND created_at > DATE_SUB(NOW(), INTERVAL 24 HOUR)"""
            )
            sent_24h = cur.fetchone()["cnt"]

            cur.execute(
                """SELECT COUNT(*) as cnt FROM email_delivery_log
                   WHERE event_type = 'bounced'
                     AND created_at > DATE_SUB(NOW(), INTERVAL 24 HOUR)"""
            )
            bounced_24h = cur.fetchone()["cnt"]

        return {
            "queued": by_status.get("queued", 0),
            "sending": by_status.get("sending", 0),
            "sent": by_status.get("sent", 0),
            "failed": by_status.get("failed", 0),
            "dead": by_status.get("dead", 0),
            "suppressed": suppressed,
            "sent_24h": sent_24h,
            "bounced_24h": bounced_24h,
        }
    finally:
        conn.close()
