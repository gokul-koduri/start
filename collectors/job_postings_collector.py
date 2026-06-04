"""Job postings collector — detects hiring signals from job board RSS feeds.

Hiring spikes are strong leading indicators of company growth:
  - A startup hiring 5+ engineers in a week suggests a growth round
  - New roles in AI/ML indicate technology pivots
  - Senior VP hires suggest organizational scaling
  - Remote-first postings indicate modern company culture

Data sources: LinkedIn RSS feeds, Indeed RSS, generic job board searches
Rate limits: Respect each source's robots.txt and rate limits
"""

import logging
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus

import feedparser

from collectors.base import BaseCollector, CollectionResult
from db.dedup import dedup_news_article
from utils.http_client import get_http_session

_logger = logging.getLogger(__name__)

# Job board RSS endpoints (public)
_JOB_SOURCES = {
    "indeed": {
        "base_url": "https://www.indeed.com/rss",
        "default_query": "startup OR SaaS OR fintech OR AI OR machine learning",
    },
}

# Skills extraction patterns
_TECH_SKILLS = re.compile(
    r"\b(python|java|javascript|typescript|react|node|aws|gcp|azure|"
    r"kubernetes|docker|machine.?learning|deep.?learning|nlp|"
    r"sql|nosql|tensorflow|pytorch|spark|kafka|scala|go|rust|"
    r"terraform|devops|sre|ml.?engineer|data.?scientist|"
    r"product.?manager|full.?stack|backend|frontend|api)\b",
    re.IGNORECASE,
)


class JobPostingsCollector(BaseCollector):
    """Collects job postings to detect hiring signals and growth indicators."""

    @property
    def name(self) -> str:
        return "job_postings"

    def collect(self, conn) -> CollectionResult:
        result = CollectionResult(collector_name=self.name)
        job_config = self.config.get("job_postings", {})
        sources = job_config.get("sources", ["indeed"])
        queries = job_config.get("queries", [])

        if not queries:
            queries = [
                {
                    "query": "senior engineer startup",
                    "location": "remote",
                },
                {
                    "query": "VP growth startup SaaS",
                    "location": "",
                },
                {
                    "query": "machine learning engineer AI",
                    "location": "remote",
                },
            ]

        session = get_http_session()

        last_run = self.get_last_run_time(conn)
        since_date = last_run - timedelta(hours=1) if last_run else datetime.now(timezone.utc) - timedelta(days=3)

        cursor = conn.cursor()
        company_counts: dict[str, int] = {}  # Track per-company posting counts

        for source_name in sources:
            source_config = _JOB_SOURCES.get(source_name, {})
            base_url = source_config.get("base_url", "")

            if not base_url:
                continue

            for query_config in queries:
                query = query_config.get("query", "")
                location = query_config.get("location", "")

                params = {
                    "q": query,
                    "l": location,
                }

                url = f"{base_url}?{quote_plus(str(params))}"
                url = f"{base_url}?q={quote_plus(query)}"
                if location:
                    url += f"&l={quote_plus(location)}"

                try:
                    resp = session.get(url, timeout=20)
                    resp.raise_for_status()
                except Exception as e:
                    result.errors.append(f"Job feed fetch failed ({source_name}): {e}")
                    continue

                feed = feedparser.parse(resp.text)
                if feed.bozo and not feed.entries:
                    continue

                for entry in feed.entries:
                    try:
                        title = entry.get("title", "")
                        link = entry.get("link", "")
                        published = entry.get("published", "")
                        summary = entry.get("summary", "")

                        if not link or not title:
                            continue

                        if published:
                            try:
                                pub_date = datetime.strptime(
                                    published, "%a, %d %b %Y %H:%M:%S %z"
                                )
                                if pub_date < since_date:
                                    result.records_skipped += 1
                                    continue
                            except ValueError:
                                pass

                        if dedup_news_article(conn, link):
                            result.records_skipped += 1
                            continue

                        # Extract company name (usually in title)
                        company_name = self._extract_company(title)
                        job_title = title.replace(company_name, "").strip() if company_name else title

                        # Extract skills
                        text = f"{title} {summary}"
                        skills = list(set(m.group(0).lower() for m in _TECH_SKILLS.finditer(text)))

                        cursor.execute(
                            """INSERT IGNORE INTO job_postings
                               (company_name, job_title, location, job_type,
                                skills_json, source_site, posted_date, collected_at)
                               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                            (
                                company_name or "Unknown",
                                job_title[:255],
                                location,
                                "remote" if "remote" in text.lower() else None,
                                ",".join(skills) if skills else None,
                                source_name,
                                published[:10] if published else None,
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
                                "job_posting_spike",
                                f"job_postings_{source_name}",
                                link,
                                title,
                                summary[:5000] if summary else None,
                                company_name or "Unknown",
                                published[:26] if published else None,
                                datetime.now(timezone.utc).isoformat(),
                            ),
                        )

                        # Track company counts for spike detection
                        if company_name:
                            company_counts[company_name] = company_counts.get(company_name, 0) + 1

                        result.records_inserted += 1
                        result.records_collected += 1

                    except Exception as e:
                        result.errors.append(f"Error processing job entry: {e}")

        cursor.close()
        conn.commit()

        # Log hiring spike detections
        for company, count in sorted(company_counts.items(), key=lambda x: -x[1]):
            if count >= 3:
                _logger.info(
                    "🎯 HIRING SPIKE: %s has %d new postings (potential growth signal)",
                    company, count,
                )

        result.status = "success" if result.records_inserted > 0 else "partial"
        return result

    def _extract_company(self, title: str) -> str:
        """Extract company name from job posting title.

        Common patterns: "Company Name - Job Title" or "Job Title at Company"
        """
        # Pattern: "Company Name - Job Title"
        if " - " in title:
            return title.split(" - ")[0].strip()
        # Pattern: "Job Title at Company"
        match = re.search(r"\bat\s+(.+?)$", title, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return title[:50].strip()
