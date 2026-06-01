"""Failory.com scraper for structured startup failure profiles."""

import logging
import re
import time
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from collectors.base import BaseCollector, CollectionResult
from utils.http_client import get_http_session
from utils.text_normalization import (
    normalize_funding, normalize_country, get_region,
    normalize_failure_category,
)
from db.dedup import dedup_startup

_logger = logging.getLogger(__name__)


class FailoryScraper(BaseCollector):
    """Scrapes Failory.com for structured failed startup profiles."""

    @property
    def name(self) -> str:
        return "failory_scraper"

    def collect(self, conn) -> CollectionResult:
        result = CollectionResult(collector_name=self.name)

        scrape_config = self.config.get("scraping", {}).get("failory", {})
        base_url = scrape_config.get("base_url", "https://www.failory.com")
        failures_path = scrape_config.get("failures_path", "/failures")
        max_profiles = scrape_config.get("max_profiles", 100)
        delay = scrape_config.get("request_delay_seconds", 3)
        user_agent = scrape_config.get("user_agent", "StartupResearchBot/1.0")
        category_pages = scrape_config.get("category_pages", [])

        session = get_http_session(user_agent=user_agent)

        # Step 1: Get list of profile URLs from category pages
        profile_urls = self._get_profile_urls(
            session, base_url, failures_path, category_pages, max_profiles, result
        )

        if not profile_urls:
            result.errors.append("No profile URLs found on Failory")
            result.status = "partial"
            return result

        _logger.info("Found %d Failory profiles to scrape", len(profile_urls))

        # Step 2: Filter out already-visited
        new_urls = []
        for url in profile_urls:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM failed_startups WHERE source_url = %s", (url,)
            )
            existing = cursor.fetchone()
            cursor.close()
            if not existing:
                new_urls.append(url)
            else:
                result.records_skipped += 1

        _logger.info("After dedup: %d new profiles to scrape", len(new_urls))

        # Step 3: Scrape each profile
        for i, url in enumerate(new_urls):
            _logger.debug("Scraping Failory profile %d/%d: %s", i + 1, len(new_urls), url)

            time.sleep(delay)

            try:
                resp = session.get(url, timeout=15)
                if resp.status_code == 429:
                    result.errors.append(f"Rate limited at {url}")
                    result.status = "partial"
                    break
                resp.raise_for_status()
            except Exception as e:
                result.errors.append(f"Failed to fetch {url}: {e}")
                continue

            soup = BeautifulSoup(resp.text, "lxml")
            profile = self._parse_profile(soup, url)

            if not profile or not profile.get("name"):
                result.records_skipped += 1
                continue

            # Normalize
            country = normalize_country(profile.get("country"))
            region = get_region(country)

            # Check dedup by (name, region)
            if dedup_startup(conn, profile["name"], region):
                result.records_skipped += 1
                continue

            if not self.dry_run:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT IGNORE INTO failed_startups
                       (name, sector, manufacturing_sub_sector, country, region,
                        funding_raised_usd, funding_description, year_founded,
                        year_shutdown, failure_reason, failure_category,
                        notable, source, source_url)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        profile["name"],
                        profile.get("industry"),
                        profile.get("manufacturing_sub_sector"),
                        country,
                        region,
                        profile.get("funding_usd"),
                        profile.get("funding_description"),
                        profile.get("year_founded"),
                        profile.get("year_failed") or 2024,
                        profile.get("failure_reason") or "Unknown",
                        profile.get("failure_category"),
                        0,  # Not marked as notable by default
                        "failory",
                        url,
                    ),
                )
                cursor.close()
                conn.commit()

            result.records_collected += 1
            result.records_inserted += 1

        if result.errors and result.records_inserted == 0:
            result.status = "failed"
        elif result.errors:
            result.status = "partial"

        return result

    def _get_profile_urls(self, session, base_url, failures_path,
                          category_pages, max_profiles, result):
        """Discover profile URLs from Failory's category pages.

        Failory uses /startups/[category]-failures as list pages with
        /cemetery/[name] links to individual startup profiles.
        """
        urls = []
        seen = set()

        # Pages to crawl: configured category pages + main failures page
        pages_to_crawl = []
        if category_pages:
            pages_to_crawl.extend(category_pages)
        pages_to_crawl.append(failures_path)

        for page_path in pages_to_crawl:
            page_url = urljoin(base_url, page_path)
            _logger.info("Discovering profiles from: %s", page_url)

            try:
                resp = session.get(page_url, timeout=15)
                if resp.status_code == 429:
                    result.errors.append(f"Rate limited on {page_url}")
                    break
                resp.raise_for_status()
            except Exception as e:
                result.errors.append(f"Failed to fetch {page_url}: {e}")
                continue

            soup = BeautifulSoup(resp.text, "lxml")

            # Find /cemetery/ links — these are individual startup profiles
            links = soup.select("a[href*='/cemetery/']")
            found = 0
            for link in links:
                href = link.get("href", "")
                if href in seen:
                    continue
                full_url = urljoin(base_url, href)
                if full_url not in urls:
                    urls.append(full_url)
                    seen.add(href)
                    found += 1
                    if len(urls) >= max_profiles:
                        break

            _logger.info("  Found %d profiles on %s (total: %d)",
                         found, page_path, len(urls))

            if len(urls) >= max_profiles:
                break

            time.sleep(2)

        return urls

    def _parse_profile(self, soup, url):
        """Parse a Failory /cemetery/ profile page.

        Failory profiles have labeled fields like:
          Category: Finances
          Country: India
          Started: 2017
          Cause: Legal Challenges
          Closed: 2019
          Total Funding Amount: -
        """
        profile = {}

        # Company name: h1 tag contains the name
        h1 = soup.find("h1")
        if h1:
            profile["name"] = h1.get_text(strip=True)
        else:
            title = soup.find("title")
            if title:
                # Title format: "What Happened to [Name]?"
                text = title.get_text(strip=True)
                for prefix in ["What Happened to ", "What happened to "]:
                    if text.startswith(prefix):
                        name = text[len(prefix):].split(",")[0].split("?")[0].strip()
                        if name:
                            profile["name"] = name
                            break
                if not profile.get("name"):
                    profile["name"] = text.split(" - ")[0].split("|")[0].strip()

        if not profile.get("name"):
            return None

        # Extract all text for field searching
        all_text = soup.get_text(separator="\n")

        # Category / Industry
        profile["industry"] = self._extract_field(all_text, [
            "Category:", "Industry:", "Sector:",
        ])

        # Country
        profile["country"] = self._extract_field(all_text, [
            "Country:", "Location:", "HQ:",
        ])

        # Failure cause
        failure_reason = self._extract_field(all_text, [
            "Cause:", "Failure Cause:", "Reason for failure:",
            "Why it failed:", "Cause of Failure:",
        ])
        profile["failure_reason"] = failure_reason
        profile["failure_category"] = normalize_failure_category(failure_reason)

        # Funding
        funding_text = self._extract_field(all_text, [
            "Total Funding Amount:", "Total Funding:", "Funding:",
            "Raised:", "Investment:",
        ])
        if funding_text and funding_text not in ("-", "N/A", "Unknown", ""):
            profile["funding_description"] = funding_text
            profile["funding_usd"] = normalize_funding(funding_text)
        else:
            profile["funding_description"] = None
            profile["funding_usd"] = None

        # Year founded
        year_text = self._extract_field(all_text, [
            "Started:", "Founded:", "Year Founded:",
        ])
        if year_text:
            match = re.search(r"\d{4}", year_text)
            if match:
                profile["year_founded"] = int(match.group())

        # Year failed/closed
        fail_text = self._extract_field(all_text, [
            "Closed:", "Failed:", "Shut Down:", "Outcome:",
        ])
        if fail_text:
            match = re.search(r"\d{4}", fail_text)
            if match:
                profile["year_failed"] = int(match.group())

        # Check for manufacturing connection
        all_text_lower = all_text.lower()
        mfg_terms = ["manufacturing", "factory", "production", "hardware",
                     "3d printing", "robotics", "battery", "semiconductor",
                     "fabrication", "assembly", "automotive", "ev "]
        if any(t in all_text_lower for t in mfg_terms):
            profile["manufacturing_sub_sector"] = profile.get("industry", "Manufacturing")

        return profile

    def _extract_field(self, text, labels):
        """Extract a field value given a list of possible label patterns."""
        for label in labels:
            pattern = re.compile(re.escape(label) + r"\s*(.+?)(?:\n|$)", re.IGNORECASE)
            match = pattern.search(text)
            if match:
                value = match.group(1).strip()
                if value and value not in ("N/A", "-", "", "Unknown"):
                    return value
        return None
