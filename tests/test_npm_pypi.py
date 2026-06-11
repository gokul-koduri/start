"""Tests for the NPM/PyPI Collector."""

import json
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

from collectors.npm_pypi_collector import NPMPyPICollector  # noqa: E402
from collectors.base import CollectionResult  # noqa: E402

# Restore real db modules so other tests aren't poisoned
for key, orig in _saved_db_modules.items():
    if orig is not None:
        sys.modules[key] = orig
    else:
        sys.modules.pop(key, None)


def _make_npm_data(
    name="next",
    version="14.0.0",
    description="The React Framework",
    keywords=None,
    license_type="MIT",
    homepage="https://nextjs.org",
    created=None,
    modified=None,
):
    """Build a mock NPM registry API response."""
    if keywords is None:
        keywords = ["react", "framework", "ssr"]
    if created is None:
        created = "2016-10-17T23:12:22.000Z"
    if modified is None:
        modified = (datetime.now(timezone.utc) - timedelta(days=15)).isoformat()
    return {
        "name": name,
        "description": description,
        "version": version,
        "license": license_type,
        "keywords": keywords,
        "homepage": homepage,
        "time": {"created": created, "modified": modified},
    }


def _make_npm_downloads(package="next", downloads=5200000):
    """Build a mock NPM downloads API response."""
    return {"package": package, "downloads": downloads}


def _make_pypi_data(
    name="fastapi",
    version="0.109.0",
    summary="Modern, fast web framework",
    author="Sebastian Ramirez",
    keywords=None,
    classifiers=None,
    license_type="MIT",
    project_url="https://github.com/tiangolo/fastapi",
):
    """Build a mock PyPI JSON API response."""
    if keywords is None:
        keywords = ""
    if classifiers is None:
        classifiers = ["Framework :: FastAPI", "Programming Language :: Python"]
    return {
        "info": {
            "name": name,
            "summary": summary,
            "version": version,
            "author": author,
            "keywords": keywords,
            "classifiers": classifiers,
            "license": license_type,
            "project_url": project_url,
        },
        "urls": {"project": project_url},
        "releases": {},
    }


def _make_pkg_dict(
    package_name="next",
    registry="npm",
    version="14.0.0",
    description="The React Framework",
    monthly_downloads=5200000,
    keywords=None,
    author="",
    license_type="MIT",
    project_url="https://nextjs.org",
    created_at_registry=None,
    updated_at_registry=None,
):
    """Build a normalized package dict matching _parse_npm/_parse_pypi output."""
    if keywords is None:
        keywords = ["react", "framework", "ssr"]
    if updated_at_registry is None:
        updated_at_registry = datetime.now(timezone.utc) - timedelta(days=15)
    return {
        "package_name": package_name,
        "registry": registry,
        "version": version,
        "description": description,
        "monthly_downloads": monthly_downloads,
        "keywords": keywords,
        "author": author,
        "license_type": license_type,
        "project_url": project_url,
        "created_at_registry": created_at_registry,
        "updated_at_registry": updated_at_registry,
    }


def _make_mock_session(responses=None):
    """Build a mock requests.Session returning JSON responses in order."""
    session = MagicMock()
    session.headers = {}
    rl = list(responses or [])

    def mock_get(url, timeout=None):
        resp = MagicMock()
        resp.status_code = 200
        if rl:
            data = rl.pop(0)
            resp.content = data.encode("utf-8") if isinstance(data, str) else b""
            resp.json.return_value = json.loads(data) if isinstance(data, str) else {}
        else:
            resp.content = b""
            resp.json.return_value = {}
        return resp

    session.get = mock_get
    return session


class TestNPMPyPICollectorName:
    def test_name(self):
        c = NPMPyPICollector(config={})
        assert c.name == "npm_pypi"


class TestNPMPyPICollectorConfig:
    def test_dry_run_mode(self):
        c = NPMPyPICollector(config={}, dry_run=True)
        mock_conn = MagicMock()
        result = c.collect(mock_conn)
        assert result.status == "success"
        assert result.records_collected == 0

    def test_no_packages(self):
        c = NPMPyPICollector(config={"npm_pypi": {"packages": []}})
        mock_conn = MagicMock()
        result = c.collect(mock_conn)
        assert result.status == "partial"
        assert result.records_collected == 0


