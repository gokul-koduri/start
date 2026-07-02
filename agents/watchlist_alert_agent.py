"""Watchlist Alert Agent — checks score deltas and fires alerts for watched entities.

Runs in the daily pipeline. For each active watchlist:
1. Collects all watched entities
2. Cross-references score_deltas from the last 24 hours
3. Filters by watchlist-specific alert_config thresholds
4. Records qualifying alerts in watchlist_alert_history
5. Dispatches notifications via the alert dispatcher's channel config

Config options:
    lookback_hours: int — how far back to check score_deltas (default: 24)
    max_alerts_per_run: int — cap per run (default: 500)
"""

import json
import logging
from datetime import datetime, timezone, timedelta

from agents.base import AgentResult, BaseAgent
from db.connection import get_connection
from db import schema

_logger = logging.getLogger(__name__)


class WatchlistAlertAgent(BaseAgent):
    """Checks score changes for watchlisted entities and dispatches alerts."""

    @property
    def name(self) -> str:
        return "watchlist_alert"

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        lookback_hours = self.config.get("lookback_hours", 24)
        max_alerts = self.config.get("max_alerts_per_run", 500)

        _logger.info(
            "WatchlistAlertAgent: Starting (lookback=%dh, max=%d)",
            lookback_hours,
            max_alerts,
        )

        try:
            conn = get_connection()
            schema.init_schema(conn)
        except Exception as e:
            _logger.error("WatchlistAlertAgent: DB connection failed: %s", e)
            return AgentResult(agent_name=self.name, status="failed", errors=[str(e)])

        try:
            cursor = conn.cursor()

            # 1. Get active watchlists with their items
            cursor.execute(
                """SELECT w.id as watchlist_id, w.user_id, w.name, w.alert_config_json,
                          wi.entity_name, wi.entity_type
                   FROM watchlists w
                   JOIN watchlist_items wi ON w.id = wi.watchlist_id
                   WHERE w.is_active = 1"""
            )
            watchlist_rows = cursor.fetchall()

            if not watchlist_rows:
                _logger.info("WatchlistAlertAgent: No active watchlists with items")
                cursor.close()
                conn.close()
                return AgentResult(
                    agent_name=self.name,
                    status="success",
                    data={"alerts_generated": 0, "watchlists_checked": 0},
                )

            # 2. Get score deltas from the lookback window
            since = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
            cursor.execute(
                """SELECT entity_name, entity_type, old_score, new_score, delta,
                          trend_previous, trend_current, signal_breakdown_json, detected_at
                   FROM score_deltas
                   WHERE detected_at >= %s""",
                (since.strftime("%Y-%m-%d %H:%M:%S"),),
            )
            delta_rows = cursor.fetchall()

            # Build lookup: (entity_name, entity_type) -> list of deltas
            deltas_by_entity = {}
            for dr in delta_rows:
                key = (dr["entity_name"], dr.get("entity_type", "company"))
                deltas_by_entity.setdefault(key, []).append(dict(dr))

            _logger.info(
                "WatchlistAlertAgent: %d watched entities, %d entities with deltas",
                len(watchlist_rows),
                len(deltas_by_entity),
            )

            # 3. Match and generate alerts
            alerts_generated = 0
            watchlists_affected = set()

            for wl_row in watchlist_rows:
                if alerts_generated >= max_alerts:
                    break

                entity_key = (wl_row["entity_name"], wl_row["entity_type"])
                entity_deltas = deltas_by_entity.get(entity_key, [])
                if not entity_deltas:
                    continue

                # Parse alert config
                alert_config = _parse_alert_config(wl_row["alert_config_json"])
                min_delta = alert_config.get("min_delta", 5.0)
                alert_on_trend = alert_config.get("alert_on_trend_change", True)

                for delta_data in entity_deltas:
                    delta = abs(delta_data.get("delta", 0))
                    if delta < min_delta:
                        continue

                    # Check trend change if configured
                    alert_type = "score_change"
                    if alert_on_trend:
                        prev_trend = delta_data.get("trend_previous")
                        curr_trend = delta_data.get("trend_current")
                        if prev_trend and curr_trend and prev_trend != curr_trend:
                            alert_type = "trend_change"

                    # Check if we already alerted for this delta
                    cursor.execute(
                        """SELECT id FROM watchlist_alert_history
                           WHERE watchlist_id = %s AND entity_name = %s
                           AND new_score = %s AND created_at > %s""",
                        (
                            wl_row["watchlist_id"],
                            wl_row["entity_name"],
                            delta_data["new_score"],
                            since.strftime("%Y-%m-%d %H:%M:%S"),
                        ),
                    )
                    if cursor.fetchone():
                        continue  # Already alerted

                    # Record alert
                    alert_data = {
                        "trend_previous": delta_data.get("trend_previous"),
                        "trend_current": delta_data.get("trend_current"),
                        "watchlist_name": wl_row["name"],
                    }
                    cursor.execute(
                        """INSERT INTO watchlist_alert_history
                           (watchlist_id, alert_type, entity_name, old_score, new_score,
                            delta, alert_data_json)
                           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                        (
                            wl_row["watchlist_id"],
                            alert_type,
                            wl_row["entity_name"],
                            delta_data.get("old_score"),
                            delta_data["new_score"],
                            delta_data["delta"],
                            json.dumps(alert_data),
                        ),
                    )
                    alerts_generated += 1
                    watchlists_affected.add(wl_row["watchlist_id"])

            conn.commit()
            cursor.close()
            conn.close()

            _logger.info(
                "WatchlistAlertAgent: Generated %d alerts for %d watchlists",
                alerts_generated,
                len(watchlists_affected),
            )

            return AgentResult(
                agent_name=self.name,
                status="success",
                data={
                    "alerts_generated": alerts_generated,
                    "watchlists_checked": len(
                        set(r["watchlist_id"] for r in watchlist_rows)
                    ),
                    "watchlists_affected": len(watchlists_affected),
                    "records_affected": alerts_generated,
                },
            )

        except Exception as e:
            _logger.error("WatchlistAlertAgent: Error: %s", e)
            try:
                conn.close()
            except Exception:
                pass
            return AgentResult(agent_name=self.name, status="failed", errors=[str(e)])


def _parse_alert_config(raw: str | None) -> dict:
    """Parse alert_config_json, returning defaults if null."""
    if raw:
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            pass
    return {
        "min_delta": 5.0,
        "alert_on_trend_change": True,
        "channels": ["email"],
        "quiet_hours_start": None,
        "quiet_hours_end": None,
    }
