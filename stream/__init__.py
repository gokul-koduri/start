"""Stream processing package — Bytewax real-time signal pipeline.

Provides a 5-stage dataflow:
  Stage 1: Ingest — consume from Kafka (Redpanda) raw.signals topic
  Stage 2: Enrich — NLP entity extraction + sentiment scoring
  Stage 3: Aggregate — window-based signal grouping per entity
  Stage 4: Score   — composite scoring via CompositeScorer
  Stage 5: Output  — MySQL upsert + Kafka publish + alert emission

Run:
    python -m stream.pipeline              # Start stream processor
    python -m stream.pipeline --workers 2   # Multi-worker mode
"""
