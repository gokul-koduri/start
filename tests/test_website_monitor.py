"""Tests for the Website Monitor Collector."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Mock DB dependencies before importing collector ──
mock_pymysql = MagicMock()
sys.modules["pymysql"] = mock_pymysql
sys.modules["pymysql.cursors"] = mock_pymysql.cursors

mock_db = MagicMock()
sys.modules["db"] = mock_db
sys.modules["db.connection"] = mock_db
sys.modules["db.connection"].get_connection = MagicMock()
sys.modules["db.schema"] = MagicMock()
sys.modules["db.dedup"] = MagicMock()
sys.modules["db.dedup"].dedup_startup = MagicMock(return_value=False)

from collectors.website_monitor_collector import WebsiteMonitorCollector
from collectors.base import CollectionResult


def _make_html(title="TechCorp AI Platform", meta="AI-powered business intelligence",
               body="We just raised Series A funding and are hiring engineers. "
                    "Our platform is now available in public beta. Check our pricing page.",
               extra_body=""):
    """Build a sample HTML page."""
    return f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <meta name="description" content="{meta}">
</head>
<body>
    <h1>{title}</h1>
    <p>{body}</p>
    <p>{extra_body}</p>
    <script>var x = 1;</script>
    <style>body {{ color: black; }}</style>
</body>
</html>"""


def _make_mock_session(responses=None):
    """Build a mock requests.Session returning HTML strings in order."""
    session = MagicMock()
    session.headers = {}
    response_list = list(responses or [])

    def mock_get(url, timeout=None):
        resp = MagicMock()
        if response_list:
            resp.status_code = 200
            resp.text = response_list.pop(0)
        else:
            resp.status_code = 0
            resp.text = ""
        return resp

    session.get = mock_get
    return session


class TestWebsiteMonitorCollectorName:
    def test_name(self):
        c = WebsiteMonitorCollector(config={})
        assert c.name == "website_monitor"


class TestWebsiteMonitorCollectorConfig:
    def test_dry_run_mode(self):
        c = WebsiteMonitorCollector(config={}, dry_run=True)
        mock_conn = MagicMock()
        result = c.collect(mock_conn)
        assert result.status == "success"
        assert result.records_collected == 0

    def test_no_urls_configured(self):
        c = WebsiteMonitorCollector(config={"website_monitor": {}})
        mock_conn = MagicMock()
        result = c.collect(mock_conn)
        assert result.status == "partial"
        assert result.records_collected == 0


class TestWebsiteMonitorCollectorScoring:
    def test_funding_signal(self):
        c = WebsiteMonitorCollector(config={})
        signals = [{"keyword": "funding", "category": "funding", "weight": 35}]
        score = c._compute_score(signals)
        assert score == 35

    def test_multiple_categories(self):
        c = WebsiteMonitorCollector(config={})
        signals = [
            {"keyword": "funding", "category": "funding", "weight": 35},
            {"keyword": "hiring", "category": "hiring", "weight": 25},
        ]
        score = c._compute_score(signals)
        assert score == 60  # 35 + 25

    def test_extra_signal_in_same_category(self):
        c = WebsiteMonitorCollector(config={})
        signals = [
            {"keyword": "funding", "category": "funding", "weight": 35},
            {"keyword": "series a", "category": "funding", "weight": 35},
        ]
        score = c._compute_score(signals)
        assert score == 40  # 35 + 5 (extra in same category)

    def test_no_signals(self):
        c = WebsiteMonitorCollector(config={})
        score = c._compute_score([])
        assert score == 0

    def test_capped_at_100(self):
        c = WebsiteMonitorCollector(config={})
        signals = [
            {"keyword": "funding", "category": "funding", "weight": 35},
            {"keyword": "hiring", "category": "hiring", "weight": 25},
            {"keyword": "launching", "category": "launch", "weight": 20},
            {"keyword": "pricing", "category": "pricing", "weight": 15},
            {"keyword": "investment", "category": "funding", "weight": 35},
            {"keyword": "careers", "category": "hiring", "weight": 25},
        ]
        score = c._compute_score(signals)
        assert score <= 100.0


