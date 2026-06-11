"""Kafka producer wrapper for signal ingestion.

Wraps the kafka-python-ng library to provide a simple interface for
collectors to publish normalized signals to Kafka topics.

Usage:
    producer = SignalKafkaProducer(bootstrap_servers="localhost:9092")
    producer.send(envelope)  # SignalEnvelope from signal_normalizer
    producer.flush()
    producer.close()

Architecture note:
    In Phase 1, Kafka is optional — collectors can still write directly
    to the raw_signals table. The Kafka producer is used when available
    to enable real-time downstream processing. The design is "write-through":
    signals go to both MySQL (for persistence) and Kafka (for real-time).

Topic design:
    - raw.signals: All signals, generic topic (partitioned by entity_name)
    - raw.signals.{type}: Typed topics per signal (e.g., raw.signals.sec_filing)
    - scores.updates: Scored opportunities (written by scoring engine)
    - alerts.triggered: High-priority alerts
"""

from __future__ import annotations

import json
import logging

_logger = logging.getLogger(__name__)

# Lazy import — kafka-python-ng is optional
_kafka_module = None


def _get_kafka_module():
    """Lazily import kafka-python-ng to avoid import errors when Kafka is not installed."""
    global _kafka_module
    if _kafka_module is None:
        try:
            import kafka_python as kp

            _kafka_module = kp
        except ImportError:
            try:
                from kafka import KafkaProducer as KP

                _kafka_module = type("kafka_module", (), {"KafkaProducer": KP})()
            except ImportError:
                _logger.debug(
                    "kafka-python-ng not installed — Kafka publishing disabled"
                )
                return None
    return _kafka_module


class SignalKafkaProducer:
    """Kafka producer for normalized signal envelopes.

    Automatically serializes SignalEnvelope objects to JSON and publishes
    to the appropriate Kafka topic based on signal type.

    Args:
        bootstrap_servers: Comma-separated Kafka broker addresses.
        topic_prefix: Prefix for topics (default: "raw.signals").
        max_retries: Maximum send retry attempts.
    """

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        topic_prefix: str = "raw.signals",
        max_retries: int = 3,
    ):
        self._bootstrap_servers = bootstrap_servers
        self._topic_prefix = topic_prefix
        self._max_retries = max_retries
        self._producer = None
        self._enabled = False

        self._connect()

    def _connect(self) -> None:
        """Initialize Kafka producer connection."""
        kp = _get_kafka_module()
        if kp is None:
            _logger.info(
                "Kafka not available — signals will only be persisted to MySQL"
            )
            return

        try:
            KP = kp.KafkaProducer if hasattr(kp, "KafkaProducer") else None
            if KP is None:
                return

            self._producer = KP(
                bootstrap_servers=self._bootstrap_servers,
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                acks="all",
                retries=self._max_retries,
                max_block_ms=5000,
            )
            self._enabled = True
            _logger.info(
                "Kafka producer connected to %s (topic prefix: %s)",
                self._bootstrap_servers,
                self._topic_prefix,
            )

        except Exception as e:
            _logger.warning(
                "Kafka connection failed: %s — falling back to MySQL-only", e
            )
            self._enabled = False

    @property
    def is_enabled(self) -> bool:
        """Whether Kafka publishing is available."""
        return self._enabled and self._producer is not None

    def send(self, envelope, topic_override: str | None = None) -> bool:
        """Publish a SignalEnvelope to Kafka.

        Args:
            envelope: SignalEnvelope or dict with signal data.
            topic_override: Override the auto-detected topic.

        Returns:
            True if successfully published, False otherwise.
        """
        if not self.is_enabled:
            return False

        # Convert envelope to dict if needed
        if hasattr(envelope, "to_dict"):
            data = envelope.to_dict()
            key = envelope.to_kafka_key()
        else:
            data = envelope
            key = data.get("entity_name", "").lower() or "unknown"

        # Determine topic
        signal_type = data.get("signal_type", "")
        topic = topic_override or f"{self._topic_prefix}.{signal_type}"

        try:
            future = self._producer.send(topic, key=key, value=data)
            result = future.get(timeout=5)
            _logger.debug(
                "Kafka: published %s → topic=%s, partition=%d, offset=%d",
                signal_type,
                topic,
                result.partition,
                result.offset,
            )
            return True

        except Exception as e:
            _logger.warning("Kafka publish failed for %s: %s", signal_type, e)
            return False

    def send_batch(self, envelopes: list) -> int:
        """Publish multiple envelopes to Kafka.

        Args:
            envelopes: List of SignalEnvelope objects or dicts.

        Returns:
            Number of successfully published envelopes.
        """
        if not self.is_enabled:
            return 0

        success = 0
        for envelope in envelopes:
            if self.send(envelope):
                success += 1
        return success

    def flush(self) -> None:
        """Flush pending messages."""
        if self._producer:
            try:
                self._producer.flush()
            except Exception as e:
                _logger.warning("Kafka flush failed: %s", e)

    def close(self) -> None:
        """Close the producer connection."""
        if self._producer:
            try:
                self._producer.flush()
                self._producer.close()
            except Exception:
                pass
            self._producer = None
            self._enabled = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
