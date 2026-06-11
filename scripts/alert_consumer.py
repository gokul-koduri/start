#!/usr/bin/env python3
"""Alert Consumer — reads from Kafka alerts.triggered and dispatches notifications.

Consumes high-value opportunity alerts from the `alerts.triggered` Kafka topic
and dispatches them through configured notification channels (email, Slack,
Discord, custom webhooks).

Supports:
    - Graceful shutdown (SIGINT/SIGTERM)
    - Dead letter queue for failed alerts (retry 3x)
    - User alert preferences (per-channel enable/disable, min score threshold)
    - Polling fallback when Kafka is unavailable

Usage:
    python scripts/alert_consumer.py                     # Kafka consumer
    python scripts/alert_consumer.py --poll              # DB poll mode (no Kafka)
    python scripts/alert_consumer.py --once              # Process pending alerts and exit

Docker:
    Runs as part of the `stream_processor` service or standalone container.
"""

import argparse
import json
import logging
import os
import signal
import sys
import threading
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import get_project_root, setup_logging, load_config  # noqa: E402

_logger = logging.getLogger("alert_consumer")

# Global shutdown flag
_shutdown = threading.Event()

# ── Alert Queue (in-memory pending alerts) ────────────────

_pending_alerts: list[dict] = []
_pending_lock = threading.Lock()


def _handle_shutdown(signum, frame):
    _logger.info("Received signal %s — initiating graceful shutdown", signum)
    _shutdown.set()


# ── Alert Preferences ─────────────────────────────────────


def _load_preferences(conn) -> dict:
    """Load alert preferences from the alert_preferences table.

    Returns:
        Dict with channel preferences:
        {
            "email_enabled": bool,
            "slack_enabled": bool,
            "min_score_threshold": float,
            "quiet_hours_start": str | None,  # "22:00"
            "quiet_hours_end": str | None,    # "08:00"
            "max_alerts_per_hour": int,
        }
    """
    defaults = {
        "email_enabled": True,
        "slack_enabled": True,
        "discord_enabled": True,
        "webhook_enabled": True,
        "min_score_threshold": 80.0,
        "quiet_hours_start": None,
        "quiet_hours_end": None,
        "max_alerts_per_hour": 20,
    }
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM alert_preferences ORDER BY updated_at DESC LIMIT 1"
        )
        row = cursor.fetchone()
        cursor.close()
        if row:
            prefs = dict(row)
            # Merge with defaults for any missing keys
            for key, val in defaults.items():
                prefs.setdefault(key, val)
            return prefs
    except Exception as e:
        _logger.warning("Could not load alert preferences: %s (using defaults)", e)
    return defaults


def _is_quiet_hours(prefs: dict) -> bool:
    """Check if current time falls within configured quiet hours."""
    start = prefs.get("quiet_hours_start")
    end = prefs.get("quiet_hours_end")
    if not start or not end:
        return False

    now = datetime.now(timezone.utc)
    try:
        current_minute = now.hour * 60 + now.minute
        start_h, start_m = int(start.split(":")[0]), int(start.split(":")[1])
        end_h, end_m = int(end.split(":")[0]), int(end.split(":")[1])
        start_minute = start_h * 60 + start_m
        end_minute = end_h * 60 + end_m

        if start_minute <= end_minute:
            return start_minute <= current_minute < end_minute
        else:
            # Wraps midnight (e.g., 22:00-08:00)
            return current_minute >= start_minute or current_minute < end_minute
    except (ValueError, IndexError):
        return False


# ── Channel Dispatchers ───────────────────────────────────


