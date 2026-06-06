"""Internet research agent — discovers new data sources via web search."""

import logging
import re
from datetime import datetime, timezone
from urllib.parse import quote_plus

from agents.base import AgentResult, BaseAgent
from config import load_config
from db.connection import get_connection
from db import schema

_logger = logging.getLogger(__name__)

# DuckDuckGo HTML search URL (no API key needed)
DDG_SEARCH_URL = "https://html.duckduckgo.com/html/"

# User agent for search requests
SEARCH_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class InternetResearchAgent(BaseAgent):
    """Agent that searches the web for new startup failure data sources.

    Uses DuckDuckGo HTML search (no API key required) to discover:
    - Open data sources for startup failures
    - APIs with startup/bankruptcy data
    - Research databases and reports
    - Manufacturing failure statistics

    Discovered sources are validated, scored for relevance, and stored
    in the discovered_sources table for potential integration.

    Config options:
        queries: list of search query strings
        max_results_per_query: max URLs to examine per query (default: 20)
        validation:
            timeout_seconds: HTTP timeout for validation requests (default: 10)
            min_content_length: minimum bytes to consider valid (default: 500)
            relevance_threshold: minimum score 0-1 to store (default: 0.3)
    """

    @property
    def name(self) -> str:
        return "internet_research"

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        config = load_config()
        queries = self.config.get("queries", [
            "startup failure database open data",
            "failed startups API data source",
            "manufacturing bankruptcy statistics data",
        ])
        max_results = self.config.get("max_results_per_query", 20)
        val_config = self.config.get("validation", {})
        timeout = val_config.get("timeout_seconds", 10)
        min_length = val_config.get("min_content_length", 500)
        threshold = val_config.get("relevance_threshold", 0.3)

        # Load classification keywords for relevance scoring
        classification = config.get("classification", {})
        mfg_keywords = [k.lower() for k in classification.get("manufacturing_keywords", [])]
        fail_keywords = [k.lower() for k in classification.get("failure_keywords", [])]

        _logger.info("InternetResearchAgent: Running %d search queries", len(queries))

        discovered = 0
        validated = 0
        high_quality = 0
        errors = []

        conn = get_connection()
        schema.init_schema(conn)

        try:
            for query in queries:
                try:
                    urls = self._search(query, max_results)
                    _logger.info("Query '%s': found %d URLs", query[:40], len(urls))

                    for url in urls:
                        discovered += 1

                        # Skip known domains we already scrape
                        if any(d in url for d in ["failory.com", "bls.gov", "reshorenow.org",
                                                    "techcrunch.com", "news.google.com"]):
                            continue

                        # Check if already discovered
                        cursor = conn.cursor()
                        cursor.execute(
                            "SELECT id FROM discovered_sources WHERE url = %s", (url,)
                        )
                        existing = cursor.fetchone()
                        cursor.close()
                        if existing:
                            continue

                        # Validate the URL
                        source_type, content_sample, score = self._validate_url(
                            url, mfg_keywords, fail_keywords, timeout, min_length
                        )

                        if score < threshold:
                            continue

                        validated += 1
                        if score >= 0.6:
                            high_quality += 1

                        # Store in database
                        cursor = conn.cursor()
                        cursor.execute(
                            """INSERT IGNORE INTO discovered_sources
                               (url, source_type, content_sample, relevance_score,
                                validation_status, last_validated_at, discovered_at, search_query)
                               VALUES (%s, %s, %s, %s, 'validated', %s, %s, %s)""",
                            (
                                url,
                                source_type,
                                content_sample[:500] if content_sample else None,
                                score,
                                datetime.now(timezone.utc).isoformat(),
                                datetime.now(timezone.utc).isoformat(),
                                query,
                            ),
                        )
                        conn.commit()
                        cursor.close()

                except Exception as e:
                    _logger.warning("InternetResearchAgent: query '%s' failed: %s", query[:30], e)
                    errors.append(f"Query '{query[:30]}': {e}")
                    continue
        finally:
            conn.close()

        _logger.info(
            "InternetResearchAgent: discovered=%d, validated=%d, high_quality=%d",
            discovered, validated, high_quality,
        )

        return AgentResult(
            agent_name=self.name,
            status="success" if not errors else "partial",
            data={
                "sources_discovered": discovered,
                "sources_validated": validated,
                "high_quality": high_quality,
                "queries_run": len(queries),
                "records_affected": validated,
            },
            errors=errors,
        )

    def _search(self, query: str, max_results: int) -> list[str]:
        """Search DuckDuckGo and return a list of result URLs."""
        import requests

        urls = []
        try:
            response = requests.post(
                DDG_SEARCH_URL,
                data={"q": query, "b": ""},
                headers={"User-Agent": SEARCH_USER_AGENT},
                timeout=15,
            )
            response.raise_for_status()

            # Parse results from DDG HTML
            # Result links are in <a class="result__a" href="..."> format
            for match in re.finditer(
                r'class="result__a"\s+href="([^"]+)"', response.text
            ):
                url = match.group(1)
                # DDG uses redirect URLs — extract the actual URL
                if "uddg=" in url:
                    actual = url.split("uddg=")[-1].split("&")[0]
                    from urllib.parse import unquote
                    url = unquote(actual)
                if url.startswith("http") and "duckduckgo.com" not in url:
                    urls.append(url)
                if len(urls) >= max_results:
                    break

        except requests.RequestException as e:
            _logger.warning("Search request failed for '%s': %s", query[:30], e)

        return urls

    def _validate_url(
        self, url: str, mfg_keywords: list[str], fail_keywords: list[str],
        timeout: int, min_length: int,
    ) -> tuple[str, str | None, float]:
        """Validate a URL and score its relevance.

        Returns (source_type, content_sample, relevance_score).
        """
        import requests

        try:
            response = requests.head(url, timeout=timeout, allow_redirects=True,
                                     headers={"User-Agent": SEARCH_USER_AGENT})
            content_type = response.headers.get("Content-Type", "")

            # Determine source type
            if "application/pdf" in content_type:
                source_type = "pdf"
            elif "application/json" in content_type or "api" in url.lower():
                source_type = "api"
            elif "rss" in url.lower() or "xml" in content_type or "feed" in url.lower():
                source_type = "rss"
            elif "text/html" in content_type:
                source_type = "html"
            else:
                source_type = "unknown"

            # For non-HTML, just do a HEAD check
            if source_type != "html":
                return source_type, None, 0.4  # Moderate score for non-HTML sources

            # Fetch content for HTML sources
            response = requests.get(url, timeout=timeout, headers={"User-Agent": SEARCH_USER_AGENT})
            content = response.text

            if len(content) < min_length:
                return source_type, content[:200], 0.1

            # Score relevance based on keyword presence
            text_lower = content[:5000].lower()
            mfg_matches = sum(1 for kw in mfg_keywords if kw in text_lower)
            fail_matches = sum(1 for kw in fail_keywords if kw in text_lower)

            # Bonus for data-related keywords
            data_bonus = 0
            for kw in ["database", "dataset", "api", "open data", "csv", "json",
                        "statistics", "research", "report", "analysis"]:
                if kw in text_lower:
                    data_bonus += 0.05

            mfg_score = min(mfg_matches / max(len(mfg_keywords) * 0.1, 1), 1.0) * 0.5
            fail_score = min(fail_matches / max(len(fail_keywords) * 0.1, 1), 1.0) * 0.5
            relevance = min(mfg_score + fail_score + data_bonus, 1.0)

            return source_type, content[:500], relevance

        except requests.RequestException:
            return "unknown", None, 0.0
