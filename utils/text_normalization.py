"""Text normalization utilities for data from varied sources."""

import re
import logging

_logger = logging.getLogger(__name__)

# Mapping of common funding text patterns to multipliers
_FUNDING_MULTIPLIERS = {
    "B": 1_000_000_000,
    "Billion": 1_000_000_000,
    "M": 1_000_000,
    "Million": 1_000_000,
    "K": 1_000,
    "Thousand": 1_000,
}

# Country name normalization
_COUNTRY_MAP = {
    "usa": "US",
    "united states": "US",
    "u.s.": "US",
    "u.s.a": "US",
    "united kingdom": "UK",
    "uk": "UK",
    "great britain": "UK",
    "england": "UK",
    "india": "India",
    "china": "China",
    "prc": "China",
    "germany": "Germany",
    "deutschland": "Germany",
    "france": "France",
    "sweden": "Sweden",
    "spain": "Spain",
    "turkey": "Turkey",
    "singapore": "Singapore",
    "japan": "Japan",
    "south korea": "South Korea",
    "brazil": "Brazil",
    "nigeria": "Nigeria",
    "kenya": "Kenya",
    "south africa": "South Africa",
    "mexico": "Mexico",
    "canada": "Canada",
    "australia": "Australia",
    "israel": "Israel",
    "netherlands": "Netherlands",
    "switzerland": "Switzerland",
}

# Country to region mapping
_REGION_MAP = {
    "US": "US & Global",
    "Canada": "US & Global",
    "Israel": "US & Global",
    "India": "India",
    "China": "China",
    "Hong Kong": "China",
    "Germany": "Europe",
    "UK": "Europe",
    "France": "Europe",
    "Sweden": "Europe",
    "Spain": "Europe",
    "Turkey": "Europe",
    "Netherlands": "Europe",
    "Switzerland": "Europe",
    "Italy": "Europe",
    "Ireland": "Europe",
    "Finland": "Europe",
    "Norway": "Europe",
    "Denmark": "Europe",
    "Poland": "Europe",
    "Estonia": "Europe",
    "Belgium": "Europe",
    "Austria": "Europe",
    "Nigeria": "Africa",
    "Kenya": "Africa",
    "South Africa": "Africa",
    "Ghana": "Africa",
    "Egypt": "Africa",
    "Tanzania": "Africa",
    "Uganda": "Africa",
    "Rwanda": "Africa",
    "Senegal": "Africa",
    "Singapore": "Asia-Pacific",
    "Japan": "Asia-Pacific",
    "South Korea": "Asia-Pacific",
    "Australia": "Asia-Pacific",
    "Indonesia": "Asia-Pacific",
    "Vietnam": "Asia-Pacific",
    "Brazil": "Latin America",
    "Mexico": "Latin America",
    "Argentina": "Latin America",
    "Colombia": "Latin America",
    "Chile": "Latin America",
}

# Failure cause normalization
_FAILURE_CATEGORY_MAP = {
    "ran out of cash": "ran_out_of_cash",
    "no market need": "no_market_need",
    "poor product": "poor_product",
    "got outcompeted": "outcompeted",
    "pricing issues": "pricing_cost",
    "pricing/cost issues": "pricing_cost",
    "no business model": "no_business_model",
    "team issues": "not_right_team",
    "bad marketing": "ineffective_marketing",
    "ignored customers": "ignored_customer_needs",
    "production delays": "capital_intensity",
    "capital intensity": "capital_intensity",
    "supply chain": "supply_chain",
    "supply chain issues": "supply_chain",
    "pilot to scale": "pilot_to_scale_gap",
    "could not scale": "pilot_to_scale_gap",
    "spac overvaluation": "spac_overvaluation",
    "market timing": "market_timing",
    "financial mismanagement": "governance",
    "governance issues": "governance",
    "regulatory": "regulatory",
    "covid": "supply_chain",
    "pandemic": "supply_chain",
    "contract manufacturing": "pilot_to_scale_gap",
    "poor quality": "poor_product",
    "unit economics": "ran_out_of_cash",
}


def normalize_funding(text: str | None) -> float | None:
    """Convert funding text like '$5.4B+', '~$300M' to numeric USD value.

    Returns None if text is None, empty, 'undisclosed', or unparseable.
    """
    if not text or text.strip().lower() in ("undisclosed", "unknown", "n/a", "tbd"):
        return None

    text = text.strip()
    # Remove common prefixes/suffixes
    text = text.replace(",", "").replace("~", "").replace("≈", "").replace("+", "")
    text = text.replace("USD", "").replace("$", "").strip()

    if not text:
        return None

    # Try to match number + suffix
    match = re.match(r"([\d.]+)\s*([BMK]?)(?:illion)?", text, re.IGNORECASE)
    if match:
        number = float(match.group(1))
        suffix = match.group(2).upper()
        multiplier = _FUNDING_MULTIPLIERS.get(suffix, 1)
        return number * multiplier

    # Try plain number
    try:
        return float(text)
    except ValueError:
        _logger.debug("Could not parse funding: '%s'", text)
        return None


def normalize_country(text: str | None) -> str:
    """Normalize country text to a standard short form."""
    if not text:
        return "Unknown"
    return _COUNTRY_MAP.get(text.strip().lower(), text.strip())


def get_region(country: str) -> str:
    """Map a country name to its report region."""
    return _REGION_MAP.get(country, "Other")


def normalize_failure_category(text: str | None, source: str = "general") -> str | None:
    """Normalize a failure reason text to a standardized category.

    Returns None if no match is found.
    """
    if not text:
        return None

    text_lower = text.strip().lower()
    for pattern, category in _FAILURE_CATEGORY_MAP.items():
        if pattern in text_lower:
            return category

    return None
