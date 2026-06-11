"""NPM/PyPI collector — tracks package metadata and download trends.

Data sources:
  - NPM Registry API (https://registry.npmjs.org/{package}) — package metadata JSON
  - NPM Downloads API (https://api.npmjs.org/downloads/point/last-month/{package})
  - PyPI JSON API (https://pypi.org/pypi/{package}/json) — package metadata JSON
No auth required for any endpoint.

Tracks technology adoption trends, emerging libraries, and developer tooling.
Writes to package_trends + raw_signals tables.
"""

import json
import logging
import time
from datetime import datetime, timezone
from urllib.parse import quote

from collectors.base import BaseCollector, CollectionResult
from utils.http_client import get_http_session

_logger = logging.getLogger(__name__)

_NPM_REGISTRY = "https://registry.npmjs.org"
_NPM_DOWNLOADS = "https://api.npmjs.org/downloads/point/last-month"
_PYPI_API = "https://pypi.org/pypi"

# Keywords/classifiers indicating startup relevance
_RELEVANT_KEYWORDS = {
    "startup",
    "saas",
    "api",
    "framework",
    "serverless",
    "microservices",
    "deployment",
    "monitoring",
    "authentication",
    "database",
    "orm",
    "machine-learning",
    "ai",
    "llm",
    "rag",
    "vector",
    "embedding",
    "devops",
    "docker",
    "kubernetes",
    "graphql",
    "real-time",
    "websocket",
}

_DEFAULT_PACKAGES = [
    {"name": "next", "registry": "npm"},
    {"name": "express", "registry": "npm"},
    {"name": "fastapi", "registry": "pypi"},
    {"name": "langchain", "registry": "pypi"},
]


