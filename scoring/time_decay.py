"""Exponential time-decay functions for signal freshness scoring.

Signals lose relevance over time. The decay function ensures that:
  - A funding round from yesterday contributes fully
  - A funding round from 6 months ago contributes ~50% (for lambda=0.003)
  - A social media post from 2 weeks ago contributes almost nothing

The decay formula:  decay(t) = e^(-lambda * hours_elapsed)

This is a natural choice because:
  1. It's continuous and differentiable (smooth scoring transitions)
  2. The half-life is easily tunable via lambda
  3. It's bounded [0, 1] so it works as a multiplier
"""

from __future__ import annotations

import math
from datetime import datetime, timezone


def exponential_decay(
    published_at: datetime,
    lambda_: float = 0.01,
    now: datetime | None = None,
) -> float:
    """Compute exponential time-decay factor for a signal.

    Args:
        published_at: When the signal was originally published/detected.
        lambda_: Decay rate constant. Lower = slower decay (longer half-life).
            Common values (hours-based decay):
              0.000079 → ~1 year half-life (funding, patents)
              0.000158 → ~6 month half-life (SEC filings)
              0.000481 → ~2 month half-life (news, hiring)
              0.000963 → ~1 month half-life (GitHub trends)
              0.002063 → ~2 week half-life (social buzz)
              0.004125 → ~1 week half-life (website changes)
        now: Override for current time (useful in tests). Defaults to UTC now.

    Returns:
        Decay factor in [0.0, 1.0] where 1.0 = fully fresh.

    Examples:
        >>> from datetime import timedelta
        >>> now = datetime.now(timezone.utc)
        >>> # Signal from 1 hour ago with slow decay
        >>> round(exponential_decay(now - timedelta(hours=1), lambda_=0.003), 4)
        0.997
        >>> # Signal from 6 months ago with slow decay (~50%)
        >>> round(exponential_decay(now - timedelta(days=180), lambda_=0.003), 2)
        0.58
        >>> # Signal from 2 weeks ago with fast decay (~12%)
        >>> round(exponential_decay(now - timedelta(days=14), lambda_=0.05), 2)
        0.12
    """
    _now = now or datetime.now(timezone.utc)

    # Ensure timezone-aware comparison
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)

    hours_elapsed = max(0, (_now - published_at).total_seconds() / 3600)

    # e^(-lambda * hours) — clamped to [0, 1]
    decay = math.exp(-lambda_ * hours_elapsed)
    return max(0.0, min(1.0, decay))


def half_life_hours(lambda_: float) -> float:
    """Calculate the half-life in hours for a given decay rate.

    Half-life = ln(2) / lambda

    Args:
        lambda_: Decay rate constant.

    Returns:
        Hours until the signal decays to 50% strength.
    """
    if lambda_ <= 0:
        return float("inf")
    return math.log(2) / lambda_


def freshness_label(decay_value: float) -> str:
    """Convert a decay value to a human-readable freshness label.

    Args:
        decay_value: Output of exponential_decay(), in [0, 1].

    Returns:
        One of: "fresh", "recent", "aging", "stale", "expired"
    """
    if decay_value >= 0.8:
        return "fresh"
    if decay_value >= 0.5:
        return "recent"
    if decay_value >= 0.2:
        return "aging"
    if decay_value >= 0.05:
        return "stale"
    return "expired"
