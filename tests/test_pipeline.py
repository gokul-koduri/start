"""Tests for the stream processing pipeline.

Tests operators, state management, and metrics without requiring
a running Kafka or Bytewax cluster. All tests use mocked sources.
"""

import json
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from ingestion.signal_normalizer import SignalEnvelope, normalize_signal
from stream.operators import (
    parse_signal_envelope,
    enrich_signal,
    build_signal_scores,
    score_entity,
    emit_alert,
    _parse_datetime,
)
from stream.state import (
    EntityState,
    init_entity_state,
    update_entity_state,
)
from stream.metrics import PipelineMetrics, MetricsWriter


# ── parse_signal_envelope ────────────────────────────────────


class TestParseSignalEnvelope:
    def test_valid_minimal(self):
        data = json.dumps({
            "signal_type": "funding_round",
            "source_name": "techcrunch",
        }).encode()
        entity, envelope = parse_signal_envelope(data)
        assert entity == "unknown"
        assert isinstance(envelope, SignalEnvelope)
        assert envelope.signal_type == "funding_round"

    def test_valid_full(self):
        now = datetime.now(timezone.utc)
        data = json.dumps({
            "signal_type": "github_trend",
            "source_name": "github_trends",
            "title": "langchain hits 50k stars",
            "entity_name": "LangChain",
            "entity_type": "technology",
            "raw_score": 75.0,
            "published_at": now.isoformat(),
            "metadata": {"stars": 50000},
        }).encode()
        entity, envelope = parse_signal_envelope(data)
        assert entity == "LangChain"  # entity_name preserved as-is
        assert envelope.entity_name == "LangChain"
        assert envelope.raw_score == 75.0

    def test_invalid_json(self):
        with pytest.raises(ValueError, match="Invalid JSON"):
            parse_signal_envelope(b"not json")

    def test_missing_required_fields(self):
        with pytest.raises(ValueError, match="Missing required fields"):
            parse_signal_envelope(b'{"signal_type": "funding"}')

    def test_empty_entity_defaults_to_unknown(self):
        data = json.dumps({
            "signal_type": "news_mention",
            "source_name": "news",
            "entity_name": "  ",
        }).encode()
        entity, envelope = parse_signal_envelope(data)
        assert entity == "unknown"


# ── enrich_signal ────────────────────────────────────────────


class TestEnrichSignal:
    def test_adds_positive_sentiment(self):
        envelope = normalize_signal(
            "funding_round", "techcrunch",
            title="NeuralForge raises $50M Series B",
            body_text="The company raised funding to expand growth",
        )
        enriched = enrich_signal(envelope)
        assert enriched.metadata["stream_enriched"] is True
        assert enriched.metadata["stream_sentiment"] > 0  # "raised", "funding", "growth"

    def test_adds_negative_sentiment(self):
        envelope = normalize_signal(
            "news_mention", "news",
            title="Startup lays off 200 workers",
            body_text="The company announced layoffs and shut down operations",
        )
        enriched = enrich_signal(envelope)
        assert enriched.metadata["stream_sentiment"] < 0  # "lays off", "shut down"

    def test_neutral_sentiment(self):
        envelope = normalize_signal(
            "github_trend", "github",
            title="Repo updated readme",
        )
        enriched = enrich_signal(envelope)
        assert enriched.metadata["stream_sentiment"] == 0.0

    def test_preserves_original_data(self):
        envelope = normalize_signal(
            "sec_filing", "sec_edgar",
            title="Form S-1 filed",
            entity_name="TestCorp",
            raw_score=80.0,
        )
        enriched = enrich_signal(envelope)
        assert enriched.entity_name == "TestCorp"
        assert enriched.raw_score == 80.0


# ── build_signal_scores ─────────────────────────────────────


