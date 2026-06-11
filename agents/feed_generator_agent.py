"""Feed generator agent — generates RSS/Atom feeds."""

import logging
from agents.base import BaseAgent, AgentResult
from datetime import datetime, timezone
from pathlib import Path

_logger = logging.getLogger(__name__)


class FeedGeneratorAgent(BaseAgent):
    """Generates curated RSS/Atom feeds."""

    @property
    def name(self) -> str:
        return "feed_generator"

    def execute(self, upstream_results) -> AgentResult:
        """Generate RSS feed."""
        try:
            from db.connection import get_connection
            from db import schema

            conn = get_connection()
            schema.init_schema(conn)
            cursor = conn.cursor()

            cursor.execute(
                """SELECT title, url, source_name, published_at, summary
                   FROM news_articles
                   ORDER BY published_at DESC LIMIT 50"""
            )
            articles = [dict(r) for r in cursor.fetchall()]

            cursor.close()
            conn.close()

            # Generate RSS XML
            rss_items = []
            for article in articles:
                rss_items.append(f"""
                <item>
                  <title>{article.get('title', '')}</title>
                  <link>{article.get('url', '')}</link>
                  <description>{article.get('summary', '')[:200]}...</description>
                  <pubDate>{article.get('published_at', '')}</pubDate>
                </item>
                """)

            rss_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
            <rss version="2.0">
              <channel>
                <title>Startup Research Report</title>
                <link>https://github.com/yourusername/startup-research</link>
                <description>Latest startup failure research and signals</description>
                <lastBuildDate>{datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S %z')}</lastBuildDate>
                {''.join(rss_items)}
              </channel>
            </rss>
            """

            output_path = "data/feed.xml"
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                f.write(rss_xml)

            return AgentResult(
                agent_name=self.name,
                status="success",
                data={"articles": len(articles), "output": output_path},
            )
        except Exception as e:
            return AgentResult(
                agent_name=self.name,
                status="failed",
                errors=[str(e)],
            )
