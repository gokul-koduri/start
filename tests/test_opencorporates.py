"""Tests for the OpenCorporates Collector."""

import sys
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

from collectors.opencorporates_collector import OpenCorporatesCollector  # noqa: E402
from collectors.base import CollectionResult  # noqa: E402

# Restore real db modules so other tests aren't poisoned
for key, orig in _saved_db_modules.items():
    if orig is not None:
        sys.modules[key] = orig
    else:
        sys.modules.pop(key, None)


def _make_oc_company(
    name="AI Corp",
    company_number="12345678",
    jurisdiction="us",
    inc_date="2023-06-15",
    status="Active",
    company_type="LLC",
    address="123 Silicon Valley, CA",
    officers=None,
    filings=None,
):
    """Build a mock OpenCorporates API company response."""
    return {
        "company": {
            "name": name,
            "company_number": company_number,
            "jurisdiction_code": jurisdiction,
            "incorporation_date": inc_date,
            "dissolution_date": None,
            "company_type": company_type,
            "current_status": status,
            "registered_address_in_full": address,
            "registry_url": f"https://opencorporates.com/companies/{jurisdiction}/{company_number}",
            "officers": officers
            or [
                {
                    "name": "John Doe",
                    "position": "Director",
                    "start_date": "2023-06-15",
                },
                {"name": "Jane Smith", "position": "CTO", "start_date": "2023-06-15"},
            ],
            "filings": filings or [],
        },
    }


def _make_search_response(companies=None):
    """Build a mock OpenCorporates search API response."""
    return {
        "results": {
            "companies": companies or [],
            "total_count": len(companies or []),
            "per_page": 30,
        },
    }


def _make_mock_session(responses=None):
    """Build a mock requests.Session returning JSON responses in order."""
    session = MagicMock()
    session.headers = {}
    response_iter = iter(responses or [])

    def mock_get(url, params=None, timeout=None):
        resp = MagicMock()
        resp.status_code = 200
        try:
            resp.json.return_value = next(response_iter)
        except StopIteration:
            resp.json.return_value = {}
        return resp

    session.get = mock_get
    return session


class TestOpenCorporatesCollectorName:
    def test_name(self):
        c = OpenCorporatesCollector(config={"opencorporates": {"api_token": "test"}})
        assert c.name == "opencorporates"


class TestOpenCorporatesCollectorConfig:
    def test_dry_run_mode(self):
        c = OpenCorporatesCollector(config={}, dry_run=True)
        mock_conn = MagicMock()
        result = c.collect(mock_conn)
        assert result.status == "success"
        assert result.records_collected == 0

    def test_no_api_token(self):
        c = OpenCorporatesCollector(config={"opencorporates": {}})
        mock_conn = MagicMock()
        result = c.collect(mock_conn)
        assert result.status == "failed"
        assert any("API token" in e for e in result.errors)


class TestOpenCorporatesCollectorScoring:
    def test_active_recent_company(self):
        c = OpenCorporatesCollector(config={})
        # Use a date < 2 years ago: Active(+40) + <2yr(+30) + Officers(+15) = 85
        recent_date = (datetime.now(timezone.utc) - timedelta(days=365)).strftime(
            "%Y-%m-%d"
        )
        company = _make_oc_company(status="Active", inc_date=recent_date)
        score = c._compute_score(company)
        assert score >= 80

    def test_dissolved_company(self):
        c = OpenCorporatesCollector(config={})
        company = _make_oc_company(
            status="Dissolved", inc_date="2020-01-01", officers=[], filings=[]
        )
        score = c._compute_score(company)
        assert score < 30

    def test_old_active_company(self):
        c = OpenCorporatesCollector(config={})
        company = _make_oc_company(
            status="Active", inc_date="2005-01-01", officers=[], filings=[]
        )
        score = c._compute_score(company)
        # Active but old, no officers/filings
        assert 40 <= score < 60

    def test_no_incorporation_date(self):
        c = OpenCorporatesCollector(config={})
        company = _make_oc_company(inc_date=None, status="Active")
        score = c._compute_score(company)
        assert score == 55  # Active + officers, no date bonus

    def test_capped_at_100(self):
        c = OpenCorporatesCollector(config={})
        company = _make_oc_company(
            status="Active",
            inc_date="2024-01-01",
            officers=[{"name": "X", "position": "Y"}],
            filings=[{"id": "f1"}],
        )
        score = c._compute_score(company)
        assert score <= 100.0


class TestOpenCorporatesCollectorFetch:
    def test_fetch_search(self):
        c = OpenCorporatesCollector(config={"opencorporates": {"api_token": "test"}})
        resp = _make_search_response([_make_oc_company()])
        mock_session = _make_mock_session([resp])
        data = c._fetch_search(
            mock_session, "https://api.example.com", "test", "AI startup", ["us"]
        )
        assert data is not None
        assert len(data["results"]["companies"]) == 1

    def test_fetch_search_empty(self):
        c = OpenCorporatesCollector(config={"opencorporates": {"api_token": "test"}})
        resp = _make_search_response([])
        mock_session = _make_mock_session([resp])
        data = c._fetch_search(
            mock_session, "https://api.example.com", "test", "AI startup"
        )
        assert len(data["results"]["companies"]) == 0

    def test_fetch_search_api_failure(self):
        c = OpenCorporatesCollector(config={"opencorporates": {"api_token": "test"}})
        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("Network error")
        data = c._fetch_search(
            mock_session, "https://api.example.com", "test", "AI startup"
        )
        assert data is None

    def test_fetch_company(self):
        c = OpenCorporatesCollector(config={"opencorporates": {"api_token": "test"}})
        company = _make_oc_company()
        mock_session = _make_mock_session([company])
        data = c._fetch_company(
            mock_session, "https://api.example.com", "test", "us", "12345678"
        )
        assert data is not None
        assert data["company"]["name"] == "AI Corp"


