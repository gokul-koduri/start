"""Whale Investor Agent — tracks large investor activity in manufacturing revival."""

import json
import logging
import re
from datetime import datetime, timezone
from urllib.parse import unquote

from agents.base import AgentResult, BaseAgent
from config import load_config
from db.connection import get_connection
from db import schema

_logger = logging.getLogger(__name__)

DDG_SEARCH_URL = "https://html.duckduckgo.com/html/"

SEARCH_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Keywords that indicate whale investor activity
INVESTOR_KEYWORDS = [
    "private equity",
    "venture capital",
    "sovereign wealth fund",
    "hedge fund",
    "institutional investor",
    "family office",
    "pension fund",
    "endowment",
    "buyout",
    "acquisition",
    "merger",
    "series a",
    "series b",
    "series c",
    "series d",
    "funding round",
    "seed funding",
    "growth equity",
    "distressed assets",
    "turnaround",
    "restructuring",
    "portfolio company",
    "leveraged buyout",
    "lbo",
    "m&a",
    "ma deal",
    "deal value",
    "deal size",
]

# Keywords for large-scale manufacturing investment
MANUFACTURING_INVEST_KEYWORDS = [
    "semiconductor",
    "battery",
    "ev",
    "electric vehicle",
    "solar",
    "pharma",
    "pharmaceutical",
    "steel",
    "biomanufacturing",
    "chip",
    "fab",
    "fabrication",
    "gigafactory",
    "reshoring",
    "onshoring",
    "nearshoring",
    "domestic manufacturing",
    "chips act",
    "ira",
    "inflation reduction act",
    "manufacturing hub",
    "industrial park",
    "production facility",
    "greenfield",
    "new plant",
    "new factory",
    "mega project",
    "groundbreaking",
    "new capacity",
    "capacity expansion",
    "construction",
    "build-out",
    "facility investment",
]

# Regex patterns to extract dollar amounts
DOLLAR_PATTERNS = [
    re.compile(r"\$\s*([\d,.]+)\s*(billion|b|million|m)", re.IGNORECASE),
    re.compile(r"([\d,.]+)\s*(billion|b|million|m)\s*(dollar|usd|\$)", re.IGNORECASE),
]


