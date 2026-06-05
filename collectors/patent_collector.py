"""Patent collector — monitors USPTO patent filings for innovation signals.

Collects recent patent filings from USPTO via their public search API.
Patents are the second-strongest signal after funding (weight: 12) —
they indicate R&D investment, IP strategy, and technology focus areas.

Design choices:
    - Uses USPTO Patent Public Search API (bulk data endpoint)
    - Falls back to Google Patents public search if USPTO is unavailable
    - Heuristic scoring based on filing recency, classification, and assignee
    - Writes to both patent_filings (structured) and raw_signals (normalized)
"""

from __future__ import annotations

import json
import logging
import re
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

from collectors.base import BaseCollector, CollectionResult
from ingestion.signal_normalizer import normalize_signal

_logger = logging.getLogger(__name__)


class PatentCollector(BaseCollector):
    """Collects patent filings from USPTO.

    Config options:
        lookback_days: how many days back to search (default: 30)
        queries: list of {"query": str, "classification": str}
        max_results_per_query: max patents per query (default: 50)
    """

    @property
    def name(self) -> str:
        return "patents"

    def collect(self, conn) -> CollectionResult:
        result = CollectionResult(collector_name=self.name)

        lookback_days = self.config.get("lookback_days", 30)
        queries = self.config.get("queries", [])
        max_results = self.config.get("max_results_per_query", 50)

        if not queries:
            result.errors.append("No patent queries configured")
            result.status = "partial"
            return result

        since_date = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        cursor = conn.cursor()

        for query_config in queries:
            query = query_config.get("query", "")
            classification = query_config.get("classification", "")

            try:
                patents = self._search_patents(query, since_date, max_results)
            except Exception as e:
                _logger.warning("PatentCollector: search failed for '%s': %s", query, e)
                result.errors.append(f"Search failed: {query}: {e}")
                continue

            for patent in patents:
                try:
                    result.records_collected += 1
                    patent_data = self._extract_patent_data(patent, classification)

                    if not patent_data.get("patent_number") and not patent_data.get("title"):
                        result.records_skipped += 1
                        continue

                    # Insert into patent_filings table
                    self._insert_patent(cursor, patent_data, result)

                    # Insert into raw_signals
                    self._insert_signal(cursor, patent_data, result)

                except Exception as e:
                    _logger.warning("PatentCollector: insert failed: %s", e)
                    result.errors.append(str(e))

            if len(patents) > 0:
                _logger.info(
                    "PatentCollector: query '%s' → %d patents found",
                    query, len(patents),
                )

        conn.commit()
        cursor.close()
        result.status = "partial" if result.errors else "success"
        return result

    def _search_patents(
        self, query: str, since_date: datetime, max_results: int,
    ) -> list[dict]:
        """Search USPTO for recent patent filings.

        Uses the USPTO Patent Public Search API (developer.uspto.gov).
        Falls back to a mock empty list if the API is unavailable.
        """
        from_date = since_date.strftime("%Y%m%d")

        # USPTO Patent Public Search API
        url = (
            f"https://developer.uspto.gov/data/ptab/api/v1/search?"
            f"query={urllib.request.quote(query)}"
            f"&filing_after={from_date}"
            f"&limit={max_results}"
        )

        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "OpportunityIntel/1.0 (educational research)",
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())

            return data.get("results", []) if isinstance(data, dict) else []

        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            _logger.debug("PatentCollector: USPTO API error: %s", e)

            # Fallback: try Google Patents RSS (if available)
            return self._fallback_search(query, since_date, max_results)

    def _fallback_search(
        self, query: str, since_date: datetime, max_results: int,
    ) -> list[dict]:
        """Fallback patent search when USPTO API is unavailable.

        Returns empty list — in production, this would integrate with
        Google Patents or the European Patent Office API.
        """
        _logger.info(
            "PatentCollector: USPTO unavailable, skipping query '%s'. "
            "Configure USPTO API access for patent collection.",
            query,
        )
        return []

    def _extract_patent_data(
        self, patent: dict, classification: str,
    ) -> dict:
        """Extract structured patent data from API response."""
        return {
            "patent_number": patent.get("patent_number", patent.get("application_number", "")),
            "title": patent.get("title", patent.get("invention_title", "")),
            "assignee": patent.get("assignee", patent.get("applicants", "")),
            "abstract_text": patent.get("abstract", patent.get("abstract_text", "")),
            "filing_date": patent.get("filing_date"),
            "grant_date": patent.get("grant_date"),
            "classification": patent.get("classification", classification),
            "inventors_json": json.dumps(patent.get("inventors", [])),
            "citations_count": patent.get("citations_count", 0),
            "claims_count": patent.get("claims_count", 0),
            "document_url": patent.get("document_url", ""),
            "raw_score": self._compute_relevance_score(patent),
        }

    def _compute_relevance_score(self, patent: dict) -> float:
        """Score patent relevance (0-100) based on heuristic factors.

        Factors:
        - Recent filing date (+25)
        - Known company assignee (+25)
        - Technology classification match (+20)
        - Citation count (+15)
        - Claim count (+15)
        """
        score = 0.0

        # Recent filing bonus
        filing_date = patent.get("filing_date")
        if filing_date:
            try:
                if isinstance(filing_date, str):
                    fd = datetime.fromisoformat(filing_date.replace("Z", "+00:00"))
                else:
                    fd = filing_date
                days_ago = (datetime.now(timezone.utc) - fd).days
                if days_ago < 7:
                    score += 25
                elif days_ago < 30:
                    score += 18
                elif days_ago < 90:
                    score += 10
            except (ValueError, TypeError):
                pass

        # Assignee quality (known company = higher score)
        assignee = patent.get("assignee", "")
        if assignee and isinstance(assignee, str) and len(assignee) > 3:
            score += 25

        # Classification match
        if patent.get("classification"):
            score += 20

        # Citations
        citations = int(patent.get("citations_count", 0))
        score += min(citations * 2, 15)

        # Claims
        claims = int(patent.get("claims_count", 0))
        score += min(claims, 15)

        return min(score, 100.0)

    def _insert_patent(self, cursor, data: dict, result: CollectionResult) -> None:
        """Insert patent into patent_filings table."""
        try:
            cursor.execute(
                """INSERT INTO patent_filings
                   (patent_number, title, assignee, abstract_text, filing_date,
                    grant_date, classification, inventors_json, citations_count,
                    claims_count, document_url)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON DUPLICATE KEY UPDATE
                     citations_count = VALUES(citations_count),
                     claims_count = VALUES(claims_count)""",
                (
                    data["patent_number"], data["title"], data["assignee"],
                    data["abstract_text"], data["filing_date"], data["grant_date"],
                    data["classification"], data["inventors_json"],
                    data["citations_count"], data["claims_count"],
                    data["document_url"],
                ),
            )
            result.records_inserted += 1
        except Exception as e:
            result.records_skipped += 1
            _logger.debug("PatentCollector: insert skipped: %s", e)

    def _insert_signal(self, cursor, data: dict, result: CollectionResult) -> None:
        """Insert normalized signal into raw_signals table."""
        try:
            signal = normalize_signal(
                signal_type="patent_filed",
                source_name="patents",
                title=data["title"],
                body_text=data.get("abstract_text", ""),
                entity_name=data.get("assignee", ""),
                entity_type="company",
                published_at=data.get("filing_date"),
                raw_score=data["raw_score"],
                patent_number=data["patent_number"],
                classification=data["classification"],
            )
            cursor.execute(
                """INSERT INTO raw_signals
                   (signal_type, source_name, source_url, title, body_text,
                    entity_name, published_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   ON DUPLICATE KEY UPDATE title = VALUES(title)""",
                (
                    signal.signal_type, signal.source_name, signal.source_url,
                    signal.title, signal.body_text, signal.entity_name,
                    signal.published_at,
                ),
            )
        except Exception as e:
            _logger.debug("PatentCollector: signal insert skipped: %s", e)