class TestBuildSignalScores:
    def test_keeps_highest_score_per_type(self):
        now = datetime.now(timezone.utc)
        signals = [
            SignalEnvelope("funding_round", "tc", raw_score=90.0, published_at=now),
            SignalEnvelope("funding_round", "tc", raw_score=70.0, published_at=now - timedelta(days=1)),
            SignalEnvelope("news_mention", "news", raw_score=50.0, published_at=now),
        ]
        scores = build_signal_scores(signals)
        assert scores["funding_round"]["raw_score"] == 90.0  # Highest wins
        assert scores["news_mention"]["raw_score"] == 50.0

    def test_empty_signals(self):
        scores = build_signal_scores([])
        assert scores == {}


# ── score_entity ─────────────────────────────────────────────


class TestScoreEntity:
    def test_single_signal(self):
        now = datetime.now(timezone.utc)
        signals = [
            SignalEnvelope(
                "funding_round", "techcrunch",
                entity_name="TestCorp",
                raw_score=90.0,
                published_at=now,
            ),
        ]
        result = score_entity("TestCorp", signals)
        assert result["composite_score"] > 0
        assert result["signal_count"] == 1
        assert result["entity_name"] == "TestCorp"

    def test_empty_signals(self):
        result = score_entity("EmptyCorp", [])
        assert result["composite_score"] == 0.0
        assert result["signal_count"] == 0

    def test_multiple_signals(self):
        now = datetime.now(timezone.utc)
        signals = [
            SignalEnvelope("funding_round", "tc", raw_score=90.0, published_at=now),
            SignalEnvelope("sec_filing", "sec", raw_score=75.0, published_at=now - timedelta(days=1)),
            SignalEnvelope("github_trend", "gh", raw_score=65.0, published_at=now - timedelta(days=3)),
        ]
        result = score_entity("MultiCorp", signals)
        assert result["composite_score"] > 0
        assert result["signal_count"] == 3


# ── emit_alert ───────────────────────────────────────────────


class TestEmitAlert:
    def test_score_above_threshold(self):
        scored = {
            "entity_name": "HotCorp",
            "composite_score": 85.0,
            "signal_count": 5,
            "trend_direction": "rising",
        }
        alert = emit_alert(scored, threshold=80.0)
        assert alert is not None
        assert alert["alert_type"] == "high_value_opportunity"
        assert alert["entity_name"] == "HotCorp"

    def test_score_below_threshold(self):
        scored = {
            "entity_name": "LowCorp",
            "composite_score": 45.0,
        }
        alert = emit_alert(scored, threshold=80.0)
        assert alert is None

    def test_custom_threshold(self):
        scored = {"entity_name": "MedCorp", "composite_score": 70.0}
        assert emit_alert(scored, threshold=75.0) is None
        assert emit_alert(scored, threshold=65.0) is not None


# ── EntityState ──────────────────────────────────────────────


class TestEntityState:
    def test_init(self):
        state = init_entity_state("TestCorp")
        assert state.entity_name == "TestCorp"
        assert state.signals == []
        assert state.total_processed == 0

    def test_add_signal(self):
        state = init_entity_state("TestCorp")
        state.add_signal({"signal_type": "funding", "raw_score": 80})
        state.add_signal({"signal_type": "news", "raw_score": 60})
        assert state.total_processed == 2
        assert len(state.signals) == 2

    def test_max_signals(self):
        state = init_entity_state("TestCorp")
        for i in range(150):
            state.add_signal({"signal_type": "test", "raw_score": i})
        assert len(state.signals) == 100  # MAX_SIGNALS
        # Should keep the last 100 (FIFO)
        assert state.signals[-1]["raw_score"] == 149

    def test_update_score(self):
        state = init_entity_state("TestCorp")
        state.update_score(75.5)
        assert state.last_score == 75.5
        assert len(state.score_history) == 1
        state.update_score(80.0)
        assert state.last_score == 80.0

    def test_get_score_history(self):
        state = init_entity_state("TestCorp")
        state.add_signal({"signal_type": "funding", "raw_score": 80})
        state.add_signal({"signal_type": "funding", "raw_score": 70})
        state.add_signal({"signal_type": "news", "raw_score": 50})
        history = state.get_score_history()
        assert "funding" in history
        assert len(history["funding"]) == 2
        assert "news" in history
        assert len(history["news"]) == 1

    def test_update_entity_state_operator(self):
        state = init_entity_state("TestCorp")
        new_signals = [
            {"signal_type": "funding", "raw_score": 90},
            {"signal_type": "news", "raw_score": 60},
        ]
        updated, all_signals = update_entity_state(state, new_signals)
        assert updated.total_processed == 2
        assert len(all_signals) == 2