def _send_email(config: dict, alert: dict) -> tuple[str, str | None]:
    """Send alert via SMTP email."""
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    smtp_host = config.get("smtp_host")
    smtp_port = config.get("smtp_port", 587)
    smtp_user = config.get("smtp_user")
    smtp_password = config.get("smtp_password")
    from_addr = config.get("from_address", smtp_user or "alerts@localhost")
    to_addrs = config.get("to_addresses", [])

    if not smtp_host or not to_addrs:
        return "skipped", "SMTP host or recipients not configured"

    entity = alert.get("entity_name", "Unknown")
    score = alert.get("composite_score", 0)
    reason = _build_reason(alert)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[OIP Alert] {entity} scored {score:.0f} — {reason}"
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_addrs)

    body = (
        f"Startup: {entity}\n"
        f"Score: {score:.1f}\n"
        f"Type: {alert.get('entity_type', 'company')}\n"
        f"Signals: {alert.get('signal_count', 0)}\n"
        f"Trend: {alert.get('trend_direction', 'stable')}\n\n"
        f"Reason: {reason}\n\n"
        f"Triggered: {alert.get('triggered_at', '')}"
    )

    html_body = (
        f"<h3>[OIP Alert] {entity}</h3>"
        f"<p><strong>Score:</strong> {score:.1f} &nbsp; "
        f"<strong>Trend:</strong> {alert.get('trend_direction', 'stable')}</p>"
        f"<p><strong>Reason:</strong> {reason}</p>"
        f"<p>Signals: {alert.get('signal_count', 0)} | "
        f"Type: {alert.get('entity_type', 'company')}</p>"
        f"<hr><small>Triggered: {alert.get('triggered_at', '')}</small>"
    )

    msg.attach(MIMEText(body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        server = smtplib.SMTP(smtp_host, smtp_port, timeout=15)
        server.starttls()
        if smtp_user and smtp_password:
            server.login(smtp_user, smtp_password)
        server.sendmail(from_addr, to_addrs, msg.as_string())
        server.quit()
        return "sent", None
    except Exception as e:
        return "failed", str(e)


def _send_slack(url: str, alert: dict) -> tuple[str, str | None]:
    """Send alert to Slack via incoming webhook."""
    entity = alert.get("entity_name", "Unknown")
    score = alert.get("composite_score", 0)
    reason = _build_reason(alert)

    payload = {
        "text": f":rocket: *[OIP Alert]* {entity} scored {score:.0f} — {reason}",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f":rocket: *[OIP Alert] {entity}*\n"
                        f"*Score:* {score:.1f} | *Trend:* {alert.get('trend_direction', 'stable')}\n"
                        f"*Reason:* {reason}\n"
                        f"*Signals:* {alert.get('signal_count', 0)} | "
                        f"*Type:* {alert.get('entity_type', 'company')}"
                    ),
                },
            }
        ],
    }
    return _post_webhook(url, payload)


def _send_discord(url: str, alert: dict) -> tuple[str, str | None]:
    """Send alert to Discord via webhook."""
    entity = alert.get("entity_name", "Unknown")
    score = alert.get("composite_score", 0)
    reason = _build_reason(alert)

    colors = {
        "critical": 15158332,
        "high": 15105570,
        "medium": 15859728,
        "low": 4289794,
    }
    priority = "high" if score >= 90 else "medium"

    payload = {
        "embeds": [
            {
                "title": f"[OIP Alert] {entity}",
                "description": reason,
                "color": colors.get(priority, 4289794),
                "fields": [
                    {"name": "Score", "value": f"{score:.1f}", "inline": True},
                    {
                        "name": "Trend",
                        "value": alert.get("trend_direction", "stable"),
                        "inline": True,
                    },
                    {
                        "name": "Signals",
                        "value": str(alert.get("signal_count", 0)),
                        "inline": True,
                    },
                ],
            }
        ]
    }
    return _post_webhook(url, payload)


def _send_custom_webhook(url: str, alert: dict) -> tuple[str, str | None]:
    """Send alert to a custom webhook URL."""
    return _post_webhook(url, alert)


def _post_webhook(url: str, payload: dict) -> tuple[str, str | None]:
    """Generic webhook POST."""
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
        return "sent", None
    except Exception as e:
        return "failed", str(e)


def _build_reason(alert: dict) -> str:
    """Build a human-readable reason string from alert attribution."""
    attribution = alert.get("attribution", [])
    if attribution and isinstance(attribution, list):
        top = attribution[0] if attribution else {}
        if isinstance(top, dict):
            signal_type = top.get("signal_type", "multiple signals")
            contribution = top.get("contribution_pct", 0)
            return f"Top signal: {signal_type} ({contribution:.0f}% contribution)"
    return "Composite score exceeded threshold"


# ── Dispatch Logic ────────────────────────────────────────


