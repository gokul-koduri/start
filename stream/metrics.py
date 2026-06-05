"""Pipeline health metrics — written to Redis, read by /api/stream/status.

Provides counters and gauges for monitoring the stream processor's health.
All metrics are stored under the Redis key "stream:metrics" as a JSON blob,
updated every FLUSH_INTERVAL_SECONDS.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field, asdict
from typing import Any

_logger = logging.getLogger(__name__)

FLUSH_INTERVAL_SECONDS = 30


@dataclass
class PipelineMetrics:
    """Counters and gauges for the stream processing pipeline.

    Attributes:
        signals_processed: Total signals that entered the pipeline.
        signals_enriched: Signals that passed through enrichment.
        signals_scored: Signals that were part of a scored entity.
        signals_errored: Signals that hit the dead letter queue.
        entities_scored: Unique entities that received a score.
        scores_written: Scores successfully written to MySQL.
        alerts_emitted: High-value alerts triggered.
        last_processed_at: Unix timestamp of the last processed signal.
        started_at: Unix timestamp when the pipeline started.
        processing_lag_seconds: Approximate lag from Kafka (if available).
    """

    signals_processed: int = 0
    signals_enriched: int = 0
    signals_scored: int = 0
    signals_errored: int = 0
    entities_scored: int = 0
    scores_written: int = 0
    alerts_emitted: int = 0
    last_processed_at: float = 0.0
    started_at: float = field(default_factory=lambda: time.time())
    processing_lag_seconds: float = 0.0

    # Throughput (computed)
    throughput_per_minute: float = 0.0

    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _prev_count: int = 0
    _prev_time: float = field(default_factory=lambda: time.time())

    def increment(self, counter: str, amount: int = 1) -> None:
        """Thread-safe counter increment.

        Args:
            counter: Name of the counter to increment.
            amount: Amount to add (default 1).
        """
        with self._lock:
            current = getattr(self, counter, 0)
            setattr(self, counter, current + amount)
            if counter == "signals_processed":
                self.last_processed_at = time.time()

    def compute_throughput(self) -> None:
        """Compute signals/minute throughput (call periodically)."""
        with self._lock:
            now = time.time()
            elapsed = now - self._prev_time
            if elapsed > 0:
                diff = self.signals_processed - self._prev_count
                self.throughput_per_minute = round((diff / elapsed) * 60, 2)
                self._prev_count = self.signals_processed
                self._prev_time = now

    def to_dict(self) -> dict[str, Any]:
        """Serialize metrics for Redis storage.

        Excludes unpicklable fields (threading.Lock) by building the dict
        manually instead of using asdict().
        """
        self.compute_throughput()
        return {
            "signals_processed": self.signals_processed,
            "signals_enriched": self.signals_enriched,
            "signals_scored": self.signals_scored,
            "signals_errored": self.signals_errored,
            "entities_scored": self.entities_scored,
            "scores_written": self.scores_written,
            "alerts_emitted": self.alerts_emitted,
            "last_processed_at": self.last_processed_at,
            "started_at": self.started_at,
            "processing_lag_seconds": self.processing_lag_seconds,
            "throughput_per_minute": self.throughput_per_minute,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PipelineMetrics:
        """Deserialize metrics from Redis."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class MetricsWriter:
    """Periodically flushes PipelineMetrics to Redis.

    Usage:
        metrics = PipelineMetrics()
        writer = MetricsWriter(metrics, redis_url="redis://localhost:6379/0")
        writer.start()  # Starts background flush thread

        # In operators:
        metrics.increment("signals_processed")

        writer.stop()  # On shutdown
    """

    def __init__(
        self,
        metrics: PipelineMetrics,
        redis_url: str = "redis://localhost:6379/0",
        key: str = "stream:metrics",
        interval: int = FLUSH_INTERVAL_SECONDS,
    ):
        self._metrics = metrics
        self._redis_url = redis_url
        self._key = key
        self._interval = interval
        self._thread: threading.Thread | None = None
        self._running = False

    def _flush_loop(self) -> None:
        """Background thread that flushes metrics to Redis."""
        _logger.info(
            "MetricsWriter started — flushing to %s every %ds",
            self._key,
            self._interval,
        )
        while self._running:
            self.flush()
            time.sleep(self._interval)

    def flush(self) -> bool:
        """Write current metrics to Redis.

        Returns:
            True if successful, False if Redis is unavailable.
        """
        try:
            import redis as redis_client
            r = redis_client.from_url(
                self._redis_url,
                socket_connect_timeout=2,
                decode_responses=True,
            )
            data = self._metrics.to_dict()
            r.set(self._key, json.dumps(data), ex=self._interval * 3)
            r.close()
            return True
        except Exception as e:
            _logger.debug("Metrics flush failed (Redis unavailable): %s", e)
            return False

    def start(self) -> None:
        """Start the background flush thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the background flush thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        # Final flush
        self.flush()
