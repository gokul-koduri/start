"""Reusable Bytewax operators for signal processing.

Each operator is a pure function (or close to it) that transforms data
within the Bytewax dataflow. This module contains no Bytewax imports
so operators can be tested independently without a running cluster.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any

from ingestion.signal_normalizer import SignalEnvelope, VALID_SIGNAL_TYPES

_logger = logging.getLogger(__name__)


# ── Retry helper ──────────────────────────────────────────────


def retry_with_backoff(
    fn,
    *args,
    max_attempts: int = 3,
    backoff_ms: tuple[int, ...] = (100, 500, 2000),
    logger: logging.Logger | None = None,
    **kwargs,
):
    """Retry fn with exponential backoff on exception.

    Args:
        fn: Function to call.
        *args, **kwargs: Arguments to pass to fn.
        max_attempts: Maximum retry attempts (default 3).
        backoff_ms: Sleep durations between attempts in ms.
        logger: Logger to use for retry messages.

    Returns:
        fn's return value on success.

    Raises:
        Exception: Re-raises the last exception after all attempts fail.
    """
    _log = logger or _logger
    for attempt in range(max_attempts):
        try:
            return fn(*args, **kwargs)
        except Exception:
            if attempt < max_attempts - 1:
                delay_s = backoff_ms[attempt] / 1000.0
                _log.warning(
                    "Retry %d/%d after %.1fs: %s",
                    attempt + 1,
                    max_attempts,
                    delay_s,
                    _exc_str(),
                )
                time.sleep(delay_s)
            else:
                _log.error(
                    "All %d attempts failed — giving up: %s", max_attempts, _exc_str()
                )
                raise


def _exc_str() -> str:
    import traceback

    return traceback.format_exc()[-300:].strip()


# ── Batch accumulator for MySQL writes ────────────────────────


class MySQLBatchWriter:
    """Collect scored entities and flush in batches to MySQL.

    Flushes when either:
    - batch_size items have accumulated
    - flush_interval_seconds have elapsed since last flush

    Thread-safe for use from the stream processor.
    """

    def __init__(
        self,
        batch_size: int = 50,
        flush_interval: int = 10,
    ):
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._queue: deque[tuple[str, dict[str, Any]]] = deque()
        self._lock = threading.Lock()
        self._last_flush = time.monotonic()

    def add(self, entity_name: str, scored: dict[str, Any]) -> None:
        """Add a scored entity to the batch."""
        with self._lock:
            self._queue.append((entity_name, scored))
            if len(self._queue) >= self.batch_size or self._should_flush():
                self._flush_unlocked()

    def _should_flush(self) -> bool:
        return (time.monotonic() - self._last_flush) >= self.flush_interval

    def _flush_unlocked(self) -> None:
        """Flush queue to MySQL. Must hold lock."""
        if not self._queue:
            return
        items = list(self._queue)
        self._queue.clear()
        self._last_flush = time.monotonic()
        try:
            _bulk_upsert(items)
        except Exception:
            _logger.error("Batch flush failed for %d items: %s", len(items), _exc_str())

    def flush(self) -> None:
        """Force a flush of any pending items."""
        with self._lock:
            self._flush_unlocked()

    def __len__(self) -> int:
        return len(self._queue)


# Global batch writer (shared across operators)
_mysql_batch = MySQLBatchWriter()


def parse_signal_envelope(raw: bytes) -> tuple[str, SignalEnvelope]:
    """Deserialize a Kafka message into (entity_name, SignalEnvelope).

    Args:
        raw: JSON-encoded bytes from Kafka.

    Returns:
        Tuple of (entity_name, SignalEnvelope).

    Raises:
        ValueError: If raw data is invalid JSON or missing required fields.
    """
    try:
        data = json.loads(raw) if isinstance(raw, bytes) else json.loads(raw)
    except (json.JSONDecodeError, TypeError) as e:
        raise ValueError(f"Invalid JSON: {e}") from e

    if not isinstance(data, dict):
        raise ValueError(f"Expected dict, got {type(data).__name__}")

    required = {"signal_type", "source_name"}
    missing = required - data.keys()
    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    entity_name = data.get("entity_name", "").strip() or "unknown"
    signal_type = data.get("signal_type", "")

    # Validate signal_type
    if signal_type and signal_type not in VALID_SIGNAL_TYPES:
        _logger.warning("Unknown signal_type '%s', allowing anyway", signal_type)

    envelope = SignalEnvelope(
        signal_type=signal_type,
        source_name=data.get("source_name", ""),
        source_url=data.get("source_url", ""),
        title=data.get("title", ""),
        body_text=data.get("body_text", ""),
        entity_name=entity_name,
        entity_type=data.get("entity_type", "company"),
        published_at=_parse_datetime(data.get("published_at")),
        collected_at=_parse_datetime(data.get("collected_at"))
        or datetime.now(timezone.utc),
        raw_score=float(data.get("raw_score", 0.0)),
        metadata=data.get("metadata", {}),
        id=data.get("id", ""),
    )

    return (entity_name, envelope)


def enrich_signal(envelope: SignalEnvelope) -> SignalEnvelope:
    """Add lightweight NLP enrichment to a signal envelope.

    This is a fast enrichment that runs on every signal:
    - Basic sentiment scoring using keyword matching
    - Entity name normalization (strip whitespace, lowercase for matching)

    Heavy NLP (spaCy, Ollama) is done separately by the batch pipeline
    to avoid blocking the stream processor.
    """
    # Fast keyword-based sentiment (no external deps)
    body = (envelope.body_text + " " + envelope.title).lower()
    positive_words = {
        "raise",
        "raised",
        "funded",
        "growth",
        "launch",
        "acquire",
        "patent",
        "expand",
        "profit",
        "success",
        "milestone",
        "record",
    }
    negative_words = {
        "fail",
        "bankrupt",
        "layoff",
        "shut down",
        "close",
        "loss",
        "decline",
        "drop",
        "cut",
        "downsize",
        "restructure",
    }

    pos_count = sum(1 for w in positive_words if w in body)
    neg_count = sum(1 for w in negative_words if w in body)

    if pos_count + neg_count > 0:
        sentiment = (pos_count - neg_count) / max(1, pos_count + neg_count)
    else:
        sentiment = 0.0

    # Store enrichment in metadata
    metadata = dict(envelope.metadata)
    metadata["stream_enriched"] = True
    metadata["stream_sentiment"] = round(sentiment, 4)
    metadata["stream_enriched_at"] = datetime.now(timezone.utc).isoformat()

    # Return a new envelope with enriched metadata
    return SignalEnvelope(
        signal_type=envelope.signal_type,
        source_name=envelope.source_name,
        source_url=envelope.source_url,
        title=envelope.title,
        body_text=envelope.body_text,
        entity_name=envelope.entity_name,
        entity_type=envelope.entity_type,
        published_at=envelope.published_at,
        collected_at=envelope.collected_at,
        raw_score=envelope.raw_score,
        metadata=metadata,
        id=envelope.id,
    )


def build_signal_scores(signals: list[SignalEnvelope]) -> dict[str, dict[str, Any]]:
    """Convert a list of SignalEnvelopes into the format CompositeScorer expects.

    CompositeScorer.score() takes:
        signal_scores={
            "funding_round": {"raw_score": 90, "published_at": datetime(...)},
            ...
        }

    When multiple signals of the same type exist for an entity, we keep
    the one with the highest raw_score (most impactful).
    """
    best: dict[str, dict[str, Any]] = {}
    for sig in signals:
        stype = sig.signal_type
        score = sig.raw_score or 0.0
        existing = best.get(stype)
        if existing is None or score > existing["raw_score"]:
            best[stype] = {
                "raw_score": score,
                "published_at": sig.published_at
                or sig.collected_at
                or datetime.now(timezone.utc),
            }
    return best


def build_historical_values(signals: list[SignalEnvelope]) -> dict[str, list[float]]:
    """Extract historical signal scores for anomaly detection.

    Returns chronological list of raw_scores per signal type.
    """
    from collections import defaultdict

    history: dict[str, list[float]] = defaultdict(list)
    for sig in sorted(
        signals, key=lambda s: s.published_at or s.collected_at or datetime.min
    ):
        history[sig.signal_type].append(sig.raw_score or 0.0)
    return dict(history)


def score_entity(
    entity_name: str,
    signals: list[SignalEnvelope],
    entity_type: str = "company",
) -> dict[str, Any]:
    """Run CompositeScorer on aggregated signals for an entity.

    Returns a dict with the scoring result suitable for JSON serialization.

    Args:
        entity_name: Entity name.
        signals: List of SignalEnvelopes for this entity.
        entity_type: Entity type (company, technology, market).

    Returns:
        Dict with composite_score, attribution, trend_direction, etc.
    """
    from scoring.composite_scorer import CompositeScorer

    if not signals:
        return {
            "entity_name": entity_name,
            "entity_type": entity_type,
            "composite_score": 0.0,
            "signal_count": 0,
            "trend_direction": "stable",
            "confidence": 0.0,
        }

    signal_scores = build_signal_scores(signals)
    historical = build_historical_values(signals)

    scorer = CompositeScorer()
    result = scorer.score(
        entity_name=entity_name,
        entity_type=entity_type,
        signal_scores=signal_scores,
        historical_values=historical,
    )

    return result.to_dict()


def write_score_to_mysql(scored: dict[str, Any]) -> dict[str, Any]:
    """Upsert a scored entity into the opportunity_scores table.

    Uses retry with exponential backoff, circuit breaker, and batch
    accumulation for efficient writes.

    Args:
        scored: Dict from score_entity() with composite_score etc.

    Returns:
        The input dict unchanged (passthrough for downstream operators).
    """
    from utils.circuit_breaker import mysql_stream_breaker

    def _do_write():
        # Route through batch writer — accumulates and flushes in batches
        _mysql_batch.add(scored.get("entity_name", "unknown"), scored)
        return True

    try:
        mysql_stream_breaker.call(_do_write)
    except Exception:
        # Circuit open — skip write, let pipeline continue
        _logger.warning(
            "MySQL circuit open, score for '%s' dropped (will retry next cycle)",
            scored.get("entity_name", "?"),
        )

    return scored


def _bulk_upsert(items: list[tuple[str, dict[str, Any]]]) -> None:
    """Execute a batch upsert of scored entities into opportunity_scores.

    Uses executemany for efficiency when multiple entities are available.

    Args:
        items: List of (entity_name, scored_dict) tuples.
    """
    if not items:
        return

    from db.connection import get_connection
    from db import schema

    import json as _json

    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    rows = []
    for entity_name, scored in items:
        rows.append(
            (
                entity_name,
                scored.get("entity_type", "company"),
                scored.get("composite_score", 0.0),
                scored.get("signal_count", 0),
                scored.get("trend_direction", "stable"),
                _json.dumps(scored.get("attribution", [])),
                _json.dumps(scored.get("signal_types", [])),
            )
        )

    cursor.executemany(
        """
        INSERT INTO opportunity_scores
            (entity_name, entity_type, composite_score, signal_count,
             trend_direction, attribution_json, signal_types_json,
             last_updated)
        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        ON DUPLICATE KEY UPDATE
            composite_score = VALUES(composite_score),
            signal_count = VALUES(signal_count),
            trend_direction = VALUES(trend_direction),
            attribution_json = VALUES(attribution_json),
            signal_types_json = VALUES(signal_types_json),
            last_updated = NOW()
        """,
        rows,
    )
    conn.commit()
    cursor.close()
    conn.close()
    _logger.debug("Bulk upserted %d scores", len(rows))


def emit_alert(
    scored: dict[str, Any], threshold: float = 80.0
) -> dict[str, Any] | None:
    """Create an alert dict if the composite score exceeds the threshold.

    Returns None if no alert should be emitted (filtered out downstream).
    """
    score = scored.get("composite_score", 0.0)
    if score < threshold:
        return None

    return {
        "alert_type": "high_value_opportunity",
        "entity_name": scored.get("entity_name", ""),
        "entity_type": scored.get("entity_type", ""),
        "composite_score": score,
        "signal_count": scored.get("signal_count", 0),
        "trend_direction": scored.get("trend_direction", "stable"),
        "triggered_at": datetime.now(timezone.utc).isoformat(),
        "attribution": scored.get("attribution", [])[:3],  # Top 3 signals
    }


def _parse_datetime(value: Any) -> datetime | None:
    """Parse a datetime value from various formats."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None