class TestNPMPyPICollectorScoring:
    def test_high_downloads_recent(self):
        c = NPMPyPICollector(config={})
        pkg = _make_pkg_dict(
            monthly_downloads=2_000_000,
            updated_at_registry=datetime.now(timezone.utc) - timedelta(days=10),
        )
        score = c._compute_score(pkg)
        # downloads(>1M +35) + recency(<30d +20) + keywords(+10) = 65
        assert score == 65.0

    def test_low_downloads_old(self):
        c = NPMPyPICollector(config={})
        pkg = _make_pkg_dict(
            monthly_downloads=500,
            keywords=["random"],
            updated_at_registry=datetime.now(timezone.utc) - timedelta(days=200),
        )
        score = c._compute_score(pkg)
        assert score == 0.0

    def test_zero_x_version_boost(self):
        c = NPMPyPICollector(config={})
        pkg = _make_pkg_dict(
            version="0.3.0",
            monthly_downloads=0,
            keywords=["random"],
            updated_at_registry=None,
        )
        pkg["updated_at_registry"] = None
        score = c._compute_score(pkg)
        # 0.x version (+15) = 15
        assert score == 15.0

    def test_medium_downloads(self):
        c = NPMPyPICollector(config={})
        pkg = _make_pkg_dict(
            monthly_downloads=500_000, keywords=["random"], version="1.0.0"
        )
        pkg["updated_at_registry"] = None
        score = c._compute_score(pkg)
        # downloads(>100K +25) = 25
        assert score == 25.0

    def test_capped_at_100(self):
        c = NPMPyPICollector(config={})
        pkg = _make_pkg_dict(
            monthly_downloads=5_000_000,
            version="0.5.0",
            updated_at_registry=datetime.now(timezone.utc) - timedelta(hours=6),
        )
        score = c._compute_score(pkg)
        assert score <= 100.0


class TestNPMPyPICollectorParseNPM:
    def test_parse_valid_npm(self):
        c = NPMPyPICollector(config={})
        data = _make_npm_data()
        pkg = c._parse_npm(data, 5200000)
        assert pkg is not None
        assert pkg["package_name"] == "next"
        assert pkg["registry"] == "npm"
        assert pkg["monthly_downloads"] == 5200000
        assert "React" in pkg["description"]

    def test_parse_npm_no_name(self):
        c = NPMPyPICollector(config={})
        data = _make_npm_data(name="")
        pkg = c._parse_npm(data, 0)
        assert pkg is None


class TestNPMPyPICollectorParsePyPI:
    def test_parse_valid_pypi(self):
        c = NPMPyPICollector(config={})
        data = _make_pypi_data()
        pkg = c._parse_pypi(data)
        assert pkg is not None
        assert pkg["package_name"] == "fastapi"
        assert pkg["registry"] == "pypi"
        assert pkg["monthly_downloads"] == 0  # PyPI doesn't provide downloads

    def test_parse_pypi_no_name(self):
        c = NPMPyPICollector(config={})
        data = _make_pypi_data(name="")
        pkg = c._parse_pypi(data)
        assert pkg is None

    def test_parse_pypi_with_keywords(self):
        c = NPMPyPICollector(config={})
        data = _make_pypi_data(keywords="api, framework, web")
        pkg = c._parse_pypi(data)
        assert pkg is not None
        assert "api" in pkg["keywords"]
        assert "framework" in pkg["keywords"]


class TestNPMPyPICollectorFetch:
    def test_fetch_npm_success(self):
        c = NPMPyPICollector(config={"npm_pypi": {}})
        npm_data = _make_npm_data()
        dl_data = _make_npm_downloads()
        session = _make_mock_session(
            [
                json.dumps(npm_data),  # registry endpoint called first
                json.dumps(dl_data),  # downloads endpoint called second
            ]
        )
        pkg = c._fetch_npm_package(session, "next")
        assert pkg is not None
        assert pkg["package_name"] == "next"
        assert pkg["monthly_downloads"] == 5200000

    def test_fetch_pypi_success(self):
        c = NPMPyPICollector(config={"npm_pypi": {}})
        pypi_data = _make_pypi_data()
        session = _make_mock_session([json.dumps(pypi_data)])
        pkg = c._fetch_pypi_package(session, "fastapi")
        assert pkg is not None
        assert pkg["package_name"] == "fastapi"

    def test_fetch_api_failure(self):
        c = NPMPyPICollector(config={"npm_pypi": {}})
        session = MagicMock()
        session.get.side_effect = Exception("Connection refused")
        pkg = c._fetch_npm_package(session, "nonexistent")
        assert pkg is None


