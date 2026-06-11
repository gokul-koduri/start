"""Email worker — drains the outbound_emails queue via SMTP.

Run as a standalone process or via the orchestrator:
    python -m agents.email_worker           # one-shot drain
    python -m agents.email_worker --loop     # continuous polling
    python -m agents.email_worker --loop --interval 30

Design choices:
  - Batch sending: drain up to `batch_size` emails per cycle
  - Rate limiting: `delay_between_emails` seconds between sends
  - Exponential backoff: next_retry_at = now + 2^attempts minutes
  - Dead letter: after max_attempts, status → 'dead' (not deleted)
  - Suppression: bounces → auto-add to email_suppressions
  - Connection reuse: single SMTP session per batch (not per email)
"""

import argparse
import logging
import os
import smtplib
import time
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate, make_msgid

from db.connection import get_connection

_logger = logging.getLogger(__name__)

# Defaults (overridable via config)
_DEFAULT_BATCH_SIZE = 50
_DEFAULT_DELAY = 0.5  # seconds between sends
_DEFAULT_LOOP_INTERVAL = 30  # seconds between polling cycles


def _get_smtp_config() -> dict:
    """Load SMTP config from env vars."""
    return {
        "host": os.environ.get("SMTP_HOST", ""),
        "port": int(os.environ.get("SMTP_PORT", "587")),
        "user": os.environ.get("SMTP_USER", ""),
        "password": os.environ.get("SMTP_PASSWORD", ""),
        "from_address": os.environ.get("SMTP_FROM", "noreply@localhost"),
    }


def _smtp_connect(cfg: dict) -> smtplib.SMTP:
    """Create and return an authenticated SMTP connection."""
    server = smtplib.SMTP(cfg["host"], cfg["port"], timeout=30)
    server.ehlo()
    server.starttls()
    server.ehlo()
    if cfg["user"] and cfg["password"]:
        server.login(cfg["user"], cfg["password"])
    return server


def _build_mime(email_row: dict, cfg: dict) -> MIMEMultipart:
    """Build a multipart/alternative MIME message (plain + HTML)."""
    msg = MIMEMultipart("alternative")

    msg["Subject"] = email_row["subject"]
    msg["From"] = formataddr(("Opportunity Intelligence Platform", cfg["from_address"]))
    if email_row.get("recipient_name"):
        msg["To"] = formataddr((email_row["recipient_name"], email_row["recipient"]))
    else:
        msg["To"] = email_row["recipient"]
    if email_row.get("reply_to"):
        msg["Reply-To"] = email_row["reply_to"]
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(
        domain=cfg["from_address"].split("@")[-1] or "localhost"
    )

    # Plain text part
    msg.attach(MIMEText(email_row["plain_body"], "plain", "utf-8"))
    # HTML part (preferred by most clients)
    msg.attach(MIMEText(email_row["html_body"], "html", "utf-8"))

    return msg


