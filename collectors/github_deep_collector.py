"""GitHub deep collector — enriched repo signals beyond basic trending.

Extends the GithubTrendsCollector pattern by fetching per-repo detail:
  - Commit frequency (last N days)
  - Contributor count and top contributors
  - Recent release cadence
  - License type, fork depth, open issues/PRs
  - Language breakdown

Data sources: GitHub REST API v3 (search + repo + commits + contributors + releases).
Rate limit: 5,000 req/hour with token, 60 req/hour without.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone

from collectors.base import BaseCollector, CollectionResult
from utils.http_client import get_http_session

_logger = logging.getLogger(__name__)

_SEARCH_URL = "https://api.github.com/search/repositories"
_REPO_URL = "https://api.github.com/repos/{owner}/{repo}"
_COMMITS_URL = "https://api.github.com/repos/{owner}/{repo}/commits"
_CONTRIBUTORS_URL = "https://api.github.com/repos/{owner}/{repo}/contributors"
_RELEASES_URL = "https://api.github.com/repos/{owner}/{repo}/releases"

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS github_deep_repos (
    id INT PRIMARY KEY AUTO_INCREMENT,
    repo_name VARCHAR(255) NOT NULL,
    repo_url VARCHAR(2048),
    description TEXT,
    stars INT DEFAULT 0,
    forks INT DEFAULT 0,
    open_issues INT DEFAULT 0,
    language VARCHAR(100),
    license_type VARCHAR(100),
    topics TEXT COMMENT 'JSON: repo topics',
    created_at DATETIME,
    pushed_at DATETIME,
    commit_count_30d INT DEFAULT 0 COMMENT 'Commits in last 30 days',
    contributor_count INT DEFAULT 0,
    top_contributors TEXT COMMENT 'JSON: top 5 contributor logins',
    recent_releases INT DEFAULT 0 COMMENT 'Releases in last 90 days',
    latest_release_at DATETIME COMMENT 'Most recent release date',
    fork_parent VARCHAR(255) COMMENT 'Parent repo if forked',
    repo_size_kb INT DEFAULT 0,
    default_branch VARCHAR(100),
    raw_score FLOAT DEFAULT 0 COMMENT 'Composite signal strength 0-100',
    collected_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_github_deep_repo (repo_name)
)
"""


