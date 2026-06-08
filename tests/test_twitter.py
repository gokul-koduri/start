"""Tests for the Twitter/X Collector."""

import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

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

from collectors.twitter_collector import TwitterCollector
from collectors.base import CollectionResult

# Restore real db modules so other tests aren't poisoned
for key, orig in _saved_db_modules.items():
    if orig is not None:
        sys.modules[key] = orig
    else:
        sys.modules.pop(key, None)


def _make_tweet_entry(author="@techfounder", text="We just raised Series A funding for our AI startup #startup #funding",
                     published="2024-01-15T10:30:00Z",
                     tweet_url="https://nitter.net/techfounder/status/12345",
                     entry_id="tag:nitter.net,2024-01-15:status12345"):
    """Build a mock Atom entry for a tweet."""
    return f"""<entry xmlns="http://www.w3.org/2005/Atom">
        <id>{entry_id}</id>
        <title>{author}: {text}</title>
        <published>{published}</published>
        <updated>2024-01-15T10:30:00Z</updated>
        <link href="{tweet_url}" rel="alternate" type="text/html" />
        <author><name>{author}</name></author>
    </entry>"""


def _make_feed_response(entries=None):
    """Build a valid Nitter RSS Atom XML feed."""
    entries_xml = "".join(entries or [])
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
    <title>Nitter Search</title>
    <id>https://nitter.net</id>
    {entries_xml}