# ── PipelineMetrics ──────────────────────────────────────────


class TestPipelineMetrics:
    def test_increment(self):
        metrics = PipelineMetrics()
        metrics.increment("signals_processed")
        metrics.increment("signals_processed")
        assert metrics.signals_processed == 2

    def test_multiple_counters(self):
        metrics = PipelineMetrics()
        metrics.increment("signals_processed", 5)
        metrics.increment("signals_errored", 2)
        metrics.increment("entities_scored")
        assert metrics.signals_processed == 5
        assert metrics.signals_errored == 2
        assert metrics.entities_scored == 1

    def test_to_dict(self):
        metrics = PipelineMetrics()
        d = metrics.to_dict()
        assert "signals_processed" in d
        assert "throughput_per_minute" in d
        assert "started_at" in d

    def test_from_dict_roundtrip(self):
        original = PipelineMetrics(signals_processed=42, entities_scored=7)
        d = original.to_dict()
        restored = PipelineMetrics.from_dict(d)
        assert restored.signals_processed == 42
        assert restored.entities_scored == 7

    def test_compute_throughput(self):
        import time
        metrics = PipelineMetrics()
        metrics._prev_time = time.time() - 60  # 60s ago
        metrics._prev_count = 0
        metrics.increment("signals_processed", 120)
        metrics.compute_throughput()
        assert metrics.throughput_per_minute == 120.0


# ── Pipeline Stage Operators ────────────────────────────────


class TestPipelineOperators:
    """Test the stage operator functions from pipeline.py."""

    def _import_pipeline_ops(self):
        from stream import pipeline
        return pipeline

    def test_op_ingest_valid(self):
        from stream.pipeline import _op_ingest
        data = json.dumps({
            "signal_type": "funding_round",
            "source_name": "tc",
            "entity_name": "TestCorp",
        }).encode()
        entity, signal = _op_ingest(data)
        assert entity == "TestCorp"
        assert signal["signal_type"] == "funding_round"

    def test_op_ingest_invalid_json(self):
        from stream.pipeline import _op_ingest
        entity, signal = _op_ingest(b"bad data")
        assert entity == "__dlq__"
        assert "error" in signal

    def test_op_enrich_passes_dlq(self):
        from stream.pipeline import _op_enrich
        result = _op_enrich(("__dlq__", {"error": "test"}))
        assert result[0] == "__dlq__"

    def test_op_enrich_valid(self):
        from stream.pipeline import _op_enrich
        result = _op_enrich((
            "TestCorp",
            {"signal_type": "funding_round", "source_name": "tc", "title": "Raises $50M",
             "entity_name": "TestCorp"},
        ))
        assert result[0] == "TestCorp"
        assert result[1]["metadata"]["stream_enriched"] is True

    def test_op_score_valid(self):
        from stream.pipeline import _op_score
        now = datetime.now(timezone.utc).isoformat()
        entity, scored = _op_score((
            "TestCorp",
            [{"signal_type": "funding_round", "raw_score": 90, "published_at": now}],
        ))
        assert entity == "TestCorp"
        assert scored["composite_score"] > 0

    def test_op_score_empty(self):
        from stream.pipeline import _op_score
        entity, scored = _op_score(("EmptyCorp", []))
        assert scored["composite_score"] == 0.0

    def test_op_emit_alert_above(self):
        from stream.pipeline import _op_emit_alert
        result = _op_emit_alert(("HotCorp", {"composite_score": 85}))
        assert result is not None
        assert result[1]["alert_type"] == "high_value_opportunity"

    def test_op_emit_alert_below(self):
        from stream.pipeline import _op_emit_alert
        result = _op_emit_alert(("LowCorp", {"composite_score": 45}))
        assert result is None