class WhaleInvestorAgent(BaseAgent):
    """Agent that searches the web for whale investor activity in manufacturing.

    Uses DuckDuckGo HTML search to discover:
    - PE/VC acquisitions of distressed manufacturing assets
    - Sovereign wealth fund investments in manufacturing
    - Large funding rounds in semiconductor, battery, EV sectors
    - Institutional investor interest in reshoring/revival

    Cross-references findings with the opportunity_pipeline analysis
    to highlight which tracked opportunities have whale backing.

    Config options:
        queries: list of search query strings
        max_results_per_query: max URLs to examine per query (default: 15)
        validation:
            timeout_seconds: HTTP timeout (default: 10)
            min_content_length: minimum bytes for valid page (default: 500)
            relevance_threshold: minimum score 0-1 to store (default: 0.3)
    """

    @property
    def name(self) -> str:
        return "whale_investor"

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        config = load_config()
        queries = self.config.get(
            "queries",
            [
                "US manufacturing revival private equity acquisitions 2024 2025",
                "semiconductor manufacturing sovereign wealth fund investment",
                "battery cell manufacturing private equity deals 2025",
                "CHIPS Act funded projects investors",
            ],
        )
        max_results = self.config.get("max_results_per_query", 15)
        val_config = self.config.get("validation", {})
        timeout = val_config.get("timeout_seconds", 10)
        min_length = val_config.get("min_content_length", 500)
        threshold = val_config.get("relevance_threshold", 0.3)

        # Load classification keywords for additional relevance
        classification = config.get("classification", {})
        mfg_keywords = [
            k.lower() for k in classification.get("manufacturing_keywords", [])
        ]

        _logger.info("WhaleInvestorAgent: Running %d search queries", len(queries))

        conn = get_connection()
        schema.init_schema(conn)

        all_findings = []
        discovered = 0
        validated = 0
        errors = []

        try:
            for query in queries:
                try:
                    urls = self._search(query, max_results)
                    _logger.info("Query '%s': found %d URLs", query[:50], len(urls))

                    for url in urls:
                        discovered += 1

                        # Skip known domains we already scrape
                        if any(
                            d in url
                            for d in [
                                "failory.com",
                                "bls.gov",
                                "reshorenow.org",
                                "techcrunch.com",
                                "news.google.com",
                            ]
                        ):
                            continue

                        # Validate and score the URL
                        source_type, content, score = self._validate_url(
                            url, timeout, min_length
                        )

                        if score < threshold or not content:
                            continue

                        validated += 1

                        # Extract investor information from the content
                        investor_info = self._extract_investor_info(content)

                        finding = {
                            "url": url,
                            "source_type": source_type,
                            "relevance_score": round(score, 2),
                            "query": query,
                            "extracted_at": datetime.now(timezone.utc).isoformat(),
                            **investor_info,
                        }
                        all_findings.append(finding)

                except Exception as e:
                    _logger.warning(
                        "WhaleInvestorAgent: query '%s' failed: %s", query[:40], e
                    )
                    errors.append(f"Query '{query[:40]}': {e}")
                    continue

            # Cross-reference with opportunity pipeline
            cross_ref = self._cross_reference_opportunities(
                conn, all_findings, mfg_keywords
            )

            # Build insights
            insights = {
                "total_findings": len(all_findings),
                "findings_with_dollar_amounts": sum(
                    1 for f in all_findings if f.get("dollar_amounts")
                ),
                "findings_by_sector": self._group_by_sector(all_findings),
                "top_findings": sorted(
                    all_findings, key=lambda x: x["relevance_score"], reverse=True
                )[:20],
                "cross_referenced_opportunities": cross_ref,
                "queries_run": len(queries),
            }

            # Store results in analysis_whale_investors
            cursor = conn.cursor()
            cursor.execute("DELETE FROM analysis_whale_investors")
            cursor.execute(
                """INSERT INTO analysis_whale_investors
                   (analysis_type, insights_json, analyzed_at, record_count)
                   VALUES (%s, %s, %s, %s)""",
                (
                    "whale_investor_search",
                    json.dumps(insights, default=str),
                    datetime.now(timezone.utc).isoformat(),
                    len(all_findings),
                ),
            )
            conn.commit()
            cursor.close()

        finally:
            conn.close()

        _logger.info(
            "WhaleInvestorAgent: discovered=%d, validated=%d, findings=%d",
            discovered,
            validated,
            len(all_findings),
        )

        return AgentResult(
            agent_name=self.name,
            status="success" if not errors else "partial",
            data={
                "sources_discovered": discovered,
                "findings_validated": validated,
                "total_findings": len(all_findings),
                "cross_referenced": len(cross_ref),
                "queries_run": len(queries),
                "records_affected": len(all_findings),
                "top_insight": (
                    f"{len(all_findings)} whale investor findings, "
                    f"{sum(1 for f in all_findings if f.get('dollar_amounts'))} with dollar amounts, "
                    f"{len(cross_ref)} matched our opportunities"
                ),
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

            for match in re.finditer(
                r'class="result__a"\s+href="([^"]+)"', response.text
            ):
                url = match.group(1)
                if "uddg=" in url:
                    actual = url.split("uddg=")[-1].split("&")[0]
                    url = unquote(actual)
                if url.startswith("http") and "duckduckgo.com" not in url:
                    urls.append(url)
                if len(urls) >= max_results:
                    break

        except Exception as e:
            _logger.warning("Search request failed for '%s': %s", query[:40], e)

        return urls

    def _validate_url(
        self,
        url: str,
        timeout: int,
        min_length: int,
    ) -> tuple[str, str | None, float]:
        """Validate a URL and score its investor relevance.

        Returns (source_type, content_text, relevance_score).
        """
        import requests

        try:
            response = requests.head(
                url,
                timeout=timeout,
                allow_redirects=True,
                headers={"User-Agent": SEARCH_USER_AGENT},
            )
            content_type = response.headers.get("Content-Type", "")

            if "application/pdf" in content_type:
                source_type = "pdf"
            elif "text/html" in content_type:
                source_type = "html"
            elif "application/json" in content_type or "api" in url.lower():
                source_type = "api"
            else:
                source_type = "unknown"

            # Only fetch full content for HTML
            if source_type != "html":
                return source_type, None, 0.3

            response = requests.get(
                url, timeout=timeout, headers={"User-Agent": SEARCH_USER_AGENT}
            )
            content = response.text

            if len(content) < min_length:
                return source_type, content[:200], 0.1

            # Score based on investor + manufacturing keywords
            text_lower = content[:8000].lower()

            investor_matches = sum(1 for kw in INVESTOR_KEYWORDS if kw in text_lower)
            mfg_invest_matches = sum(
                1 for kw in MANUFACTURING_INVEST_KEYWORDS if kw in text_lower
            )

            investor_score = (
                min(investor_matches / max(len(INVESTOR_KEYWORDS) * 0.15, 1), 1.0) * 0.5
            )
            mfg_score = (
                min(
                    mfg_invest_matches
                    / max(len(MANUFACTURING_INVEST_KEYWORDS) * 0.15, 1),
                    1.0,
                )
                * 0.5
            )

            # Bonus for dollar amounts and specific investor names
            dollar_bonus = 0
            for pattern in DOLLAR_PATTERNS:
                if pattern.search(content[:5000]):
                    dollar_bonus += 0.1
                    break

            # Bonus for specific high-value signals
            signal_bonus = 0
            for signal in [
                "13f",
                "sec filing",
                "edgar",
                "holdings",
                "stake",
                "acquired",
                "portfolio",
                "fund size",
            ]:
                if signal in text_lower:
                    signal_bonus += 0.03
            signal_bonus = min(signal_bonus, 0.2)

            relevance = min(
                investor_score + mfg_score + dollar_bonus + signal_bonus, 1.0
            )

            return source_type, content[:3000], relevance

        except Exception:
            return "unknown", None, 0.0

    def _extract_investor_info(self, content: str) -> dict:
        """Extract investor-related information from page content.

        Returns dict with:
            dollar_amounts: list of (amount_text, numeric_value_billions)
            investor_names: list of potential investor names found
            sectors_mentioned: list of manufacturing sectors mentioned
        """
        info: dict = {
            "dollar_amounts": [],
            "investor_names": [],
            "sectors_mentioned": [],
        }

        text = content[:5000]

        # Extract dollar amounts
        for pattern in DOLLAR_PATTERNS:
            for match in pattern.finditer(text):
                amount_str = match.group(1).replace(",", "")
                unit = match.group(2).lower()
                try:
                    value = float(amount_str)
                    if unit in ("billion", "b"):
                        value_b = value
                    elif unit in ("million", "m"):
                        value_b = value / 1000
                    else:
                        value_b = 0
                    info["dollar_amounts"].append(
                        {
                            "text": match.group(0),
                            "value_billions": round(value_b, 3),
                        }
                    )
                except ValueError:
                    pass

        # Deduplicate dollar amounts
        seen_values = set()
        unique_amounts = []
        for da in info["dollar_amounts"]:
            key = da["value_billions"]
            if key not in seen_values:
                seen_values.add(key)
                unique_amounts.append(da)
        info["dollar_amounts"] = unique_amounts

        # Extract known investor firm names
        known_firms = [
            "Blackstone",
            "KKR",
            "Carlyle Group",
            "Apollo Global",
            "Bain Capital",
            "Goldman Sachs",
            "Morgan Stanley",
            "TPG",
            "Warburg Pincus",
            "General Atlantic",
            "Silver Lake",
            "Thoma Bravo",
            "Vista Equity",
            "GlobalFoundries",
            "TSMC",
            "Intel Capital",
            "CORE Industrial Partners",
            "SK Hynix",
            "SoftBank",
            "Vision Fund",
            "Temasek",
            "Mubadala",
            "PIF",
            "Public Investment Fund",
            "GIC",
            "CPPIB",
            "CDPQ",
        ]
        text_title = content[:5000]
        for firm in known_firms:
            if firm.lower() in text_title.lower():
                info["investor_names"].append(firm)

        # Extract manufacturing sectors mentioned
        text_lower = text.lower()
        for kw in MANUFACTURING_INVEST_KEYWORDS:
            if kw in text_lower:
                info["sectors_mentioned"].append(kw)

        # Deduplicate sectors
        info["sectors_mentioned"] = list(set(info["sectors_mentioned"]))

        return info

    def _cross_reference_opportunities(
        self,
        conn,
        findings: list[dict],
        mfg_keywords: list[str],
    ) -> list[dict]:
        """Cross-reference findings with opportunity pipeline results.

        Matches whale investor findings against our tracked opportunities
        to identify which revival sectors have institutional backing.

        An opportunity is considered "whale-backed" if its sector/industry
        appears in any finding that also names a known investor firm OR
        contains a dollar amount.
        """
        cross_ref = []

        # Load latest opportunity pipeline results
        cursor = conn.cursor()
        cursor.execute(
            """SELECT insights_json FROM analysis_opportunity_pipeline
               ORDER BY analyzed_at DESC LIMIT 1"""
        )
        opp_row = cursor.fetchone()
        cursor.close()

        if not opp_row:
            return cross_ref

        try:
            opp_data = json.loads(opp_row["insights_json"])
        except (json.JSONDecodeError, TypeError):
            return cross_ref

        opportunities = opp_data.get("opportunities", [])

        # Build a sector -> [findings] index
        sector_findings: dict[str, list[dict]] = {}
        for f in findings:
            for sector in f.get("sectors_mentioned", []):
                sector_lower = sector.lower()
                sector_findings.setdefault(sector_lower, []).append(f)

        # Build a list of all investor names found
        all_investors = set()
        for f in findings:
            for inv in f.get("investor_names", []):
                all_investors.add(inv)

        # Helper: get the industry/sector text from any opportunity type
        def opp_industries(opp: dict) -> str:
            parts = [
                opp.get("sub_sector") or "",
                opp.get("revival_industry") or "",
                opp.get("matching_industries") or "",
                opp.get("industry") or "",
                opp.get("region") or "",
                opp.get("startup") or "",
            ]
            return " ".join(p.lower() for p in parts if p)

        for opp in opportunities:
            opp_text = opp_industries(opp)
            opp_name = opp.get("startup") or opp.get("region", "unknown")

            # Find findings whose sector appears in this opportunity's industry text
            matched_sectors = []
            matched_findings = []
            matched_investors = []
            total_dollar_value = 0.0

            for sector, sector_fs in sector_findings.items():
                # Match if the sector keyword is in the opportunity text
                # (e.g., "battery" matches "Battery Cell Manufacturing")
                if sector in opp_text or any(
                    word in opp_text for word in sector.split()
                ):
                    matched_sectors.append(sector)
                    matched_findings.extend(sector_fs)
                    for f in sector_fs:
                        for inv in f.get("investor_names", []):
                            if inv not in matched_investors:
                                matched_investors.append(inv)
                        for da in f.get("dollar_amounts", []):
                            total_dollar_value += da.get("value_billions", 0)

            # Whale-backed = the matched findings either:
            #   (a) name a known investor, OR
            #   (b) reference dollar amounts (institutional-scale capital)
            whale_backed = bool(matched_investors) or total_dollar_value > 0

            if matched_sectors or matched_investors:
                cross_ref.append(
                    {
                        "opportunity": opp_name,
                        "opportunity_type": opp.get("type", "unknown"),
                        "opportunity_score": opp.get("opportunity_score", 0),
                        "matched_sectors": matched_sectors,
                        "matched_investors": matched_investors,
                        "matched_finding_count": len(matched_findings),
                        "total_dollar_value_billions": round(total_dollar_value, 2),
                        "whale_backed": whale_backed,
                    }
                )

        return cross_ref

    def _group_by_sector(self, findings: list[dict]) -> dict[str, int]:
        """Group findings by manufacturing sector mentioned."""
        sector_counts: dict[str, int] = {}
        for f in findings:
            for sector in f.get("sectors_mentioned", []):
                sector_counts[sector] = sector_counts.get(sector, 0) + 1
        return dict(sorted(sector_counts.items(), key=lambda x: x[1], reverse=True))
