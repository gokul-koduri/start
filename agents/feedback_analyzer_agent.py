"""Feedback analyzer agent — analyzes user feedback patterns weekly."""

import json
import logging
from agents.base import BaseAgent, AgentResult
from datetime import datetime, timezone

_logger = logging.getLogger(__name__)


class FeedbackAnalyzerAgent(BaseAgent):
    """Analyzes user feedback to identify trends and patterns.

    Reads from: query_log, chat_log, score_feedback, feature_requests
    Writes to: feedback_analysis
    """

    @property
    def name(self) -> str:
        return "feedback_analyzer"

    def execute(self, upstream_results=None) -> AgentResult:
        """Analyze feedback data from the past 7 days."""
        try:
            from db.connection import get_connection
            from db import schema

            conn = get_connection()
            schema.init_schema(conn)
            cursor = conn.cursor()

            week_str = datetime.now(timezone.utc).strftime("%G-W%V")

            # --- Trending queries (top 20 by count, last 7 days) ---
            cursor.execute(
                """SELECT query, COUNT(*) as count
                   FROM query_log
                   WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                   GROUP BY query ORDER BY count DESC LIMIT 20"""
            )
            trending_queries = [dict(r) for r in cursor.fetchall()]

            # --- Common chat questions (top 20 by frequency, last 7 days) ---
            cursor.execute(
                """SELECT user_message, COUNT(*) as count
                   FROM chat_log
                   WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                   GROUP BY user_message ORDER BY count DESC LIMIT 20"""
            )
            common_questions = [dict(r) for r in cursor.fetchall()]

            # --- Score feedback stats ---
            cursor.execute(
                """SELECT rating, COUNT(*) as count
                   FROM score_feedback
                   WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                   GROUP BY rating ORDER BY rating"""
            )
            rating_distribution = {str(r["rating"]): r["count"] for r in cursor.fetchall()}

            cursor.execute(
                """SELECT COUNT(*) as cnt, AVG(rating) as avg
                   FROM score_feedback
                   WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)"""
            )
            rating_row = cursor.fetchone()
            avg_rating = float(rating_row["avg"]) if rating_row and rating_row["avg"] else 0.0
            rating_count = rating_row["cnt"] if rating_row else 0

            # --- Score calibration gaps (user_score differs by >20 from AI score) ---
            cursor.execute(
                """SELECT entity_name, score_given, user_score, rating
                   FROM score_feedback
                   WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                     AND user_score IS NOT NULL
                     AND ABS(score_given - user_score) > 20
                   ORDER BY ABS(score_given - user_score) DESC LIMIT 20"""
            )
            calibration_gaps = [dict(r) for r in cursor.fetchall()]

            # --- Top feature requests ---
            cursor.execute(
                """SELECT feature, category, upvotes, status
                   FROM feature_requests
                   WHERE status = 'open'
                   ORDER BY upvotes DESC LIMIT 20"""
            )
            top_features = [dict(r) for r in cursor.fetchall()]

            # --- Total counts ---
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM query_log "
                "WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)"
            )
            total_queries = cursor.fetchone()["cnt"]

            cursor.execute(
                "SELECT COUNT(*) as cnt FROM chat_log "
                "WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)"
            )
            total_chats = cursor.fetchone()["cnt"]

            cursor.execute(
                "SELECT COUNT(*) as cnt FROM score_feedback "
                "WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)"
            )
            total_feedback = cursor.fetchone()["cnt"]

            # --- Upsert analysis row ---
            cursor.execute(
                """INSERT INTO feedback_analysis
                   (analysis_week, trending_queries, common_questions, avg_rating,
                    rating_count, rating_distribution, calibration_gaps,
                    top_feature_requests, total_queries, total_chats, total_feedback)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON DUPLICATE KEY UPDATE
                    trending_queries=VALUES(trending_queries),
                    common_questions=VALUES(common_questions),
                    avg_rating=VALUES(avg_rating),
                    rating_count=VALUES(rating_count),
                    rating_distribution=VALUES(rating_distribution),
                    calibration_gaps=VALUES(calibration_gaps),
                    top_feature_requests=VALUES(top_feature_requests),
                    total_queries=VALUES(total_queries),
                    total_chats=VALUES(total_chats),
                    total_feedback=VALUES(total_feedback)
                """,
                (
                    week_str,
                    json.dumps(trending_queries),
                    json.dumps(common_questions),
                    avg_rating,
                    rating_count,
                    json.dumps(rating_distribution),
                    json.dumps(calibration_gaps),
                    json.dumps(top_features),
                    total_queries,
                    total_chats,
                    total_feedback,
                ),
            )
            conn.commit()
            cursor.close()
            conn.close()

            return AgentResult(
                agent_name=self.name,
                status="success",
                data={
                    "analysis_week": week_str,
                    "trending_queries_count": len(trending_queries),
                    "common_questions_count": len(common_questions),
                    "avg_rating": avg_rating,
                    "calibration_gaps_count": len(calibration_gaps),
                    "top_features_count": len(top_features),
                    "total_queries": total_queries,
                    "total_chats": total_chats,
                    "total_feedback": total_feedback,
                    "records_affected": 1,
                },
            )
        except Exception as e:
            return AgentResult(
                agent_name=self.name,
                status="failed",
                errors=[str(e)],
            )
