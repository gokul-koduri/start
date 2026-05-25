"""Failory.com scraper for structured startup failure profiles."""

import sqlite3
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

    def collect(self, conn: sqlite3.Connection) -> CollectionResult:
        result = CollectionResult(collector_name=self.name)

        scrape_config = self.config.get("scraping", {}).get("failory", {})
        base_url = scrape_config.get("base_url", "https://failory.com")
        failures_path = scrape_config.get("failures_path", "/failures")
        max_pages = scrape_config.get("max_pages", 20)
        delay = scrape_config.get("request_delay_seconds", 3)
        user_agent = scrape_config.get("user_agent", "StartupResearchBot/1.0")

        session = get_http_session(user_agent=user_agent)

        # Step 1: Get list of failure profile URLs
        profile_urls = self._get_profile_urls(session, base_url, failures_path, max_pages, result)

        if not profile_urls:
            result.errors.append("No profile URLs found on Failory")
            result.status = "partial"
            return result

        _logger.info("Found %d Failory profiles to scrape", len(profile_urls))

        # Step 2: Filter out already-visited
        new_urls = []
        for url in profile_urls:
            existing = conn.execute(
                "SELECT 1 FROM failed_startups WHERE source_url = ?", (url,)
            ).fetchone()
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
                conn.execute(
                    """INSERT OR IGNORE INTO failed_startups
                       (name, sector, manufacturing_sub_sector, country, region,
                        funding_raised_usd, funding_description, year_founded,
                        year_shutdown, failure_reason, failure_category,
                        notable, source, source_url)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                conn.commit()

            result.records_collected += 1
            result.records_inserted += 1

        if result.errors and result.records_inserted == 0:
            result.status = "failed"
        elif result.errors:
            result.status = "partial"

        return result

    def _get_profile_urls(self, session, base_url, failures_path, max_pages, result):
        """Scrape the failures list page to get individual profile URLs."""
        urls = []
        url = f"{base_url}{failures_path}"

        for page in range(1, max_pages + 1):
            if page > 1:
                page_url = f"{url}?page={page}"
            else:
                page_url = url

            try:
                resp = session.get(page_url, timeout=15)
                if resp.status_code == 429:
                    result.errors.append("Rate limited on list page")
                    break
                resp.raise_for_status()
            except Exception as e:
                result.errors.append(f"Failed to fetch list page {page}: {e}")
                break

            soup = BeautifulSoup(resp.text, "lxml")

            # Find profile links
            links = soup.select("a[href*='/company/']")
            found_on_page = 0
            for link in links:
                href = link.get("href", "")
                full_url = urljoin(base_url, href)
                if full_url not in urls and "/company/" in full_url:
                    urls.append(full_url)
                    found_on_page += 1

            _logger.debug("Page %d: found %d profile links", page, found_on_page)

            if found_on_page == 0:
                _logger.info("No more profiles found on page %d, stopping", page)
                break

            time.sleep(2)

        return urls

    def _parse_profile(self, soup, url):
        """Parse a Failory company profile page."""
        profile = {}

        # Company name from title or h1
        h1 = soup.find("h1")
        if h1:
            profile["name"] = h1.get_text(strip=True)
        else:
            title = soup.find("title")
            if title:
                name = title.get_text(strip=True).split(" - ")[0].split(" | ")[0]
                profile["name"] = name

        # Try to extract structured data from info sections
        # Failory uses labeled fields in their profiles
        info_section = soup.find("div", class_="company-info") or soup

        # Extract all text content for keyword searching
        all_text = soup.get_text(separator="\n")

        # Look for industry
        profile["industry"] = self._extract_field(all_text, [
            "Industry:", "Sector:", "Category:",
        ])

        # Look for failure cause
        failure_reason = self._extract_field(all_text, [
            "Failure Cause:", "Reason for failure:", "Why it failed:",
            "Cause of Failure:", "Main Reason:",
        ])
        profile["failure_reason"] = failure_reason
        profile["failure_category"] = normalize_failure_category(failure_reason)

        # Look for funding
        funding_text = self._extract_field(all_text, [
            "Funding:", "Total Funding:", "Raised:", "Investment:",
        ])
        profile["funding_description"] = funding_text
        profile["funding_usd"] = normalize_funding(funding_text)

        # Look for founded year
        year_text = self._extract_field(all_text, [
            "Founded:", "Year Founded:", "Started:",
        ])
        if year_text:
            import re
            match = re.search(r"\d{4}", year_text)
            if match:
                profile["year_founded"] = int(match.group())

        # Look for failure year
        fail_text = self._extract_field(all_text, [
            "Failed:", "Year Failed:", "Closed:", "Shut Down:",
        ])
        if fail_text:
            match = re.search(r"\d{4}", fail_text)
            if match:
                profile["year_failed"] = int(match.group())

        # Look for country
        profile["country"] = self._extract_field(all_text, [
            "Country:", "Location:", "HQ:",
        ])

        # Look for business model
        profile["business_model"] = self._extract_field(all_text, [
            "Business Model:", "Model:",
        ])

        # Check if manufacturing
        all_text_lower = all_text.lower()
        mfg_terms = ["manufacturing", "factory", "production", "hardware", "3d printing",
                     "robotics", "battery", "semiconductor", "fabrication", "assembly"]
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
