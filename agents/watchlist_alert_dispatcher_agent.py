"""Watchlist Alert Dispatcher Agent — sends watchlist alerts to users.

Runs in the daily pipeline after WatchlistAlertAgent. For each undispatched
watchlist alert:
1. Fetch the user's alert_preferences
2. Send through enabled channels (email, Slack, Discord, webhook)
3. Mark as dispatched so users don't get duplicate notifications.

Config options:
    max_dispatches_per_run: int — cap per run (default: 100)
    lookback_hours: int — how far back to check alerts (default: 48)
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

# Flag that marks an alert as dispatched — stored in alert_data_json
_DISPATCHED_MARKER = "dispatched_at"


class WatchlistAlertDispatcherAgent(BaseAgent):
    """Dispatches watchlist alerts to users via their configured channels."""

    @property
    def name(self) -> str:
        return "watchlist_alert_dispatcher"

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        max_dispatches = self.config.get("max_dispatches_per_run", 100)
        lookback_hours = self.config.get("lookback_hours", 48)

        _logger.info(
            "WatchlistAlertDispatcher: Starting (max=%d, lookback=%dh)",
            max_dispatches,
            lookback_hours,
        )

        try:
            conn = get_connection()
            schema.init_schema(conn)
        except Exception as e:
            _logger.error("WatchlistAlertDispatcher: DB connection failed: %s", e)
            return AgentResult(agent_name=self.name, status="failed", errors=[str(e)])

        try:
            cursor = conn.cursor()

            # Fetch undispatched watchlist alerts from last N hours
            since = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
            cursor.execute(
                """SELECT ah.id, ah.watchlist_id, ah.alert_type, ah.entity_name,
                          ah.old_score, ah.new_score, ah.delta, ah.alert_data_json,
                          ah.created_at,
                          w.user_id, w.name as watchlist_name, w.alert_config_json,
                          u.email as user_email, u.name as user_name
                   FROM watchlist_alert_history ah
                   JOIN watchlists w ON ah.watchlist_id = w.id
                   JOIN users u ON w.user_id = u.id
                   WHERE ah.created_at >= %s
                     AND (ah.alert_data_json IS NULL
                          OR ah.alert_data_json NOT LIKE %s)
                   ORDER BY ah.created_at DESC
                   LIMIT %s""",
                (
                    since.strftime("%Y-%m-%d %H:%M:%S"),
                    f"%{_DISPATCHED_MARKER}%",
                    max_dispatches,
                ),
            )
            alerts = [dict(r) for r in cursor.fetchall()]

            if not alerts:
                _logger.info("WatchlistAlertDispatcher: No alerts to dispatch")
                cursor.close()
                conn.close()
                return AgentResult(
                    agent_name=self.name,
                    status="success",
                    data={"dispatched": 0, "failed": 0, "records_affected": 0},
                )

            dispatched = 0
            failed = 0

            for alert in alerts:
                alert_id = alert["id"]
                user_id = alert["user_id"]

                # Fetch user's channel preferences
                prefs = self._get_user_preferences(cursor, user_id)
                channels_config = self.config.get("channels", {})

                # Check quiet hours
                if self._in_quiet_hours(prefs):
                    _logger.debug(
                        "WatchlistAlertDispatcher: Skipping alert %d (quiet hours)",
                        alert_id,
                    )
                    continue

                # Build the alert payload
                payload = self._build_payload(alert)

                # Email
                email_ok = False
                if prefs.get("email_enabled") and prefs.get("user_email"):
                    # Get SMTP config from channels (share AlertDispatcherAgent config)
                    email_config = channels_config.get("email", {})
                    if email_config.get("enabled"):
                        status, error = self._send_email(email_config, prefs, payload)
                        if status == "sent":
                            dispatched += 1
                            email_ok = True
                        else:
                            failed += 1
                            _logger.warning(
                                "WatchlistAlertDispatcher: Email failed for user %d: %s",
                                user_id,
                                error,
                            )

                # Slack
                slack_ok = False
                if prefs.get("slack_enabled") and channels_config.get(
                    "webhook_slack", {}
                ).get("url"):
                    url = channels_config["webhook_slack"]["url"]
                    status, error = self._send_slack_webhook(url, payload)
                    if status == "sent":
                        dispatched += 1
                        slack_ok = True
                    else:
                        failed += 1

                # Discord
                discord_ok = False
                if prefs.get("discord_enabled") and channels_config.get(
                    "webhook_discord", {}
                ).get("url"):
                    url = channels_config["webhook_discord"]["url"]
                    status, error = self._send_discord_webhook(url, payload)
                    if status == "sent":
                        dispatched += 1
                        discord_ok = True
                    else:
                        failed += 1

                # Custom webhook
                webhook_ok = False
                if prefs.get("webhook_enabled") and channels_config.get(
                    "webhook_custom", {}
                ).get("url"):
                    url = channels_config["webhook_custom"]["url"]
                    status, error = self._send_webhook(url, payload)
                    if status == "sent":
                        dispatched += 1
                        webhook_ok = True
                    else:
                        failed += 1

                # Mark as dispatched if at least one channel succeeded
                if email_ok or slack_ok or discord_ok or webhook_ok:
                    self._mark_dispatched(cursor, alert, prefs)

            conn.commit()
            cursor.close()
            conn.close()

            _logger.info(
                "WatchlistAlertDispatcher: Done — %d dispatched, %d failed of %d alerts",
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
                errors=[f"{failed} dispatch failures"] if failed > 0 else [],
            )

        except Exception as e:
            _logger.error("WatchlistAlertDispatcher: Error: %s", e)
            try:
                conn.close()
            except Exception:
                pass
            return AgentResult(
                agent_name=self.name, status="failed", errors=[str(e)]
            )

    # ── Helpers ──

    def _get_user_preferences(self, cursor, user_id: int) -> dict:
        """Fetch user alert preferences with safe defaults."""
        cursor.execute(
            "SELECT * FROM alert_preferences WHERE user_id = %s", (user_id,)
        )
        row = cursor.fetchone()
        if row:
            return dict(row)

        # Sensible defaults if no preferences saved
        return {
            "email_enabled": True,
            "slack_enabled": False,
            "discord_enabled": False,
            "webhook_enabled": False,
            "min_score_threshold": 80.0,
            "quiet_hours_start": None,
            "quiet_hours_end": None,
            "max_alerts_per_hour": 20,
            "user_email": None,
        }

    def _in_quiet_hours(self, prefs: dict) -> bool:
        """Check if current UTC time is within quiet hours."""
        start = prefs.get("quiet_hours_start")
        end = prefs.get("quiet_hours_end")
        if not start or not end:
            return False

        now = datetime.now(timezone.utc).strftime("%H:%M")
        if start <= end:
            return start <= now <= end
        else:  # Overnight range (e.g., 22:00 - 08:00)
            return now >= start or now <= end

    def _build_payload(self, alert: dict) -> dict:
        """Build a normalized alert payload for all channels."""
        alert_data = {}
        if alert.get("alert_data_json"):
            try:
                alert_data = json.loads(alert["alert_data_json"])
            except (json.JSONDecodeError, TypeError):
                pass

        delta = alert.get("delta", 0)
        direction = "↑" if delta > 0 else "↓"

        return {
            "source": "watchlist",
            "alert_id": alert.get("id"),
            "alert_type": alert.get("alert_type", "score_change"),
            "entity_name": alert.get("entity_name", ""),
            "watchlist_name": alert.get("watchlist_name", ""),
            "old_score": alert.get("old_score"),
            "new_score": alert.get("new_score"),
            "delta": delta,
            "direction": direction,
            "delta_abs": abs(delta),
            "trend_previous": alert_data.get("trend_previous"),
            "trend_current": alert_data.get("trend_current"),
            "created_at": alert.get("created_at"),
            "user_name": alert.get("user_name", ""),
        }

    def _mark_dispatched(self, cursor, alert: dict, prefs: dict):
        """Mark a watchlist alert as dispatched by updating alert_data_json."""
        alert_data = {}
        if alert.get("alert_data_json"):
            try:
                alert_data = json.loads(alert["alert_data_json"])
            except (json.JSONDecodeError, TypeError):
                pass

        alert_data[_DISPATCHED_MARKER] = datetime.now(timezone.utc).isoformat()
        alert_data["dispatched_to"] = [
            c
            for c in ["email", "slack", "discord", "webhook"]
            if prefs.get(f"{c}_enabled")
        ]

        cursor.execute(
            "UPDATE watchlist_alert_history SET alert_data_json = %s WHERE id = %s",
            (json.dumps(alert_data), alert["id"]),
        )

    # ── Channel dispatchers ──

    def _send_email(
        self, config: dict, prefs: dict, payload: dict
    ) -> tuple[str, str | None]:
        """Send watchlist alert via SMTP email."""
        smtp_host = config.get("smtp_host")
        smtp_port = config.get("smtp_port", 587)
        smtp_user = config.get("smtp_user")
        smtp_password = config.get("smtp_password")
        from_addr = config.get("from_address", smtp_user or "alerts@localhost")
        to_addrs = config.get("to_addresses", None)

        # Default: send to the user's registered email
        if not to_addrs:
            user_email = prefs.get("user_email")
            if not user_email:
                return "skipped", "No recipient email configured"
            to_addrs = [user_email]

        entity = payload["entity_name"]
        alert_type = payload["alert_type"]
        delta = payload["delta_abs"]
        direction = payload["direction"]
        score = payload["new_score"]

        msg = MIMEMultipart("alternative")
        msg["Subject"] = (
            f"[Watchlist Alert] {entity} changed {direction}{delta:.1f}pts → score {score:.1f}"
        )
        msg["From"] = from_addr
        msg["To"] = ", ".join(to_addrs) if isinstance(to_addrs, list) else str(to_addrs)

        body = (
            f"Watchlist Alert\n"
            f"{'=' * 40}\n\n"
            f"Entity: {entity}\n"
            f"Watchlist: {payload['watchlist_name']}\n"
            f"Alert Type: {alert_type}\n"
            f"Score Change: {direction}{delta:.1f}pts "
            f"({payload.get('old_score', '?')} → {score})\n"
        )
        if payload.get("trend_previous") and payload.get("trend_current"):
            body += f"Trend: {payload['trend_previous']} → {payload['trend_current']}\n"

        body += f"\nTime: {payload['created_at']}\n"
        if prefs.get("max_alerts_per_hour"):
            body += f"Max per hour: {prefs['max_alerts_per_hour']}\n"

        html_body = body.replace("\n", "<br>").replace("  ", "&nbsp;")

        msg.attach(MIMEText(body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        try:
            if not smtp_host:
                return "skipped", "SMTP host not configured"
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=15)
            server.starttls()
            if smtp_user and smtp_password:
                server.login(smtp_user, smtp_password)
            server.sendmail(from_addr, to_addrs, msg.as_string())
            server.quit()
            return "sent", None
        except Exception as e:
            _logger.warning("WatchlistAlertDispatcher: Email failed: %s", e)
            return "failed", str(e)

    def _send_slack_webhook(self, url: str, payload: dict) -> tuple[str, str | None]:
        """Send watchlist alert to Slack."""
        emoji = "📈" if payload["delta"] > 0 else "📉"
        alert_emoji = {"score_change": "📊", "trend_change": "🔄"}.get(
            payload["alert_type"], "🔔"
        )

        diff = payload["delta"]
        old_s = payload.get("old_score") or "?"
        new_s = payload.get("new_score") or "?"

        payload_normalized = {
            "alert_type": f"watchlist:{payload['alert_type']}",
            "title": f"{alert_emoji} {payload['entity_name']} score change",
            "description": (
                f"{emoji} {payload['direction']}{abs(diff):.1f}pt "
                f"({old_s} → {new_s}) in *{payload['watchlist_name']}*"
            ),
            "priority": "medium",
            "affected_models": [],
            "created_at": payload["created_at"],
        }
        return self._send_webhook(url, payload_normalized)

    def _send_discord_webhook(self, url: str, payload: dict) -> tuple[str, str | None]:
        """Send watchlist alert to Discord."""
        color = 3066990 if payload["delta"] > 0 else 15158332  # green / red
        diff = payload["delta"]

        payload_normalized = {
            "alert_type": f"watchlist:{payload['alert_type']}",
            "title": f"{payload['entity_name']} — score update",
            "description": (
                f"**{abs(diff):.1f}pt** {'increase' if diff > 0 else 'decrease'} "
                f"from {payload.get('old_score', '?')} → {payload.get('new_score', '?')}\n"
                f"Watchlist: *{payload['watchlist_name']}*"
            ),
            "priority": "medium",
            "affected_models": [],
            "created_at": payload["created_at"],
            "color_override": color,
        }
        return self._send_webhook(url, payload_normalized)

    def _send_webhook(
        self, url: str, payload: dict
    ) -> tuple[str, str | None]:
        """Generic webhook POST dispatcher."""
        # Normalize payload for watchlist alerts
        data = {
            "source": "watchlist",
            "alert_type": payload.get("alert_type"),
            "title": payload.get("title"),
            "description": payload.get("description"),
            "entity_name": payload.get("entity_name"),
            "watchlist_name": payload.get("watchlist_name"),
            "old_score": payload.get("old_score"),
            "new_score": payload.get("new_score"),
            "delta": payload.get("delta"),
            "priority": payload.get("priority", "medium"),
            "created_at": payload.get("created_at"),
        }

        # Handle color override for Discord
        if payload.get("color_override"):
            data["color"] = payload["color_override"]

        try:
            body = json.dumps(data).encode()
            req = urllib.request.Request(
                url,
                data=body,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp.read()
            return "sent", None
        except Exception as e:
            _logger.warning("WatchlistAlertDispatcher: Webhook failed: %s", e)
            return "failed", str(e)