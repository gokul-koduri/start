"""Opportunity Scorer Agent — wraps the composite scoring engine.

This agent orchestrates the full scoring pipeline:
1. Load unprocessed raw_signals from the database
2. Group signals by entity (company/technology/market)
3. For each entity, compute the composite opportunity score
4. Write scored results to opportunity_scores table
5. Mark processed signals to avoid re-scoring

The agent is designed to run in the analysis pipeline after collectors
have populated raw_signals. In Phase 3, this logic moves into the
Bytewax stream processor for real-time scoring.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from agents.base import AgentResult, BaseAgent
from db.connection import get_connection
from db import schema
from scoring.composite_scorer import CompositeScorer

_logger = logging.getLogger(__name__)


class OpportunityScorerAgent(BaseAgent):
    """Scores entities based on multi-signal composite scoring.

    Reads from raw_signals (unprocessed), applies the CompositeScorer,
    and writes results to opportunity_scores. This is the central
    intelligence engine of the Opportunity Intelligence Platform.
    """

    @property
    def name(self) -> str:
        return "opportunity_scorer"

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        """Run the scoring pipeline.

        Args:
            upstream_results: Optional results from upstream agents (ignored).

        Returns:
            AgentResult with scoring statistics.
        """
        result = AgentResult(
            agent_name=self.name,
            started_at=datetime.now(timezone.utc).isoformat(),
        )

        try:
            conn = get_connection()
            schema.init_schema(conn)
            cursor = conn.cursor()

            scorer = CompositeScorer()

            # ── Step 1: Load unprocessed signals grouped by entity ──
            entity_signals = self._load_unprocessed_signals(cursor)

            if not entity_signals:
                _logger.info("No unprocessed signals to score")
                result.status = "success"
                result.data["entities_scored"] = 0
                result.completed_at = datetime.now(timezone.utc).isoformat()
                conn.close()
                return result

            _logger.info(
                "Scoring %d entities from %d signals",
                len(entity_signals),
                sum(len(v) for v in entity_signals.values()),
            )

            # ── Step 2: Score each entity ──
            scored_count = 0
            high_value_count = 0

            for entity_name, signals in entity_signals.items():
                try:
                    # Build signal_scores dict for the scorer
                    signal_scores = self._build_signal_scores(signals)
                    historical_values = self._build_historical_values(
                        cursor, entity_name, signals
                    )

                    # Compute composite score
                    score_result = scorer.score(
                        entity_name=entity_name,
                        entity_type=self._infer_entity_type(signals),
                        signal_scores=signal_scores,
                        historical_values=historical_values,
                    )

                    # Upsert to opportunity_scores
                    self._upsert_score(cursor, score_result, signals)

                    # Track high-value opportunities
                    if score_result.composite_score >= 70:
                        high_value_count += 1
                        _logger.info(
                            "🔥 HIGH VALUE: %s — score=%.1f (%s, %d signals)",
                            entity_name,
                            score_result.composite_score,
                            score_result.trend_direction,
                            score_result.signal_count,
                        )

                    scored_count += 1

                except Exception as e:
                    result.errors.append(f"Error scoring {entity_name}: {e}")
                    _logger.warning("Scoring error for %s: %s", entity_name, e)

            # ── Step 3: Mark signals as processed ──
            self._mark_signals_processed(cursor, entity_signals)

            conn.commit()
            cursor.close()
            conn.close()

            result.status = "success"
            result.data = {
                "entities_scored": scored_count,
                "total_signals_processed": sum(len(v) for v in entity_signals.values()),
                "high_value_opportunities": high_value_count,
            }

            _logger.info(
                "=== OpportunityScorer: %d entities scored, %d high-value (≥70) ===",
                scored_count,
                high_value_count,
            )

        except Exception as e:
            result.status = "failed"
            result.errors.append(str(e))
            _logger.error("OpportunityScorer failed: %s", e)

        result.completed_at = datetime.now(timezone.utc).isoformat()
        return result

    def _load_unprocessed_signals(self, cursor) -> dict[str, list[dict]]:
        """Load unprocessed signals from raw_signals, grouped by entity_name."""
        cursor.execute(
            """SELECT id, signal_type, source_name, source_url, title, body_text,
                      entity_name, published_at, collected_at
               FROM raw_signals
               WHERE processed = 0 AND entity_name IS NOT NULL AND entity_name != ''
               ORDER BY entity_name, published_at DESC"""
        )

        rows = cursor.fetchall()
        entity_signals: dict[str, list[dict]] = defaultdict(list)

        for row in rows:
            entity_name = row["entity_name"].strip()
            if entity_name:
                entity_signals[entity_name].append(dict(row))

        return dict(entity_signals)

    def _build_signal_scores(self, signals: list[dict]) -> dict[str, dict[str, Any]]:
        """Convert raw signal rows into the format expected by CompositeScorer.

        For each signal type, keep the most recent signal with its raw_score.
        Raw scores are computed from basic heuristics:
          - funding_round: based on amount
          - sec_filing: based on filing type weight
          - job_posting_spike: based on count
          - github_trend: based on star velocity
          - news_mention: based on recency
        """
        signal_scores: dict[str, dict[str, Any]] = {}

        # Group by signal_type, keep most recent
        by_type: dict[str, dict] = {}
        for signal in signals:
            stype = signal["signal_type"]
            if stype not in by_type:
                by_type[stype] = signal
            # Keep most recent
            if signal.get("published_at") and by_type[stype].get("published_at"):
                if signal["published_at"] > by_type[stype]["published_at"]:
                    by_type[stype] = signal

        for stype, signal in by_type.items():
            raw_score = self._compute_raw_score(stype, signal)
            published_at = None
            if signal.get("published_at"):
                try:
                    published_at = datetime.fromisoformat(
                        signal["published_at"].replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    published_at = None

            signal_scores[stype] = {
                "raw_score": raw_score,
                "published_at": published_at,
                "signal_id": signal.get("id"),
            }

        return signal_scores

    def _compute_raw_score(self, signal_type: str, signal: dict) -> float:
        """Compute a heuristic raw_score (0-100) for a signal.

        These are quick heuristics before full NLP processing in Phase 2.
        """
        text = f"{signal.get('title', '')} {signal.get('body_text', '')}".lower()

        if signal_type == "funding_round":
            # Higher score for larger funding rounds
            return 85.0  # Default high score — amount parsing added in Phase 2

        elif signal_type == "sec_filing":
            filing_type = text.lower()
            if "10-k" in filing_type:
                return 80.0
            if "8-k" in filing_type:
                return 70.0
            if "s-1" in filing_type:
                return 90.0  # IPO filing is very significant
            return 60.0

        elif signal_type == "job_posting_spike":
            # Score based on number of postings for this entity
            return min(100.0, 50.0 + len(text.split()) * 0.5)

        elif signal_type == "github_trend":
            return 65.0  # Default — enhanced with star velocity in Phase 2

        elif signal_type == "news_mention":
            return 55.0  # Default — enhanced with sentiment in Phase 2

        elif signal_type == "patent_filed":
            return 75.0  # Patents are inherently significant

        elif signal_type == "social_buzz":
            return 40.0  # Low weight by default

        else:
            return 50.0

    def _build_historical_values(
        self, cursor, entity_name: str, current_signals: list[dict]
    ) -> dict[str, list[float]]:
        """Load historical signal counts for anomaly detection.

        For each signal type, fetch daily counts from the past 30 days.
        This enables Z-score anomaly detection in the scoring engine.
        """
        historical: dict[str, list[float]] = {}

        # Get signal types present in current data
        signal_types = set(s["signal_type"] for s in current_signals)

        for stype in signal_types:
            cursor.execute(
                """SELECT DATE(collected_at) as day, COUNT(*) as cnt
                   FROM raw_signals
                   WHERE entity_name = %s AND signal_type = %s
                     AND collected_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                   GROUP BY DATE(collected_at)
                   ORDER BY day""",
                (entity_name, stype),
            )
            rows = cursor.fetchall()
            historical[stype] = [float(r["cnt"]) for r in rows]

        return historical

    def _infer_entity_type(self, signals: list[dict]) -> str:
        """Infer entity type from signal patterns."""
        signal_types = set(s["signal_type"] for s in signals)

        if "github_trend" in signal_types:
            return "technology"
        if "funding_round" in signal_types or "sec_filing" in signal_types:
            return "company"
        return "company"  # Default

    def _upsert_score(self, cursor, score_result, signals: list[dict]) -> None:
        """Insert or update the opportunity_scores table."""
        signal_types_list = list(set(s["signal_type"] for s in signals))
        signal_weights_json = json.dumps(
            {
                a.signal_type: {
                    "weight": a.weight,
                    "contribution": round(a.contribution, 2),
                }
                for a in score_result.attribution
            }
        )
        attribution_json = json.dumps([a.to_dict() for a in score_result.attribution])

        cursor.execute(
            """INSERT INTO opportunity_scores
               (entity_name, entity_type, composite_score, raw_weighted_score,
                signal_count, signal_types_json, signal_weights_json,
                freshness_score, anomaly_z_score, anomaly_type,
                trend_direction, confidence, attribution_json, scored_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
                 composite_score = VALUES(composite_score),
                 raw_weighted_score = VALUES(raw_weighted_score),
                 signal_count = VALUES(signal_count),
                 signal_types_json = VALUES(signal_types_json),
                 signal_weights_json = VALUES(signal_weights_json),
                 freshness_score = VALUES(freshness_score),
                 anomaly_z_score = VALUES(anomaly_z_score),
                 anomaly_type = VALUES(anomaly_type),
                 trend_direction = VALUES(trend_direction),
                 confidence = VALUES(confidence),
                 attribution_json = VALUES(attribution_json),
                 scored_at = VALUES(scored_at),
                 updated_at = NOW()""",
            (
                score_result.entity_name,
                score_result.entity_type,
                score_result.composite_score,
                score_result.raw_weighted_score,
                score_result.signal_count,
                json.dumps(signal_types_list),
                signal_weights_json,
                sum(a.freshness for a in score_result.attribution)
                / len(score_result.attribution)
                if score_result.attribution
                else 0.0,
                score_result.anomaly.z_score if score_result.anomaly else None,
                score_result.anomaly.anomaly_type if score_result.anomaly else None,
                score_result.trend_direction,
                score_result.confidence,
                attribution_json,
                datetime.now(timezone.utc).isoformat(),
            ),
        )

    def _mark_signals_processed(
        self, cursor, entity_signals: dict[str, list[dict]]
    ) -> None:
        """Mark all scored signals as processed."""
        signal_ids = []
        for signals in entity_signals.values():
            signal_ids.extend(s["id"] for s in signals)

        if signal_ids:
            # Process in batches of 500
            batch_size = 500
            for i in range(0, len(signal_ids), batch_size):
                batch = signal_ids[i : i + batch_size]
                placeholders = ",".join(["%s"] * len(batch))
                cursor.execute(
                    f"UPDATE raw_signals SET processed = 1 WHERE id IN ({placeholders})",
                    batch,
                )
