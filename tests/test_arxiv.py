"""Tests for the arXiv Collector."""

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

from collectors.arxiv_collector import ArxivCollector  # noqa: E402
from collectors.base import CollectionResult  # noqa: E402

# Restore real db modules so other tests aren't poisoned
for key, orig in _saved_db_modules.items():
    if orig is not None:
        sys.modules[key] = orig
    else:
        sys.modules.pop(key, None)


def _make_atom_response(entries=None):
    """Build a valid arXiv Atom XML response with given entries."""
    entries_xml = ""
    for e in entries or []:
        authors_xml = ""
        for a in e.get("authors", []):
            authors_xml += f"<author><name>{a}</name></author>"

        cats_xml = ""
        for c in e.get("categories", []):
            cats_xml += f'<category term="{c}" />'

        primary_cat = e.get("primary_category", "")
        primary_xml = (
            f'<arxiv:primary_category term="{primary_cat}" scheme="http://arxiv.org/schemas/atom" />'
            if primary_cat
            else ""
        )

        doi_xml = f"<arxiv:doi>{e.get('doi', '')}</arxiv:doi>" if e.get("doi") else ""

        published = e.get("published", "2024-01-15T00:00:00Z")
        updated = e.get("updated", "2024-01-16T00:00:00Z")

        entry_xml = f"""<entry>
            <id>http://arxiv.org/abs/{e.get('arxiv_id', '0000.00000')}</id>
            <updated>{updated}</updated>
            <published>{published}</published>
            <title>{e.get('title', '')}</title>
            <summary>{e.get('abstract', '')}</summary>
            {authors_xml}
            {primary_xml}
            {cats_xml}
            <link href="http://arxiv.org/abs/{e.get('arxiv_id', '0000.00000')}" rel="alternate" type="text/html" />
            <link title="pdf" href="http://arxiv.org/pdf/{e.get('arxiv_id', '0000.00000')}" rel="related" type="application/pdf" />
            {doi_xml}
        </entry>"""
        entries_xml += entry_xml

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:arxiv="http://arxiv.org/schemas/atom">
    <title>arXiv Search</title>
    <link href="http://arxiv.org" rel="alternate" />
    <id>http://arxiv.org</id>
    {entries_xml}
