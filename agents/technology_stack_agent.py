"""Technology Stack Agent — analyzes technology adoption patterns."""

import json
import logging
from datetime import datetime, timezone

from agents.base import AgentResult, BaseAgent
from db.connection import get_connection
from db import schema

_logger = logging.getLogger(__name__)


class TechnologyStackAgent(BaseAgent):
    """Analyzes technology adoption patterns from GitHub and StackOverflow data.

    Produces:
    - Technology adoption scores
    - Trend direction indicators
    - GitHub and StackOverflow metrics
    - Average company age by technology
    """

    @property
    def name(self) -> str:
        return "technology_stack"

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        conn = get_connection()
        schema.init_schema(conn)

        insights = {}

        # Analyze GitHub trends by language
        cursor = conn.cursor()
        cursor.execute(
            """SELECT language, COUNT(*) as repo_count,
                      AVG(weekly_stars_delta) as avg_velocity
               FROM github_trends
               WHERE language IS NOT NULL
               GROUP BY language
               ORDER BY repo_count DESC
               LIMIT 20"""
        )
        github_trends = cursor.fetchall()
        cursor.close()

        # Analyze StackOverflow activity by tag
        cursor = conn.cursor()
        cursor.execute(
            """SELECT tags, COUNT(*) as question_count,
                      AVG(score) as avg_score
               FROM stackoverflow_posts
               WHERE tags IS NOT NULL
               GROUP BY tags
               ORDER BY question_count DESC
               LIMIT 20"""
        )
        stackoverflow_trends = cursor.fetchall()
        cursor.close()

        # Combine and analyze technology patterns
        tech_data = []
        tech_map = {}

        # Build technology map from GitHub
        for gt in github_trends:
            lang = gt.get("language", "Unknown")
            tech_map[lang] = {
                "github_repos": gt.get("repo_count", 0) or 0,
                "avg_velocity": gt.get("avg_velocity", 0) or 0,
                "stackoverflow_questions": 0,
                "category": "language" if lang else "unknown",
            }

        # Add StackOverflow data (simplified tag parsing)
        for st in stackoverflow_trends:
            try:
                tags = (
                    json.loads(st.get("tags", "[]"))
                    if isinstance(st.get("tags"), str)
                    else st.get("tags", [])
                )
                for tag in tags[:1]:  # Take first tag as primary
                    if tag and tag not in tech_map:
                        tech_map[tag] = {
                            "github_repos": 0,
                            "avg_velocity": 0,
                            "stackoverflow_questions": st.get("question_count", 0) or 0,
                            "category": "framework",
                        }
                    elif tag:
                        tech_map[tag]["stackoverflow_questions"] = (
                            st.get("question_count", 0) or 0
                        )
            except (json.JSONDecodeError, TypeError):
                pass

        # Convert to list and calculate metrics
        for tech, metrics in tech_map.items():
            adoption_score = min(
                1.0,
                (metrics["github_repos"] + metrics["stackoverflow_questions"]) / 1000,
            )

            # Determine trend direction
            if metrics["avg_velocity"] > 50:
                trend_direction = "rising"
            elif metrics["avg_velocity"] > 10:
                trend_direction = "stable"
            else:
                trend_direction = "declining"

            tech_data.append(
                {
                    "technology": tech,
                    "category": metrics["category"],
                    "adoption_score": adoption_score,
                    "trend_direction": trend_direction,
                    "github_repos": metrics["github_repos"],
                    "stackoverflow_questions": metrics["stackoverflow_questions"],
                    "avg_company_age": 3.0,  # Placeholder
                    "analyzed_at": datetime.now(timezone.utc).isoformat(),
                    "record_count": metrics["github_repos"]
                    + metrics["stackoverflow_questions"],
                }
            )

        insights["tech_data"] = tech_data

        # Store results
        cursor = conn.cursor()
        cursor.execute("DELETE FROM analysis_technology_stack")

        for data in tech_data:
            cursor.execute(
                """INSERT INTO analysis_technology_stack
                   (technology, category, adoption_score, trend_direction,
                    github_repos, stackoverflow_questions, avg_company_age,
                    analyzed_at, record_count)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    data["technology"],
                    data["category"],
                    data["adoption_score"],
                    data["trend_direction"],
                    data["github_repos"],
                    data["stackoverflow_questions"],
                    data["avg_company_age"],
                    data["analyzed_at"],
                    data["record_count"],
                ),
            )

        conn.commit()
        cursor.close()
        conn.close()

        _logger.info("TechnologyStackAgent: Analyzed %d technologies", len(tech_data))

        return AgentResult(
            agent_name=self.name,
            status="success",
            data={
                "technologies_analyzed": len(tech_data),
                "records_affected": len(tech_data),
            },
        )
