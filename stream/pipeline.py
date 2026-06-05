"""Bytewax real-time signal processing pipeline.

5-stage dataflow:
  1. Ingest   — consume raw.signals from Kafka (Redpanda)
  2. Enrich   — add fast sentiment + metadata
  3. Aggregate — group signals per entity over tumbling windows
  4. Score    — run CompositeScorer on aggregated signals
  5. Output   — MySQL upsert + Kafka scores.updates + alerts

Run:
    python -m stream.pipeline                # Single worker
    python -m stream.pipeline --workers 2     # Multi-worker (cluster)
    python -m stream.pipeline --test          # Run with in-memory test data

The pipeline is designed to be additive — the batch pipeline (run_agent.py)
continues to work independently. If Kafka is unavailable, the pipeline exits
gracefully with a warning.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from ingestion.signal_normalizer import SignalEnvelope
from stream.metrics import MetricsWriter, PipelineMetrics

_logger = logging.getLogger("stream.pipeline")

# Global metrics instance (shared across operators)
_metrics = PipelineMetrics()
_metrics_writer: MetricsWriter | None = None


def _get_config() -> dict[str, Any]:
    """Load pipeline configuration from environment and defaults."""
    return {
        "kafka_brokers": os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
        "kafka_group": os.environ.get("KAFKA_GROUP_ID", "signal-processor"),
        "kafka_topic_in": os.environ.get("KAFKA_TOPIC_IN", "raw.signals"),
        "kafka_topic_scores": os.environ.get("KAFKA_TOPIC_SCORES", "scores.updates"),
        "kafka_topic_alerts": os.environ.get("KAFKA_TOPIC_ALERTS", "alerts.triggered"),
        "kafka_topic_dlq": os.environ.get("KAFKA_TOPIC_DLQ", "dead.letters"),
        "redis_url": os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        "mysql_host": os.environ.get("MYSQL_HOST", "localhost"),
        "alert_threshold": float(os.environ.get("ALERT_THRESHOLD", "80.0")),
        "window_seconds": int(os.environ.get("WINDOW_SECONDS", "300")),  # 5 min
    }


# ── Stage Operators ──────────────────────────────────────────


def _op_ingest(raw: bytes) -> tuple[str, dict[str, Any]]:
    """Stage 1: Parse Kafka message into (entity_name, signal_dict).

    Invalid messages are logged and still passed through with entity_name='__dlq__'
    so the dead letter branch can filter them.
    """
    try:
        from stream.operators import parse_signal_envelope
        entity_name, envelope = parse_signal_envelope(raw)
        _metrics.increment("signals_processed")
        return (entity_name, envelope.to_dict())
    except Exception as e:
        _metrics.increment("signals_errored")
        _logger.warning("Ingest failed: %s", e)
        return ("__dlq__", {"raw": str(raw)[:500], "error": str(e), "timestamp": _now_iso()})


def _op_enrich(key_entity: tuple[str, dict]) -> tuple[str, dict]:
    """Stage 2: Add fast enrichment (sentiment, metadata).

    Dead letter items are passed through unchanged.
    """
    entity_name, signal_dict = key_entity
    if entity_name == "__dlq__":
        return key_entity

    try:
        envelope = SignalEnvelope(
            signal_type=signal_dict.get("signal_type", ""),
            source_name=signal_dict.get("source_name", ""),
            source_url=signal_dict.get("source_url", ""),
            title=signal_dict.get("title", ""),
            body_text=signal_dict.get("body_text", ""),
            entity_name=signal_dict.get("entity_name", ""),
            entity_type=signal_dict.get("entity_type", "company"),
            published_at=_parse_dt(signal_dict.get("published_at")),
            collected_at=_parse_dt(signal_dict.get("collected_at")),
            raw_score=float(signal_dict.get("raw_score", 0.0)),
            metadata=signal_dict.get("metadata", {}),
        )

        from stream.operators import enrich_signal
        enriched = enrich_signal(envelope)
        _metrics.increment("signals_enriched")
        return (enriched.entity_name, enriched.to_dict())
    except Exception as e:
        _metrics.increment("signals_errored")
        _logger.warning("Enrich failed for %s: %s", entity_name, e)
        return (entity_name, signal_dict)


def _op_score(key_entity: tuple[str, list[dict]]) -> tuple[str, dict]:
    """Stage 4: Run CompositeScorer on aggregated signals.

    Args:
        key_entity: (entity_name, list_of_signal_dicts)
    """
    entity_name, signals = key_entity
    if not signals:
        return (entity_name, {"entity_name": entity_name, "composite_score": 0.0})

    try:
        envelopes = []
        for s in signals:
            envelopes.append(SignalEnvelope(
                signal_type=s.get("signal_type", ""),
                source_name=s.get("source_name", ""),
                title=s.get("title", ""),
                body_text=s.get("body_text", ""),
                entity_name=s.get("entity_name", entity_name),
                entity_type=s.get("entity_type", "company"),
                published_at=_parse_dt(s.get("published_at")),
                collected_at=_parse_dt(s.get("collected_at")),
                raw_score=float(s.get("raw_score", 0.0)),
                metadata=s.get("metadata", {}),
            ))

        from stream.operators import score_entity
        scored = score_entity(entity_name, envelopes)
        _metrics.increment("entities_scored")
        _metrics.increment("signals_scored", len(signals))
        return (entity_name, scored)
    except Exception as e:
        _metrics.increment("signals_errored")
        _logger.error("Scoring failed for %s: %s", entity_name, e)
        return (entity_name, {"entity_name": entity_name, "composite_score": 0.0, "error": str(e)})


def _op_write_mysql(key_entity: tuple[str, dict]) -> tuple[str, dict]:
    """Stage 5a: Write scored entity to MySQL opportunity_scores.

    Passthrough — returns input unchanged for downstream Kafka publish.
    """
    entity_name, scored = key_entity
    if scored.get("composite_score", 0) <= 0:
        return key_entity

    try:
        from stream.operators import write_score_to_mysql
        write_score_to_mysql(scored)
        _metrics.increment("scores_written")
    except Exception as e:
        _logger.error("MySQL write failed for %s: %s", entity_name, e)

    return key_entity


def _op_emit_alert(key_entity: tuple[str, dict]) -> tuple[str, dict] | None:
    """Stage 5b: Emit alert if score exceeds threshold.

    Returns None to filter out non-alerts (Bytewax filter semantics).
    """
    entity_name, scored = key_entity
    try:
        from stream.operators import emit_alert
        alert = emit_alert(scored, threshold=_get_config()["alert_threshold"])
        if alert:
            _metrics.increment("alerts_emitted")
            return (entity_name, alert)
    except Exception as e:
        _logger.error("Alert emission failed for %s: %s", entity_name, e)
    return None


# ── Helpers ───────────────────────────────────────────────────


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_dt(value: Any) -> Any:
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


# ── Pipeline Builder ────────────────────────────────────────


def build_pipeline() -> Any:
    """Build the Bytewax dataflow with all 5 stages.

    Uses a late import of bytewax to allow the module to load even
    if bytewax is not installed (for testing the operators independently).
    """
    try:
        from bytewax import Dataflow
    except ImportError:
        _logger.error(
            "Bytewax is not installed. Install with: pip install bytewax>=0.16.0"
        )
        sys.exit(1)

    flow = Dataflow("signal_processing")

    # ── Stage 1: Ingest from Kafka ──
    try:
        from bytewax.connectors.kafka import KafkaSource
        config = _get_config()
        source = KafkaSource(
            brokers=config["kafka_brokers"].split(","),
            topics=[config["kafka_topic_in"]],
            group_id=config["kafka_group"],
            batch_size=100,
        )
        flow.input("kafka_in", source)
        _logger.info("Connected to Kafka at %s, topic: %s", config["kafka_brokers"], config["kafka_topic_in"])
    except ImportError:
        _logger.warning("KafkaSource not available — using SimulatedInput for testing")
        flow.input("simulated", _simulated_source())

    # ── Stage 2: Enrich ──
    flow.map(_op_enrich)

    # ── Stage 3: Aggregate by entity (tumbling window) ──
    # Group signals by entity_name within tumbling windows
    try:
        from bytewax.window import TumblingClocker
        window_seconds = int(os.environ.get("WINDOW_SECONDS", "300"))
        clock = TumblingClocker(window_seconds)

        def _collect_signals(acc: list, item: tuple[str, dict]) -> list:
            """Accumulate signals per entity within a window."""
            entity_name, signal_dict = item
            acc.append(signal_dict)
            return acc

        flow.reduce_window(
            _collect_signals,
            clock,
        )
    except ImportError:
        # Fallback: simple group_by_key (no windowing)
        flow.reduce_key(lambda acc, item: acc + [item[1]], lambda acc: acc or [])

    # ── Stage 4: Score ──
    flow.map(_op_score)

    # ── Stage 5a: Write to MySQL ──
    flow.map(_op_write_mysql)

    # ── Stage 5b: Output to Kafka (scores) ──
    try:
        from bytewax.connectors.kafka import KafkaSink
        config = _get_config()

        def _serialize_score(item: tuple[str, dict]) -> bytes:
            return json.dumps(item[1]).encode("utf-8")

        flow.output("kafka_scores", KafkaSink(
            brokers=config["kafka_brokers"].split(","),
            topic=config["kafka_topic_scores"],
        ))
        _logger.info("Output to Kafka topic: %s", config["kafka_topic_scores"])
    except ImportError:
        flow.output("stdout_scores", lambda x: print(f"SCORE: {x}"))

    # ── Stage 5c: Alert emission (branch) ──
    flow.filter(_op_emit_alert)
    try:
        from bytewax.connectors.kafka import KafkaSink
        config = _get_config()
        flow.output("kafka_alerts", KafkaSink(
            brokers=config["kafka_brokers"].split(","),
            topic=config["kafka_topic_alerts"],
        ))
    except ImportError:
        flow.output("stdout_alerts", lambda x: print(f"ALERT: {x}"))

    return flow


def _simulated_source():
    """Generate test signals for local testing without Kafka."""
    import itertools
    from bytewax.connectors.iter import IterableSource

    test_signals = [
        {
            "signal_type": "funding_round",
            "source_name": "techcrunch",
            "title": "NeuralForge AI raises $50M Series B",
            "entity_name": "NeuralForge AI",
            "entity_type": "company",
            "raw_score": 85.0,
            "published_at": _now_iso(),
        },
        {
            "signal_type": "github_trend",
            "source_name": "github_trends",
            "title": "langchain reaches 50k stars",
            "entity_name": "LangChain",
            "entity_type": "technology",
            "raw_score": 70.0,
            "published_at": _now_iso(),
        },
        {
            "signal_type": "sec_filing",
            "source_name": "sec_edgar",
            "title": "CloudSync Inc files Form S-1",
            "entity_name": "CloudSync",
            "entity_type": "company",
            "raw_score": 90.0,
            "published_at": _now_iso(),
        },
    ]

    def signal_generator():
        for i in itertools.count():
            signal = test_signals[i % len(test_signals)].copy()
            signal["id"] = f"test-{i}"
            yield json.dumps(signal).encode("utf-8")
            time.sleep(5)  # Emit every 5 seconds for testing

    return IterableSource(signal_generator())


# ── Main ─────────────────────────────────────────────────────


def main():
    """Entry point: python -m stream.pipeline"""
    global _metrics_writer

    parser = argparse.ArgumentParser(description="Stream Processing Pipeline")
    parser.add_argument("--workers", type=int, default=1, help="Number of workers")
    parser.add_argument("--test", action="store_true", help="Use simulated input (no Kafka)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    if args.test:
        os.environ["KAFKA_BOOTSTRAP_SERVERS"] = "localhost:9999"  # Force simulated

    _logger.info("Starting stream processor (workers=%d, test=%s)", args.workers, args.test)

    # Start metrics writer
    config = _get_config()
    _metrics_writer = MetricsWriter(
        _metrics,
        redis_url=config["redis_url"],
        interval=30,
    )
    _metrics_writer.start()

    try:
        from bytewax import run
        flow = build_pipeline()
        _logger.info("Pipeline built — starting execution")
        run(flow)
    except ImportError:
        _logger.error("Bytewax not installed. Run: pip install bytewax>=0.16.0")
        sys.exit(1)
    except KeyboardInterrupt:
        _logger.info("Pipeline shutting down...")
    finally:
        _metrics_writer.stop()
        _logger.info("Pipeline stopped. Final metrics: %s", _metrics.to_dict())


if __name__ == "__main__":
    main()