</feed>"""


def _make_paper(
    arxiv_id="2401.12345",
    title="Attention Is All You Need",
    authors=None,
    abstract="We propose a new network architecture",
    primary_category="cs.CL",
    categories=None,
    published_date=None,
    doi=None,
):
    """Build a paper dict matching _parse_entry output."""
    now = datetime.now(timezone.utc)
    default_date = (now - timedelta(days=3)).strftime("%Y-%m-%d")
    return {
        "arxiv_id": arxiv_id,
        "title": title,
        "authors": authors or ["Alice Smith", "Bob Jones", "Carol Lee"],
        "abstract": abstract,
        "primary_category": primary_category,
        "categories": categories or [primary_category, "cs.AI"],
        "published_date": published_date
        if published_date is not None
        else default_date,
        "updated_date": published_date
        if published_date is not None
        else now.strftime("%Y-%m-%d"),
        "pdf_url": f"http://arxiv.org/pdf/{arxiv_id}",
        "source_url": f"http://arxiv.org/abs/{arxiv_id}",
        "doi": doi or "",
    }


def _make_mock_session(responses=None):
    """Build a mock requests.Session returning XML strings in order."""
    session = MagicMock()
    session.headers = {}
    response_iter = iter(responses or [])

    def mock_get(url, params=None, timeout=None):
        resp = MagicMock()
        resp.status_code = 200
        try:
            resp.content = (
                next(response_iter).encode("utf-8")
                if isinstance(
                    next(iter([next(response_iter)] if False else []), None), bytes
                )
                else next(response_iter).encode("utf-8")
            )
        except StopIteration:
            resp.content = b""
        return resp

    # Simpler approach
    response_list = list(responses or [])

    def mock_get_v2(url, params=None, timeout=None):
        resp = MagicMock()
        resp.status_code = 200
        nonlocal response_list
        if response_list:
            data = response_list.pop(0)
            resp.content = data.encode("utf-8") if isinstance(data, str) else data
        else:
            resp.content = b""
        return resp

    session.get = mock_get_v2
    return session


class TestArxivCollectorName:
    def test_name(self):
        c = ArxivCollector(config={})
        assert c.name == "arxiv"


class TestArxivCollectorConfig:
    def test_dry_run_mode(self):
        c = ArxivCollector(config={}, dry_run=True)
        mock_conn = MagicMock()
        result = c.collect(mock_conn)
        assert result.status == "success"
        assert result.records_collected == 0


class TestArxivCollectorBuildQuery:
    def test_terms_only(self):
        c = ArxivCollector(config={})
        q = c._build_query("machine learning")
        assert "all:machine learning" in q
        assert "cat:" not in q

    def test_terms_with_categories(self):
        c = ArxivCollector(config={})
        q = c._build_query("transformer", ["cs.CL", "cs.AI"])
        assert "all:transformer" in q
        assert "cat:cs.CL" in q
        assert "cat:cs.AI" in q

    def test_single_category(self):
        c = ArxivCollector(config={})
        q = c._build_query("reinforcement learning", ["cs.LG"])
        assert "all:reinforcement learning" in q
        assert "cat:cs.LG" in q


class TestArxivCollectorScoring:
    def test_very_recent_relevant_paper(self):
        c = ArxivCollector(config={})
        paper = _make_paper(
            published_date=(datetime.now(timezone.utc) - timedelta(days=2)).strftime(
                "%Y-%m-%d"
            ),
            primary_category="cs.AI",
            authors=["A", "B", "C"],
        )
        score = c._compute_score(paper)
        # <7 days(+40) + 3 authors(+20) + cs.AI(+20) = 80
        assert score >= 80

    def test_old_irrelevant_paper(self):
        c = ArxivCollector(config={})
        paper = _make_paper(
            published_date=(datetime.now(timezone.utc) - timedelta(days=180)).strftime(
                "%Y-%m-%d"
            ),
            primary_category="physics.fluid-dyn",
            authors=["Single Author"],
        )
        score = c._compute_score(paper)
        assert score == 0  # Old + irrelevant + solo author

    def test_medium_recency(self):
        c = ArxivCollector(config={})
        paper = _make_paper(
            published_date=(datetime.now(timezone.utc) - timedelta(days=20)).strftime(
                "%Y-%m-%d"
            ),
            primary_category="cs.LG",
            authors=["A", "B"],
        )
        score = c._compute_score(paper)
        # <30 days(+25) + 2 authors(no bonus) + cs.LG(+20) = 45
        assert score == 45

    def test_capped_at_100(self):
        c = ArxivCollector(config={})
        paper = _make_paper(
            published_date=(datetime.now(timezone.utc) - timedelta(days=1)).strftime(
                "%Y-%m-%d"
            ),
            primary_category="cs.AI",
            authors=["A", "B", "C", "D"],
        )
        score = c._compute_score(paper)
        assert score <= 100.0

    def test_no_date(self):
        c = ArxivCollector(config={})
        paper = _make_paper(
            published_date=None, primary_category="cs.CL", authors=["A", "B", "C"]
        )
        # Override to actually set None
        paper["published_date"] = None
        score = c._compute_score(paper)
        # No date bonus: 0 + 20 (authors) + 20 (category) = 40
        assert score == 40


class TestArxivCollectorParseEntry:
    def test_parse_valid_entry(self):
        c = ArxivCollector(config={})
        xml = _make_atom_response([_make_paper()])
        root = ET.fromstring(xml)
        entry = root.findall("{http://www.w3.org/2005/Atom}entry")[0]
        paper = c._parse_entry(entry)
        assert paper is not None
        assert paper["arxiv_id"] == "2401.12345"
        assert "Attention" in paper["title"]
        assert len(paper["authors"]) == 3

    def test_parse_no_arxiv_id(self):
        c = ArxivCollector(config={})
        xml = """<?xml version="1.0"?>
        <entry xmlns="http://www.w3.org/2005/Atom">
            <id>http://example.com/invalid</id>
            <title>Test</title>
        </entry>"""
        root = ET.fromstring(xml)
        paper = c._parse_entry(root)
        assert paper is None

    def test_parse_whitespace_collapsed(self):
        c = ArxivCollector(config={})
        paper_data = _make_paper(title="  Multi-line   title   with   extra   spaces  ")
        xml = _make_atom_response([paper_data])
        root = ET.fromstring(xml)
        entry = root.findall("{http://www.w3.org/2005/Atom}entry")[0]
        paper = c._parse_entry(entry)
        assert paper is not None
        assert "  " not in paper["title"]


class TestArxivCollectorFetch:
    def test_fetch_papers_success(self):
        c = ArxivCollector(config={"arxiv": {}})
        paper = _make_paper()
        xml = _make_atom_response([paper])
        session = _make_mock_session([xml])
        papers = c._fetch_papers(session, "http://example.com", "test")
        assert len(papers) == 1
        assert papers[0]["arxiv_id"] == "2401.12345"

    def test_fetch_empty_feed(self):
        c = ArxivCollector(config={"arxiv": {}})
        xml = _make_atom_response([])
        session = _make_mock_session([xml])
        papers = c._fetch_papers(session, "http://example.com", "test")
        assert len(papers) == 0

    def test_fetch_api_failure(self):
        c = ArxivCollector(config={"arxiv": {}})
        session = MagicMock()
        session.get.side_effect = Exception("Connection refused")
        papers = c._fetch_papers(session, "http://example.com", "test")
        assert len(papers) == 0

    def test_fetch_invalid_xml(self):
        c = ArxivCollector(config={"arxiv": {}})
        session = _make_mock_session(["<not valid xml"])
        papers = c._fetch_papers(session, "http://example.com", "test")
        assert len(papers) == 0


class TestArxivCollectorInsert:
    def test_insert_single_paper(self):
        c = ArxivCollector(config={"arxiv": {}})
        mock_cursor = MagicMock()
        result = CollectionResult(collector_name="arxiv")

        paper = _make_paper()
        c._insert_paper(mock_cursor, paper, "machine learning", result)
        assert result.records_collected == 1
        # 2 SQL calls: arxiv_papers + raw_signals
        assert mock_cursor.execute.call_count == 2

    def test_insert_multiple_papers(self):
        c = ArxivCollector(config={"arxiv": {}})
        mock_cursor = MagicMock()
        result = CollectionResult(collector_name="arxiv")

        for i in range(5):
            c._insert_paper(
                mock_cursor, _make_paper(arxiv_id=f"2401.{10000+i}"), "test", result
            )
        assert result.records_collected == 5

    def test_insert_paper_no_authors(self):
        c = ArxivCollector(config={"arxiv": {}})
        mock_cursor = MagicMock()
        result = CollectionResult(collector_name="arxiv")

        paper = _make_paper(authors=[])
        c._insert_paper(mock_cursor, paper, "test", result)
        assert result.records_collected == 1

    def test_insert_paper_error(self):
        import pytest

        c = ArxivCollector(config={"arxiv": {}})
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("DB error")
        result = CollectionResult(collector_name="arxiv")

        paper = _make_paper()
        with pytest.raises(Exception, match="DB error"):
            c._insert_paper(mock_cursor, paper, "test", result)
        assert result.records_collected == 0


class TestArxivCollectorIntegration:
    @patch("collectors.arxiv_collector.get_http_session")
    @patch("collectors.arxiv_collector.time")
    def test_collect_full_flow(self, mock_time, mock_get_session):
        paper = _make_paper()
        xml = _make_atom_response([paper])
        session = _make_mock_session([xml])
        mock_get_session.return_value = session

        c = ArxivCollector(
            config={
                "arxiv": {
                    "search_queries": [
                        {"terms": "machine learning", "categories": ["cs.AI"]}
                    ],
                    "max_results_per_query": 10,
                    "min_delay_seconds": 0,
                },
            }
        )

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        result = c.collect(mock_conn)
        assert result.status == "success"
        assert result.records_collected == 1
        mock_time.sleep.assert_called()
        mock_conn.commit.assert_called()

    @patch("collectors.arxiv_collector.get_http_session")
    def test_collect_no_results(self, mock_get_session):
        xml = _make_atom_response([])
        session = _make_mock_session([xml])
        mock_get_session.return_value = session

        c = ArxivCollector(
            config={
                "arxiv": {
                    "search_queries": [{"terms": "nonexistent", "categories": []}],
                    "min_delay_seconds": 0,
                },
            }
        )

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        result = c.collect(mock_conn)
        assert result.status == "partial"
        assert result.records_collected == 0

    @patch("collectors.arxiv_collector.get_http_session")
    def test_collect_multiple_queries(self, mock_get_session):
        p1 = _make_paper(arxiv_id="2401.11111", title="Paper One")
        p2 = _make_paper(arxiv_id="2402.22222", title="Paper Two")
        xml1 = _make_atom_response([p1])
        xml2 = _make_atom_response([p2])

        session = _make_mock_session([xml1, xml2])
        mock_get_session.return_value = session

        c = ArxivCollector(
            config={
                "arxiv": {
                    "search_queries": [
                        {"terms": "query one", "categories": ["cs.AI"]},
                        {"terms": "query two", "categories": ["cs.CL"]},
                    ],
                    "min_delay_seconds": 0,
                },
            }
        )

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        result = c.collect(mock_conn)
        assert result.status == "success"
        assert result.records_collected == 2

    @patch("collectors.arxiv_collector.get_http_session")
    def test_collect_handles_individual_error(self, mock_get_session):
        paper = _make_paper()
        xml = _make_atom_response([paper])
        session = _make_mock_session([xml])
        mock_get_session.return_value = session

        c = ArxivCollector(
            config={
                "arxiv": {
                    "search_queries": [{"terms": "test", "categories": []}],
                    "min_delay_seconds": 0,
                },
            }
        )

        call_count = {"n": 0}

        def execute_side_effect(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise Exception("DB error")

        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = execute_side_effect

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        result = c.collect(mock_conn)
        # Error captured but collection continues
        assert len(result.errors) > 0