def _mark_status(
    conn,
    email_id: int,
    status: str,
    error: str | None = None,
    message_id: str | None = None,
) -> None:
    """Update email status and log the delivery event."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    with conn.cursor() as cur:
        cur.execute(
            """UPDATE outbound_emails
               SET status = %s, last_error = %s, message_id = %s,
                   updated_at = %s
               WHERE id = %s""",
            (status, error, message_id, now, email_id),
        )

        # Log event
        event_type = status  # sent, failed, dead
        detail = error or f"Status changed to {status}"
        cur.execute(
            """INSERT INTO email_delivery_log
               (outbound_email_id, event_type, detail, created_at)
               VALUES (%s, %s, %s, %s)""",
            (email_id, event_type, detail, now),
        )
    conn.commit()


def _schedule_retry(conn, email_id: int, attempts: int) -> None:
    """Calculate next retry with exponential backoff and update row."""
    delay_minutes = min(2**attempts, 16)  # cap at 16 minutes
    next_retry = datetime.now(timezone.utc) + __import__("datetime").timedelta(
        minutes=delay_minutes
    )
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    next_str = next_retry.strftime("%Y-%m-%d %H:%M:%S")

    with conn.cursor() as cur:
        cur.execute(
            """UPDATE outbound_emails
               SET status = 'queued', attempts = %s, last_attempt_at = %s,
                   next_retry_at = %s, updated_at = %s
               WHERE id = %s""",
            (attempts, now, next_str, now, email_id),
        )

        cur.execute(
            """INSERT INTO email_delivery_log
               (outbound_email_id, event_type, detail, created_at)
               VALUES (%s, 'deferred', 'Retry scheduled (attempt %d, next at %s)', %s)""",
            (email_id, attempts, next_str, now),
        )
    conn.commit()


def drain_queue(
    batch_size: int = _DEFAULT_BATCH_SIZE, delay_between: float = _DEFAULT_DELAY
) -> dict:
    """Drain the outbound_emails queue. Returns stats dict."""
    cfg = _get_smtp_config()

    if not cfg["host"]:
        _logger.warning("drain_queue: SMTP_HOST not configured, skipping")
        return {"sent": 0, "failed": 0, "retried": 0, "dead": 0, "skipped": 0}

    stats = {"sent": 0, "failed": 0, "retried": 0, "dead": 0, "skipped": 0}
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    # Claim a batch of emails
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Atomically claim emails: set status='sending' for up to batch_size
            cur.execute(
                """UPDATE outbound_emails
                   SET status = 'sending', last_attempt_at = %s, updated_at = %s
                   WHERE status = 'queued'
                     AND (next_retry_at IS NULL OR next_retry_at <= %s)
                     AND attempts < max_attempts
                   ORDER BY priority ASC, created_at ASC
                   LIMIT %s""",
                (now_str, now_str, now_str, batch_size),
            )
            claimed = cur.rowcount
            conn.commit()

            if claimed == 0:
                _logger.debug("drain_queue: No emails to send")
                return stats

            # Fetch claimed emails
            cur.execute(
                """SELECT id, recipient, recipient_name, subject,
                          plain_body, html_body, from_address, reply_to,
                          attempts, max_attempts
                   FROM outbound_emails
                   WHERE status = 'sending' AND last_attempt_at = %s""",
                (now_str,),
            )
            emails = cur.fetchall()
    finally:
        conn.close()

    _logger.info("drain_queue: Claimed %d emails", len(emails))

    # Connect SMTP once for the batch
    server = None
    try:
        server = _smtp_connect(cfg)
    except Exception as e:
        _logger.error("drain_queue: SMTP connection failed: %s", e)
        # Revert all claimed emails back to queued
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE outbound_emails SET status = 'queued', updated_at = %s
                       WHERE status = 'sending'""",
                    (now_str,),
                )
            conn.commit()
        finally:
            conn.close()
        stats["failed"] = len(emails)
        return stats

    # Send each email
    for email_row in emails:
        email_id = email_row["id"]
        attempts = email_row["attempts"] + 1

        try:
            mime = _build_mime(email_row, cfg)
            server.sendmail(
                email_row["from_address"] or cfg["from_address"],
                [email_row["recipient"]],
                mime.as_string(),
            )

            conn = get_connection()
            try:
                _mark_status(conn, email_id, "sent", message_id=mime["Message-ID"])
            finally:
                conn.close()

            stats["sent"] += 1
            _logger.info(
                "drain_queue: Sent email id=%d to %s", email_id, email_row["recipient"]
            )

        except smtplib.SMTPRecipientsRefused as e:
            # Hard bounce — suppress and mark dead
            _logger.warning(
                "drain_queue: Recipient refused %s: %s", email_row["recipient"], e
            )
            conn = get_connection()
            try:
                _mark_status(
                    conn, email_id, "dead", error=f"SMTPRecipientsRefused: {e}"
                )
                # Auto-suppress
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO email_suppressions (email, reason, detail)
                           VALUES (%s, 'bounce', %s)
                           ON DUPLICATE KEY UPDATE detail = VALUES(detail)""",
                        (email_row["recipient"], str(e)[:500]),
                    )
                conn.commit()
            finally:
                conn.close()
            stats["dead"] += 1

        except smtplib.SMTPServerDisconnected:
            # Connection lost — try reconnecting
            _logger.warning("drain_queue: SMTP disconnected, reconnecting")
            try:
                server = _smtp_connect(cfg)
            except Exception as re:
                _logger.error("drain_queue: Reconnect failed: %s", re)
                # Put remaining back in queue
                break

        except Exception as e:
            _logger.error("drain_queue: Send failed for id=%d: %s", email_id, e)

            conn = get_connection()
            try:
                if attempts >= email_row["max_attempts"]:
                    _mark_status(conn, email_id, "dead", error=str(e)[:500])
                    stats["dead"] += 1
                else:
                    _schedule_retry(conn, email_id, attempts)
                    stats["retried"] += 1
            finally:
                conn.close()

            stats["failed"] += 1

        # Rate limit between sends
        if delay_between > 0:
            time.sleep(delay_between)

    # Close SMTP session
    try:
        server.quit()
    except Exception:
        pass

    _logger.info(
        "drain_queue: Done — sent=%d failed=%d retried=%d dead=%d",
        stats["sent"],
        stats["failed"],
        stats["retried"],
        stats["dead"],
    )
    return stats


def run_loop(
    interval: int = _DEFAULT_LOOP_INTERVAL, batch_size: int = _DEFAULT_BATCH_SIZE
) -> None:
    """Run the email worker in a continuous loop."""
    _logger.info(
        "email_worker: Starting loop (interval=%ds, batch=%d)", interval, batch_size
    )
    while True:
        try:
            drain_queue(batch_size=batch_size)
        except Exception as e:
            _logger.error("email_worker: Loop error: %s", e)
        time.sleep(interval)


# ── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="Email worker — drains outbound queue")
    parser.add_argument("--loop", action="store_true", help="Run continuously")
    parser.add_argument(
        "--interval", type=int, default=30, help="Seconds between polls (default: 30)"
    )
    parser.add_argument(
        "--batch-size", type=int, default=50, help="Emails per batch (default: 50)"
    )
    args = parser.parse_args()

    if args.loop:
        run_loop(interval=args.interval, batch_size=args.batch_size)
    else:
        stats = drain_queue(batch_size=args.batch_size)
        print(f"Done: {stats}")
