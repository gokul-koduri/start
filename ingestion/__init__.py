"""Signal ingestion package — Kafka producer and signal normalization."""

from ingestion.kafka_producer import SignalKafkaProducer
from ingestion.signal_normalizer import normalize_signal, SignalEnvelope

__all__ = ["SignalKafkaProducer", "normalize_signal", "SignalEnvelope"]