class NPMPyPICollector(BaseCollector):
    """Collects package metadata from NPM and PyPI registries.

    Config options:
        npm_pypi.packages: list of {name, registry} dicts
        npm_pypi.timeout_seconds: HTTP timeout (default: 15)
        npm_pypi.min_delay_seconds: delay between requests (default: 1)
    """

    @property
    def name(self) -> str:
        return "npm_pypi"

    def _parse_iso_date(self, date_str: str) -> datetime | None:
        """Parse ISO date string to datetime."""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None

    def _fetch_npm_package(
        self, session, package_name: str, timeout: int = 15
    ) -> dict | None:
        """Fetch package metadata from NPM registry."""
        url = f"{_NPM_REGISTRY}/{quote(package_name)}"
        try:
            resp = session.get(url, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            _logger.warning(
                "NPMPyPICollector: NPM fetch failed for %s — %s", package_name, e
            )
            return None

        # Fetch downloads separately
        downloads = self._fetch_npm_downloads(session, package_name, timeout)
        return self._parse_npm(data, downloads)

    def _fetch_npm_downloads(
        self, session, package_name: str, timeout: int = 15
    ) -> int:
        """Fetch monthly download count from NPM downloads API."""
        url = f"{_NPM_DOWNLOADS}/{quote(package_name)}"
        try:
            resp = session.get(url, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            return int(data.get("downloads", 0))
        except Exception:
            return 0

    def _parse_npm(self, data: dict, downloads: int = 0) -> dict | None:
        """Parse NPM registry response into a normalized dict."""
        name = data.get("name", "").strip()
        if not name:
            return None

        time_data = data.get("time", {})
        created_at = self._parse_iso_date(time_data.get("created", ""))
        modified_at = self._parse_iso_date(time_data.get("modified", ""))

        return {
            "package_name": name,
            "registry": "npm",
            "version": data.get("version", ""),
            "description": data.get("description", ""),
            "monthly_downloads": downloads,
            "keywords": data.get("keywords", []),
            "author": "",
            "license_type": data.get("license", ""),
            "project_url": data.get("homepage", ""),
            "created_at_registry": created_at,
            "updated_at_registry": modified_at,
        }

    def _fetch_pypi_package(
        self, session, package_name: str, timeout: int = 15
    ) -> dict | None:
        """Fetch package metadata from PyPI JSON API."""
        url = f"{_PYPI_API}/{quote(package_name)}/json"
        try:
            resp = session.get(url, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            _logger.warning(
                "NPMPyPICollector: PyPI fetch failed for %s — %s", package_name, e
            )
            return None

        return self._parse_pypi(data)

    def _parse_pypi(self, data: dict) -> dict | None:
        """Parse PyPI JSON API response into a normalized dict."""
        info = data.get("info", {})
        name = info.get("name", "").strip()
        if not name:
            return None

        # PyPI doesn't provide monthly downloads via JSON API
        # We use release count as a proxy for activity
        data.get("releases", {})
        version = info.get("version", "")

        return {
            "package_name": name,
            "registry": "pypi",
            "version": version,
            "description": info.get("summary", ""),
            "monthly_downloads": 0,
            "keywords": [
                k.strip() for k in info.get("keywords", "").split(",") if k.strip()
            ]
            if info.get("keywords")
            else info.get("classifiers", []),
            "author": info.get("author", ""),
            "license_type": info.get("license", ""),
            "project_url": (data.get("urls") or {}).get(
                "project", info.get("project_url", "")
            ),
            "created_at_registry": None,  # PyPI doesn't expose creation date easily
            "updated_at_registry": None,
        }

    def _compute_score(self, pkg: dict) -> float:
        """Compute signal strength (0-100).

        Factors:
          - Downloads: >1M/month (+35), >100K (+25), >10K (+15), >1K (+8)
          - Recency (updated <30d: +20, <90d: +10)
          - New major version (version starts with 0.x or <1 year old): +15
          - Relevant keywords: +10
          - Capped at 100
        """
        score = 0.0

        # Downloads (NPM only has this)
        downloads = pkg.get("monthly_downloads", 0)
        if downloads > 1_000_000:
            score += 35
        elif downloads > 100_000:
            score += 25
        elif downloads > 10_000:
            score += 15
        elif downloads > 1_000:
            score += 8

        # Recency
        updated = pkg.get("updated_at_registry")
        if updated:
            age_hours = (datetime.now(timezone.utc) - updated).total_seconds() / 3600
            if age_hours < 720:  # 30 days
                score += 20
            elif age_hours < 2160:  # 90 days
                score += 10

        # New major version (0.x prefix = early-stage)
        version = pkg.get("version", "")
        if version and version.startswith("0."):
            score += 15

        # Relevant keywords
        keywords = pkg.get("keywords", [])
        kw_set = {k.lower() for k in keywords if isinstance(k, str)}
        if kw_set & _RELEVANT_KEYWORDS:
            score += 10

        return min(score, 100.0)

    def _insert_package(
        self, cursor, pkg: dict, raw_score: float, result: CollectionResult
    ) -> None:
        """Insert package into package_trends + raw_signals tables."""
        created_iso = (
            pkg["created_at_registry"].isoformat()
            if pkg.get("created_at_registry")
            else None
        )
        updated_iso = (
            pkg["updated_at_registry"].isoformat()
            if pkg.get("updated_at_registry")
            else None
        )

        # Insert into package_trends
        cursor.execute(
            """INSERT IGNORE INTO package_trends
               (package_name, registry, version, description, monthly_downloads,
                keywords, author, license_type, project_url,
                created_at_registry, updated_at_registry, collected_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                pkg["package_name"],
                pkg["registry"],
                pkg["version"],
                pkg["description"],
                pkg["monthly_downloads"],
                json.dumps(pkg["keywords"]),
                pkg["author"],
                pkg["license_type"],
                pkg["project_url"],
                created_iso,
                updated_iso,
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        # Insert into raw_signals
        signal_title = (
            f"[{pkg['registry'].upper()}] {pkg['package_name']} v{pkg['version']}"
        )
        signal_body = pkg["description"][:500] if pkg["description"] else ""

        cursor.execute(
            """INSERT IGNORE INTO raw_signals
               (signal_type, source_name, source_url, title, body_text,
                entity_name, published_at, collected_at, processed)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0)""",
            (
                "package_trend",
                pkg["registry"],
                pkg["project_url"],
                signal_title,
                signal_body,
                pkg["author"],
                updated_iso,
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        # Kafka publish
        self.publish_signal(
            "package_trend",
            title=signal_title,
            entity_name=pkg["package_name"],
            source_url=pkg["project_url"],
            body_text=signal_body[:300],
            raw_score=raw_score,
            signal_keywords=pkg["keywords"],
        )

        result.records_collected += 1

    def collect(self, conn) -> CollectionResult:
        result = CollectionResult(collector_name=self.name)
        config = self.config.get("npm_pypi", {})

        if self.dry_run:
            result.status = "success"
            return result

        packages = config.get("packages", _DEFAULT_PACKAGES)
        timeout = config.get("timeout_seconds", 15)
        min_delay = config.get("min_delay_seconds", 1)

        if not packages:
            _logger.info("NPMPyPICollector: no packages configured")
            result.status = "partial"
            return result

        session = get_http_session(timeout=timeout)
        session.headers["Accept"] = "application/json"

        cursor = conn.cursor()

        for pkg_config in packages:
            pkg_name = pkg_config.get("name", "")
            registry = pkg_config.get("registry", "npm").lower()

            if not pkg_name:
                continue

            if registry == "npm":
                pkg = self._fetch_npm_package(session, pkg_name, timeout)
            elif registry == "pypi":
                pkg = self._fetch_pypi_package(session, pkg_name, timeout)
            else:
                _logger.warning(
                    "NPMPyPICollector: unknown registry '%s' for %s", registry, pkg_name
                )
                continue

            if pkg is None:
                continue

            raw_score = self._compute_score(pkg)

            try:
                self._insert_package(cursor, pkg, raw_score, result)
            except Exception as e:
                result.errors.append(
                    f"Error inserting package {pkg_name} ({registry}): {e}"
                )

            time.sleep(min_delay)

        result.records_inserted = result.records_collected
        cursor.close()
        conn.commit()
        result.status = "success" if result.records_inserted > 0 else "partial"
        return result
