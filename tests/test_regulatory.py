"""Tests for the Regulatory Collector."""

import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock

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

from collectors.regulatory_collector import RegulatoryCollector
from collectors.base import CollectionResult


def _make_atom_entry(filing_id="0000320193-24-0001",
                     filing_type="S-1",
                     company_name="TechCorp AI Inc.",
                     summary="Registration statement under the Securities Act of 1933",
                     filed_date=None,
                     link="https://www.sec.gov/Archives/edgar/data/320193/0000320193240001/"):
    """Build a mock SEC EDGAR Atom XML entry element."""
    import xml.etree.ElementTree as ET

    # Namespaces
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "sec": "http://www.sec.gov/Archives/edgar",
    }

    entry = ET.Element(f"{{{ns['atom']}}}entry")

    # ID
    eid = ET.SubElement(entry, f"{{{ns['atom']}}}id")
    eid.text = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={filing_id.split('-')[0]}&type={filing_type}"

    # Title
    title_elem = ET.SubElement(entry, f"{{{ns['atom']}}}title")
    title_elem.text = f"{filing_type} - {company_name}"

    # Summary
    summary_elem = ET.SubElement(entry, f"{{{ns['atom']}}}summary")
    summary_elem.text = f"{company_name} (CIK: {filing_id.split('-')[0]})\n{summary}"

    # Updated (filed date)
    updated_elem = ET.SubElement(entry, f"{{{ns['atom']}}}updated")
    if filed_date:
        if isinstance(filed_date, datetime):
            updated_elem.text = filed_date.isoformat()
        else:
            updated_elem.text = filed_date
    else:
        # Default to old date
        old_date = datetime.now(timezone.utc) - timedelta(days=120)
        updated_elem.text = old_date.isoformat()

    # Link
    link_elem = ET.SubElement(entry, f"{{{ns['atom']}}}link")
    link_elem.set("rel", "alternate")
    link_elem.set("href", link)

    return entry


def _make_filing_dict(filing_id="0000320193-24-0001",
                      filing_type="S-1",
                      company_name="TechCorp AI Inc.",
                      summary="Registration statement",
                      filed_date=None,
                      link="https://www.sec.gov/Archives/edgar/data/320193/"):
    """Build a parsed filing dict matching _parse_entry output."""
    if filed_date is None:
        # Default to old date (NOT recent)
        filed_date = datetime.now(timezone.utc) - timedelta(days=120)
    return {
        "filing_id": filing_id,
        "filing_type": filing_type,
        "company_name": company_name,
        "summary": summary,
        "filed_date": filed_date,
        "link": link,
    }


def _make_mock_session(responses=None):
    """Build a mock requests.Session returning XML bytes in order."""
    session = MagicMock()
    session.headers = {}
    rl = list(responses or [])

    def mock_get(url, params=None, timeout=None, headers=None):
        resp = MagicMock()
        resp.status_code = 200
        if rl:
            data = rl.pop(0)
            resp.content = data.encode("utf-8") if isinstance(data, str) else data
        else:
            resp.content = b""
        return resp

    session.get = mock_get
    return session


def _make_feed_xml(entries=None):
    """Build a mock SEC EDGAR RSS feed XML string."""
    import xml.etree.ElementTree as ET

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "sec": "http://www.sec.gov/Archives/edgar",
    }

    root = ET.Element(f"{{{ns['atom']}}}feed")
    root.set("xmlns", ns["atom"])

    # Add entries
    for entry in (entries or []):
        root.append(entry)

    return ET.tostring(root, encoding="unicode")


class TestRegulatoryCollectorName:
    def test_name(self):
        c = RegulatoryCollector(config={})
        assert c.name == "regulatory"


class TestRegulatoryCollectorConfig:
    def test_dry_run_mode(self):
        c = RegulatoryCollector(config={}, dry_run=True)
        mock_conn = MagicMock()
        result = c.collect(mock_conn)
        assert result.status == "success"
        assert result.records_collected == 0


class TestRegulatoryCollectorScoring:
    def test_s1_recent(self):
        c = RegulatoryCollector(config={})
        filing = _make_filing_dict(
            filing_type="S-1",
            filed_date=datetime.now(timezone.utc) - timedelta(days=3)
        )
        score = c._compute_score(filing)
        # S-1 (+30) + recent <7d (+20) = 50
        assert score == 50.0

    def test_8k_medium_recency(self):
        c = RegulatoryCollector(config={})
        filing = _make_filing_dict(
            filing_type="8-K",
            filed_date=datetime.now(timezone.utc) - timedelta(days=15)
        )
        score = c._compute_score(filing)
        # 8-K (+20) + recent <30d (+10) = 30
        assert score == 30.0

    def test_sc13d_old(self):
        c = RegulatoryCollector(config={})
        filing = _make_filing_dict(
            filing_type="SC 13D",
            filed_date=datetime.now(timezone.utc) - timedelta(days=120)
        )
        score = c._compute_score(filing)
        # SC 13D (+25) = 25
        assert score == 25.0

    def test_old_no_type(self):
        c = RegulatoryCollector(config={})
        filing = _make_filing_dict(
            filing_type="",
            filed_date=datetime.now(timezone.utc) - timedelta(days=120)
        )
        score = c._compute_score(filing)
        assert score == 0.0

    def test_capped_at_100(self):
        c = RegulatoryCollector(config={})
        # Create a filing with max possible score
        filing = _make_filing_dict(
            filing_type="S-1",
            filed_date=datetime.now(timezone.utc) - timedelta(days=1)
        )
        score = c._compute_score(filing)
        # S-1 (+30) + recent <7d (+20) = 50 (not over 100)
        assert score <= 100.0