</feed>"""


def _make_tweet_dict(author="@techfounder",
                      text="We just raised Series A funding #startup",
                      published_date=None, url="https://nitter.net/user/status/123"):
    """Build a tweet dict matching _parse_entry output."""
    return {
        "author": author,
        "text": text,
        "published_date": published_date or (datetime.now(timezone.utc) - timedelta(hours=12)).strftime("%Y-%m-%d"),
        "url": url,
    }


def _make_mock_session(responses=None):
    """Build a mock requests.Session returning XML strings in order."""
    session = MagicMock()
    session.headers = {}
    response_list = list(responses or [])

    def mock_get(url, timeout=None):
        resp = MagicMock()
        resp.status_code = 200
        if response_list:
            resp.content = response_list.pop(0).encode("utf-8") if isinstance(response_list and response_list[0], str) else b""
            # Reset for pop
        else:
            resp.content = b""
        return resp

    # Fix: response_list is already a copy from list()
    rl = list(responses or [])

    def mock_get_v2(url, timeout=None):
        resp = MagicMock()
        resp.status_code = 200
        nonlocal rl
        if rl:
            data = rl.pop(0)
            resp.content = data.encode("utf-8") if isinstance(data, str) else data
        else:
            resp.content = b""
        return resp

    session.get = mock_get_v2
    return session


class TestTwitterCollectorName:
    def test_name(self):
        c = TwitterCollector(config={})
        assert c.name == "twitter"


class TestTwitterCollectorConfig:
    def test_dry_run_mode(self):
        c = TwitterCollector(config={}, dry_run=True)
        mock_conn = MagicMock()
        result = c.collect(mock_conn)
        assert result.status == "success"
        assert result.records_collected == 0

    def test_no_instances_or_queries(self):
        c = TwitterCollector(config={"twitter": {}})
        mock_conn = MagicMock()
        result = c.collect(mock_conn)
        assert result.status == "partial"
        assert result.records_collected == 0


class TestTwitterCollectorScoring:
    def test_recent_with_signals(self):
        c = TwitterCollector(config={})
        # Use today's date so the recency bonus applies (< 72h)
        tweet = _make_tweet_dict(
            published_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        signals = [{"keyword": "funding", "category": "funding"}]
        score = c._compute_score(tweet, signals, [])
        # signals(+30) + recent_today(+25) = 55
        assert score == 55

    def test_old_no_signals(self):
        c = TwitterCollector(config={})
        tweet = _make_tweet_dict(
            published_date=(datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d"),
            text="Just a random tweet about nothing")
        score = c._compute_score(tweet, [], [])
        assert score == 0

    def test_hashtags_boost(self):
        c = TwitterCollector(config={})
        tweet = _make_tweet_dict(
            text="Check out #saas tool",
            published_date=(datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d"))
        score = c._compute_score(tweet, [], ["#saas"])
        # hashtags(+10) + no signals/no recency = 10
        assert score == 10

    def test_entity_mention(self):
        c = TwitterCollector(config={})
        tweet = _make_tweet_dict(
            text='Today "Tech Corp" launched their AI platform',
            published_date=(datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d"))
        score = c._compute_score(tweet, [], [])
        # entity(+15) = 15
        assert score == 15

    def test_capped_at_100(self):
        c = TwitterCollector(config={})
        tweet = _make_tweet_dict(
            published_date=(datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%d"))
        signals = [{"keyword": "funding", "category": "funding"},
                   {"keyword": "launching", "category": "launch"}]
        score = c._compute_score(tweet, signals, ["#ai", "#saas", "#startup"])
        assert score <= 100.0


class TestTwitterCollectorParse:
    def test_parse_valid_entry(self):
        c = TwitterCollector(config={})
        xml = _make_feed_response([_make_tweet_entry()])
        root = ET.fromstring(xml)
        entry = root.findall("{http://www.w3.org/2005/Atom}entry")[0]
        tweet = c._parse_entry(entry)
        assert tweet is not None
        assert tweet["author"] == "@techfounder"
        assert "raised" in tweet["text"]
        assert tweet["url"] == "https://nitter.net/techfounder/status/12345"

    def test_parse_no_title(self):
        c = TwitterCollector(config={})
        xml = """<?xml version="1.0"?>
        <entry xmlns="http://www.w3.org/2005/Atom">
            <id>tag:nitter.net:status999</id>
            <published>2024-01-15T10:30:00Z</published>
        </entry>"""
        root = ET.fromstring(xml)
        tweet = c._parse_entry(root)
        assert tweet is None


class TestTwitterCollectorSignals:
    def test_funding_signal(self):
        c = TwitterCollector(config={})
        signals = c._find_signals("We just raised Series A funding for our startup")
        categories = {s["category"] for s in signals}
        assert "funding" in categories

    def test_multiple_signals(self):
        c = TwitterCollector(config={})
        signals = c._find_signals("Launching our new product, we are hiring engineers")
        categories = {s["category"] for s in signals}
        assert "launch" in categories
        assert "hiring" in categories

    def test_no_signals(self):
        c = TwitterCollector(config={})
        signals = c._find_signals("Just had coffee this morning")
        assert len(signals) == 0

    def test_no_duplicates(self):
        c = TwitterCollector(config={})
        signals = c._find_signals("funding funding funding")
        assert len(signals) == 1


class TestTwitterCollectorHashtags:
    def test_relevant_hashtags(self):
        c = TwitterCollector(config={})
        tags = c._find_hashtags("Check out our #startup #ai product")
        assert "#startup" in tags
        assert "#ai" in tags

    def test_irrelevant_hashtags(self):
        c = TwitterCollector(config={})
        tags = c._find_hashtags("Love #cats and #dogs")
        assert len(tags) == 0


class TestTwitterCollectorEntity:
    def test_mention_entity(self):
        c = TwitterCollector(config={})
        entity = c._find_entity("@TechCorp just launched their AI platform")
        assert entity == "@TechCorp"

    def test_quoted_entity(self):
        c = TwitterCollector(config={})
        entity = c._find_entity('Today "Tech Corp" announced their seed round')
        assert entity == "Tech Corp"

    def test_no_entity(self):
        c = TwitterCollector(config={})
        entity = c._find_entity("just some random text")
        assert entity == ""


class TestTwitterCollectorFetch:
    def test_fetch_feed_success(self):
        c = TwitterCollector(config={"twitter": {}})
        entry = _make_tweet_entry()
        xml = _make_feed_response([entry])
        session = _make_mock_session([xml])
        tweets = c._fetch_feed(session, "https://nitter.net", "startup")
        assert len(tweets) == 1
        assert tweets[0]["author"] == "@techfounder"

    def test_fetch_empty_feed(self):
        c = TwitterCollector(config={"twitter": {}})
        xml = _make_feed_response([])
        session = _make_mock_session([xml])
        tweets = c._fetch_feed(session, "https://nitter.net", "startup")
        assert len(tweets) == 0

    def test_fetch_api_failure(self):
        c = TwitterCollector(config={"twitter": {}})
        session = MagicMock()
        session.get.side_effect = Exception("Connection refused")
        tweets = c._fetch_feed(session, "https://nitter.net", "startup")
        assert len(tweets) == 0

    def test_fetch_invalid_xml(self):
        c = TwitterCollector(config={"twitter": {}})
        session = _make_mock_session(["<not valid xml"])
        tweets = c._fetch_feed(session, "https://nitter.net", "startup")
        assert len(tweets) == 0


class TestTwitterCollectorInsert:
    def test_insert_single_tweet(self):
        c = TwitterCollector(config={"twitter": {}})
        mock_cursor = MagicMock()
        result = CollectionResult(collector_name="twitter")

        tweet = _make_tweet_dict()
        c._insert_tweet(mock_cursor, tweet, "startup", [], [], 50, result)
        assert result.records_collected == 1
        # 2 SQL calls: social_posts + raw_signals
        assert mock_cursor.execute.call_count == 2

    def test_insert_multiple_tweets(self):
        c = TwitterCollector(config={"twitter": {}})
        mock_cursor = MagicMock()
        result = CollectionResult(collector_name="twitter")

        for i in range(5):
            t = _make_tweet_dict(author=f"@user{i}", url=f"https://nitter.net/user/status/{i}")
            c._insert_tweet(mock_cursor, t, "test", [], [], 0, result)
        assert result.records_collected == 5


class TestTwitterCollectorIntegration:
    @patch("collectors.twitter_collector.time")
    @patch("collectors.twitter_collector.get_http_session")
    def test_collect_full_flow(self, mock_get_session, mock_time):
        entry = _make_tweet_entry(text="We raised Series A #startup")
        xml = _make_feed_response([entry])
        session = _make_mock_session([xml])
        mock_get_session.return_value = session

        c = TwitterCollector(config={
            "twitter": {
                "nitter_instances": ["https://nitter.net"],
                "search_queries": ["startup funding"],
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

    @patch("collectors.twitter_collector.get_http_session")
    def test_collect_empty_feed(self, mock_get_session):
        xml = _make_feed_response([])
        session = _make_mock_session([xml])
        mock_get_session.return_value = session

        c = TwitterCollector(config={
            "twitter": {
                "nitter_instances": ["https://nitter.net"],
                "search_queries": ["nonexistent"],
                "min_delay_seconds": 0,
            },
        })

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        result = c.collect(mock_conn)
        assert result.status == "partial"
        assert result.records_collected == 0

    @patch("collectors.twitter_collector.get_http_session")
    def test_collect_multiple_instances(self, mock_get_session):
        entry1 = _make_tweet_entry(author="@user1", text="Tweet one")
        entry2 = _make_tweet_entry(author="@user2", text="Tweet two")
        session = _make_mock_session([
            _make_feed_response([entry1]),
            _make_feed_response([entry2]),
        ])
        mock_get_session.return_value = session

        c = TwitterCollector(config={
            "twitter": {
                "nitter_instances": ["https://nitter.net", "https://nitter.privacydev.net"],
                "search_queries": ["startup"],
                "min_delay_seconds": 0,
            },
        })

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        result = c.collect(mock_conn)
        assert result.records_collected == 2

    @patch("collectors.twitter_collector.get_http_session")
    def test_collect_handles_insert_error(self, mock_get_session):
        entry = _make_tweet_entry()
        session = _make_mock_session([_make_feed_response([entry])])
        mock_get_session.return_value = session

        c = TwitterCollector(config={
            "twitter": {
                "nitter_instances": ["https://nitter.net"],
                "search_queries": ["test"],
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
