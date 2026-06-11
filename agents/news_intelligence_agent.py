"""News Intelligence Agent — trend analysis of collected news articles."""

import json
import logging
from collections import Counter
from datetime import datetime, timezone

from agents.base import AgentResult, BaseAgent
from db.connection import get_connection
from db import schema

_logger = logging.getLogger(__name__)


class NewsIntelligenceAgent(BaseAgent):
    """Analyzes news articles for sentiment, trends, and emerging patterns.

    Produces:
    - Trending failure topics
    - Manufacturing news volume and trends
    - Most-mentioned startup names
    - Source reliability analysis
    - Emerging patterns detection
    """

    @property
    def name(self) -> str:
        return "news_intelligence"

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        conn = get_connection()
        schema.init_schema(conn)

        insights = {}

        # 1. Manufacturing news volume
        cursor = conn.cursor()
        cursor.execute(
            """SELECT
                 COUNT(*) as total_articles,
                 SUM(CASE WHEN is_manufacturing = 1 THEN 1 ELSE 0 END) as mfg_articles,
                 SUM(CASE WHEN mentions_failure = 1 THEN 1 ELSE 0 END) as failure_articles,
                 SUM(CASE WHEN is_manufacturing = 1 AND mentions_failure = 1 THEN 1 ELSE 0 END) as mfg_failure_intersection
               FROM news_articles"""
        )
        mfg_volume = cursor.fetchone()
        cursor.close()
        insights["volume_overview"] = dict(mfg_volume) if mfg_volume else {}

        # 2. Source distribution
        cursor = conn.cursor()
        cursor.execute(
            """SELECT source_feed, COUNT(*) as count,
                      SUM(is_manufacturing) as mfg_count,
                      SUM(mentions_failure) as failure_count
               FROM news_articles
               GROUP BY source_feed
               ORDER BY count DESC"""
        )
        source_dist = cursor.fetchall()
        insights["source_distribution"] = [dict(r) for r in source_dist]
        cursor.close()

        # 3. Most-mentioned startup names
        cursor = conn.cursor()
        cursor.execute(
            """SELECT startup_name_extracted, COUNT(*) as mentions
               FROM news_articles
               WHERE startup_name_extracted IS NOT NULL
                 AND startup_name_extracted != ''
               GROUP BY startup_name_extracted
               ORDER BY mentions DESC
               LIMIT 20"""
        )
        startup_mentions = cursor.fetchall()
        insights["startup_mentions"] = [dict(r) for r in startup_mentions]
        cursor.close()

        # 4. Title keyword frequency (top 30 non-stopwords)
        cursor = conn.cursor()
        cursor.execute("SELECT title FROM news_articles")
        titles = cursor.fetchall()
        cursor.close()
        stopwords = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "is",
            "it",
            "its",
            "was",
            "are",
            "has",
            "had",
            "be",
            "this",
            "that",
            "from",
            "as",
            "how",
            "not",
            "will",
            "can",
            "do",
            "we",
            "he",
            "she",
            "they",
            "their",
            "you",
            "your",
            "who",
            "what",
            "when",
            "which",
        }
        word_freq = Counter()
        for row in titles:
            words = row["title"].lower().split()
            for w in words:
                w = w.strip(".,!?;:'\"()-")
                if len(w) > 3 and w not in stopwords:
                    word_freq[w] += 1
        insights["top_keywords"] = dict(word_freq.most_common(30))

        # 5. Manufacturing keyword trends in titles
        cursor = conn.cursor()
        cursor.execute("""SELECT title FROM news_articles WHERE is_manufacturing = 1""")
        mfg_titles = cursor.fetchall()
        cursor.close()
        mfg_word_freq = Counter()
        for row in mfg_titles:
            words = row["title"].lower().split()
            for w in words:
                w = w.strip(".,!?;:'\"()-")
                if len(w) > 3 and w not in stopwords:
                    mfg_word_freq[w] += 1
        insights["manufacturing_keywords"] = dict(mfg_word_freq.most_common(20))

        # 6. Publication timeline
        cursor = conn.cursor()
        cursor.execute(
            """SELECT DATE(published_at) as pub_date, COUNT(*) as articles
               FROM news_articles
               WHERE published_at IS NOT NULL
               GROUP BY pub_date
               ORDER BY pub_date DESC
               LIMIT 30"""
        )
        timeline = cursor.fetchall()
        insights["publication_timeline"] = [dict(r) for r in timeline]
        cursor.close()

        # Store results
        cursor = conn.cursor()
        cursor.execute("DELETE FROM analysis_news_intelligence")
        cursor.execute(
            """INSERT INTO analysis_news_intelligence
               (analysis_type, insights_json, analyzed_at, record_count)
               VALUES (%s, %s, %s, %s)""",
            (
                "news_intelligence_full",
                json.dumps(insights, default=str),
                datetime.now(timezone.utc).isoformat(),
                mfg_volume["total_articles"] if mfg_volume else 0,
            ),
        )
        conn.commit()
        cursor.close()
        conn.close()

        total = mfg_volume["total_articles"] if mfg_volume else 0
        mfg = mfg_volume["mfg_articles"] if mfg_volume else 0
        _logger.info(
            "NewsIntelligenceAgent: %d articles, %d manufacturing, top keyword: %s",
            total,
            mfg,
            list(word_freq.keys())[0] if word_freq else "N/A",
        )

        return AgentResult(
            agent_name=self.name,
            status="success",
            data={
                "total_articles": total,
                "manufacturing_articles": mfg,
                "unique_startups_mentioned": len(startup_mentions),
                "top_keywords": len(insights["top_keywords"]),
                "records_affected": total,
                "top_insight": f"{total} articles analyzed, {mfg} manufacturing-related ({round(mfg/total*100, 1) if total else 0}%)",
            },
        )
