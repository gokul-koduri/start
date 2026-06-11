"""Composite Opportunity Scorer — the central scoring engine.

Combines multiple signal sources into a single explainable opportunity score
using time-weighted decay, anomaly detection, and confidence factors.

Formula:
  Composite_Score(entity, t) =
      SUM( w_i * signal_score_i * decay(t - t_i) ) / SUM( w_i * decay(t - t_i) )
      * anomaly_multiplier
      * confidence_factor

Usage:
  scorer = CompositeScorer()
  result = scorer.score(
      entity_name="Neuromorphic Labs",
      entity_type="company",
      signal_scores={
          "funding_round": {"raw_score": 90, "published_at": datetime(...)},
          "sec_filing":    {"raw_score": 75, "published_at": datetime(...)},
          "job_posting_spike": {"raw_score": 70, "published_at": datetime(...)},
      },
  )
  # result.composite_score → 78.5
  # result.attribution → [SignalAttribution, ...]
  # result.anomaly → AnomalyResult
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from scoring.anomaly_detector import AnomalyResult, z_score_anomaly
from scoring.feature_attribution import (
    SignalAttribution,
    build_attribution,
    compute_confidence,
)
from scoring.signal_weights import (
    ANOMALY_BOOST_FACTOR,
    ANOMALY_Z_THRESHOLD,
    SIGNAL_WEIGHTS,
)
from scoring.time_decay import exponential_decay, freshness_label


@dataclass
class ScoreResult:
    """Complete scoring result for an entity."""

    entity_name: str
    entity_type: str
    composite_score: float  # 0-100
    raw_weighted_score: float  # Before anomaly/confidence adjustment
    signal_count: int
    anomaly: AnomalyResult | None = None
    attribution: list[SignalAttribution] = field(default_factory=list)
    trend_direction: str = "stable"  # "rising" | "falling" | "stable"
    confidence: float = 1.0
    signal_types: list[str] = field(default_factory=list)
    freshness_summary: str = "unknown"  # "fresh" | "recent" | "aging" | "stale"

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_name": self.entity_name,
            "entity_type": self.entity_type,
            "composite_score": round(self.composite_score, 2),
            "raw_weighted_score": round(self.raw_weighted_score, 2),
            "signal_count": self.signal_count,
            "signal_types": self.signal_types,
            "trend_direction": self.trend_direction,
            "confidence": round(self.confidence, 4),
            "freshness_summary": self.freshness_summary,
            "attribution": [a.to_dict() for a in self.attribution],
            "anomaly": self.anomaly.to_dict() if self.anomaly else None,
        }


class CompositeScorer:
    """Score entities based on multi-signal composite scoring.

    The scorer is stateless by design — all state (historical values for anomaly
    detection, etc.) is passed in per-call. This makes it easy to test and
    horizontally scale.

    Args:
        weights: Override default signal weights. If None, uses SIGNAL_WEIGHTS.
        anomaly_threshold: Z-score threshold for anomaly detection.
        anomaly_boost: Multiplier applied when anomaly is detected.
    """

    def __init__(
        self,
        weights: dict[str, dict[str, Any]] | None = None,
        anomaly_threshold: float = ANOMALY_Z_THRESHOLD,
        anomaly_boost: float = ANOMALY_BOOST_FACTOR,
    ):
        self._weights = weights or SIGNAL_WEIGHTS
        self._anomaly_threshold = anomaly_threshold
        self._anomaly_boost = anomaly_boost

    def score(
        self,
        entity_name: str,
        entity_type: str = "company",
        signal_scores: dict[str, dict[str, Any]] | None = None,
        historical_values: dict[str, list[float]] | None = None,
    ) -> ScoreResult:
        """Compute the composite opportunity score for an entity.

        Args:
            entity_name: Name of the entity (company, technology, market).
            entity_type: Entity type ("company", "technology", "market").
            signal_scores: Map of signal_type → {raw_score, published_at}.
                raw_score is 0-100. published_at is when the signal was detected.
            historical_values: Optional map of signal_type → historical values
                for anomaly detection (chronological, oldest first).

        Returns:
            ScoreResult with composite score and full attribution.

        Examples:
            >>> from datetime import timedelta
            >>> scorer = CompositeScorer()
            >>> now = datetime.now(timezone.utc)
            >>> result = scorer.score(
            ...     entity_name="Test Corp",
            ...     signal_scores={
            ...         "funding_round": {"raw_score": 90, "published_at": now - timedelta(days=1)},
            ...         "news_mention": {"raw_score": 60, "published_at": now - timedelta(days=3)},
            ...     },
            ... )
            >>> result.composite_score > 0
            True
        """
        signal_scores = signal_scores or {}
        now = datetime.now(timezone.utc)

        # ── Step 1: Compute time-decay for each signal ──
        decay_values: dict[str, float] = {}
        for signal_type, data in signal_scores.items():
            if signal_type in self._weights:
                published_at = data.get("published_at", now)
                lambda_ = self._weights[signal_type]["decay_lambda"]
                decay_values[signal_type] = exponential_decay(
                    published_at, lambda_, now=now
                )

        # ── Step 2: Build attribution ──
        attribution = build_attribution(signal_scores, self._weights, decay_values)

        # ── Step 3: Compute weighted, decayed average ──
        weighted_sum = 0.0
        weight_sum = 0.0

        for attr in attribution:
            weighted_sum += attr.contribution
            weight_sum += attr.weight

        raw_weighted = (weighted_sum / weight_sum * 100.0) if weight_sum > 0 else 0.0

        # ── Step 4: Confidence factor ──
        confidence = compute_confidence(signal_scores, self._weights)

        # ── Step 5: Anomaly detection ──
        anomaly_result = None
        anomaly_multiplier = 1.0

        if historical_values:
            # Use the signal with the most history for anomaly detection
            best_signal = max(
                historical_values.items(),
                key=lambda kv: len(kv[1]),
                default=(None, []),
            )
            if best_signal[0] and len(best_signal[1]) >= 3:
                anomaly_result = z_score_anomaly(
                    best_signal[1],
                    threshold=self._anomaly_threshold,
                )
                if anomaly_result.is_anomaly:
                    anomaly_multiplier = self._anomaly_boost

        # ── Step 6: Final composite score ──
        composite = raw_weighted * anomaly_multiplier * confidence
        composite = max(0.0, min(100.0, composite))

        # ── Step 7: Trend direction ──
        trend = self._compute_trend(attribution)

        # ── Step 8: Freshness summary ──
        avg_freshness = (
            sum(a.freshness for a in attribution) / len(attribution)
            if attribution
            else 0.0
        )

        return ScoreResult(
            entity_name=entity_name,
            entity_type=entity_type,
            composite_score=round(composite, 2),
            raw_weighted_score=round(raw_weighted, 2),
            signal_count=len(signal_scores),
            anomaly=anomaly_result,
            attribution=attribution,
            trend_direction=trend,
            confidence=confidence,
            signal_types=list(signal_scores.keys()),
            freshness_summary=freshness_label(avg_freshness),
        )

    def _compute_trend(self, attribution: list[SignalAttribution]) -> str:
        """Determine trend direction based on signal freshness distribution.

        If most signals are fresh → "rising"
        If most are aging/stale → "falling"
        Otherwise → "stable"
        """
        if not attribution:
            return "stable"

        fresh_count = sum(1 for a in attribution if a.freshness >= 0.7)
        stale_count = sum(1 for a in attribution if a.freshness < 0.3)

        if fresh_count >= len(attribution) * 0.6:
            return "rising"
        if stale_count >= len(attribution) * 0.6:
            return "falling"
        return "stable"
