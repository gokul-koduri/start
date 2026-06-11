"""Feature attribution for explainable scoring.

For each scored entity, the attribution module explains WHICH signals
contributed HOW MUCH to the final composite score. This is critical for:
  1. User trust — analysts can verify why an opportunity scored high
  2. Debugging — identify if a signal is overweighted or noisy
  3. Tuning — adjust weights based on real signal contributions
  4. Compliance — audit trail for automated decision-making

Attribution breakdown:
  contribution_i = weight_i × raw_score_i × freshness_i
  composite = sum(contributions) × anomaly_multiplier × confidence
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class SignalAttribution:
    """Attribution for a single signal's contribution to the composite score."""

    signal_type: str
    signal_label: str
    raw_score: float  # 0-100, the original signal strength
    weight: float  # Configured weight for this signal type
    freshness: float  # 0-1, time-decay factor
    contribution: float  # Actual numeric contribution to composite
    published_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal": self.signal_type,
            "label": self.signal_label,
            "raw_score": round(self.raw_score, 2),
            "weight": round(self.weight, 2),
            "freshness": round(self.freshness, 4),
            "contribution": round(self.contribution, 2),
        }


def build_attribution(
    signal_scores: dict[str, dict[str, Any]],
    signal_weights: dict[str, dict[str, Any]],
    decay_values: dict[str, float],
) -> list[SignalAttribution]:
    """Build a sorted list of signal attributions for an entity.

    Args:
        signal_scores: Map of signal_type → {raw_score, published_at, ...}
            Example: {"funding_round": {"raw_score": 90, "published_at": datetime(...)}}
        signal_weights: Map of signal_type → {weight, label, decay_lambda, ...}
        decay_values: Map of signal_type → freshness decay value (0-1)
            Example: {"funding_round": 0.85}

    Returns:
        List of SignalAttribution sorted by contribution (highest first).
    """
    attributions: list[SignalAttribution] = []

    for signal_type, score_data in signal_scores.items():
        if signal_type not in signal_weights:
            continue

        weight_config = signal_weights[signal_type]
        raw_score = score_data.get("raw_score", 0.0)
        weight = weight_config["weight"]
        label = weight_config.get("label", signal_type)
        freshness = decay_values.get(signal_type, 1.0)

        contribution = (
            weight * raw_score * freshness / 100.0
        )  # Normalize to [0, weight]

        attributions.append(
            SignalAttribution(
                signal_type=signal_type,
                signal_label=label,
                raw_score=raw_score,
                weight=weight,
                freshness=freshness,
                contribution=contribution,
                published_at=score_data.get("published_at"),
            )
        )

    # Sort by contribution descending
    return sorted(attributions, key=lambda a: a.contribution, reverse=True)


def compute_confidence(
    signal_scores: dict[str, dict[str, Any]],
    signal_weights: dict[str, dict[str, Any]],
    category: str = "primary",
) -> float:
    """Compute a confidence factor based on signal coverage.

    Confidence decreases when expected signal types are missing.
    A company with only social buzz but no funding/SEC data gets lower confidence.

    Args:
        signal_scores: Map of signal_type → score data (only types with data)
        signal_weights: Full signal weight config
        category: Which signal category to base confidence on ("primary", "all")

    Returns:
        Confidence factor in [0.1, 1.0] where 1.0 = all signals present.
    """
    relevant_types = {
        st
        for st, cfg in signal_weights.items()
        if category == "all" or cfg.get("category") == category
    }

    if not relevant_types:
        return 1.0

    present_types = set(signal_scores.keys()) & relevant_types
    coverage_ratio = len(present_types) / len(relevant_types)

    # Exponential confidence: 1 type → 0.3, half → 0.7, all → 1.0
    confidence = 1.0 - math.exp(-3.0 * coverage_ratio)

    return max(0.1, min(1.0, confidence))


# Need math for compute_confidence
import math  # noqa: E402
