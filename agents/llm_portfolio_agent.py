"""LLM Portfolio Agent — recommends optimal model mix per task category.

Treats LLM models like a stock portfolio: for each task category (code generation,
summarization, analysis, etc.), ranks all available models by a weighted composite
score and recommends allocation percentages.

The composite score formula:
    composite = (quality_score * w_q) + (cost_score * w_c)
             + (speed_score * w_s) + (context_score * w_ctx)

Weights vary by task category — coding needs quality, summarization needs cost.

Depends on:
    - llm_pricing table (populated by LLMPricingAgent)
    - llm_benchmarks table (populated by LLMBenchmarkAgent)

Runs weekly via the ``weekly`` pipeline, after ``llm_benchmark``.
"""

import json
import logging
from datetime import datetime, timezone

from agents.base import AgentResult, BaseAgent
from db.connection import get_connection
from db import schema

_logger = logging.getLogger(__name__)

# ── Task categories with per-category scoring weights ──────────────────────
# Each category defines how important quality vs cost vs speed vs context is.
TASK_CATEGORIES: dict[str, dict] = {
    "code_generation": {
        "label": "Code Generation",
        "weight_quality": 0.50, "weight_cost": 0.25, "weight_speed": 0.15, "weight_context": 0.10,
        "icon": "💻",
        "relevant_benchmarks": ["HumanEval", "MBPP", "SWE-bench"],
    },
    "code_review": {
        "label": "Code Review",
        "weight_quality": 0.40, "weight_cost": 0.30, "weight_speed": 0.20, "weight_context": 0.10,
        "icon": "🔍",
        "relevant_benchmarks": ["HumanEval", "MBPP"],
    },
    "summarization": {
        "label": "Summarization",
        "weight_quality": 0.30, "weight_cost": 0.40, "weight_speed": 0.20, "weight_context": 0.10,
        "icon": "📝",
        "relevant_benchmarks": ["MMLU", "IFEval"],
    },
    "analysis_reasoning": {
        "label": "Analysis & Reasoning",
        "weight_quality": 0.60, "weight_cost": 0.15, "weight_speed": 0.10, "weight_context": 0.15,
        "icon": "🧠",
        "relevant_benchmarks": ["GPQA", "MMLU", "MATH"],
    },
    "creative_writing": {
        "label": "Creative Writing",
        "weight_quality": 0.40, "weight_cost": 0.30, "weight_speed": 0.15, "weight_context": 0.15,
        "icon": "✍️",
        "relevant_benchmarks": ["MMLU", "IFEval"],
    },
    "data_extraction": {
        "label": "Data Extraction",
        "weight_quality": 0.30, "weight_cost": 0.40, "weight_speed": 0.20, "weight_context": 0.10,
        "icon": "📊",
        "relevant_benchmarks": ["MMLU", "IFEval"],
    },
    "rag_qa": {
        "label": "RAG & Q&A",
        "weight_quality": 0.30, "weight_cost": 0.25, "weight_speed": 0.15, "weight_context": 0.30,
        "icon": "📚",
        "relevant_benchmarks": ["MMLU", "LongBench"],
    },
    "chatbot_general": {
        "label": "Chatbot / General",
        "weight_quality": 0.30, "weight_cost": 0.40, "weight_speed": 0.20, "weight_context": 0.10,
        "icon": "💬",
        "relevant_benchmarks": ["MMLU", "MT-Bench", "IFEval"],
    },
    "agent_tool_use": {
        "label": "Agent & Tool Use",
        "weight_quality": 0.45, "weight_cost": 0.20, "weight_speed": 0.20, "weight_context": 0.15,
        "icon": "🤖",
        "relevant_benchmarks": ["IFEval", "HumanEval", "MMLU"],
    },
    "math_science": {
        "label": "Math & Science",
        "weight_quality": 0.55, "weight_cost": 0.20, "weight_speed": 0.10, "weight_context": 0.15,
        "icon": "🔢",
        "relevant_benchmarks": ["MATH", "GPQA", "MMLU"],
    },
}

# Allocation weights for portfolio positions
ALLOCATION_WEIGHTS = {1: 0.70, 2: 0.20, 3: 0.10}  # rank -> allocation %