def dispatch_alert(alert: dict, config: dict, prefs: dict, conn) -> dict:
    """Dispatch a single alert through enabled channels.

    Returns a result dict with dispatch status per channel.
    """
    result = {
        "entity_name": alert.get("entity_name", ""),
        "score": alert.get("composite_score", 0),
        "channels": {},
        "status": "pending",
    }

    channels_config = config.get("channels", {})
    score = alert.get("composite_score", 0)

    # Check min score threshold from preferences
    min_score = prefs.get("min_score_threshold", 80.0)
    if score < min_score:
        result["status"] = "filtered"
        result["reason"] = f"Score {score:.1f} below threshold {min_score}"
        return result

    # Check quiet hours
    if _is_quiet_hours(prefs):
        result["status"] = "deferred"
        result["reason"] = "Within quiet hours"
        return result

    any_sent = False
    any_failed = False

    # Email
    if prefs.get("email_enabled", True):
        email_config = channels_config.get("email", {})
        if email_config.get("enabled") and email_config.get("smtp_host"):
            status, error = _send_email(email_config, alert)
            result["channels"]["email"] = {"status": status, "error": error}
            _log_dispatch(
                conn,
                alert,
                "email",
                email_config.get("to_addresses", []),
                status,
                error,
            )
            if status == "sent":
                any_sent = True
            elif status == "failed":
                any_failed = True

    # Slack
    if prefs.get("slack_enabled", True):
        slack_config = channels_config.get("webhook_slack", {})
        if slack_config.get("enabled") and slack_config.get("url"):
            status, error = _send_slack(slack_config["url"], alert)
            result["channels"]["slack"] = {"status": status, "error": error}
            _log_dispatch(
                conn, alert, "webhook_slack", slack_config["url"], status, error
            )
            if status == "sent":
                any_sent = True
            elif status == "failed":
                any_failed = True

    # Discord
    if prefs.get("discord_enabled", True):
        discord_config = channels_config.get("webhook_discord", {})
        if discord_config.get("enabled") and discord_config.get("url"):
            status, error = _send_discord(discord_config["url"], alert)
            result["channels"]["discord"] = {"status": status, "error": error}
            _log_dispatch(
                conn, alert, "webhook_discord", discord_config["url"], status, error
            )
            if status == "sent":
                any_sent = True
            elif status == "failed":
                any_failed = True

    # Custom webhook
    if prefs.get("webhook_enabled", True):
        custom_config = channels_config.get("webhook_custom", {})
        if custom_config.get("enabled") and custom_config.get("url"):
            status, error = _send_custom_webhook(custom_config["url"], alert)
            result["channels"]["custom"] = {"status": status, "error": error}
            _log_dispatch(
                conn, alert, "webhook_custom", custom_config["url"], status, error
            )
            if status == "sent":
                any_sent = True
            elif status == "failed":
                any_failed = True

    if any_sent:
        result["status"] = "dispatched"
    elif any_failed:
        result["status"] = "failed"
    else:
        result["status"] = "no_channels"

    return result