class TestNPMPyPICollectorInsert:
    def test_insert_single_package(self):
        c = NPMPyPICollector(config={"npm_pypi": {}})
        mock_cursor = MagicMock()
        result = CollectionResult(collector_name="npm_pypi")

        pkg = _make_pkg_dict()
        c._insert_package(mock_cursor, pkg, 65.0, result)
        assert result.records_collected == 1
        # 2 SQL calls: package_trends + raw_signals
        assert mock_cursor.execute.call_count == 2

    def test_insert_multiple_packages(self):
        c = NPMPyPICollector(config={"npm_pypi": {}})
        mock_cursor = MagicMock()
        result = CollectionResult(collector_name="npm_pypi")

        for name in ["next", "express", "fastapi"]:
            pkg = _make_pkg_dict(package_name=name, registry="npm")
            c._insert_package(mock_cursor, pkg, 50, result)
        assert result.records_collected == 3


class TestNPMPyPICollectorIntegration:
    @patch("collectors.npm_pypi_collector.time")
    @patch("collectors.npm_pypi_collector.get_http_session")
    def test_collect_npm_flow(self, mock_get_session, mock_time):
        npm_data = _make_npm_data()
        dl_data = _make_npm_downloads()
        session = _make_mock_session(
            [
                json.dumps(npm_data),  # registry endpoint first
                json.dumps(dl_data),  # downloads endpoint second
            ]
        )
        mock_get_session.return_value = session

        c = NPMPyPICollector(
            config={
                "npm_pypi": {
                    "packages": [{"name": "next", "registry": "npm"}],
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
        mock_conn.commit.assert_called()

    @patch("collectors.npm_pypi_collector.time")
    @patch("collectors.npm_pypi_collector.get_http_session")
    def test_collect_pypi_flow(self, mock_get_session, mock_time):
        pypi_data = _make_pypi_data()
        session = _make_mock_session([json.dumps(pypi_data)])
        mock_get_session.return_value = session

        c = NPMPyPICollector(
            config={
                "npm_pypi": {
                    "packages": [{"name": "fastapi", "registry": "pypi"}],
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

    @patch("collectors.npm_pypi_collector.time")
    @patch("collectors.npm_pypi_collector.get_http_session")
    def test_collect_mixed_registries(self, mock_get_session, mock_time):
        npm_data = _make_npm_data(name="next")
        dl_data = _make_npm_downloads(package="next")
        pypi_data = _make_pypi_data()
        session = _make_mock_session(
            [
                json.dumps(npm_data),  # next registry
                json.dumps(dl_data),  # next downloads
                json.dumps(pypi_data),  # fastapi
            ]
        )
        mock_get_session.return_value = session

        c = NPMPyPICollector(
            config={
                "npm_pypi": {
                    "packages": [
                        {"name": "next", "registry": "npm"},
                        {"name": "fastapi", "registry": "pypi"},
                    ],
                    "min_delay_seconds": 0,
                },
            }
        )

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        result = c.collect(mock_conn)
        assert result.records_collected == 2

    @patch("collectors.npm_pypi_collector.time")
    @patch("collectors.npm_pypi_collector.get_http_session")
    def test_collect_handles_insert_error(self, mock_get_session, mock_time):
        npm_data = _make_npm_data()
        dl_data = _make_npm_downloads()
        session = _make_mock_session(
            [
                json.dumps(npm_data),  # registry endpoint first
                json.dumps(dl_data),  # downloads endpoint second
            ]
        )
        mock_get_session.return_value = session

        c = NPMPyPICollector(
            config={
                "npm_pypi": {
                    "packages": [{"name": "next", "registry": "npm"}],
                    "min_delay_seconds": 0,
                },
            }
        )

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