class TestRegulatoryCollectorParse:
    def test_parse_valid_entry(self):
        c = RegulatoryCollector(config={})
        entry = _make_atom_entry()
        filing = c._parse_entry(entry)
        assert filing is not None
        assert filing["filing_type"] == "S-1"
        assert "TechCorp AI" in filing["company_name"]
        assert "Registration statement" in filing["summary"]

    def test_parse_no_filing_type(self):
        c = RegulatoryCollector(config={})
        entry = _make_atom_entry(filing_type="")
        filing = c._parse_entry(entry)
        assert filing is not None
        assert filing["filing_type"] == ""

    def test_parse_whitespace_collapsed(self):
        c = RegulatoryCollector(config={})
        entry = _make_atom_entry(summary="   Multiple   spaces   in   text   ")
        filing = c._parse_entry(entry)
        assert filing is not None
        assert "Multiple" in filing["summary"]
        # Check spaces are collapsed
        assert "  " not in filing["summary"]


class TestRegulatoryCollectorFetch:
    def test_fetch_success(self):
        c = RegulatoryCollector(config={"regulatory": {"user_agent": "TestBot"}})
        entry = _make_atom_entry()
        feed_xml = _make_feed_xml([entry])
        session = _make_mock_session([feed_xml])
        filings = c._fetch_filings(session, "http://example.com")
        assert len(filings) == 1
        assert filings[0]["filing_type"] == "S-1"

    def test_fetch_empty_feed(self):
        c = RegulatoryCollector(config={"regulatory": {}})
        feed_xml = _make_feed_xml([])
        session = _make_mock_session([feed_xml])
        filings = c._fetch_filings(session, "http://example.com")
        assert len(filings) == 0

    def test_fetch_api_failure(self):
        c = RegulatoryCollector(config={"regulatory": {}})
        session = MagicMock()
        session.get.side_effect = Exception("Connection refused")
        filings = c._fetch_filings(session, "http://example.com")
        assert len(filings) == 0

    def test_fetch_invalid_xml(self):
        c = RegulatoryCollector(config={"regulatory": {}})
        session = _make_mock_session(["{not valid xml}"])
        filings = c._fetch_filings(session, "http://example.com")
        assert len(filings) == 0


class TestRegulatoryCollectorInsert:
    def test_insert_single_filing(self):
        c = RegulatoryCollector(config={"regulatory": {}})
        mock_cursor = MagicMock()
        result = CollectionResult(collector_name="regulatory")

        filing = _make_filing_dict()
        c._insert_filing(mock_cursor, filing, result)
        assert result.records_collected == 1
        # 2 SQL calls: regulatory_filings + raw_signals
        assert mock_cursor.execute.call_count == 2

    def test_insert_multiple_filings(self):
        c = RegulatoryCollector(config={"regulatory": {}})
        mock_cursor = MagicMock()
        result = CollectionResult(collector_name="regulatory")

        for i in range(5):
            filing = _make_filing_dict(filing_id=f"0000320193-24-{i:04d}")
            c._insert_filing(mock_cursor, filing, result)
        assert result.records_collected == 5


class TestRegulatoryCollectorIntegration:
    def test_collect_full_flow(self):
        from unittest.mock import patch

        entry = _make_atom_entry(filing_type="8-K", company_name="TestCorp")
        feed_xml = _make_feed_xml([entry])
        session = _make_mock_session([feed_xml])

        with patch("collectors.regulatory_collector.get_http_session", return_value=session):
            c = RegulatoryCollector(config={
                "regulatory": {
                    "search_companies": [],
                    "filing_types": ["8-K"],
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

    def test_collect_empty_results(self):
        from unittest.mock import patch

        feed_xml = _make_feed_xml([])
        session = _make_mock_session([feed_xml])

        with patch("collectors.regulatory_collector.get_http_session", return_value=session):
            c = RegulatoryCollector(config={
                "regulatory": {
                    "search_companies": [],
                    "filing_types": ["S-1"],
                    "min_delay_seconds": 0,
                },
            })

            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor

            result = c.collect(mock_conn)
            assert result.status == "partial"
            assert result.records_collected == 0

    def test_collect_multiple_companies(self):
        from unittest.mock import patch

        entry1 = _make_atom_entry(filing_id="00001", company_name="Company1")
        entry2 = _make_atom_entry(filing_id="00002", company_name="Company2")
        session = _make_mock_session([
            _make_feed_xml([]),  # General feed empty
            _make_feed_xml([entry1]),  # Company1
            _make_feed_xml([entry2]),  # Company2
        ])

        with patch("collectors.regulatory_collector.get_http_session", return_value=session):
            c = RegulatoryCollector(config={
                "regulatory": {
                    "search_companies": ["Company1", "Company2"],
                    "filing_types": ["S-1"],
                    "min_delay_seconds": 0,
                },
            })

            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor

            result = c.collect(mock_conn)
            assert result.records_collected == 2

    def test_collect_handles_insert_error(self):
        from unittest.mock import patch

        entry = _make_atom_entry()
        feed_xml = _make_feed_xml([entry])
        session = _make_mock_session([feed_xml])

        with patch("collectors.regulatory_collector.get_http_session", return_value=session):
            c = RegulatoryCollector(config={
                "regulatory": {
                    "search_companies": [],
                    "filing_types": ["S-1"],
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
