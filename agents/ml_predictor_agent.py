"""ML Predictor Agent — scores startups using trained ML models.

Loads the best available model (XGBoost > Random Forest) and scores
all startups in failed_startups. Falls back to rule-based heuristic
if no trained model is available.

Run:
    python run_agent.py --pipeline analysis   (includes ml_predictor agent)
"""

import json
import logging
from datetime import datetime, timezone

from agents.base import AgentResult, BaseAgent
from agents.risk_scorer_agent import score_startup
from agents.ml_trainer_agent import MLTrainer, _build_features
from db.connection import get_connection
from db import schema

_logger = logging.getLogger(__name__)


class MLPredictorAgent(BaseAgent):
    """Scores startups using trained ML models for failure prediction.

    Pipeline position: runs after ml_trainer in the analysis pipeline.
    Falls back to rule-based heuristic if no model is available.
    """

    @property
    def name(self) -> str:
        return "ml_predictor"

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        _logger.info("MLPredictorAgent: Starting ML-based risk scoring")

        try:
            conn = get_connection()
            schema.init_schema(conn)
        except Exception as e:
            return AgentResult(agent_name=self.name, status="failed", errors=[str(e)])

        # Load trained model
        trainer = MLTrainer(self.config)
        model, model_name, features = trainer.load_best_model()

        if model is None:
            _logger.info("MLPredictorAgent: No trained model found — skipping")
            return AgentResult(
                agent_name=self.name,
                status="success",
                data={
                    "skipped": True,
                    "reason": "no_trained_model",
                    "records_affected": 0,
                },
            )

        _logger.info("MLPredictorAgent: Using model %s", model_name)

        try:
            cursor = conn.cursor()

            # Fetch all startups
            cursor.execute(
                """SELECT id, sector, manufacturing_sub_sector, country, region,
                          funding_raised_usd, year_founded, year_shutdown, failure_reason
                   FROM failed_startups"""
            )
            startups = [dict(r) for r in cursor.fetchall()]

            if not startups:
                return AgentResult(
                    agent_name=self.name,
                    status="success",
                    data={"scored": 0, "records_affected": 0},
                )

            scored = 0
            level_counts = {}

            for s in startups:
                # Build feature vector
                feat_dict = _build_features(s)
                feat_vector = [[feat_dict[col] for col in features]]

                # Predict failure probability
                try:
                    proba = model.predict_proba(feat_vector)[0]
                    # Probability of class 1 (failure)
                    failure_prob = proba[1] if len(proba) > 1 else proba[0]
                except Exception:
                    # Some models don't have predict_proba
                    pred = model.predict(feat_vector)[0]
                    failure_prob = float(pred)

                # Also get heuristic for comparison and recommendation
                heuristic = score_startup(
                    sector=s.get("sector", ""),
                    funding_usd=s.get("funding_raised_usd"),
                    country=s.get("country", ""),
                    region=s.get("region", ""),
                    year_founded=s.get("year_founded"),
                    failure_reason=s.get("failure_reason", ""),
                )

                # Blend: 70% ML, 30% heuristic for robustness
                blended_score = 0.7 * failure_prob + 0.3 * heuristic["risk_score"]
                blended_score = min(1.0, max(0.0, blended_score))

                # Risk level
                if blended_score >= 0.75:
                    risk_level = "critical"
                elif blended_score >= 0.60:
                    risk_level = "high"
                elif blended_score >= 0.45:
                    risk_level = "moderate"
                else:
                    risk_level = "low"

                level_counts[risk_level] = level_counts.get(risk_level, 0) + 1

                if not self.dry_run:
                    cursor.execute(
                        """INSERT INTO startup_risk_scores
                           (startup_id, risk_score, risk_level, factors_json,
                            recommendation, scored_at, model_name, model_version, confidence)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                           ON DUPLICATE KEY UPDATE
                           risk_score = VALUES(risk_score),
                           risk_level = VALUES(risk_level),
                           factors_json = VALUES(factors_json),
                           recommendation = VALUES(recommendation),
                           scored_at = VALUES(scored_at),
                           model_name = VALUES(model_name),
                           model_version = VALUES(model_version),
                           confidence = VALUES(confidence)""",
                        (
                            s["id"],
                            round(blended_score, 3),
                            risk_level,
                            json.dumps(heuristic["factors"]),
                            heuristic["recommendation"],
                            datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                            model_name,
                            "1.0",
                            round(failure_prob, 3),
                        ),
                    )
                scored += 1

            if not self.dry_run:
                conn.commit()

            _logger.info(
                "MLPredictorAgent: Scored %d startups with %s — %s",
                scored,
                model_name,
                level_counts,
            )

            return AgentResult(
                agent_name=self.name,
                status="success",
                data={
                    "scored": scored,
                    "model_used": model_name,
                    "level_distribution": level_counts,
                    "records_affected": scored,
                },
            )

        except Exception as e:
            _logger.error("MLPredictorAgent: Error: %s", e)
            return AgentResult(agent_name=self.name, status="failed", errors=[str(e)])
        finally:
            conn.close()
