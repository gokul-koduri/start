"""GitHub trending repositories collector.

Monitors GitHub trending repos and star velocity to detect:
  - Emerging technologies gaining traction
  - Open-source projects entering growth phase
  - Technology adoption signals (e.g., new LLM frameworks)
  - Developer community signals around specific domains

Data source: GitHub Search API (public, rate-limited to 10 req/min unauthenticated)
Alternative: GitHub Trending page scraping (backup)
"""

import logging
from datetime import datetime, timedelta, timezone

from collectors.base import BaseCollector, CollectionResult
from utils.http_client import get_http_session

_logger = logging.getLogger(__name__)

_GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"
_GITHUB_TRENDING_URL = "https://github.com/trending"


class GithubTrendsCollector(BaseCollector):
    """Collects trending GitHub repositories as technology adoption signals."""

    @property
    def name(self) -> str:
        return "github_trends"

    def collect(self, conn) -> CollectionResult:
        result = CollectionResult(collector_name=self.name)
        gh_config = self.config.get("github", {})
        token = gh_config.get("token", "")

        session = get_http_session()
        if token:
            session.headers["Authorization"] = f"token {token}"

        session.headers["Accept"] = "application/vnd.github.v3+json"

        search_queries = gh_config.get("search_queries", [
            "created:>{since} stars:>5 language:python topic:machine-learning",
            "created:>{since} stars:>5 topic:startup topic:saas",
            "created:>{since} stars:>5 topic:ai topic:agent topic:llm",
        ])

        since = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")

        cursor = conn.cursor()

        for raw_query in search_queries:
            query = raw_query.replace("{since}", since)

            params = {
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": 30,
            }

            try:
                resp = session.get(_GITHUB_SEARCH_URL, params=params, timeout=20)
                resp.raise_for_status()

                if resp.status_code != 200:
                    result.errors.append(f"GitHub API returned {resp.status_code}")
                    continue

                data = resp.json()

            except Exception as e:
                result.errors.append(f"GitHub API fetch failed: {e}")
                _logger.warning("GitHub fetch failed: %s", e)
                continue

            for item in data.get("items", []):
                try:
                    repo_name = item.get("full_name", "")
                    repo_url = item.get("html_url", "")
                    stars = item.get("stargazers_count", 0)
                    forks = item.get("forks_count", 0)
                    language = item.get("language", "")
                    description = item.get("description", "")
                    topics = item.get("topics", [])
                    created = item.get("created_at", "")
                    pushed = item.get("pushed_at", "")

                    # Calculate star velocity (stars per day since creation)
                    weekly_stars_delta = 0
                    if created:
                        try:
                            created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                            age_days = max(1, (datetime.now(timezone.utc) - created_dt).days)
                            weekly_stars_delta = round(stars / age_days * 7, 1)
                        except (ValueError, TypeError):
                            pass

                    # Upsert repo data
                    cursor.execute(
                        """INSERT INTO github_trends
                           (repo_name, repo_url, stars, forks, language, description,
                            topic_tags, created_at, pushed_at, weekly_stars_delta,
                            source_signal_type, collected_at)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                           ON DUPLICATE KEY UPDATE
                             stars = VALUES(stars),
                             forks = VALUES(forks),
                             weekly_stars_delta = VALUES(weekly_stars_delta),
                             pushed_at = VALUES(pushed_at),
                             collected_at = VALUES(collected_at)""",
                        (
                            repo_name,
                            repo_url,
                            stars,
                            forks,
                            language,
                            (description or "")[:1000],
                            ",".join(topics) if topics else None,
                            created[:26] if created else None,
                            pushed[:26] if pushed else None,
                            weekly_stars_delta,
                            "github_trending",
                            datetime.now(timezone.utc).isoformat(),
                        ),
                    )

                    # Insert into raw_signals
                    cursor.execute(
                        """INSERT IGNORE INTO raw_signals
                           (signal_type, source_name, source_url, title, body_text,
                            entity_name, published_at, collected_at, processed)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0)""",
                        (
                            "github_trend",
                            "github_trends",
                            repo_url,
                            f"{repo_name} ({language}) — {stars}★",
                            (description or "")[:5000],
                            repo_name,
                            pushed[:26] if pushed else created[:26],
                            datetime.now(timezone.utc).isoformat(),
                        ),
                    )

                    # Publish to Kafka for real-time stream processing
                    self.publish_signal(
                        "github_trend",
                        title=f"{repo_name} ({language}) — {stars}★",
                        entity_name=repo_name,
                        source_url=repo_url,
                        body_text=(description or "")[:5000],
                        raw_score=raw_score_value,
                        language=language,
                        stars=stars,
                    )

                    result.records_collected += 1

                    # Check if this is a notable repo
                    if weekly_stars_delta > 10 and stars > 50:
                        _logger.info(
                            "⭐ TRENDING: %s — %d★, %.1f stars/week",
                            repo_name, stars, weekly_stars_delta,
                        )

                except Exception as e:
                    result.errors.append(f"Error processing GitHub repo: {e}")

            result.records_inserted = result.records_collected

        cursor.close()
        conn.commit()
        result.status = "success" if result.records_inserted > 0 else "partial"
        return result