class TestWebsiteMonitorCollectorExtract:
    def test_extract_title(self):
        c = WebsiteMonitorCollector(config={})
        html = _make_html(title="My Startup")
        assert c._extract_title(html) == "My Startup"

    def test_extract_title_multiline(self):
        c = WebsiteMonitorCollector(config={})
        html = "<title>\n  Multi-line\n  Title\n</title>"
        assert c._extract_title(html) == "Multi-line Title"

    def test_extract_meta_description(self):
        c = WebsiteMonitorCollector(config={})
        html = _make_html(meta="Great AI product")
        assert "Great AI product" in c._extract_meta_description(html)

    def test_extract_meta_reversed_order(self):
        c = WebsiteMonitorCollector(config={})
        html = '<meta content="Reversed" name="description">'
        assert c._extract_meta_description(html) == "Reversed"

    def test_extract_text_strips_html(self):
        c = WebsiteMonitorCollector(config={})
        html = _make_html(body="Hello <b>World</b>")
        text = c._extract_text(html)
        assert "<b>" not in text
        assert "Hello World" in text

    def test_extract_text_strips_scripts(self):
        c = WebsiteMonitorCollector(config={})
        html = _make_html(extra_body="before<script>var x = 1;</script>after")
        text = c._extract_text(html)
        assert "var x" not in text
        assert "before" in text
        assert "after" in text


class TestWebsiteMonitorCollectorSignals:
    def test_find_funding_signals(self):
        c = WebsiteMonitorCollector(config={})
        html = _make_html(body="We just raised Series A funding")
        text = c._extract_text(html)
        signals = c._find_signals(text, {
            "funding": ["raised", "funding", "series a"],
            "hiring": ["careers"],
        })
        assert len(signals) >= 2
        categories = {s["category"] for s in signals}
        assert "funding" in categories

    def test_find_multiple_categories(self):
        c = WebsiteMonitorCollector(config={})
        html = _make_html(body="We are hiring engineers. Check our pricing page.")
        text = c._extract_text(html)
        signals = c._find_signals(text, {
            "hiring": ["hiring"],
            "pricing": ["pricing"],
        })
        assert len(signals) == 2

    def test_no_signals_found(self):
        c = WebsiteMonitorCollector(config={})
        text = "Welcome to our website about gardening"
        signals = c._find_signals(text, {
            "funding": ["raised", "funding"],
        })
        assert len(signals) == 0

    def test_case_insensitive(self):
        c = WebsiteMonitorCollector(config={})
        text = "WE ARE HIRING NOW"
        signals = c._find_signals(text, {
            "hiring": ["hiring"],
        })
        assert len(signals) == 1

    def test_no_duplicate_signals(self):
        c = WebsiteMonitorCollector(config={})
        text = "Funding is funding is funding"
        signals = c._find_signals(text, {
            "funding": ["funding"],
        })
        assert len(signals) == 1


class TestWebsiteMonitorCollectorHash:
    def test_consistent_hash(self):
        c = WebsiteMonitorCollector(config={})
        h1 = c._compute_hash("hello world")
        h2 = c._compute_hash("hello world")
        assert h1 == h2
        assert len(h1) == 64

    def test_different_content_different_hash(self):
        c = WebsiteMonitorCollector(config={})
        h1 = c._compute_hash("hello world")
        h2 = c._compute_hash("goodbye world")
        assert h1 != h2


