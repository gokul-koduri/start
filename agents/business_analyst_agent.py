"""Business Analyst Agent — requirements, feasibility, cost-benefit, market fit.

This agent acts as the Business Analyst role in the AI Product Development Team.
It translates business needs into formal requirements, performs cost-benefit
analysis, tracks competitive landscape changes, and validates that features
align with market needs.

Key responsibilities:
    - Analyze and document business requirements
    - Cost-benefit analysis for each feature
    - Market fit validation (does this solve a real problem?)
    - Competitive intelligence tracking
    - ROI estimation for feature development
    - User persona validation

Tables used:
    - user_stories          (formal stories with acceptance criteria)
    - score_feedback        (user feedback on score accuracy)
    - query_log             (what users search for)
    - chat_log              (what users ask about)
    - daily_metrics         (business KPIs)

Usage:
    ba = BusinessAnalystAgent()
    result = ba.execute()
    # Returns: requirements gap analysis, market fit score, ROI estimates
"""

import json
import logging
from datetime import datetime, timezone

from agents.base import AgentResult, BaseAgent
from db.connection import get_connection
from db import schema

_logger = logging.getLogger(__name__)


class BusinessAnalystAgent(BaseAgent):
    """Business Analyst — requirements analysis, feasibility, cost-benefit.

    Generates:
    - User need analysis (top queries, unanswered questions)
    - Feature-market fit score
    - Cost-benefit ranking of planned features
    - Requirements gap report (what users want but don't have)
    - Competitive positioning update
    """

    @property
    def name(self) -> str:
        return "business_analyst"

    def execute(self, upstream_results=None) -> AgentResult:
        """Run business analysis.

        Steps:
            1. Analyze user queries to identify unmet needs
            2. Score feature-market fit based on feedback data
            3. Calculate cost-benefit for planned features
            4. Identify requirements gaps
            5. Generate actionable recommendations
        """
        started = datetime.now(timezone.utc).isoformat()
        errors = []

        try:
            conn = get_connection()
            schema.init_schema(conn)
            cursor = conn.cursor()

            # ── Step 1: User need analysis ──
            user_needs = self._analyze_user_needs(cursor)

            # ── Step 2: Feature-market fit ──
            market_fit = self._score_market_fit(cursor)

            # ── Step 3: Cost-benefit analysis ──
            cost_benefit = self._cost_benefit_analysis(cursor)

            # ── Step 4: Requirements gaps ──
            gaps = self._identify_requirements_gaps(cursor, user_needs)

            # ── Step 5: Build recommendations ──
            recommendations = self._build_recommendations(
                user_needs, market_fit, cost_benefit, gaps
            )

            result_data = {
                "user_needs": user_needs,
                "market_fit": market_fit,
                "cost_benefit": cost_benefit,
                "requirements_gaps": gaps,
                "recommendations": recommendations,
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
            }

            cursor.close()
            conn.close()

            return AgentResult(
                agent_name=self.name,
                status="success",
                started_at=started,
                completed_at=datetime.now(timezone.utc).isoformat(),
                data=result_data,
                errors=errors,
            )

        except Exception as e:
            errors.append(str(e))
            _logger.error("BusinessAnalyst error: %s", e)
            return AgentResult(
                agent_name=self.name,
                status="failed",
                started_at=started,
                completed_at=datetime.now(timezone.utc).isoformat(),
                errors=errors,
            )

    def _analyze_user_needs(self, cursor) -> dict:
        """Analyze what users search for and ask about."""
        needs = {"top_queries": [], "top_chat_topics": [], "zero_result_queries": [],
                 "total_queries": 0, "total_chats": 0}

        try:
            # Top search queries
            cursor.execute(
                "SELECT query, COUNT(*) as cnt FROM query_log "
                "WHERE created_at > DATE_SUB(NOW(), INTERVAL 7 DAY) "
                "GROUP BY query ORDER BY cnt DESC LIMIT 20"
            )
            needs["top_queries"] = cursor.fetchall()

            cursor.execute("SELECT COUNT(*) as cnt FROM query_log "
                           "WHERE created_at > DATE_SUB(NOW(), INTERVAL 7 DAY)")
            needs["total_queries"] = cursor.fetchone()["cnt"]

            # Top chat topics
            cursor.execute(
                "SELECT LEFT(question, 100) as question, COUNT(*) as cnt FROM chat_log "
                "WHERE created_at > DATE_SUB(NOW(), INTERVAL 7 DAY) "
                "GROUP BY LEFT(question, 100) ORDER BY cnt DESC LIMIT 20"
            )
            needs["top_chat_topics"] = cursor.fetchall()

            cursor.execute("SELECT COUNT(*) as cnt FROM chat_log "
                           "WHERE created_at > DATE_SUB(NOW(), INTERVAL 7 DAY)")
            needs["total_chats"] = cursor.fetchone()["cnt"]

        except Exception as e:
            needs["error"] = str(e)

        return needs

    def _score_market_fit(self, cursor) -> dict:
        """Score how well current features match user needs."""
        fit = {"score_feedback_avg": 0, "score_feedback_count": 0,
               "positive_pct": 0, "negative_pct": 0}

        try:
            cursor.execute("SHOW TABLES LIKE 'score_feedback'")
            if cursor.fetchone():
                cursor.execute(
                    "SELECT COUNT(*) as cnt, AVG(rating) as avg_rating "
                    "FROM score_feedback"
                )
                row = cursor.fetchone()
                if row and row["cnt"] > 0:
                    fit["score_feedback_count"] = row["cnt"]
                    fit["score_feedback_avg"] = round(row["avg_rating"], 2)

                cursor.execute(
                    "SELECT "
                    "SUM(CASE WHEN rating >= 4 THEN 1 ELSE 0 END) as positive, "
                    "SUM(CASE WHEN rating <= 2 THEN 1 ELSE 0 END) as negative, "
                    "COUNT(*) as total "
                    "FROM score_feedback"
                )
                row = cursor.fetchone()
                if row and row["total"] > 0:
                    fit["positive_pct"] = round(row["positive"] / row["total"] * 100, 1)
                    fit["negative_pct"] = round(row["negative"] / row["total"] * 100, 1)

        except Exception as e:
            fit["error"] = str(e)

        return fit

    def _cost_benefit_analysis(self, cursor) -> list[dict]:
        """Rank planned features by estimated cost vs expected benefit."""
        # Based on PROBLEM_FEATURE_MAP.md priorities
        features = [
            {"feature": "Collector Scheduler", "cost_hours": 16, "benefit": "high",
             "priority": "P0", "roi_score": 9},
            {"feature": "Alert Consumer", "cost_hours": 12, "benefit": "high",
             "priority": "P0", "roi_score": 9},
            {"feature": "WebSocket Score Push", "cost_hours": 8, "benefit": "high",
             "priority": "P0", "roi_score": 8},
            {"feature": "User Auth (JWT)", "cost_hours": 12, "benefit": "high",
             "priority": "P0", "roi_score": 8},
            {"feature": "Input Validation", "cost_hours": 4, "benefit": "high",
             "priority": "P0", "roi_score": 10},
            {"feature": "Rate Limiting", "cost_hours": 4, "benefit": "medium",
             "priority": "P1", "roi_score": 7},
            {"feature": "Watchlists", "cost_hours": 8, "benefit": "medium",
             "priority": "P1", "roi_score": 6},
            {"feature": "CSV Export", "cost_hours": 6, "benefit": "medium",
             "priority": "P1", "roi_score": 5},
            {"feature": "Stripe Pro Tier", "cost_hours": 16, "benefit": "high",
             "priority": "P1", "roi_score": 8},
            {"feature": "Feedback System", "cost_hours": 8, "benefit": "medium",
             "priority": "P2", "roi_score": 5},
        ]
        return sorted(features, key=lambda x: -x["roi_score"])

    def _identify_requirements_gaps(self, cursor, user_needs) -> list[dict]:
        """Identify features users want but don't have yet."""
        gaps = []

        if user_needs.get("total_queries", 0) > 100:
            gaps.append({
                "gap": "High query volume but no search analytics",
                "recommendation": "Build search analytics dashboard",
                "priority": "P2",
            })

        gaps.append({
            "gap": "No user accounts or personalization",
            "recommendation": "Implement auth + user profiles (Sprint 4)",
            "priority": "P0",
        })
        gaps.append({
            "gap": "No data export capability",
            "recommendation": "Build CSV/PDF export (Sprint 6)",
            "priority": "P1",
        })
        gaps.append({
            "gap": "No scheduled/automated alerts",
            "recommendation": "Build alert scheduler (Sprint 2)",
            "priority": "P0",
        })

        return gaps

    def _build_recommendations(self, needs, fit, cost_benefit, gaps) -> list[str]:
        """Build actionable business recommendations."""
        recs = []

        top_p0 = [f for f in cost_benefit if f["priority"] == "P0"]
        recs.append(
            f"Focus on {len(top_p0)} P0 features first (highest ROI): "
            + ", ".join(f["feature"] for f in top_p0)
        )

        if fit.get("negative_pct", 0) > 30:
            recs.append(
                f"Score accuracy concern: {fit['negative_pct']}% negative feedback. "
                "Investigate and fix scoring weights."
            )

        if needs.get("total_queries", 0) > 0:
            recs.append(
                f"Users made {needs['total_queries']} searches this week. "
                "Ensure search relevance is high."
            )

        return recs
