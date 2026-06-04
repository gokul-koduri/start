"""Configurable signal weights and decay parameters for the composite scoring engine.

Each signal type has:
  - weight: relative importance (higher = more impact on composite score)
  - decay_lambda: controls how fast the signal fades (lower = slower decay)

Decay half-life reference (formula: half_life_hours = ln(2) / lambda):
  - 0.000079 lambda → ~1 year half-life (enduring signals like patents, funding)
  - 0.000158 lambda → ~6 month half-life (SEC filings)
  - 0.000481 lambda → ~2 month half-life (news mentions, hiring spikes)
  - 0.000963 lambda → ~1 month half-life (GitHub trends)
  - 0.002063 lambda → ~2 week half-life (social buzz)
  - 0.004125 lambda → ~1 week half-life (website changes)
"""

from __future__ import annotations

from typing import TypedDict


class SignalWeightConfig(TypedDict):
    """Configuration for a single signal type."""

    weight: float
    decay_lambda: float
    label: str
    category: str  # "primary" | "secondary" | "tertiary"


# Default signal weights — override via config/settings.yaml
SIGNAL_WEIGHTS: dict[str, SignalWeightConfig] = {
    # ── Primary signals (high confidence, low noise) ──
    "funding_round": {
        "weight": 25.0,
        "decay_lambda": 0.000079,  # ~1 year half-life
        "label": "Funding Round",
        "category": "primary",
    },
    "sec_filing": {
        "weight": 20.0,
        "decay_lambda": 0.000158,  # ~6 month half-life
        "label": "SEC Filing",
        "category": "primary",
    },
    "job_posting_spike": {
        "weight": 15.0,
        "decay_lambda": 0.000481,  # ~2 month half-life
        "label": "Hiring Spike",
        "category": "primary",
    },
    "patent_filed": {
        "weight": 12.0,
        "decay_lambda": 0.000079,  # ~1 year half-life
        "label": "Patent Filed",
        "category": "primary",
    },
    # ── Secondary signals (trending, moderate confidence) ──
    "github_trend": {
        "weight": 10.0,
        "decay_lambda": 0.000963,  # ~1 month half-life
        "label": "GitHub Trend",
        "category": "secondary",
    },
    "news_mention": {
        "weight": 10.0,
        "decay_lambda": 0.000481,  # ~2 month half-life
        "label": "News Mention",
        "category": "secondary",
    },
    # ── Tertiary signals (ephemeral, low individual weight) ──
    "social_buzz": {
        "weight": 5.0,
        "decay_lambda": 0.002063,  # ~2 week half-life
        "label": "Social Buzz",
        "category": "tertiary",
    },
    "website_change": {
        "weight": 3.0,
        "decay_lambda": 0.004125,  # ~1 week half-life
        "label": "Website Change",
        "category": "tertiary",
    },
}

# Anomaly detection thresholds
ANOMALY_Z_THRESHOLD = 2.0  # Flag as anomaly if |z| > this
ANOMALY_BOOST_FACTOR = 1.5  # Multiplier for anomaly-boosted scores
ANOMALY_WINDOW = 30  # Rolling window for Z-score calculation (days)