class TestOpenCorporatesCollectorInsert:
    def test_insert_single_company(self):
        c = OpenCorporatesCollector(config={"opencorporates": {"api_token": "test"}})
        mock_cursor = MagicMock()
        result = CollectionResult(collector_name="opencorporates")

        company = _make_oc_company()
        c._insert_company(mock_cursor, company, "AI startup", result)
        assert result.records_collected == 1
        # 2 SQL calls: company_profiles + raw_signals
        assert mock_cursor.execute.call_count == 2

    def test_insert_multiple_companies(self):
        c = OpenCorporatesCollector(config={"opencorporates": {"api_token": "test"}})
        mock_cursor = MagicMock()
        result = CollectionResult(collector_name="opencorporates")

        for i in range(5):
            c._insert_company(
                mock_cursor, _make_oc_company(name=f"Company {i}"), "test", result
            )
        assert result.records_collected == 5

    def test_insert_company_no_officers(self):
        c = OpenCorporatesCollector(config={"opencorporates": {"api_token": "test"}})
        mock_cursor = MagicMock()
        result = CollectionResult(collector_name="opencorporates")

        company = _make_oc_company(officers=[])
        c._insert_company(mock_cursor, company, "test", result)
        assert result.records_collected == 1

    def test_extract_officers(self):
        c = OpenCorporatesCollector(config={})
        company = _make_oc_company(
            officers=[
                {"name": "Alice", "position": "CEO"},
                {"name": "Bob", "position": "CTO"},
            ]
        )
        officers = c._extract_officers(company["company"])
        assert len(officers) == 2
        assert officers[0]["name"] == "Alice"

    def test_extract_officers_capped(self):
        c = OpenCorporatesCollector(config={})
        officers = [
            {"name": f"Officer {i}", "position": f"Role {i}"} for i in range(15)
        ]
        company = _make_oc_company(officers=officers)
        extracted = c._extract_officers(company["company"])
        assert len(extracted) == 10  # Cap at 10


class TestOpenCorporatesCollectorIntegration:
    @patch("collectors.opencorporates_collector.time")
    @patch("collectors.opencorporates_collector.get_http_session")
    def test_collect_full_flow(self, mock_get_session, mock_time):
        company = _make_oc_company()
        resp = _make_search_response([company])

        mock_session = _make_mock_session([resp])
        mock_get_session.return_value = mock_session

        c = OpenCorporatesCollector(
            config={
                "opencorporates": {
                    "api_token": "test",
                    "search_queries": [
                        {"query": "AI startup", "jurisdictions": ["us"]}
                    ],
                    "per_page": 30,
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
        mock_time.sleep.assert_called()  # Rate limit delay
        mock_conn.commit.assert_called()

    @patch("collectors.opencorporates_collector.get_http_session")
    def test_collect_no_results(self, mock_get_session):
        resp = _make_search_response([])
        mock_session = _make_mock_session([resp])
        mock_get_session.return_value = mock_session

        c = OpenCorporatesCollector(
            config={
                "opencorporates": {
                    "api_token": "test",
                    "search_queries": [{"query": "nonexistent", "jurisdictions": []}],
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

    @patch("collectors.opencorporates_collector.get_http_session")
    def test_collect_multiple_queries(self, mock_get_session):
        c1 = _make_oc_company(name="Company A")
        c2 = _make_oc_company(name="Company B")
        resp1 = _make_search_response([c1])
        resp2 = _make_search_response([c2])

        mock_session = _make_mock_session([resp1, resp2])
        mock_get_session.return_value = mock_session

        c = OpenCorporatesCollector(
            config={
                "opencorporates": {
                    "api_token": "test",
                    "search_queries": [
                        {"query": "AI", "jurisdictions": ["us"]},
                        {"query": "fintech", "jurisdictions": ["gb"]},
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

    @patch("collectors.opencorporates_collector.get_http_session")
    def test_collect_handles_individual_error(self, mock_get_session):
        # Build a company with an invalid incorporation_date to trigger DB error
        c1 = _make_oc_company(inc_date="not-a-date")
        resp = _make_search_response([c1])

        mock_session = _make_mock_session([resp])
        mock_get_session.return_value = mock_session

        c = OpenCorporatesCollector(
            config={
                "opencorporates": {
                    "api_token": "test",
                    "search_queries": [{"query": "test", "jurisdictions": []}],
                    "min_delay_seconds": 0,
                },
            }
        )

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        # Make the second execute call (raw_signals) fail
        call_count = {"n": 0}

        def execute_side_effect(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise Exception("DB error")

        mock_cursor.execute.side_effect = execute_side_effect
        mock_conn.cursor.return_value = mock_cursor

        result = c.collect(mock_conn)
        # Error captured but collection continues
        assert len(result.errors) > 0