class TestWebsiteMonitorCollectorInsert:
    def test_insert_single_snapshot(self):
        c = WebsiteMonitorCollector(config={})
        mock_cursor = MagicMock()
        result = CollectionResult(collector_name="website_monitor")

        c._insert_snapshot(
            mock_cursor, "https://example.com", "Example",
            "Title", "Meta", "Body text", "abc123",
            [{"keyword": "funding", "category": "funding", "weight": 35}],
            200, result,
        )
        assert result.records_collected == 1
        # 2 SQL calls: website_monitor_snapshots + raw_signals
        assert mock_cursor.execute.call_count == 2

    def test_insert_no_signals(self):
        c = WebsiteMonitorCollector(config={})
        mock_cursor = MagicMock()
        result = CollectionResult(collector_name="website_monitor")

        c._insert_snapshot(
            mock_cursor, "https://example.com", "Example",
            "Title", "Meta", "Body text", "abc123",
            [], 200, result,
        )
        assert result.records_collected == 1
        # Only 1 SQL call: website_monitor_snapshots (no raw_signals)
        assert mock_cursor.execute.call_count == 1

    def test_insert_multiple_snapshots(self):
        c = WebsiteMonitorCollector(config={})
        mock_cursor = MagicMock()
        result = CollectionResult(collector_name="website_monitor")

        for i in range(5):
            c._insert_snapshot(
                mock_cursor, f"https://example{i}.com", f"Site {i}",
                "Title", "Meta", "Body", f"hash{i}",
                [{"keyword": "hiring", "category": "hiring", "weight": 25}],
                200, result,
            )
        assert result.records_collected == 5


class TestWebsiteMonitorCollectorIntegration:
    @patch("collectors.website_monitor_collector.time")
    @patch("collectors.website_monitor_collector.get_http_session")
    def test_collect_full_flow(self, mock_get_session, mock_time):
        html = _make_html()
        session = _make_mock_session([html])
        mock_get_session.return_value = session

        c = WebsiteMonitorCollector(config={
            "website_monitor": {
                "watch_urls": [{"url": "https://example.com", "label": "Example"}],
                "min_delay_seconds": 0,
            },
        })

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        result = c.collect(mock_conn)
        assert result.status == "success"
        assert result.records_collected == 1
        mock_conn.commit.assert_called()

    @patch("collectors.website_monitor_collector.get_http_session")
    def test_collect_multiple_urls(self, mock_get_session):
        html1 = _make_html(title="Site One", body="We raised funding")
        html2 = _make_html(title="Site Two", body="Welcome to our website")
        session = _make_mock_session([html1, html2])
        mock_get_session.return_value = session

        c = WebsiteMonitorCollector(config={
            "website_monitor": {
                "watch_urls": [
                    {"url": "https://one.com", "label": "One"},
                    {"url": "https://two.com", "label": "Two"},
                ],
                "min_delay_seconds": 0,
            },
        })

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        result = c.collect(mock_conn)
        assert result.records_collected == 2

    @patch("collectors.website_monitor_collector.get_http_session")
    def test_collect_http_failure(self, mock_get_session):
        session = MagicMock()
        session.get.side_effect = Exception("DNS failure")
        mock_get_session.return_value = session

        c = WebsiteMonitorCollector(config={
            "website_monitor": {
                "watch_urls": [{"url": "https://fail.com", "label": "Fail"}],
                "min_delay_seconds": 0,
            },
        })

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        result = c.collect(mock_conn)
        assert len(result.errors) > 0
        assert result.records_collected == 0

    @patch("collectors.website_monitor_collector.get_http_session")
    def test_collect_handles_insert_error(self, mock_get_session):
        html = _make_html()
        session = _make_mock_session([html])
        mock_get_session.return_value = session

        c = WebsiteMonitorCollector(config={
            "website_monitor": {
                "watch_urls": [{"url": "https://example.com", "label": "Example"}],
                "min_delay_seconds": 0,
            },
        })

        call_count = {"n": 0}

        def execute_side_effect(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise Exception("DB error")

        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = execute_side_effect

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        result = c.collect(mock_conn)
        assert len(result.errors) > 0
