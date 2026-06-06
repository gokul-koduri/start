"""Tests for data collection and parsing logic."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Mock all DB/MySQL dependencies before importing collectors ──
mock_pymysql = MagicMock()
sys.modules['pymysql'] = mock_pymysql
sys.modules['pymysql.cursors'] = mock_pymysql.cursors

# Save originals so we don't poison other test modules
_saved_db_modules = {
    key: sys.modules.pop(key, None)
    for key in ("db", "db.connection", "db.schema", "db.dedup")
}

# Mock db modules that try to connect to MySQL
mock_db_conn = MagicMock()
sys.modules['db'] = MagicMock()
sys.modules['db.connection'] = MagicMock()
sys.modules['db.connection'].get_connection = MagicMock()
sys.modules['db.dedup'] = MagicMock()
sys.modules['db.dedup'].dedup_startup = MagicMock(return_value=False)
sys.modules['db.schema'] = MagicMock()

from collectors.failory_scraper import FailoryScraper
from bs4 import BeautifulSoup

# Restore real db modules so other tests aren't poisoned
for key, orig in _saved_db_modules.items():
    if orig is not None:
        sys.modules[key] = orig
    else:
        sys.modules.pop(key, None)


class TestFailoryScraper:
    def test_name(self):
        scraper = FailoryScraper(config={"scraping": {"failory": {}}})
        assert scraper.name == "failory_scraper"

    def test_parse_profile_name_from_h1(self):
        html = """
        <html><body>
        <h1>TestCompany</h1>
        <p>Category: Fintech</p>
        <p>Country: United States</p>
        <p>Cause: Ran out of money</p>
        <p>Total Funding Amount: $100M</p>
        <p>Started: 2019</p>
        <p>Closed: 2024</p>
        </body></html>
        """
        soup = BeautifulSoup(html, "lxml")
        scraper = FailoryScraper(config={"scraping": {"failory": {}}})
        profile = scraper._parse_profile(soup, "https://example.com/test")

        assert profile is not None
        assert profile["name"] == "TestCompany"
        assert profile["industry"] == "Fintech"
        assert profile["country"] == "United States"
        assert profile["year_founded"] == 2019
        assert profile["year_failed"] == 2024

    def test_parse_profile_empty_html(self):
        html = "<html><body></body></html>"
        soup = BeautifulSoup(html, "lxml")
        scraper = FailoryScraper(config={"scraping": {"failory": {}}})
        profile = scraper._parse_profile(soup, "https://example.com/empty")
        assert profile is None

    def test_parse_profile_manufacturing_detection(self):
        html = """
        <html><body>
        <h1>RoboFactory</h1>
        <p>Category: Robotics</p>
        <p>Country: Germany</p>
        <p>Cause: Pilot could not scale</p>
        <p>Total Funding Amount: $50M</p>
        <p>Started: 2020</p>
        <p>Closed: 2024</p>
        </body></html>
        """
        soup = BeautifulSoup(html, "lxml")
        scraper = FailoryScraper(config={"scraping": {"failory": {}}})
        profile = scraper._parse_profile(soup, "https://example.com/robofactory")

        assert profile is not None
        assert profile["name"] == "RoboFactory"
        assert profile.get("manufacturing_sub_sector") is not None

    def test_extract_field_with_multiple_labels(self):
        scraper = FailoryScraper(config={"scraping": {"failory": {}}})
        text = "Industry: HealthTech\nSome other text"
        result = scraper._extract_field(text, ["Category:", "Industry:", "Sector:"])
        assert result == "HealthTech"

    def test_extract_field_not_found(self):
        scraper = FailoryScraper(config={"scraping": {"failory": {}}})
        text = "Some text without the label"
        result = scraper._extract_field(text, ["Category:", "Industry:"])
        assert result is None

    def test_extract_field_dash_value(self):
        scraper = FailoryScraper(config={"scraping": {"failory": {}}})
        text = "Total Funding Amount: -"
        result = scraper._extract_field(text, ["Total Funding Amount:"])
        assert result is None
