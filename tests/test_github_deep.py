"""Tests for the GitHub Deep Collector."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch, call

sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Mock DB dependencies before importing collector ──
mock_pymysql = MagicMock()
sys.modules["pymysql"] = mock_pymysql
sys.modules["pymysql.cursors"] = mock_pymysql.cursors

# Save originals so we don't poison other test modules
_saved_db_modules = {
    key: sys.modules.pop(key, None)
    for key in ("db", "db.connection", "db.schema", "db.dedup")
}

mock_db = MagicMock()
sys.modules["db"] = mock_db
sys.modules["db.connection"] = mock_db
sys.modules["db.connection"].get_connection = MagicMock()
sys.modules["db.schema"] = MagicMock()
sys.modules["db.dedup"] = MagicMock()
sys.modules["db.dedup"].dedup_startup = MagicMock(return_value=False)

from collectors.github_deep_collector import GithubDeepCollector, _CREATE_TABLE_SQL

# Restore real db modules so other tests aren't poisoned
for key, orig in _saved_db_modules.items():
    if orig is not None:
        sys.modules[key] = orig
    else:
        sys.modules.pop(key, None)


def _make_search_response(repos=None):
    """Build a mock GitHub Search API response."""
    return {
        "total_count": len(repos or []),
        "items": repos or [],
    }


def _make_repo_item(name="org/repo", stars=100, forks=20, lang="Python",
                    description="A test repo", topics=None, created="2024-01-01T00:00:00Z",
                    pushed="2024-06-01T00:00:00Z"):
    """Build a single repo item from search results."""
    return {
        "full_name": name,
        "html_url": f"https://github.com/{name}",
        "stargazers_count": stars,
        "forks_count": forks,
        "language": lang,
        "description": description,
        "topics": topics or ["ai", "ml"],
        "created_at": created,
        "pushed_at": pushed,
    }


def _make_mock_session(responses=None):
    """Build a mock requests.Session that returns given JSON responses in order."""
    session = MagicMock()
    session.headers = {}
    response_iter = iter(responses or [])

    def mock_get(url, params=None, timeout=None):
        resp = MagicMock()
        resp.headers = {"X-RateLimit-Remaining": "4999", "X-RateLimit-Reset": "9999999999"}
        try:
            resp.json.return_value = next(response_iter)
            resp.status_code = 200
        except StopIteration:
            resp.json.return_value = {}
            resp.status_code = 200
        return resp

    session.get = mock_get
    return session


class TestGithubDeepCollectorName:
    def test_name(self):
        c = GithubDeepCollector(config={"github_deep": {}})
        assert c.name == "github_deep"


class TestGithubDeepCollectorConfig:
    def test_config_defaults_empty(self):
        c = GithubDeepCollector(config={})
        assert c.name == "github_deep"
        assert c.dry_run is False

    def test_dry_run_mode(self):
        c = GithubDeepCollector(config={}, dry_run=True)
        mock_conn = MagicMock()
        result = c.collect(mock_conn)
        assert result.status == "success"
        assert result.records_collected == 0


class TestGithubDeepCollectorScoring:
    def test_score_high_activity(self):
        c = GithubDeepCollector(config={"github_deep": {}})
        score = c._compute_raw_score(stars=1000, commit_count=60,
                                    contributor_count=30, recent_releases=5)
        assert score > 80

    def test_score_low_activity(self):
        c = GithubDeepCollector(config={"github_deep": {}})
        score = c._compute_raw_score(stars=5, commit_count=2,
                                    contributor_count=1, recent_releases=0)
        assert score < 20

    def test_score_capped_at_100(self):
        c = GithubDeepCollector(config={"github_deep": {}})
        score = c._compute_raw_score(stars=50000, commit_count=999,
                                    contributor_count=500, recent_releases=100)
        assert score <= 100.0

    def test_score_zero(self):
        c = GithubDeepCollector(config={"github_deep": {}})
        score = c._compute_raw_score(stars=0, commit_count=0,
                                    contributor_count=0, recent_releases=0)
        assert score == 0.0


class TestGithubDeepCollectorCollect:
    @patch("collectors.github_deep_collector.get_http_session")
    def test_collect_search_results(self, mock_get_session):
        """Test basic search flow: search returns repos, detail endpoints called."""
        repo = _make_repo_item("openai/whisper", stars=60000)
        search_resp = _make_search_response([repo])
        # Detail endpoints return minimal data
        repo_detail = {"license": {"spdx_id": "MIT"}, "open_issues_count": 42,
                       "size": 5000, "default_branch": "main", "parent": None}
        commits_resp = [{"sha": "abc"}]
        contrib_resp = [{"login": "user1"}, {"login": "user2"}]
        releases_resp = [{"published_at": "2024-05-01T00:00:00Z"}]

        mock_session = _make_mock_session([
            search_resp, repo_detail, commits_resp, contrib_resp, releases_resp,
        ])
        mock_get_session.return_value = mock_session

        c = GithubDeepCollector(config={"github_deep": {"min_stars": 0}})
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        result = c.collect(mock_conn)

        assert result.status == "success"
        assert result.records_collected == 1
        assert result.records_inserted == 1
        # Verify UPSERT was called (github_deep_repos + raw_signals + CREATE TABLE)
        assert mock_cursor.execute.call_count >= 3
        mock_conn.commit.assert_called()

    @patch("collectors.github_deep_collector.get_http_session")
    def test_collect_min_stars_filter(self, mock_get_session):
        """Test that repos below min_stars threshold are skipped."""
        repo_low = _make_repo_item("low/repo", stars=10)
        repo_high = _make_repo_item("high/repo", stars=500)

        search_resp_low = _make_search_response([repo_low])
        search_resp_high = _make_search_response([repo_high])
        # Detail for high repo only
        repo_detail = {"license": None, "open_issues_count": 0, "size": 100, "default_branch": "main"}

        mock_session = _make_mock_session([
            search_resp_low,  # First query returns low-star repo
        ])
        mock_get_session.return_value = mock_session

        c = GithubDeepCollector(config={"github_deep": {"min_stars": 50}})
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        result = c.collect(mock_conn)
        assert result.records_collected == 0  # Filtered out

    @patch("collectors.github_deep_collector.get_http_session")
    def test_collect_empty_search_results(self, mock_get_session):
        """Test handling of empty search results."""
        search_resp = _make_search_response([])
        mock_session = _make_mock_session([search_resp])
        mock_get_session.return_value = mock_session

        c = GithubDeepCollector(config={"github_deep": {"min_stars": 0}})
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        result = c.collect(mock_conn)
        assert result.records_collected == 0
        assert result.status == "partial"

    @patch("collectors.github_deep_collector.get_http_session")
    def test_collect_multiple_repos(self, mock_get_session):
        """Test collecting multiple repos from a single search query."""
        repos = [
            _make_repo_item("org/repo1", stars=100),
            _make_repo_item("org/repo2", stars=200),
            _make_repo_item("org/repo3", stars=300),
        ]
        search_resp = _make_search_response(repos)
        # Detail endpoints cycle for each repo
        repo_detail = {"license": {"spdx_id": "Apache-2.0"}, "open_issues_count": 5,
                       "size": 200, "default_branch": "main", "parent": None}
        commits_resp = []
        contrib_resp = [{"login": "dev1"}, {"login": "dev2"}, {"login": "dev3"}]
        releases_resp = []

        # For 3 repos: search + 4 detail calls each = search + 12 detail calls
        mock_session = _make_mock_session(
            [search_resp] +
            [repo_detail, commits_resp, contrib_resp, releases_resp] * 3
        )
        mock_get_session.return_value = mock_session

        c = GithubDeepCollector(config={"github_deep": {"min_stars": 0}})
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        result = c.collect(mock_conn)
        assert result.records_collected == 3
        assert result.status == "success"


class TestGithubDeepCollectorRateLimit:
    @patch("collectors.github_deep_collector.time")
    def test_rate_limit_sleep(self, mock_time):
        """Test that low rate limit remaining triggers sleep."""
        mock_time.time.return_value = 1000
        c = GithubDeepCollector(config={"github_deep": {}})
        resp = MagicMock()
        # remaining < 5, reset at timestamp 1010 → sleep ~10s
        resp.headers = {"X-RateLimit-Remaining": "2", "X-RateLimit-Reset": "1010"}
        c._check_rate_limit(resp)
        mock_time.sleep.assert_called_once()
        assert mock_time.sleep.call_args[0][0] >= 1

    @patch("collectors.github_deep_collector.time")
    def test_rate_limit_no_sleep_when_high(self, mock_time):
        """Test that high rate limit remaining does NOT trigger sleep."""
        c = GithubDeepCollector(config={"github_deep": {}})
        resp = MagicMock()
        resp.headers = {"X-RateLimit-Remaining": "4990", "X-RateLimit-Reset": "0"}
        c._check_rate_limit(resp)
        mock_time.sleep.assert_not_called()


class TestGithubDeepCollectorErrorHandling:
    @patch("collectors.github_deep_collector.get_http_session")
    def test_api_failure_continues(self, mock_get_session):
        """Test that a failed search query doesn't crash the collector."""
        # Non-dict response simulates API failure
        mock_session = _make_mock_session(["error"])
        mock_get_session.return_value = mock_session

        c = GithubDeepCollector(config={"github_deep": {"min_stars": 0}})
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        result = c.collect(mock_conn)
        assert result.status == "partial"
        assert result.records_collected == 0

    @patch("collectors.github_deep_collector.get_http_session")
    def test_individual_repo_error_appended(self, mock_get_session):
        """Test that detail API failures are handled gracefully — repo still collected with defaults."""
        repo = _make_repo_item("bad/repo", stars=100)
        search_resp = _make_search_response([repo])

        call_count = {"n": 0}

        def mock_get(url, params=None, timeout=None):
            resp = MagicMock()
            resp.headers = {"X-RateLimit-Remaining": "4999", "X-RateLimit-Reset": "9999999999"}
            resp.status_code = 200
            call_count["n"] += 1
            if "search" not in url:
                resp.raise_for_status.side_effect = Exception("API error")
            else:
                resp.json.return_value = search_resp
            return resp

        mock_session = MagicMock()
        mock_session.headers = {}
        mock_session.get = mock_get
        mock_get_session.return_value = mock_session

        c = GithubDeepCollector(config={
            "github_deep": {
                "min_stars": 0,
                "search_queries": ["created:>2024-01-01 stars:>100 topic:test"],
            },
        })
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        result = c.collect(mock_conn)
        # Repo still collected with default detail values (0 commits, 0 contributors, etc.)
        assert result.records_collected == 1
        assert result.status == "success"


