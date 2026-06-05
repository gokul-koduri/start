"""arXiv collector — fetches ML/AI research papers from the arXiv API.

Data source: arXiv API (Atom XML feed, no auth required).
Rate limit: No strict limit — uses polite delay between requests.

This collector tracks emerging research trends, author institutions, and
paper categories to identify early technology signals for downstream analysis.
"""

import json
import logging
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import quote

from collectors.base import BaseCollector, CollectionResult
from utils.http_client import get_http_session

_logger = logging.getLogger(__name__)

_BASE_URL = "http://export.arxiv.org/api/query"

# arXiv XML namespaces
_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}

# High-relevance categories for startup/tech signal detection
_RELEVANT_CATEGORIES = {"cs.AI", "cs.CL", "cs.LG", "cs.CV", "stat.ML"}


class ArxivCollector(BaseCollector):
    """Collects research papers from arXiv API.

    Searches for papers using configurable terms + category filters.
    Parses Atom XML responses and stores paper metadata.

    Config options:
        arxiv.base_url: API base URL
        arxiv.search_queries: list of {terms, categories} dicts
        arxiv.max_results_per_query: results per query (default: 50)
        arxiv.min_delay_seconds: delay between API calls (default: 3)
    """

    @property
    def name(self) -> str:
        return "arxiv"

    def _build_query(self, terms: str, categories: list[str] | None = None) -> str:
        """Build arXiv search query string.

        Format: all:{terms} AND cat:{cat1} AND cat:{cat2} ...
        """
        q = f"all:{terms}"
        if categories:
            cat_clause = " OR ".join(f"cat:{c}" for c in categories)
            q = f"{q} AND ({cat_clause})"
        return q

    def _fetch_papers(self, session, base_url: str,
                      query: str, max_results: int = 50) -> list[dict]:
        """Fetch papers from arXiv API and parse Atom XML response."""
        params = {
            "search_query": query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }

        try:
            resp = session.get(base_url, params=params, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            _logger.warning("arXiv API request failed: %s — %s", query, e)
            return []

        try:
            root = ET.fromstring(resp.content)
        except ET.ParseError as e:
            _logger.warning("arXiv XML parse failed: %s", e)
            return []

        entries = []
        for entry in root.findall("atom:entry", _NS):
            paper = self._parse_entry(entry)
            if paper:
                entries.append(paper)

        return entries

    def _parse_entry(self, entry: ET.Element) -> dict | None:
        """Extract paper metadata from an Atom entry element."""
        # arXiv ID from <id> tag (e.g., http://arxiv.org/abs/2401.12345v1)
        arxiv_url = entry.findtext("atom:id", default="", namespaces=_NS)
        arxiv_id = arxiv_url.split("/abs/")[-1].split("v")[0] if "/abs/" in arxiv_url else ""

        if not arxiv_id:
            _logger.warning("Skipping entry without arXiv ID")
            return None

        title = entry.findtext("atom:title", default="", namespaces=_NS).strip()
        title = " ".join(title.split())  # Collapse whitespace from XML

        abstract = entry.findtext("atom:summary", default="", namespaces=_NS).strip()
        abstract = " ".join(abstract.split())

        # Authors
        authors = []
        for author in entry.findall("atom:author", _NS):
            name = author.findtext("atom:name", default="", namespaces=_NS).strip()
            if name:
                authors.append(name)

        # Categories
        primary_category = ""
        categories = []
        cat_elem = entry.find("arxiv:primary_category", _NS)
        if cat_elem is not None:
            primary_category = cat_elem.get("term", "")
            categories.append(primary_category)
        for cat in entry.findall("atom:category", _NS):
            term = cat.get("term", "")
            if term and term not in categories:
                categories.append(term)

        # Dates
        published_str = entry.findtext("atom:published", default="", namespaces=_NS)
        updated_str = entry.findtext("atom:updated", default="", namespaces=_NS)

        published_date = self._parse_date(published_str)
        updated_date = self._parse_date(updated_str)

        # Links — PDF and abstract page
        pdf_url = ""
        source_url = arxiv_url
        for link in entry.findall("atom:link", _NS):
            if link.get("title") == "pdf":
                href = link.get("href", "")
                pdf_url = href.split("/pdf/")[0] + "/pdf/" + arxiv_id if href else ""
                break

        # DOI
        doi_elem = entry.find("arxiv:doi", _NS)
        doi = doi_elem.text.strip() if doi_elem is not None and doi_elem.text else ""

        return {
            "arxiv_id": arxiv_id,
            "title": title,
            "authors": authors,
            "abstract": abstract,
            "primary_category": primary_category,
            "categories": categories,
            "published_date": published_date,
            "updated_date": updated_date,
            "pdf_url": pdf_url,
            "source_url": source_url,
            "doi": doi,
        }

    def _parse_date(self, date_str: str) -> str | None:
        """Parse ISO date string to YYYY-MM-DD format."""
        if not date_str:
            return None
        try:
            # arXiv dates like "2024-01-15T12:34:56Z"
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            return None

    def _compute_score(self, paper: dict) -> float:
        """Compute signal strength (0-100).

        Factors:
          - Recent publication (< 7 days): +40
          - Recent (< 30 days): +25
          - Recent (< 90 days): +10
          - Multiple authors (collaboration signal): +20
          - High-relevance primary category: +20
        """
        score = 0.0

        # Recency
        pub_str = paper.get("published_date")
        if pub_str:
            try:
                pub_dt = datetime.strptime(pub_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                age_days = (datetime.now(timezone.utc) - pub_dt).days
                if age_days < 7:
                    score += 40
                elif age_days < 30:
                    score += 25
                elif age_days < 90:
                    score += 10
            except (ValueError, TypeError):
                pass

        # Author collaboration signal
        authors = paper.get("authors", [])
        if len(authors) >= 3:
            score += 20

        # Category relevance
        primary_cat = paper.get("primary_category", "")
        if primary_cat in _RELEVANT_CATEGORIES:
            score += 20

        return min(score, 100.0)

    def _insert_paper(self, cursor, paper: dict, search_term: str,
                      result: CollectionResult) -> None:
        """Insert paper into arxiv_papers and raw_signals."""
        arxiv_id = paper["arxiv_id"]
        title = paper["title"]
        authors = paper["authors"]
        abstract = paper["abstract"]
        primary_category = paper["primary_category"]
        categories = paper["categories"]
        published_date = paper["published_date"]
        updated_date = paper["updated_date"]
        pdf_url = paper["pdf_url"]
        source_url = paper["source_url"]
        doi = paper["doi"]

        raw_score = self._compute_score(paper)

        # Insert into arxiv_papers
        cursor.execute(
            """INSERT INTO arxiv_papers
               (arxiv_id, title, authors, abstract, primary_category, categories,
                published_date, updated_date, pdf_url, source_url, doi,
                search_term, raw_score, collected_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
                 title = VALUES(title),
                 updated_date = VALUES(updated_date),
                 raw_score = VALUES(raw_score),
                 collected_at = VALUES(collected_at)""",
            (
                arxiv_id,
                title,
                json.dumps(authors) if authors else None,
                abstract or None,
                primary_category or None,
                json.dumps(categories) if categories else None,
                published_date,
                updated_date,
                pdf_url or None,
                source_url,
                doi or None,
                search_term,
                raw_score,
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        # Insert into raw_signals
        cursor.execute(
            """INSERT IGNORE INTO raw_signals
               (signal_type, source_name, source_url, title, body_text,
                entity_name, published_at, collected_at, processed)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0)""",
            (
                "arxiv",
                "arxiv",
                source_url,
                title,
                abstract[:500] if abstract else "",
                authors[0] if authors else "",
                published_date,
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        # Kafka publish
        self.publish_signal(
            "arxiv",
            title=title,
            entity_name=authors[0] if authors else "",
            source_url=source_url,
            body_text=abstract[:300] if abstract else "",
            raw_score=raw_score,
            arxiv_id=arxiv_id,
            primary_category=primary_category,
            author_count=len(authors),
        )

        result.records_collected += 1

    def collect(self, conn) -> CollectionResult:
        result = CollectionResult(collector_name=self.name)
        config = self.config.get("arxiv", {})

        if self.dry_run:
            result.status = "success"
            return result

        search_queries = config.get("search_queries", [
            {"terms": "machine learning", "categories": ["cs.AI", "cs.LG"]},
            {"terms": "large language model", "categories": ["cs.CL", "cs.AI"]},
        ])
        base_url = config.get("base_url", _BASE_URL)
        max_results = config.get("max_results_per_query", 50)
        min_delay = config.get("min_delay_seconds", 3)

        session = get_http_session(timeout=30)
        session.headers["Accept"] = "application/xml"

        cursor = conn.cursor()

        for sq in search_queries:
            terms = sq.get("terms", "")
            categories = sq.get("categories", [])

            if not terms:
                continue

            query = self._build_query(terms, categories)

            papers = self._fetch_papers(session, base_url, query, max_results)

            for paper in papers:
                try:
                    self._insert_paper(cursor, paper, terms, result)
                except Exception as e:
                    result.errors.append(f"Error inserting paper {paper.get('arxiv_id', '?')}: {e}")

            time.sleep(min_delay)  # Polite delay

            _logger.info(
                "ArxivCollector: query '%s' → %d papers",
                terms, len(papers),
            )

        result.records_inserted = result.records_collected
        cursor.close()
        conn.commit()
        result.status = "success" if result.records_inserted > 0 else "partial"
        return result
