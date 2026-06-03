"""LLM Cost Optimizer Agent — detects savings opportunities and price changes.

Monitors for:
1. Price drops across providers (>5% change triggers an alert)
2. "Good enough" alternatives — cheaper models that match >=85% quality
3. New models in the portfolio that offer better value
4. Portfolio rebalance recommendations when rankings change

Depends on:
    - llm_pricing table (current and historical pricing)
    - llm_benchmarks table (quality scores)
    - llm_portfolio table (current recommendations)

Runs weekly via the ``weekly`` pipeline, after ``llm_portfolio``.
"""

import json
import logging
from datetime import datetime, timezone, timedelta

from agents.base import AgentResult, BaseAgent
from db.connection import get_connection
from db import schema

_logger = logging.getLogger(__name__)


class LLMCostOptimizerAgent(BaseAgent):
    """Agent that detects cost optimization opportunities across LLM providers.

    Compares current pricing against historical data, finds cheaper alternatives
    that meet quality thresholds, and generates actionable alerts.

    Config options:
        price_change_threshold: minimum price change % to trigger alert (default: 0.05)
        quality_match_threshold: minimum quality ratio for "good enough" (default: 0.85)
        max_alerts: maximum alerts to generate per run (default: 20)
    """

    @property
    def name(self) -> str:
        return "llm_cost_optimizer"

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        price_threshold = self.config.get("price_change_threshold", 0.05)
        quality_threshold = self.config.get("quality_match_threshold", 0.85)
        max_alerts = self.config.get("max_alerts", 20)

        _logger.info("LLMCostOptimizerAgent: Scanning for optimization opportunities")

        try:
            conn = get_connection()
            schema.init_schema(conn)
        except Exception as e:
            _logger.error("LLMCostOptimizerAgent: Cannot connect to DB: %s", e)
            return AgentResult(agent_name=self.name, status="failed", errors=[str(e)])

        try:
            cursor = conn.cursor()
            alerts_generated = 0
            price_changes = 0
            savings_found = 0

            # ── Phase 1: Detect price changes ────────────────────────────────
            price_change_count = self._detect_price_changes(conn, price_threshold)
            price_changes = price_change_count

            # ── Phase 2: Find "good enough" cheaper alternatives ─────────────
            alternatives = self._find_better_alternatives(conn, quality_threshold)
            savings_found = len(alternatives)

            # ── Phase 3: Generate optimization alerts ────────────────────────
            for alt in alternatives[:max_alerts]:
                priority = self._compute_priority(alt)
                cursor.execute(
                    """INSERT INTO llm_optimization_alerts
                       (alert_type, title, description, affected_models,
                        estimated_savings_pct, priority, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (
                        alt["alert_type"],
                        alt["title"],
                        alt["description"],
                        json.dumps(alt.get("affected_models", [])),
                        alt.get("estimated_savings_pct", 0),
                        priority,
                        datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
                alerts_generated += 1

            # ── Phase 4: Check for new models (models in benchmarks not in pricing) ─
            new_model_alerts = self._detect_new_models(conn)
            for alert in new_model_alerts:
                cursor.execute(
                    """INSERT INTO llm_optimization_alerts
                       (alert_type, title, description, affected_models,
                        estimated_savings_pct, priority, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (
                        "new_model",
                        alert["title"],
                        alert["description"],
                        json.dumps(alert.get("affected_models", [])),
                        alert.get("estimated_savings_pct", 0),
                        "medium",
                        datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
                alerts_generated += 1

            conn.commit()

            # Summary stats
            total_savings = self._compute_total_savings(conn)

            _logger.info(
                "LLMCostOptimizerAgent: Done — %d price changes, %d alternatives found, "
                "%d alerts generated, ~%d%% potential savings",
                price_changes, savings_found, alerts_generated, total_savings,
            )

            return AgentResult(
                agent_name=self.name,
                status="success",
                data={
                    "price_changes_detected": price_changes,
                    "alternatives_found": savings_found,
                    "alerts_generated": alerts_generated,
                    "potential_savings_pct": total_savings,
                    "records_affected": alerts_generated,
                },
            )

        except Exception as e:
            _logger.error("LLMCostOptimizerAgent: Error: %s", e)
            return AgentResult(agent_name=self.name, status="failed", errors=[str(e)])
        finally:
            conn.close()

    def _detect_price_changes(self, conn, threshold: float) -> int:
        """Compare current pricing with the most recent price changes table.

        Uses the llm_pricing table's collected_at timestamp to detect when prices
        have been updated and logs any changes.
        """
        cursor = conn.cursor()

        # Get current pricing grouped by provider + model
        cursor.execute(
            "SELECT provider, model_name, input_price_per_1m, output_price_per_1m, "
            "collected_at FROM llm_pricing ORDER BY provider, model_name"
        )
        current = [dict(r) for r in cursor.fetchall()]

        # Check for existing price change records to avoid duplicates
        cursor.execute(
            "SELECT provider, model_name, new_input_price, new_output_price "
            "FROM llm_price_changes ORDER BY detected_at DESC"
        )
        previous = [dict(r) for r in cursor.fetchall()]

        # Build lookup of previous prices
        prev_lookup = {}
        for p in previous:
            prev_lookup[(p["provider"], p["model_name"])] = (
                p["new_input_price"], p["new_output_price"],
            )

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        change_count = 0

        for curr in current:
            key = (curr["provider"], curr["model_name"])
            if key in prev_lookup:
                old_in, old_out = prev_lookup[key]
                new_in = curr["input_price_per_1m"]
                new_out = curr["output_price_per_1m"]

                # Compute percentage change
                in_change = 0
                out_change = 0
                if old_in > 0:
                    in_change = (new_in - old_in) / old_in
                if old_out > 0:
                    out_change = (new_out - old_out) / old_out

                # Only record significant changes
                if abs(in_change) >= threshold or abs(out_change) >= threshold:
                    cursor.execute(
                        """INSERT INTO llm_price_changes
                           (provider, model_name, old_input_price, old_output_price,
                            new_input_price, new_output_price, input_change_pct,
                            output_change_pct, detected_at)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (
                            curr["provider"], curr["model_name"],
                            old_in, old_out, new_in, new_out,
                            round(in_change * 100, 1), round(out_change * 100, 1),
                            now,
                        ),
                    )
                    change_count += 1

        return change_count

    def _find_better_alternatives(self, conn, quality_threshold: float) -> list[dict]:
        """Find cheaper models that meet quality threshold of expensive ones.

        For each model above $1/1M tokens, checks if a cheaper model has
        >= quality_threshold * quality score.
        """
        cursor = conn.cursor()

        # Get all models with pricing
        cursor.execute(
            "SELECT provider, model_name, input_price_per_1m, output_price_per_1m, "
            "context_window FROM llm_pricing WHERE pricing_tier != 'self-hosted' "
            "ORDER BY (input_price_per_1m + output_price_per_1m) DESC"
        )
        all_models = [dict(r) for r in cursor.fetchall()]

        # Get benchmark quality scores
        cursor.execute(
            "SELECT provider, model_name, benchmark_category, AVG(benchmark_score) as avg_score "
            "FROM llm_benchmarks GROUP BY provider, model_name, benchmark_category"
        )
        benchmark_rows = [dict(r) for r in cursor.fetchall()]

        # Build quality lookup: (provider, model) -> list of (category, score)
        quality_lookup: dict[tuple, list[tuple]] = {}
        for row in benchmark_rows:
            key = (row["provider"], row["model_name"])
            if key not in quality_lookup:
                quality_lookup[key] = []
            quality_lookup[key].append((row["benchmark_category"], row["avg_score"]))

        # Compute overall quality per model (max across categories)
        model_quality: dict[tuple, float] = {}
        for key, scores in quality_lookup.items():
            model_quality[key] = max(s for _, s in scores) if scores else 0

        alternatives: list[dict] = []

        # For each "expensive" model (cost > $1/1M blended), find cheaper alternatives
        for expensive in all_models:
            exp_key = (expensive["provider"], expensive["model_name"])
            exp_cost = expensive["input_price_per_1m"] + expensive["output_price_per_1m"]

            if exp_cost <= 1.0:
                continue  # Skip already-cheap models

            exp_quality = model_quality.get(exp_key, 0)
            if exp_quality <= 0:
                continue  # Skip models without benchmark data

            for candidate in all_models:
                cand_key = (candidate["provider"], candidate["model_name"])
                cand_cost = candidate["input_price_per_1m"] + candidate["output_price_per_1m"]

                # Candidate must be significantly cheaper
                if cand_cost >= exp_cost * 0.8:
                    continue

                cand_quality = model_quality.get(cand_key, 0)
                if cand_quality <= 0:
                    continue

                # Check if candidate meets quality threshold
                quality_ratio = cand_quality / exp_quality if exp_quality > 0 else 0

                if quality_ratio >= quality_threshold:
                    savings_pct = round((1 - cand_cost / exp_cost) * 100, 0)

                    alternatives.append({
                        "alert_type": "better_alternative",
                        "title": (
                            f"{candidate['model_name']} ({candidate['provider']}) is "
                            f"{quality_ratio:.0%} as good as {expensive['model_name']} "
                            f"but {savings_pct:.0f}% cheaper"
                        ),
                        "description": (
                            f"Quality: {cand_quality:.1f} vs {exp_quality:.1f} "
                            f"(ratio: {quality_ratio:.0%}). "
                            f"Cost: ${cand_cost:.2f}/1M vs ${exp_cost:.2f}/1M tokens. "
                            f"Savings: {savings_pct:.0f}%."
                        ),
                        "affected_models": [
                            expensive["model_name"], candidate["model_name"],
                        ],
                        "estimated_savings_pct": savings_pct,
                        "expensive_model": expensive["model_name"],
                        "alternative_model": candidate["model_name"],
                    })

        # Deduplicate: keep only the best alternative per expensive model
        best_alternatives: dict[str, dict] = {}
        for alt in alternatives:
            exp_model = alt["expensive_model"]
            if exp_model not in best_alternatives or alt["estimated_savings_pct"] > best_alternatives[exp_model]["estimated_savings_pct"]:
                best_alternatives[exp_model] = alt

        return list(best_alternatives.values())

    def _detect_new_models(self, conn) -> list[dict]:
        """Detect models in benchmarks that don't appear in pricing table."""
        cursor = conn.cursor()

        cursor.execute("SELECT DISTINCT model_name FROM llm_benchmarks")
        benchmark_models = {r["model_name"] for r in cursor.fetchall()}

        cursor.execute("SELECT DISTINCT model_name FROM llm_pricing")
        pricing_models = {r["model_name"] for r in cursor.fetchall()}

        new_models = benchmark_models - pricing_models
        alerts = []

        if new_models:
            alerts.append({
                "title": f"{len(new_models)} new model(s) detected in benchmarks",
                "description": (
                    f"Models found in benchmark data but not yet in pricing: "
                    f"{', '.join(sorted(new_models)[:10])}. "
                    f"Consider adding pricing data for these models."
                ),
                "affected_models": sorted(new_models),
            })

        return alerts

    def _compute_priority(self, alt: dict) -> str:
        """Compute alert priority based on savings and type."""
        savings = alt.get("estimated_savings_pct", 0)

        if savings >= 80:
            return "critical"
        if savings >= 50:
            return "high"
        if savings >= 25:
            return "medium"
        return "low"

    def _compute_total_savings(self, conn) -> int:
        """Compute aggregate potential savings percentage from active alerts."""
        cursor = conn.cursor()
        cursor.execute(
            "SELECT AVG(estimated_savings_pct) FROM llm_optimization_alerts "
            "WHERE dismissed = 0 AND alert_type = 'better_alternative'"
        )
        row = cursor.fetchone()
        if row and row[0]:
            return int(row[0])
        return 0