def _log_dispatch(
    conn, alert: dict, channel: str, destination, status: str, error: str | None
):
    """Log a dispatch attempt to alert_dispatches table (best-effort)."""
    try:
        cursor = conn.cursor()
        dest_str = (
            ", ".join(destination)
            if isinstance(destination, list)
            else str(destination)
        )
        # Try to find an alert_id in llm_optimization_alerts
        alert_id = alert.get("alert_id") or alert.get("id")
        if not alert_id:
            # Insert into llm_optimization_alerts to get an ID
            cursor.execute(
                """INSERT INTO llm_optimization_alerts
                   (alert_type, title, description, priority, created_at)
                   VALUES (%s, %s, %s, %s, %s)""",
                (
                    alert.get("alert_type", "high_value_opportunity"),
                    f"[OIP Alert] {alert.get('entity_name', 'Unknown')} scored {alert.get('composite_score', 0):.0f}",
                    _build_reason(alert),
                    "high" if alert.get("composite_score", 0) >= 90 else "medium",
                    datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            alert_id = cursor.lastrowid

        cursor.execute(
            """INSERT INTO alert_dispatches
               (alert_id, channel, destination, dispatch_status, error_message, dispatched_at)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (
                alert_id,
                channel,
                dest_str[:500],
                status,
                error,
                datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        conn.commit()
        cursor.close()
    except Exception as e:
        _logger.debug("Could not log dispatch: %s", e)


# ── Dead Letter Queue ─────────────────────────────────────


def _move_to_dlq(conn, alert: dict, error: str, attempts: int):
    """Move a failed alert to the dead letter queue table."""
    try:
        cursor = conn.cursor()
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS alert_dead_letters (
                id              INT PRIMARY KEY AUTO_INCREMENT,
                alert_type      VARCHAR(100),
                entity_name     VARCHAR(255),
                entity_type     VARCHAR(50),
                composite_score DOUBLE,
                alert_payload   JSON,
                error_message   TEXT,
                attempts        INT DEFAULT 1,
                last_attempt_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        )
        cursor.execute(
            """INSERT INTO alert_dead_letters
               (alert_type, entity_name, entity_type, composite_score,
                alert_payload, error_message, attempts, last_attempt_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                alert.get("alert_type", "unknown"),
                alert.get("entity_name", ""),
                alert.get("entity_type", ""),
                alert.get("composite_score", 0),
                json.dumps(alert, default=str),
                error[:1000],
                attempts,
                datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        conn.commit()
        cursor.close()
        _logger.info(
            "Moved alert for '%s' to dead letter queue (attempts=%d)",
            alert.get("entity_name"),
            attempts,
        )
    except Exception as e:
        _logger.error("Failed to move alert to DLQ: %s", e)


def _retry_dlq_alerts(conn, config: dict, prefs: dict, max_retries: int = 3):
    """Re-attempt delivery of dead-lettered alerts that haven't exceeded max retries."""
    try:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT id, alert_payload, attempts, error_message
               FROM alert_dead_letters
               WHERE attempts < %s
               ORDER BY created_at ASC
               LIMIT 50""",
            (max_retries,),
        )
        rows = cursor.fetchall()

        retried = 0
        recovered = 0
        for row in rows:
            try:
                alert = json.loads(row["alert_payload"])
            except (json.JSONDecodeError, TypeError):
                continue

            result = dispatch_alert(alert, config, prefs, conn)
            retried += 1

            if result["status"] == "dispatched":
                # Remove from DLQ on success
                cursor.execute(
                    "DELETE FROM alert_dead_letters WHERE id = %s", (row["id"],)
                )
                recovered += 1
            else:
                # Increment attempts
                cursor.execute(
                    "UPDATE alert_dead_letters SET attempts = attempts + 1, last_attempt_at = %s WHERE id = %s",
                    (
                        datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                        row["id"],
                    ),
                )

        if retried > 0:
            _logger.info("DLQ retry: %d retried, %d recovered", retried, recovered)
            conn.commit()

        cursor.close()
    except Exception as e:
        _logger.error("DLQ retry failed: %s", e)


# ── Kafka Consumer ────────────────────────────────────────


def _consume_from_kafka(config: dict, prefs: dict, conn):
    """Consume alerts from Kafka alerts.triggered topic."""
    try:
        from kafka import KafkaConsumer
    except ImportError:
        _logger.error(
            "kafka-python-ng not installed. Use --poll mode or install: pip install kafka-python-ng"
        )
        return

    stream_config = config.get("stream", {})
    kafka_brokers = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    topic = stream_config.get("topics", {}).get("alerts", "alerts.triggered")

    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=kafka_brokers.split(","),
        group_id="alert-consumer",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="latest",
        enable_auto_commit=True,
        consumer_timeout_ms=5000,
    )

    _logger.info("Kafka consumer started: topic=%s, brokers=%s", topic, kafka_brokers)

    try:
        while not _shutdown.is_set():
            try:
                messages = consumer.poll(timeout_ms=5000)
                for tp, msgs in messages.items():
                    for msg in msgs:
                        alert = msg.value
                        _logger.info(
                            "Alert received: %s (score=%.1f)",
                            alert.get("entity_name", ""),
                            alert.get("composite_score", 0),
                        )
                        result = dispatch_alert(alert, config, prefs, conn)
                        if result["status"] == "failed":
                            _move_to_dlq(conn, alert, "All channels failed", 1)

                        # Periodically retry DLQ
                        _retry_dlq_alerts(conn, config, prefs)

            except StopIteration:
                pass
            except Exception as e:
                _logger.error("Kafka consumer error: %s", e)
                _shutdown.wait(5)
    finally:
        consumer.close()
        _logger.info("Kafka consumer closed")


# ── DB Poll Mode ──────────────────────────────────────────


def _poll_from_db(config: dict, prefs: dict, conn, interval: int = 60):
    """Poll opportunity_scores for high-value entities not yet alerted.

    Fallback mode when Kafka is not available.
    """
    _logger.info("DB poll mode started (interval=%ds)", interval)
    min_score = prefs.get("min_score_threshold", 80.0)

    last_alerted_ids: set[int] = set()

    while not _shutdown.is_set():
        try:
            cursor = conn.cursor()

            # Find high-scoring entities that haven't been alerted recently
            cursor.execute(
                """SELECT os.id, os.entity_name, os.entity_type, os.composite_score,
                          os.signal_count, os.trend_direction, os.attribution_json,
                          os.last_updated
                   FROM opportunity_scores os
                   WHERE os.composite_score >= %s
                     AND os.last_updated >= DATE_SUB(NOW(), INTERVAL 2 HOUR)
                   ORDER BY os.composite_score DESC
                   LIMIT 20""",
                (min_score,),
            )
            rows = cursor.fetchall()
            cursor.close()

            for row in rows:
                if row["id"] in last_alerted_ids:
                    continue

                alert = {
                    "alert_type": "high_value_opportunity",
                    "entity_name": row["entity_name"],
                    "entity_type": row["entity_type"],
                    "composite_score": row["composite_score"],
                    "signal_count": row["signal_count"],
                    "trend_direction": row["trend_direction"],
                    "attribution": json.loads(row.get("attribution_json", "[]")),
                    "triggered_at": datetime.now(timezone.utc).isoformat(),
                }

                _logger.info(
                    "Poll alert: %s (score=%.1f)",
                    alert["entity_name"],
                    alert["composite_score"],
                )
                result = dispatch_alert(alert, config, prefs, conn)
                if result["status"] == "failed":
                    _move_to_dlq(conn, alert, "All channels failed", 1)
                last_alerted_ids.add(row["id"])

            # Keep only recent IDs to avoid memory growth
            if len(last_alerted_ids) > 1000:
                last_alerted_ids = set(list(last_alerted_ids)[-500:])

            # Retry DLQ
            _retry_dlq_alerts(conn, config, prefs)

        except Exception as e:
            _logger.error("DB poll error: %s", e)

        _shutdown.wait(interval)


# ── One-shot Mode ─────────────────────────────────────────


def run_once(config: dict):
    """Process all pending high-value opportunities and exit."""
    from db.connection import get_connection
    from db import schema

    conn = get_connection()
    schema.init_schema(conn)

    prefs = _load_preferences(conn)
    min_score = prefs.get("min_score_threshold", 80.0)

    cursor = conn.cursor()
    cursor.execute(
        """SELECT os.entity_name, os.entity_type, os.composite_score,
                  os.signal_count, os.trend_direction, os.attribution_json
           FROM opportunity_scores os
           WHERE os.composite_score >= %s
           ORDER BY os.composite_score DESC
           LIMIT 50""",
        (min_score,),
    )
    rows = cursor.fetchall()
    cursor.close()

    if not rows:
        _logger.info(
            "No alerts to process (no entities above threshold %.1f)", min_score
        )
        conn.close()
        return

    _logger.info("Processing %d potential alerts...", len(rows))
    dispatched = 0
    failed = 0

    for row in rows:
        alert = {
            "alert_type": "high_value_opportunity",
            "entity_name": row["entity_name"],
            "entity_type": row["entity_type"],
            "composite_score": row["composite_score"],
            "signal_count": row["signal_count"],
            "trend_direction": row["trend_direction"],
            "attribution": json.loads(row.get("attribution_json", "[]")),
            "triggered_at": datetime.now(timezone.utc).isoformat(),
        }

        result = dispatch_alert(alert, config, prefs, conn)
        if result["status"] == "dispatched":
            dispatched += 1
        elif result["status"] == "failed":
            failed += 1
            _move_to_dlq(conn, alert, "All channels failed", 1)

    conn.close()
    _logger.info(
        "One-shot complete: %d dispatched, %d failed, %d total",
        dispatched,
        failed,
        len(rows),
    )


# ── Main ──────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Alert Consumer for Opportunity Intelligence Platform"
    )
    parser.add_argument(
        "--poll", action="store_true", help="Poll DB mode (no Kafka needed)"
    )
    parser.add_argument(
        "--once", action="store_true", help="Process pending alerts and exit"
    )
    args = parser.parse_args()

    setup_logging()

    # Load config and extract alert_consumer section
    full_config = load_config()
    # Reuse alert_dispatcher config for channel settings
    config = full_config.get("alert_dispatcher", {})

    signal.signal(signal.SIGINT, _handle_shutdown)
    signal.signal(signal.SIGTERM, _handle_shutdown)

    _logger.info("Alert Consumer — Opportunity Intelligence Platform")
    _logger.info("Project root: %s", get_project_root())

    if args.once:
        run_once(config)
        return

    # Connect to DB for preferences and logging
    from db.connection import get_connection
    from db import schema

    conn = get_connection()
    schema.init_schema(conn)

    prefs = _load_preferences(conn)
    _logger.info(
        "Preferences loaded: min_score=%.1f, email=%s, slack=%s",
        prefs.get("min_score_threshold", 80.0),
        prefs.get("email_enabled", True),
        prefs.get("slack_enabled", True),
    )

    if args.poll:
        _poll_from_db(config, prefs, conn)
    else:
        _consume_from_kafka(config, prefs, conn)

    conn.close()
    _logger.info("Alert consumer shutting down")


if __name__ == "__main__":
    main()
