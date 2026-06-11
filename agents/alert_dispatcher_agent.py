"""Alert Dispatcher Agent — dispatches notifications via email and webhooks.

Dispatches undismissed alerts from llm_optimization_alerts and rule-based
alerts (data freshness, pipeline failures) through configured channels.

Channels:
    - Email via SMTP (Python stdlib smtplib)
    - Slack webhook (HTTP POST)
    - Discord webhook (HTTP POST)
    - Custom webhook (HTTP POST)

Graceful degradation: If a channel is not configured, it is skipped with a
warning log rather than causing a pipeline failure.

Runs in the weekly pipeline after llm_cost_optimizer.
"""

import json
import logging
import smtplib
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from agents.base import AgentResult, BaseAgent
from db.connection import get_connection
from db import schema

_logger = logging.getLogger(__name__)


class AlertDispatcherAgent(BaseAgent):
    """Dispatches alerts through email and webhook channels.

    Config options:
        channels.email.enabled: bool — enable email dispatch
        channels.email.smtp_host: str — SMTP server hostname
        channels.email.smtp_port: int — SMTP port (default 587)
        channels.email.smtp_user: str — SMTP username
        channels.email.smtp_password: str — SMTP password
        channels.email.from_address: str — sender email
        channels.email.to_addresses: list[str] — recipient list
        channels.webhook_slack.enabled: bool — enable Slack webhook
        channels.webhook_slack.url: str — Slack webhook URL
        channels.webhook_discord.enabled: bool — enable Discord webhook
        channels.webhook_discord.url: str — Discord webhook URL
        channels.webhook_custom.enabled: bool — enable custom webhook
        channels.webhook_custom.url: str — custom webhook URL
        max_alerts_per_run: int — max alerts to dispatch per run (default 50)
    """

    @property
    def name(self) -> str:
        return "alert_dispatcher"

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        max_alerts = self.config.get("max_alerts_per_run", 50)
        channels_config = self.config.get("channels", {})

        _logger.info(
            "AlertDispatcherAgent: Starting dispatch (max %d alerts)", max_alerts
        )

        try:
            conn = get_connection()
            schema.init_schema(conn)
        except Exception as e:
            _logger.error("AlertDispatcherAgent: Cannot connect to DB: %s", e)
            return AgentResult(agent_name=self.name, status="failed", errors=[str(e)])

        try:
            cursor = conn.cursor()
            dispatched = 0
            failed = 0

            # Fetch undispatched, undismissed alerts
            cursor.execute(
                """SELECT a.id, a.alert_type, a.title, a.description,
                          a.affected_models, a.estimated_savings_pct, a.priority,
                          a.created_at
                   FROM llm_optimization_alerts a
                   LEFT JOIN alert_dispatches d ON d.alert_id = a.id
                   WHERE a.dismissed = 0 AND d.id IS NULL
                   ORDER BY a.priority DESC, a.created_at DESC
                   LIMIT %s""",
                (max_alerts,),
            )
            alerts = [dict(r) for r in cursor.fetchall()]

            # Also check rule-based alerts (data freshness, pipeline failures)
            rule_alerts = self._check_rule_alerts(conn, cursor)
            alerts.extend(rule_alerts)

            if not alerts:
                _logger.info("AlertDispatcherAgent: No alerts to dispatch")
                return AgentResult(
                    agent_name=self.name,
                    status="success",
                    data={"dispatched": 0, "failed": 0, "records_affected": 0},
                )

            # Seed default alert rules if table is empty
            self._seed_default_rules(cursor)

            # Dispatch each alert through enabled channels
            for alert in alerts[:max_alerts]:
                alert_id = alert.get("id")
                alert.get("title", "Unknown Alert")
                alert.get("description", "")

                # Email channel
                email_config = channels_config.get("email", {})
                if email_config.get("enabled"):
                    status, error = self._send_email(email_config, alert)
                    self._log_dispatch(
                        cursor,
                        alert_id,
                        "email",
                        email_config.get("to_addresses", []),
                        status,
                        error,
                    )
                    if status == "sent":
                        dispatched += 1
                    else:
                        failed += 1
                else:
                    _logger.debug(
                        "AlertDispatcherAgent: Email channel not configured, skipping"
                    )

                # Slack webhook
                slack_config = channels_config.get("webhook_slack", {})
                if slack_config.get("enabled") and slack_config.get("url"):
                    status, error = self._send_slack_webhook(slack_config["url"], alert)
                    self._log_dispatch(
                        cursor,
                        alert_id,
                        "webhook_slack",
                        slack_config["url"],
                        status,
                        error,
                    )
                    if status == "sent":
                        dispatched += 1
                    else:
                        failed += 1

                # Discord webhook
                discord_config = channels_config.get("webhook_discord", {})
                if discord_config.get("enabled") and discord_config.get("url"):
                    status, error = self._send_discord_webhook(
                        discord_config["url"], alert
                    )
                    self._log_dispatch(
                        cursor,
                        alert_id,
                        "webhook_discord",
                        discord_config["url"],
                        status,
                        error,
                    )
                    if status == "sent":
                        dispatched += 1
                    else:
                        failed += 1

                # Custom webhook
                custom_config = channels_config.get("webhook_custom", {})
                if custom_config.get("enabled") and custom_config.get("url"):
                    status, error = self._send_webhook(custom_config["url"], alert)
                    self._log_dispatch(
                        cursor,
                        alert_id,
                        "webhook_custom",
                        custom_config["url"],
                        status,
                        error,
                    )
                    if status == "sent":
                        dispatched += 1
                    else:
                        failed += 1

            conn.commit()

            _logger.info(
                "AlertDispatcherAgent: Done — %d dispatched, %d failed out of %d alerts",
                dispatched,
                failed,
                len(alerts),
            )

            return AgentResult(
                agent_name=self.name,
                status="success" if failed == 0 else "partial",
                data={
                    "dispatched": dispatched,
                    "failed": failed,
                    "total_alerts": len(alerts),
                    "records_affected": dispatched,
                },
                errors=[f"{failed} alerts failed to dispatch"] if failed > 0 else [],
            )

        except Exception as e:
            _logger.error("AlertDispatcherAgent: Error: %s", e)
            return AgentResult(agent_name=self.name, status="failed", errors=[str(e)])
        finally:
            conn.close()

    # ── Rule-based alert generation ──

    def _check_rule_alerts(self, conn, cursor) -> list[dict]:
        """Check configurable rules and generate alerts for triggered conditions."""
        alerts = []
        now = datetime.now(timezone.utc)

        # Check if alert_rules table exists and has rules
        cursor.execute("SELECT COUNT(*) as cnt FROM alert_rules WHERE enabled = 1")
        row = cursor.fetchone()
        if not row or row["cnt"] == 0:
            return alerts

        cursor.execute(
            """SELECT id, rule_name, rule_type, condition_json, channel,
                      cooldown_minutes, last_triggered_at
               FROM alert_rules WHERE enabled = 1"""
        )
        rules = [dict(r) for r in cursor.fetchall()]

        for rule in rules:
            cooldown = timedelta(minutes=rule.get("cooldown_minutes", 1440))
            last_triggered = rule.get("last_triggered_at")
            if last_triggered:
                try:
                    lt = datetime.strptime(last_triggered, "%Y-%m-%d %H:%M:%S").replace(
                        tzinfo=timezone.utc
                    )
                    if now - lt < cooldown:
                        continue
                except ValueError:
                    pass

            condition = {}
            try:
                condition = json.loads(rule.get("condition_json", "{}"))
            except json.JSONDecodeError:
                continue

            triggered = False
            detail = ""

            if rule["rule_type"] == "data_freshness":
                triggered, detail = self._check_data_freshness(cursor, condition)

            elif rule["rule_type"] == "pipeline_failure":
                triggered, detail = self._check_pipeline_failure(cursor, condition)

            if triggered:
                alerts.append(
                    {
                        "id": None,
                        "alert_type": rule["rule_type"],
                        "title": f"Rule triggered: {rule['rule_name']}",
                        "description": detail,
                        "affected_models": [],
                        "priority": condition.get("priority", "medium"),
                        "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )
                cursor.execute(
                    "UPDATE alert_rules SET last_triggered_at = %s WHERE id = %s",
                    (now.strftime("%Y-%m-%d %H:%M:%S"), rule["id"]),
                )

        return alerts

    def _check_data_freshness(self, cursor, condition: dict) -> tuple[bool, str]:
        """Check if data collectors have run recently."""
        stale_hours = condition.get("stale_hours", 48)
        threshold = datetime.now(timezone.utc) - timedelta(hours=stale_hours)
        cutoff = threshold.strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute(
            """SELECT collector_name, started_at, status FROM collection_runs
               WHERE started_at >= %s ORDER BY started_at DESC""",
            (cutoff,),
        )
        recent = cursor.fetchall()
        collectors_run = {r["collector_name"] for r in recent}

        expected = condition.get(
            "expected_collectors", ["google_news_rss", "techcrunch_rss"]
        )
        missing = [c for c in expected if c not in collectors_run]

        if missing:
            return True, (
                f"No data collected in the last {stale_hours}h from: "
                f"{', '.join(missing)}. Check scheduled tasks."
            )
        return False, ""

    def _check_pipeline_failure(self, cursor, condition: dict) -> tuple[bool, str]:
        """Check for recent pipeline failures."""
        lookback_hours = condition.get("lookback_hours", 24)
        threshold = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
        cutoff = threshold.strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute(
            """SELECT agent_name, status, started_at, error_message FROM agent_runs
               WHERE started_at >= %s AND status = 'failed'
               ORDER BY started_at DESC LIMIT 10""",
            (cutoff,),
        )
        failures = cursor.fetchall()

        if failures:
            names = ", ".join(
                f"{r['agent_name']} ({r['started_at']})" for r in failures
            )
            return (
                True,
                f"{len(failures)} agent failure(s) in last {lookback_hours}h: {names}",
            )
        return False, ""

    def _seed_default_rules(self, cursor):
        """Insert default alert rules if the table is empty."""
        cursor.execute("SELECT COUNT(*) as cnt FROM alert_rules")
        if cursor.fetchone()["cnt"] > 0:
            return

        defaults = [
            {
                "rule_name": "Data freshness — RSS collectors",
                "rule_type": "data_freshness",
                "condition_json": json.dumps(
                    {
                        "stale_hours": 48,
                        "expected_collectors": ["google_news_rss", "techcrunch_rss"],
                        "priority": "medium",
                    }
                ),
                "channel": "email",
                "cooldown_minutes": 1440,
            },
            {
                "rule_name": "Pipeline failure detection",
                "rule_type": "pipeline_failure",
                "condition_json": json.dumps(
                    {
                        "lookback_hours": 24,
                        "priority": "high",
                    }
                ),
                "channel": "email",
                "cooldown_minutes": 360,
            },
        ]
        for rule in defaults:
            cursor.execute(
                """INSERT INTO alert_rules (rule_name, rule_type, condition_json,
                   channel, enabled, cooldown_minutes)
                   VALUES (%s, %s, %s, %s, 1, %s)""",
                (
                    rule["rule_name"],
                    rule["rule_type"],
                    rule["condition_json"],
                    rule["channel"],
                    rule["cooldown_minutes"],
                ),
            )

    # ── Channel dispatchers ──

    def _send_email(self, config: dict, alert: dict) -> tuple[str, str | None]:
        """Send alert via SMTP email."""
        smtp_host = config.get("smtp_host")
        smtp_port = config.get("smtp_port", 587)
        smtp_user = config.get("smtp_user")
        smtp_password = config.get("smtp_password")
        from_addr = config.get("from_address", smtp_user or "alerts@localhost")
        to_addrs = config.get("to_addresses", [])

        if not smtp_host or not to_addrs:
            return "skipped", "SMTP host or recipients not configured"

        msg = MIMEMultipart("alternative")
        msg["Subject"] = (
            f"[Startup Research] {alert.get('priority', 'medium').upper()}: {alert.get('title', 'Alert')}"
        )
        msg["From"] = from_addr
        msg["To"] = ", ".join(to_addrs)

        priority = alert.get("priority", "medium")
        savings = alert.get("estimated_savings_pct")
        savings_line = f"\n\nEstimated savings: {savings:.0f}%" if savings else ""

        body = (
            f"Alert Type: {alert.get('alert_type', 'unknown')}\n"
            f"Priority: {priority.upper()}\n"
            f"Title: {alert.get('title', '')}\n\n"
            f"{alert.get('description', '')}"
            f"{savings_line}\n\n"
            f"Generated: {alert.get('created_at', '')}"
        )

        html_body = (
            f"<h3>{alert.get('title', 'Alert')}</h3>"
            f"<p><strong>Type:</strong> {alert.get('alert_type', '')} &nbsp; "
            f"<strong>Priority:</strong> {priority.upper()}</p>"
            f"<p>{alert.get('description', '').replace(chr(10), '<br>')}</p>"
            f"{f'<p><strong>Estimated savings:</strong> {savings:.0f}%</p>' if savings else ''}"
            f"<hr><small>Generated: {alert.get('created_at', '')}</small>"
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
            _logger.error("AlertDispatcherAgent: Email failed: %s", e)
            return "failed", str(e)

    def _send_slack_webhook(self, url: str, alert: dict) -> tuple[str, str | None]:
        """Send alert to Slack via incoming webhook."""
        priority = alert.get("priority", "medium")
        emoji = {
            "critical": ":rotating_light:",
            "high": ":warning:",
            "medium": ":bell:",
            "low": ":information_source:",
        }
        icon = emoji.get(priority, ":bell:")

        payload = {
            "text": f"{icon} *[{priority.upper()}]* {alert.get('title', 'Alert')}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"{icon} *[{priority.upper()}] {alert.get('title', '')}*\n"
                            f"*Type:* {alert.get('alert_type', '')}\n"
                            f"{alert.get('description', '')}"
                        ),
                    },
                }
            ],
        }

        return self._send_webhook(url, alert, payload)

    def _send_discord_webhook(self, url: str, alert: dict) -> tuple[str, str | None]:
        """Send alert to Discord via webhook."""
        priority = alert.get("priority", "medium")
        colors = {
            "critical": 15158332,
            "high": 15105570,
            "medium": 15859728,
            "low": 4289794,
        }

        payload = {
            "embeds": [
                {
                    "title": alert.get("title", "Alert"),
                    "description": alert.get("description", ""),
                    "color": colors.get(priority, 4289794),
                    "fields": [
                        {
                            "name": "Type",
                            "value": alert.get("alert_type", ""),
                            "inline": True,
                        },
                        {"name": "Priority", "value": priority.upper(), "inline": True},
                    ],
                    "footer": {"text": f"Generated: {alert.get('created_at', '')}"},
                }
            ]
        }

        return self._send_webhook(url, alert, payload)

    def _send_webhook(
        self, url: str, alert: dict, payload: dict | None = None
    ) -> tuple[str, str | None]:
        """Generic webhook POST dispatcher."""
        if payload is None:
            payload = {
                "alert_type": alert.get("alert_type"),
                "title": alert.get("title"),
                "description": alert.get("description"),
                "priority": alert.get("priority"),
                "created_at": alert.get("created_at"),
            }

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
            _logger.error("AlertDispatcherAgent: Webhook failed (%s): %s", url, e)
            return "failed", str(e)

    def _log_dispatch(
        self,
        cursor,
        alert_id: int | None,
        channel: str,
        destination: str | list[str],
        status: str,
        error: str | None,
    ):
        """Log a dispatch attempt to alert_dispatches table."""
        if not alert_id:
            return
        dest_str = (
            ", ".join(destination)
            if isinstance(destination, list)
            else str(destination)
        )
        cursor.execute(
            """INSERT INTO alert_dispatches (alert_id, channel, destination,
               dispatch_status, error_message, dispatched_at)
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