class LLMPortfolioAgent(BaseAgent):
    """Agent that computes optimal LLM model portfolio per task category.

    Reads pricing from ``llm_pricing`` and benchmark data from ``llm_benchmarks``,
    then computes weighted composite scores to recommend the top 3 models per
    task category with allocation percentages.

    Config options:
        allocation_weights: dict mapping rank (1,2,3) to allocation fraction
        min_models_for_category: minimum models needed to generate recommendations (default: 3)
    """

    @property
    def name(self) -> str:
        return "llm_portfolio"

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        _logger.info("LLMPortfolioAgent: Computing model portfolio recommendations")

        try:
            conn = get_connection()
            schema.init_schema(conn)
        except Exception as e:
            _logger.error("LLMPortfolioAgent: Cannot connect to DB: %s", e)
            return AgentResult(agent_name=self.name, status="failed", errors=[str(e)])

        try:
            # 1. Load all model pricing
            pricing = self._load_pricing(conn)
            if not pricing:
                _logger.warning("LLMPortfolioAgent: No pricing data found — run llm_pricing agent first")
                return AgentResult(
                    agent_name=self.name, status="partial",
                    errors=["No pricing data in database"],
                )

            # 2. Load all benchmark scores
            benchmarks = self._load_benchmarks(conn)
            if not benchmarks:
                _logger.warning("LLMPortfolioAgent: No benchmark data found — using pricing only")

            # 3. Compute per-model quality scores by category
            quality_scores = self._compute_quality_scores(benchmarks)

            # 4. Compute cost and context scores
            cost_scores = self._compute_cost_scores(pricing)
            context_scores = self._compute_context_scores(pricing)

            # 5. For each task category, rank models and generate portfolio
            total_recommendations = 0
            portfolio_summary = {}
            cursor = conn.cursor()

            # Clear previous recommendations
            cursor.execute("DELETE FROM llm_portfolio")

            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

            for task_id, task_config in TASK_CATEGORIES.items():
                ranked = self._rank_models(
                    pricing, quality_scores, cost_scores, context_scores, task_config,
                )

                if len(ranked) < 1:
                    continue

                category_summary = {
                    "label": task_config["label"],
                    "icon": task_config["icon"],
                    "models": [],
                }

                for rank, model_data in enumerate(ranked[:3], start=1):
                    allocation = ALLOCATION_WEIGHTS.get(rank, 0.05) * 100

                    cursor.execute(
                        """INSERT INTO llm_portfolio
                           (task_category, provider, model_name, allocation_pct, rank_position,
                            composite_score, quality_score, cost_score, speed_score, context_score,
                            cost_per_1m_tokens, recommended_at)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (
                            task_id,
                            model_data["provider"],
                            model_data["model_name"],
                            allocation,
                            rank,
                            model_data["composite_score"],
                            model_data["quality_score"],
                            model_data["cost_score"],
                            model_data.get("speed_score", 0),
                            model_data.get("context_score", 0),
                            model_data.get("cost_per_1m_tokens", 0),
                            now,
                        ),
                    )

                    category_summary["models"].append({
                        "rank": rank,
                        "provider": model_data["provider"],
                        "model_name": model_data["model_name"],
                        "score": round(model_data["composite_score"], 1),
                        "allocation_pct": allocation,
                        "cost_per_1m_tokens": model_data.get("cost_per_1m_tokens", 0),
                    })
                    total_recommendations += 1

                portfolio_summary[task_id] = category_summary

            conn.commit()

            # Compute overall savings estimate
            savings = self._compute_savings_estimate(portfolio_summary)

            _logger.info(
                "LLMPortfolioAgent: Done — %d recommendations across %d task categories, est. %d%% savings",
                total_recommendations, len(portfolio_summary), savings,
            )

            return AgentResult(
                agent_name=self.name,
                status="success",
                data={
                    "recommendations": total_recommendations,
                    "task_categories": len(portfolio_summary),
                    "estimated_savings_pct": savings,
                    "portfolio_summary": portfolio_summary,
                    "records_affected": total_recommendations,
                },
            )

        except Exception as e:
            _logger.error("LLMPortfolioAgent: Error: %s", e)
            return AgentResult(agent_name=self.name, status="failed", errors=[str(e)])
        finally:
            conn.close()

    def _load_pricing(self, conn) -> list[dict]:
        """Load all model pricing from the database."""
        cursor = conn.cursor()
        cursor.execute(
            "SELECT provider, model_name, input_price_per_1m, output_price_per_1m, "
            "context_window, pricing_tier FROM llm_pricing ORDER BY provider"
        )
        return [dict(r) for r in cursor.fetchall()]

    def _load_benchmarks(self, conn) -> list[dict]:
        """Load all benchmark scores from the database."""
        cursor = conn.cursor()
        cursor.execute(
            "SELECT provider, model_name, benchmark_name, benchmark_score, "
            "benchmark_category, speed_tokens_per_sec FROM llm_benchmarks ORDER BY provider"
        )
        return [dict(r) for r in cursor.fetchall()]

    def _compute_quality_scores(self, benchmarks: list[dict]) -> dict:
        """Compute per-model quality score per benchmark category.

        Returns:
            dict mapping (provider, model_name, category) -> float score (0-100)
        """
        scores: dict[tuple, list[float]] = {}

        for b in benchmarks:
            key = (b["provider"], b["model_name"], b["benchmark_category"])
            if key not in scores:
                scores[key] = []
            if b["benchmark_score"] and b["benchmark_score"] > 0:
                scores[key].append(b["benchmark_score"])

        # Average scores per (provider, model, category)
        averaged: dict[tuple, float] = {}
        for key, vals in scores.items():
            averaged[key] = round(sum(vals) / len(vals), 1)

        return averaged

    def _compute_cost_scores(self, pricing: list[dict]) -> dict:
        """Compute cost score (inverse of price, normalized 0-100).

        Cheapest model = 100, most expensive = ~0.
        """
        if not pricing:
            return {}

        # Compute blended cost (input + output) for each model
        costs: dict[tuple, float] = {}
        for p in pricing:
            if p["pricing_tier"] == "self-hosted":
                # Self-hosted: free API cost, assign high cost score
                costs[(p["provider"], p["model_name"])] = 100.0
            else:
                blended = p["input_price_per_1m"] + p["output_price_per_1m"]
                costs[(p["provider"], p["model_name"])] = blended

        if not costs:
            return {}

        max_cost = max(costs.values()) if costs else 1.0
        if max_cost == 0:
            return {k: 100.0 for k in costs}

        # Normalize: cheapest = 100, most expensive = ~0
        return {
            key: round((1 - cost / max_cost) * 100, 1)
            for key, cost in costs.items()
        }

    def _compute_context_scores(self, pricing: list[dict]) -> dict:
        """Compute context window score (normalized 0-100).

        Largest context = 100, smallest = ~0. Uses log scale for fair comparison.
        """
        import math

        contexts: dict[tuple, int] = {}
        for p in pricing:
            ctx = p.get("context_window") or 4096
            contexts[(p["provider"], p["model_name"])] = ctx

        if not contexts:
            return {}

        max_ctx = max(contexts.values()) if contexts else 1
        if max_ctx == 0:
            return {k: 50.0 for k in contexts}

        return {
            key: round((math.log(ctx) / math.log(max_ctx)) * 100, 1)
            for key, ctx in contexts.items()
        }

    def _rank_models(
        self,
        pricing: list[dict],
        quality_scores: dict,
        cost_scores: dict,
        context_scores: dict,
        task_config: dict,
    ) -> list[dict]:
        """Rank all models for a specific task category by composite score.

        Uses task-specific weights to compute the composite score.
        Returns list sorted by composite score descending.
        """
        w_q = task_config["weight_quality"]
        w_c = task_config["weight_cost"]
        w_s = task_config["weight_speed"]
        w_ctx = task_config["weight_context"]

        # Get quality-relevant categories for this task
        relevant_benchmarks = task_config.get("relevant_benchmarks", [])

        model_scores: list[dict] = []
        seen = set()

        for p in pricing:
            key = (p["provider"], p["model_name"])
            if key in seen:
                continue
            seen.add(key)

            # Get quality score: prefer relevant benchmarks, fall back to any
            quality = 0.0
            for bench_cat in ["coding", "reasoning", "math", "instruction_following", "general"]:
                q = quality_scores.get((p["provider"], p["model_name"], bench_cat), 0)
                if q > 0:
                    quality = q
                    if bench_cat in ("coding", "reasoning"):
                        break  # Prefer coding/reasoning as quality proxy

            # If task has specific category preference, try to match
            category_mapping = {
                "code_generation": "coding",
                "code_review": "coding",
                "analysis_reasoning": "reasoning",
                "math_science": "math",
                "rag_qa": "long_context",
            }
            preferred_cat = category_mapping.get(list(TASK_CATEGORIES.keys())[
                list(TASK_CATEGORIES.values()).index(task_config)
            ] if task_config in TASK_CATEGORIES.values() else "", None)

            if preferred_cat:
                q_specific = quality_scores.get((p["provider"], p["model_name"], preferred_cat), 0)
                if q_specific > 0:
                    quality = (quality + q_specific) / 2  # Blend

            c_score = cost_scores.get(key, 50.0)
            ctx_score = context_scores.get(key, 50.0)

            # Speed: not yet tracked from scraping, default to 70 (middle)
            speed = 70.0

            composite = (quality * w_q) + (c_score * w_c) + (speed * w_s) + (ctx_score * w_ctx)

            blended_cost = 0
            if p["pricing_tier"] != "self-hosted":
                blended_cost = p["input_price_per_1m"] + p["output_price_per_1m"]

            model_scores.append({
                "provider": p["provider"],
                "model_name": p["model_name"],
                "composite_score": round(composite, 1),
                "quality_score": quality,
                "cost_score": c_score,
                "speed_score": speed,
                "context_score": ctx_score,
                "cost_per_1m_tokens": round(blended_cost, 2),
            })

        # Sort by composite score descending
        model_scores.sort(key=lambda x: x["composite_score"], reverse=True)
        return model_scores

    def _compute_savings_estimate(self, portfolio_summary: dict) -> int:
        """Estimate potential savings from using recommended portfolio vs single model.

        Compares the weighted average cost of the recommended portfolio per category
        against using only the #1 model for everything.
        """
        if not portfolio_summary:
            return 0

        # Simple heuristic: if at least one category recommends a cheap model in top 3,
        # there's savings to be had
        has_cheap_picks = 0
        total_categories = 0

        for task_id, summary in portfolio_summary.items():
            total_categories += 1
            for m in summary["models"]:
                if m["cost_per_1m_tokens"] < 1.0 and m["rank"] >= 2:
                    has_cheap_picks += 1
                    break

        if total_categories == 0:
            return 0

        # Rough estimate: categories with cheap alternatives * ~15% savings each
        savings = int((has_cheap_picks / total_categories) * 100 * 0.15)
        return min(savings, 60)  # Cap at 60%
