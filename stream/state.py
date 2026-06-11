"""Entity state management for the stream processor.

Maintains per-entity state (signal history, last score) across processing
windows. Used by the stateful_map operator in the Bytewax dataflow to provide
incremental scoring without reprocessing the full history.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class EntityState:
    """Tracks per-entity signal history and scoring state.

    This is the value type stored in Bytewax's stateful_map keyed by
    entity_name. It provides:

    - Rolling buffer of the last N signals (prevents unbounded growth)
    - Score history for anomaly detection
    - Timestamps for lag measurement

    Attributes:
        entity_name: The entity this state belongs to.
        signals: Rolling buffer of recent signals (max 100).
        score_history: List of (timestamp, score) tuples for anomaly detection.
        last_score: Most recent composite score.
        last_updated: When this state was last touched.
        total_processed: Cumulative signal count.
    """

    entity_name: str
    signals: list[dict[str, Any]] = field(default_factory=list)
    score_history: list[tuple[float, float]] = field(default_factory=list)
    last_score: float = 0.0
    last_updated: float = 0.0
    total_processed: int = 0

    MAX_SIGNALS: int = 100
    MAX_SCORE_HISTORY: int = 50

    def add_signal(self, signal_dict: dict[str, Any]) -> None:
        """Add a signal to the rolling buffer.

        Args:
            signal_dict: Serialized SignalEnvelope dict.
        """
        self.signals.append(signal_dict)
        # Trim to max size (FIFO)
        if len(self.signals) > self.MAX_SIGNALS:
            self.signals = self.signals[-self.MAX_SIGNALS :]
        self.total_processed += 1
        self.last_updated = _now_timestamp()

    def update_score(self, composite_score: float) -> None:
        """Record a new composite score.

        Args:
            composite_score: The new score for this entity.
        """
        self.last_score = composite_score
        self.score_history.append((_now_timestamp(), composite_score))
        if len(self.score_history) > self.MAX_SCORE_HISTORY:
            self.score_history = self.score_history[-self.MAX_SCORE_HISTORY :]

    def get_score_history(self) -> dict[str, list[float]]:
        """Extract historical values for anomaly detection.

        Returns format expected by CompositeScorer:
            {"funding_round": [85.0, 78.0, ...], "news_mention": [60.0, ...]}
        """
        from collections import defaultdict

        history: dict[str, list[float]] = defaultdict(list)

        for signal_dict in self.signals:
            signal_type = signal_dict.get("signal_type", "unknown")
            raw_score = signal_dict.get("raw_score", 0.0)
            if signal_type != "unknown":
                history[signal_type].append(raw_score)

        return dict(history)

    def to_dict(self) -> dict[str, Any]:
        """Serialize state for Redis persistence or debugging."""
        return {
            "entity_name": self.entity_name,
            "signal_count": len(self.signals),
            "score_history_count": len(self.score_history),
            "last_score": self.last_score,
            "last_updated": self.last_updated,
            "total_processed": self.total_processed,
        }


def init_entity_state(entity_name: str) -> EntityState:
    """Create initial state for a new entity.

    Args:
        entity_name: Entity name (used as key in stateful_map).

    Returns:
        Fresh EntityState with empty signal history.
    """
    return EntityState(entity_name=entity_name)


def update_entity_state(
    state: EntityState, new_signals: list[dict[str, Any]]
) -> tuple[EntityState, list[dict[str, Any]]]:
    """Stateful update function for Bytewax's stateful_map operator.

    Adds new signals to the entity's rolling buffer and returns the
    full accumulated signal list for downstream scoring.

    Args:
        state: Current EntityState (or freshly initialized if first seen).
        new_signals: List of signal dicts from the current window.

    Returns:
        Tuple of (updated_state, output_value) where output_value is the
        list of all accumulated signals ready for scoring.
    """
    for sig in new_signals:
        state.add_signal(sig)

    # Output: all accumulated signals for this entity
    all_signals = state.signals
    return (state, all_signals)


def _now_timestamp() -> float:
    """Return current UTC time as a Unix timestamp."""
    return datetime.now(timezone.utc).timestamp()