class TestGithubDeepCollectorRepoDetail:
    @patch("collectors.github_deep_collector.get_http_session")
    def test_repo_detail_fork_detection(self, mock_get_session):
        """Test that fork parent is detected from repo metadata."""
        repo = _make_repo_item("fork/user-repo", stars=50)
        search_resp = _make_search_response([repo])
        repo_detail = {"license": None, "open_issues_count": 0, "size": 100,
                        "default_branch": "main",
                        "parent": {"full_name": "original/user-repo"}}
        commits_resp = []
        contrib_resp = []
        releases_resp = []

        mock_session = _make_mock_session([
            search_resp, repo_detail, commits_resp, contrib_resp, releases_resp,
        ])
        mock_get_session.return_value = mock_session

        c = GithubDeepCollector(config={"github_deep": {"min_stars": 0}})
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        result = c.collect(mock_conn)
        assert result.records_collected == 1
        # Verify UPSERT was called with fork_parent
        upsert_call = mock_cursor.execute.call_args_list[2]  # 0=CREATE TABLE, 1=INSERT
        assert upsert_call is not None

    @patch("collectors.github_deep_collector.get_http_session")
    def test_detail_endpoints_disabled(self, mock_get_session):
        """Test that detail endpoints can be disabled via config."""
        repo = _make_repo_item("org/simple", stars=100)
        search_resp = _make_search_response([repo])
        repo_detail = {"license": {"spdx_id": "MIT"}, "open_issues_count": 10,
                       "size": 500, "default_branch": "main", "parent": None}

        # Only repo_detail called, no commits/contributors/releases
        mock_session = _make_mock_session([search_resp, repo_detail])
        mock_get_session.return_value = mock_session

        c = GithubDeepCollector(config={"github_deep": {
            "min_stars": 0,
            "detail_endpoints": {
                "commits": False,
                "contributors": False,
                "releases": False,
                "lookback_days": 30,
            },
        }})
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        result = c.collect(mock_conn)
        assert result.records_collected == 1


class TestCreateTableSQL:
    def test_table_sql_is_valid(self):
        """Verify the CREATE TABLE statement has key columns."""
        assert "github_deep_repos" in _CREATE_TABLE_SQL
        assert "repo_name" in _CREATE_TABLE_SQL
        assert "commit_count_30d" in _CREATE_TABLE_SQL
        assert "contributor_count" in _CREATE_TABLE_SQL
        assert "raw_score" in _CREATE_TABLE_SQL
        assert "UNIQUE KEY" in _CREATE_TABLE_SQL