class GithubDeepCollector(BaseCollector):
    """Collects deep GitHub repository data for opportunity intelligence.

    Goes beyond basic star/fork trending by fetching per-repo detail pages:
    commit activity, contributor profiles, release history, and license data.
    This richer signal feeds Phase 5 agents (Technology Stack, Moat Analyzer).
    """

    @property
    def name(self) -> str:
        return "github_deep"

    def _build_session(self, config: dict) -> "requests.Session":  # noqa: F821
        """Build an HTTP session with GitHub auth headers."""
        session = get_http_session(timeout=20)
        api_conf = config.get("api", {})
        token = api_conf.get("token", "")
        if token:
            session.headers["Authorization"] = f"token {token}"
        session.headers["Accept"] = "application/vnd.github.v3+json"
        return session

    def _check_rate_limit(self, resp) -> None:
        """Sleep if approaching GitHub rate limit."""
        remaining = resp.headers.get("X-RateLimit-Remaining", "")
        if remaining and int(remaining) < 5:
            reset_ts = int(resp.headers.get("X-RateLimit-Reset", "0"))
            if reset_ts:
                wait = max(1, reset_ts - int(time.time()))
                _logger.warning(
                    "GitHub rate limit low (%s remaining), sleeping %ds",
                    remaining,
                    wait,
                )
                time.sleep(wait)

    def _fetch_json(
        self, session, url: str, params: dict | None = None
    ) -> dict | list | None:
        """Fetch JSON from GitHub API with error handling."""
        try:
            resp = session.get(url, params=params, timeout=20)
            self._check_rate_limit(resp)
            if resp.status_code == 403:
                _logger.warning("GitHub API forbidden (rate limit?): %s", url)
                return None
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            _logger.warning("GitHub API fetch failed: %s — %s", url, e)
            return None

    def _compute_raw_score(
        self,
        stars: int,
        commit_count: int,
        contributor_count: int,
        recent_releases: int,
    ) -> float:
        """Compute composite signal strength (0-100).

        Weights:
          - Star velocity (normalized to 0-30)
          - Commit frequency (normalized to 0-30)
          - Contributor breadth (normalized to 0-20)
          - Release cadence (normalized to 0-20)
        """
        star_score = min(30, stars / 100 * 30)
        commit_score = min(30, commit_count / 30 * 30)
        contrib_score = min(20, contributor_count / 20 * 20)
        release_score = min(20, recent_releases / 5 * 20)
        return round(
            min(100, star_score + commit_score + contrib_score + release_score), 1
        )

    def _fetch_repo_detail(
        self, session, owner: str, repo: str, detail_config: dict
    ) -> dict:
        """Fetch enriched repo detail from multiple GitHub endpoints."""
        detail = {
            "commit_count_30d": 0,
            "contributor_count": 0,
            "top_contributors": [],
            "recent_releases": 0,
            "latest_release_at": None,
            "fork_parent": None,
            "repo_size_kb": 0,
            "default_branch": "main",
            "license_type": None,
            "open_issues": 0,
        }

        lookback = detail_config.get("lookback_days", 30)
        since_date = (datetime.now(timezone.utc) - timedelta(days=lookback)).strftime(
            "%Y-%m-%dT00:00:00Z"
        )

        # Repo metadata
        repo_data = self._fetch_json(session, _REPO_URL.format(owner=owner, repo=repo))
        if isinstance(repo_data, dict):
            detail["license_type"] = (repo_data.get("license") or {}).get("spdx_id")
            detail["open_issues"] = repo_data.get("open_issues_count", 0)
            detail["repo_size_kb"] = repo_data.get("size", 0)
            detail["default_branch"] = repo_data.get("default_branch", "main")
            if repo_data.get("parent"):
                detail["fork_parent"] = repo_data["parent"].get("full_name")

        # Commits (last N days)
        if detail_config.get("commits", True):
            commits = self._fetch_json(
                session,
                _COMMITS_URL.format(owner=owner, repo=repo),
                params={"since": since_date, "per_page": 1},
            )
            if isinstance(commits, list):
                detail["commit_count_30d"] = len(commits)

        # Contributors
        if detail_config.get("contributors", True):
            contributors = self._fetch_json(
                session,
                _CONTRIBUTORS_URL.format(owner=owner, repo=repo),
                params={"per_page": 5},
            )
            if isinstance(contributors, list):
                detail["contributor_count"] = len(contributors)
                detail["top_contributors"] = [
                    c.get("login", "") for c in contributors[:5]
                ]

        # Releases (last 90 days)
        if detail_config.get("releases", True):
            releases = self._fetch_json(
                session,
                _RELEASES_URL.format(owner=owner, repo=repo),
                params={"per_page": 10},
            )
            if isinstance(releases, list):
                release_since = datetime.now(timezone.utc) - timedelta(days=90)
                recent = []
                for r in releases:
                    published = r.get("published_at", "")
                    if published:
                        try:
                            pub_dt = datetime.fromisoformat(
                                published.replace("Z", "+00:00")
                            )
                            if pub_dt >= release_since:
                                recent.append(r)
                        except (ValueError, TypeError):
                            pass
                detail["recent_releases"] = len(recent)
                if recent:
                    latest_pub = recent[0].get("published_at", "")
                    if latest_pub:
                        detail["latest_release_at"] = latest_pub[:26]

        return detail

    def collect(self, conn) -> CollectionResult:
        result = CollectionResult(collector_name=self.name)
        config = self.config.get("github_deep", {})

        if self.dry_run:
            result.status = "success"
            return result

        session = self._build_session(config)

        # Ensure table exists
        cursor = conn.cursor()
        cursor.execute(_CREATE_TABLE_SQL)
        conn.commit()

        # Build search queries with {since} substitution
        search_queries = config.get(
            "search_queries",
            [
                "created:>{since} stars:>50 language:python topic:ai",
                "created:>{since} stars:>50 topic:llm topic:agent",
                "created:>{since} stars:>100 topic:startup topic:saas",
            ],
        )
        since = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
        min_stars = config.get("min_stars", 50)

        detail_config = config.get(
            "detail_endpoints",
            {
                "commits": True,
                "contributors": True,
                "releases": True,
                "lookback_days": 30,
            },
        )

        for raw_query in search_queries:
            query = raw_query.replace("{since}", since)
            params = {"q": query, "sort": "stars", "order": "desc", "per_page": 30}

            data = self._fetch_json(session, _SEARCH_URL, params=params)
            if not isinstance(data, dict):
                continue

            items = data.get("items", [])
            if not items:
                continue

            for item in items:
                try:
                    repo_name = item.get("full_name", "")
                    repo_url = item.get("html_url", "")
                    stars = item.get("stargazers_count", 0)

                    if stars < min_stars:
                        continue

                    parts = repo_name.split("/", 1)
                    if len(parts) != 2:
                        continue
                    owner, repo = parts

                    # Fetch enriched detail
                    detail = self._fetch_repo_detail(
                        session, owner, repo, detail_config
                    )

                    description = item.get("description", "") or ""
                    topics = item.get("topics", [])
                    created = item.get("created_at", "")
                    pushed = item.get("pushed_at", "")
                    forks = item.get("forks_count", 0)
                    language = item.get("language", "")

                    raw_score = self._compute_raw_score(
                        stars,
                        detail["commit_count_30d"],
                        detail["contributor_count"],
                        detail["recent_releases"],
                    )

                    import json as _json

                    cursor.execute(
                        """INSERT INTO github_deep_repos
                           (repo_name, repo_url, description, stars, forks, open_issues,
                            language, license_type, topics, created_at, pushed_at,
                            commit_count_30d, contributor_count, top_contributors,
                            recent_releases, latest_release_at, fork_parent,
                            repo_size_kb, default_branch, raw_score, collected_at)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                   %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                           ON DUPLICATE KEY UPDATE
                             stars = VALUES(stars),
                             forks = VALUES(forks),
                             open_issues = VALUES(open_issues),
                             commit_count_30d = VALUES(commit_count_30d),
                             contributor_count = VALUES(contributor_count),
                             top_contributors = VALUES(top_contributors),
                             recent_releases = VALUES(recent_releases),
                             latest_release_at = VALUES(latest_release_at),
                             raw_score = VALUES(raw_score),
                             pushed_at = VALUES(pushed_at),
                             collected_at = VALUES(collected_at)""",
                        (
                            repo_name,
                            repo_url,
                            description[:2000],
                            stars,
                            forks,
                            detail["open_issues"],
                            language,
                            detail["license_type"],
                            _json.dumps(topics) if topics else None,
                            created[:26] if created else None,
                            pushed[:26] if pushed else None,
                            detail["commit_count_30d"],
                            detail["contributor_count"],
                            _json.dumps(detail["top_contributors"]),
                            detail["recent_releases"],
                            detail["latest_release_at"],
                            detail["fork_parent"],
                            detail["repo_size_kb"],
                            detail["default_branch"],
                            raw_score,
                            datetime.now(timezone.utc).isoformat(),
                        ),
                    )

                    # Dual-write: raw_signals for scoring pipeline
                    cursor.execute(
                        """INSERT IGNORE INTO raw_signals
                           (signal_type, source_name, source_url, title, body_text,
                            entity_name, published_at, collected_at, processed)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0)""",
                        (
                            "github_deep",
                            "github_deep",
                            repo_url,
                            f"{repo_name} — {stars}★, {detail['commit_count_30d']} commits/30d, {detail['contributor_count']} contributors",
                            description[:5000],
                            repo_name,
                            pushed[:26] if pushed else created[:26],
                            datetime.now(timezone.utc).isoformat(),
                        ),
                    )

                    # Publish to Kafka for real-time stream
                    self.publish_signal(
                        "github_deep",
                        title=f"{repo_name} — {stars}★, {detail['commit_count_30d']} commits/30d",
                        entity_name=repo_name,
                        source_url=repo_url,
                        body_text=description[:5000],
                        raw_score=raw_score,
                        language=language,
                        stars=stars,
                        commit_count=detail["commit_count_30d"],
                        contributor_count=detail["contributor_count"],
                    )

                    result.records_collected += 1

                except Exception as e:
                    result.errors.append(f"Error processing repo {repo_name}: {e}")

        result.records_inserted = result.records_collected
        cursor.close()
        conn.commit()
        result.status = "success" if result.records_inserted > 0 else "partial"
        return result
