"""Email digest agent — generates and queues email digests for Pro/Enterprise users.

Instead of sending emails inline (which blocks the agent and has no retry),
this agent renders digest content, builds HTML via templates, and queues
to the outbound_emails table. The email_worker.py process drains the queue
asynchronously with retry, rate limiting, and bounce handling.

Config options:
    enabled: bool — enable/disable
    template: str — template filename (default: digest.html)
    max_recipients: int — cap per run (default: 500)
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from agents.base import AgentResult, BaseAgent
from db.connection import get_connection
from utils.email_queue import (
    queue_bulk,
    get_active_recipients,
    render_template,
    plain_from_html,
    queue_stats,
)

_logger = logging.getLogger(__name__)


class EmailDigestAgent(BaseAgent):
    """Generates and queues email digests for active subscribers."""

    @property
    def name(self) -> str:
        return "email_digest"

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        template_name = self.config.get("template", "digest.html")
        max_recipients = self.config.get("max_recipients", 500)
        now = datetime.now(timezone.utc)

        try:
            conn = get_connection()
            cursor = conn.cursor()
        except Exception as e:
            return AgentResult(agent_name=self.name, status="failed", errors=[str(e)])

        try:
            # ── Gather data ──
            cursor.execute("SELECT COUNT(*) as cnt FROM failed_startups")
            total_startups = cursor.fetchone()["cnt"]

            cursor.execute(
                "SELECT COUNT(*) as cnt FROM news_articles WHERE DATE(collected_at) = CURDATE()"
            )
            news_today = cursor.fetchone()["cnt"]

            cursor.execute(
                """SELECT COUNT(*) as cnt FROM opportunity_scores
                   WHERE composite_score >= 70"""
            )
            high_value_count = cursor.fetchone()["cnt"]

            # Top failure reasons
            cursor.execute(
                """SELECT failure_category, COUNT(*) as cnt FROM failed_startups
                   WHERE failure_category IS NOT NULL
                   GROUP BY failure_category ORDER BY cnt DESC LIMIT 5"""
            )
            top_failures = [
                {"category": r["failure_category"], "count": r["cnt"]}
                for r in cursor.fetchall()
            ]

            # Active alerts
            cursor.execute(
                """SELECT title, priority, estimated_savings_pct
                   FROM llm_optimization_alerts
                   WHERE dismissed = 0
                   ORDER BY priority DESC LIMIT 5"""
            )
            alerts = []
            for a in cursor.fetchall():
                priority = (a["priority"] or "medium").lower()
                alerts.append({
                    "title": a["title"],
                    "priority": priority,
                    "priority_class": priority,
                    "savings": f"{a['estimated_savings_pct']:.0f}" if a.get("estimated_savings_pct") else None,
                })

            # Collection health
            cursor.execute(
                """SELECT collector_name, records_collected, status
                   FROM collection_runs ORDER BY started_at DESC LIMIT 5"""
            )
            collection_runs = [
                {"collector": r["collector_name"], "records": r["records_collected"], "status": r["status"]}
                for r in cursor.fetchall()
            ]

            cursor.close()
            conn.close()

            # ── Build context ──
            period_label = "daily"
            header_title = "Daily Digest"
            header_subtitle = now.strftime("%B %d, %Y")

            # Determine period from pipeline name
            pipeline = self.config.get("_pipeline_name", "daily")
            if pipeline == "weekly":
                period_label = "weekly"
                header_title = "Weekly Digest"
            elif pipeline == "full":
                period_label = "monthly"
                header_title = "Monthly Deep Dive"

            context = {
                "header_title": header_title,
                "header_subtitle": header_subtitle,
                "period_label": period_label,
                "total_startups": f"{total_startups:,}",
                "news_count": f"{news_today:,}",
                "high_value_count": f"{high_value_count:,}",
                "top_failures": top_failures,
                "alerts": alerts,
                "collection_runs": collection_runs,
                "dashboard_url": "https://github.com/gokul-koduri/start",
                "unsubscribe_url": "https://github.com/gokul-koduri/start#email-preferences",
                "preferences_url": "https://github.com/gokul-koduri/start#email-preferences",
                "subject": f"[OIP] {header_title} — {now.strftime('%b %d, %Y')}",
            }

            # ── Render HTML ──
            html_body = render_template(template_name, context)

            # ── Build plain text ──
            plain_lines = [
                f"{header_title} — {now.strftime('%B %d, %Y')}",
                "",
                f"Failed Startups: {total_startups:,}",
                f"New Articles: {news_today:,}",
                f"High-Value Opportunities: {high_value_count:,}",
                "",
            ]
            if top_failures:
                plain_lines.append("Top Failure Reasons:")
                for f in top_failures:
                    plain_lines.append(f"  · {f['category']}: {f['count']}")
                plain_lines.append("")
            if alerts:
                plain_lines.append("Active Alerts:")
                for a in alerts:
                    plain_lines.append(f"  · [{a['priority'].upper()}] {a['title']}")
                plain_lines.append("")
            plain_lines.append("View dashboard: https://github.com/gokul-koduri/start")
            plain_body = "\n".join(plain_lines)

            # ── Queue to recipients ──
            recipients = get_active_recipients()[:max_recipients]
            emails = [r["email"] for r in recipients if r.get("email")]

            if not emails:
                _logger.info("EmailDigestAgent: No active recipients, skipping")
                return AgentResult(
                    agent_name=self.name,
                    status="success",
                    data={"queued": 0, "reason": "no_recipients"},
                )

            queued_ids = queue_bulk(
                emails,
                subject=context["subject"],
                email_type="digest",
                plain_body=plain_body,
                html_body=html_body,
                priority=5,
                metadata={"period": period_label, "total_recipients": len(emails)},
            )

            _logger.info("EmailDigestAgent: Queued %d digest emails", len(queued_ids))

            return AgentResult(
                agent_name=self.name,
                status="success",
                data={
                    "queued": len(queued_ids),
                    "period": period_label,
                    "total_startups": total_startups,
                    "news_today": news_today,
                    "high_value_opportunities": high_value_count,
                    "queue_stats": queue_stats(),
                },
            )

        except Exception as e:
            _logger.error("EmailDigestAgent: Error: %s", e)
            return AgentResult(agent_name=self.name, status="failed", errors=[str(e)])
