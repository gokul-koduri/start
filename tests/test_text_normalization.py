"""Tests for text normalization utilities."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.text_normalization import (
    normalize_funding,
    normalize_country,
    get_region,
    normalize_failure_category,
)


# ── normalize_funding ──────────────────────────────────────────────

class TestNormalizeFunding:
    def test_dollar_millions(self):
        assert normalize_funding("$500M") == 500_000_000

    def test_dollar_billions(self):
        assert normalize_funding("$2.5B") == 2_500_000_000

    def test_dollar_thousands(self):
        assert normalize_funding("$500K") == 500_000

    def test_plain_number(self):
        assert normalize_funding("15000000") == 15_000_000

    def test_millions_text(self):
        result = normalize_funding("$100 million")
        assert result == 100_000_000

    def test_none_input(self):
        assert normalize_funding(None) is None

    def test_empty_string(self):
        assert normalize_funding("") is None

    def test_dash(self):
        assert normalize_funding("-") is None

    def test_na(self):
        assert normalize_funding("N/A") is None


# ── normalize_country ──────────────────────────────────────────────

class TestNormalizeCountry:
    def test_usa(self):
        assert normalize_country("United States") == "US"

    def test_us(self):
        assert normalize_country("US") == "US"

    def test_uk(self):
        assert normalize_country("United Kingdom") == "UK"

    def test_germany(self):
        assert normalize_country("Germany") == "Germany"

    def test_none(self):
        result = normalize_country(None)
        assert result is None or result == "Unknown"

    def test_empty(self):
        result = normalize_country("")
        assert result is None or result == "Unknown"


# ── get_region ─────────────────────────────────────────────────────

class TestGetRegion:
    def test_us_is_global(self):
        assert get_region("US") == "US & Global"

    def test_germany_is_europe(self):
        assert get_region("Germany") == "Europe"

    def test_india(self):
        # India maps to itself if not in the explicit region map
        result = get_region("India")
        assert result is not None

    def test_none(self):
        result = get_region(None)
        assert result is not None  # should return a default


# ── normalize_failure_category ─────────────────────────────────────

class TestNormalizeFailureCategory:
    def test_ran_out_of_cash(self):
        assert normalize_failure_category("Ran out of cash") == "ran_out_of_cash"

    def test_no_market_need(self):
        assert normalize_failure_category("No market need") == "no_market_need"

    def test_none(self):
        # None input should return None or a default
        result = normalize_failure_category(None)
        # Accept either None or a default string
        assert result is None or isinstance(result, str)

    def test_empty(self):
        result = normalize_failure_category("")
        assert result is None or isinstance(result, str)
