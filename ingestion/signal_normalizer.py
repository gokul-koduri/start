"""Signal normalization — unified envelope for all signal types.

Different collectors produce data in different shapes. The normalizer
converts them into a common SignalEnvelope that downstream consumers
(NLP pipeline, scoring engine, stream processing) can handle uniformly.

This is the "Rosetta Stone" of the ingestion layer — it ensures that
a SEC filing and a GitHub trending repo both look like a `SignalEnvelope`
with the same fields by the time they reach the scoring engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import uuid


@dataclass
class SignalEnvelope:
    """Unified signal envelope for all data sources.

    Every signal — whether from SEC EDGAR, job postings, GitHub, or news —
    is normalized into this common structure before being written to Kafka
    or the raw_signals table.

    Attributes:
        id: Unique identifier for this signal instance.
        signal_type: Category (sec_filing, job_posting_spike, github_trend,
            funding_round, patent_filed, news_mention, social_buzz, website_change).
        source_name: Which collector produced this (e.g., "sec_edgar", "github_trends").
        source_url: URL where the signal was found.
        title: Human-readable title/headline.
        body_text: Full text content (truncated to 50K chars).
        entity_name: Primary entity (company, person, technology) mentioned.
        entity_type: Type of entity (company, technology, market, person).
        published_at: When the signal was originally published/detected.
        collected_at: When our system collected it.
        raw_score: Initial signal strength (0-100), set by collector heuristics.
        metadata: Arbitrary key-value metadata specific to the signal type.
    """

    signal_type: str
    source_name: str
    source_url: str = ""
    title: str = ""
    body_text: str = ""
    entity_name: str = ""
    entity_type: str = "company"
    published_at: datetime | None = None
    collected_at: datetime | None = None
    raw_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.collected_at:
            self.collected_at = datetime.now(timezone.utc)
        # Truncate body text to prevent oversized messages
        self.body_text = self.body_text[:50_000]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for JSON encoding."""
        return {
            "id": self.id,
            "signal_type": self.signal_type,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "title": self.title[:1000],
            "body_text": self.body_text[:50_000],
            "entity_name": self.entity_name[:255],
            "entity_type": self.entity_type,
            "published_at": self.published_at.isoformat()
            if self.published_at
            else None,
            "collected_at": self.collected_at.isoformat()
            if self.collected_at
            else None,
            "raw_score": self.raw_score,
            "metadata": self.metadata,
        }

    def to_kafka_key(self) -> str:
        """Generate a Kafka partition key from the entity name.

        Using entity_name as key ensures all signals for the same entity
        go to the same partition — enabling efficient per-entity aggregation
        in the stream processor.
        """
        return self.entity_name.lower().strip() or "unknown"


def normalize_signal(
    signal_type: str,
    source_name: str,
    *,
    source_url: str = "",
    title: str = "",
    body_text: str = "",
    entity_name: str = "",
    entity_type: str = "company",
    published_at: datetime | str | None = None,
    raw_score: float = 0.0,
    **metadata: Any,
) -> SignalEnvelope:
    """Factory function to create a normalized SignalEnvelope.

    Args:
        signal_type: One of the defined signal types.
        source_name: Collector name that produced this signal.
        source_url: URL of the original source.
        title: Headline or summary.
        body_text: Full text content.
        entity_name: Primary entity referenced.
        entity_type: Type of entity.
        published_at: When published (datetime or ISO string).
        raw_score: Initial heuristic score (0-100).
        **metadata: Additional key-value metadata.

    Returns:
        Normalized SignalEnvelope ready for Kafka or DB insertion.

    Examples:
        >>> envelope = normalize_signal(
        ...     "funding_round", "funding_techcrunch",
        ...     title="Neuromorphic Labs raises $50M Series B",
        ...     entity_name="Neuromorphic Labs",
        ...     published_at="2025-12-01T10:00:00Z",
        ...     raw_score=85.0,
        ...     round_type="Series B",
        ...     amount_usd=50_000_000,
        ... )
        >>> envelope.signal_type
        'funding_round'
        >>> envelope.metadata["round_type"]
        'Series B'
    """
    # Normalize published_at to datetime
    if isinstance(published_at, str):
        try:
            published_at = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        except ValueError:
            published_at = None

    return SignalEnvelope(
        signal_type=signal_type,
        source_name=source_name,
        source_url=source_url,
        title=title,
        body_text=body_text,
        entity_name=entity_name,
        entity_type=entity_type,
        published_at=published_at,
        raw_score=raw_score,
        metadata=metadata,
    )


# Valid signal types for validation
VALID_SIGNAL_TYPES = {
    "sec_filing",
    "job_posting_spike",
    "github_trend",
    "funding_round",
    "patent_filed",
    "news_mention",
    "social_buzz",
    "website_change",
}
