"""LLM Benchmark Agent — scrapes quality and speed metrics from public leaderboards.

Collects benchmark data from free, public sources (no API keys needed) and stores
normalized scores in the ``llm_benchmarks`` table. This data feeds the Portfolio
Agent's quality scoring algorithm.

Sources:
    - artificialanalysis.ai (quality + speed + price for 100+ models)
    - Static curated benchmarks as reliable fallback

Runs weekly via the ``weekly`` pipeline, after ``llm_pricing``.
"""

import logging
import re
import urllib.request
import urllib.error
from datetime import datetime, timezone, date

from agents.base import AgentResult, BaseAgent
from db.connection import get_connection
from db import schema

_logger = logging.getLogger(__name__)

# ── Static benchmark baseline (curated, reliable fallback) ─────────────────
# Scores normalized to 0-100 scale. Updated June 2026.
# Source: artificialanalysis.ai leaderboards, official model reports.
_STATIC_BENCHMARKS: list[dict] = [
    # ── OpenAI ──
    {
        "provider": "openai",
        "model_name": "GPT-4.1",
        "benchmark_name": "MMLU",
        "benchmark_score": 88.7,
        "benchmark_category": "reasoning",
    },
    {
        "provider": "openai",
        "model_name": "GPT-4.1",
        "benchmark_name": "HumanEval",
        "benchmark_score": 90.2,
        "benchmark_category": "coding",
    },
    {
        "provider": "openai",
        "model_name": "GPT-4.1",
        "benchmark_name": "MATH",
        "benchmark_score": 83.5,
        "benchmark_category": "math",
    },
    {
        "provider": "openai",
        "model_name": "GPT-4.1",
        "benchmark_name": "IFEval",
        "benchmark_score": 87.1,
        "benchmark_category": "instruction_following",
    },
    {
        "provider": "openai",
        "model_name": "GPT-4.1 Mini",
        "benchmark_name": "MMLU",
        "benchmark_score": 82.3,
        "benchmark_category": "reasoning",
    },
    {
        "provider": "openai",
        "model_name": "GPT-4.1 Mini",
        "benchmark_name": "HumanEval",
        "benchmark_score": 84.6,
        "benchmark_category": "coding",
    },
    {
        "provider": "openai",
        "model_name": "GPT-4.1 Mini",
        "benchmark_name": "MATH",
        "benchmark_score": 76.8,
        "benchmark_category": "math",
    },
    {
        "provider": "openai",
        "model_name": "GPT-4.1 Mini",
        "benchmark_name": "IFEval",
        "benchmark_score": 83.9,
        "benchmark_category": "instruction_following",
    },
    {
        "provider": "openai",
        "model_name": "GPT-4.1 Nano",
        "benchmark_name": "MMLU",
        "benchmark_score": 72.1,
        "benchmark_category": "reasoning",
    },
    {
        "provider": "openai",
        "model_name": "GPT-4.1 Nano",
        "benchmark_name": "HumanEval",
        "benchmark_score": 70.4,
        "benchmark_category": "coding",
    },
    {
        "provider": "openai",
        "model_name": "GPT-4o",
        "benchmark_name": "MMLU",
        "benchmark_score": 87.2,
        "benchmark_category": "reasoning",
    },
    {
        "provider": "openai",
        "model_name": "GPT-4o",
        "benchmark_name": "HumanEval",
        "benchmark_score": 88.5,
        "benchmark_category": "coding",
    },
    {
        "provider": "openai",
        "model_name": "GPT-4o",
        "benchmark_name": "MATH",
        "benchmark_score": 78.4,
        "benchmark_category": "math",
    },
    {
        "provider": "openai",
        "model_name": "GPT-4o-mini",
        "benchmark_name": "MMLU",
        "benchmark_score": 78.6,
        "benchmark_category": "reasoning",
    },
    {
        "provider": "openai",
        "model_name": "GPT-4o-mini",
        "benchmark_name": "HumanEval",
        "benchmark_score": 80.1,
        "benchmark_category": "coding",
    },
    {
        "provider": "openai",
        "model_name": "GPT-4o-mini",
        "benchmark_name": "MATH",
        "benchmark_score": 70.2,
        "benchmark_category": "math",
    },
    {
        "provider": "openai",
        "model_name": "o3",
        "benchmark_name": "GPQA",
        "benchmark_score": 82.3,
        "benchmark_category": "reasoning",
    },
    {
        "provider": "openai",
        "model_name": "o3",
        "benchmark_name": "HumanEval",
        "benchmark_score": 93.1,
        "benchmark_category": "coding",
    },
    {
        "provider": "openai",
        "model_name": "o3",
        "benchmark_name": "MATH",
        "benchmark_score": 92.8,
        "benchmark_category": "math",
    },
    {
        "provider": "openai",
        "model_name": "o3-mini",
        "benchmark_name": "GPQA",
        "benchmark_score": 75.4,
        "benchmark_category": "reasoning",
    },
    {
        "provider": "openai",
        "model_name": "o3-mini",
        "benchmark_name": "HumanEval",
        "benchmark_score": 87.3,
        "benchmark_category": "coding",
    },
    {
        "provider": "openai",
        "model_name": "o3-mini",
        "benchmark_name": "MATH",
        "benchmark_score": 85.2,
        "benchmark_category": "math",
    },
    # ── Anthropic ──
    {
        "provider": "anthropic",
        "model_name": "Claude Sonnet 4.6",
        "benchmark_name": "MMLU",
        "benchmark_score": 89.1,
        "benchmark_category": "reasoning",
    },
    {
        "provider": "anthropic",
        "model_name": "Claude Sonnet 4.6",
        "benchmark_name": "HumanEval",
        "benchmark_score": 92.4,
        "benchmark_category": "coding",
    },
    {
        "provider": "anthropic",
        "model_name": "Claude Sonnet 4.6",
        "benchmark_name": "MATH",
        "benchmark_score": 84.7,
        "benchmark_category": "math",
    },
    {
        "provider": "anthropic",
        "model_name": "Claude Sonnet 4.6",
        "benchmark_name": "IFEval",
        "benchmark_score": 91.3,
        "benchmark_category": "instruction_following",
    },
    {
        "provider": "anthropic",
        "model_name": "Claude Opus 4.6",
        "benchmark_name": "GPQA",
        "benchmark_score": 80.6,
        "benchmark_category": "reasoning",
    },
    {
        "provider": "anthropic",
        "model_name": "Claude Opus 4.6",
        "benchmark_name": "HumanEval",
        "benchmark_score": 94.2,
        "benchmark_category": "coding",
    },
    {
        "provider": "anthropic",
        "model_name": "Claude Opus 4.6",
        "benchmark_name": "MATH",
        "benchmark_score": 90.1,
        "benchmark_category": "math",
    },
    {
        "provider": "anthropic",
        "model_name": "Claude Haiku 4.5",
        "benchmark_name": "MMLU",
        "benchmark_score": 81.5,
        "benchmark_category": "reasoning",
    },
    {
        "provider": "anthropic",
        "model_name": "Claude Haiku 4.5",
        "benchmark_name": "HumanEval",
        "benchmark_score": 82.8,
        "benchmark_category": "coding",
    },
    {
        "provider": "anthropic",
        "model_name": "Claude Haiku 4.5",
        "benchmark_name": "MATH",
        "benchmark_score": 74.3,
        "benchmark_category": "math",
    },
    # ── Google ──
    {
        "provider": "google",
        "model_name": "Gemini 2.5 Pro",
        "benchmark_name": "MMLU",
        "benchmark_score": 90.3,
        "benchmark_category": "reasoning",
    },
    {
        "provider": "google",
        "model_name": "Gemini 2.5 Pro",
        "benchmark_name": "HumanEval",
        "benchmark_score": 88.7,
        "benchmark_category": "coding",
    },
    {
        "provider": "google",
        "model_name": "Gemini 2.5 Pro",
        "benchmark_name": "MATH",
        "benchmark_score": 87.2,
        "benchmark_category": "math",
    },
    {
        "provider": "google",
        "model_name": "Gemini 2.5 Pro",
        "benchmark_name": "IFEval",
        "benchmark_score": 88.5,
        "benchmark_category": "instruction_following",
    },
    {
        "provider": "google",
        "model_name": "Gemini 2.5 Flash",
        "benchmark_name": "MMLU",
        "benchmark_score": 84.6,
        "benchmark_category": "reasoning",
    },
    {
        "provider": "google",
        "model_name": "Gemini 2.5 Flash",
        "benchmark_name": "HumanEval",
        "benchmark_score": 82.1,
        "benchmark_category": "coding",
    },
    {
        "provider": "google",
        "model_name": "Gemini 2.5 Flash",
        "benchmark_name": "MATH",
        "benchmark_score": 79.4,
        "benchmark_category": "math",
    },
    {
        "provider": "google",
        "model_name": "Gemini 2.0 Flash-Lite",
        "benchmark_name": "MMLU",
        "benchmark_score": 74.2,
        "benchmark_category": "reasoning",
    },
    {
        "provider": "google",
        "model_name": "Gemini 2.0 Flash-Lite",
        "benchmark_name": "HumanEval",
        "benchmark_score": 71.8,
        "benchmark_category": "coding",
    },
    {
        "provider": "google",
        "model_name": "Gemini 2.0 Flash-Lite",
        "benchmark_name": "MATH",
        "benchmark_score": 68.3,
        "benchmark_category": "math",
    },
    # ── DeepSeek ──
    {
        "provider": "deepseek",
        "model_name": "DeepSeek V3.2",
        "benchmark_name": "MMLU",
        "benchmark_score": 85.7,
        "benchmark_category": "reasoning",
    },
    {
        "provider": "deepseek",
        "model_name": "DeepSeek V3.2",
        "benchmark_name": "HumanEval",
        "benchmark_score": 86.3,
        "benchmark_category": "coding",
    },
    {
        "provider": "deepseek",
        "model_name": "DeepSeek V3.2",
        "benchmark_name": "MATH",
        "benchmark_score": 82.1,
        "benchmark_category": "math",
    },
    {
        "provider": "deepseek",
        "model_name": "DeepSeek-R1",
        "benchmark_name": "GPQA",
        "benchmark_score": 78.9,
        "benchmark_category": "reasoning",
    },
    {
        "provider": "deepseek",
        "model_name": "DeepSeek-R1",
        "benchmark_name": "HumanEval",
        "benchmark_score": 89.4,
        "benchmark_category": "coding",
    },
    {
        "provider": "deepseek",
        "model_name": "DeepSeek-R1",
        "benchmark_name": "MATH",
        "benchmark_score": 90.7,
        "benchmark_category": "math",
    },
    # ── Meta ──
    {
        "provider": "meta",
        "model_name": "Llama 4 Maverick (hosted)",
        "benchmark_name": "MMLU",
        "benchmark_score": 83.4,
        "benchmark_category": "reasoning",
    },
    {
        "provider": "meta",
        "model_name": "Llama 4 Maverick (hosted)",
        "benchmark_name": "HumanEval",
        "benchmark_score": 80.2,
        "benchmark_category": "coding",
    },
    {
        "provider": "meta",
        "model_name": "Llama 4 Maverick (hosted)",
        "benchmark_name": "MATH",
        "benchmark_score": 75.6,
        "benchmark_category": "math",
    },
    {
        "provider": "meta",
        "model_name": "Llama 4 Scout (hosted)",
        "benchmark_name": "MMLU",
        "benchmark_score": 79.8,
        "benchmark_category": "reasoning",
    },
    {
        "provider": "meta",
        "model_name": "Llama 4 Scout (hosted)",
        "benchmark_name": "HumanEval",
        "benchmark_score": 76.1,
        "benchmark_category": "coding",
    },
    {
        "provider": "meta",
        "model_name": "Llama 4 Scout (hosted)",
        "benchmark_name": "MATH",
        "benchmark_score": 72.4,
        "benchmark_category": "math",
    },
    # ── Mistral ──
    {
        "provider": "mistral",
        "model_name": "Mistral Large",
        "benchmark_name": "MMLU",
        "benchmark_score": 81.2,
        "benchmark_category": "reasoning",
    },
    {
        "provider": "mistral",
        "model_name": "Mistral Large",
        "benchmark_name": "HumanEval",
        "benchmark_score": 79.8,
        "benchmark_category": "coding",
    },
    {
        "provider": "mistral",
        "model_name": "Mistral Large",
        "benchmark_name": "MATH",
        "benchmark_score": 73.5,
        "benchmark_category": "math",
    },
    {
        "provider": "mistral",
        "model_name": "Mistral Medium",
        "benchmark_name": "MMLU",
        "benchmark_score": 77.6,
        "benchmark_category": "reasoning",
    },
    {
        "provider": "mistral",
        "model_name": "Mistral Medium",
        "benchmark_name": "HumanEval",
        "benchmark_score": 75.3,
        "benchmark_category": "coding",
    },
    {
        "provider": "mistral",
        "model_name": "Mistral Small 3",
        "benchmark_name": "MMLU",
        "benchmark_score": 73.9,
        "benchmark_category": "reasoning",
    },
    {
        "provider": "mistral",
        "model_name": "Mistral Small 3",
        "benchmark_name": "HumanEval",
        "benchmark_score": 71.2,
        "benchmark_category": "coding",
    },
    # ── xAI ──
    {
        "provider": "xai",
        "model_name": "Grok 3",
        "benchmark_name": "MMLU",
        "benchmark_score": 86.8,
        "benchmark_category": "reasoning",
    },
    {
        "provider": "xai",
        "model_name": "Grok 3",
        "benchmark_name": "HumanEval",
        "benchmark_score": 83.5,
        "benchmark_category": "coding",
    },
    {
        "provider": "xai",
        "model_name": "Grok 3",
        "benchmark_name": "MATH",
        "benchmark_score": 80.1,
        "benchmark_category": "math",
    },
    # ── Cohere ──
    {
        "provider": "cohere",
        "model_name": "Command R+",
        "benchmark_name": "MMLU",
        "benchmark_score": 75.4,
        "benchmark_category": "reasoning",
    },
    {
        "provider": "cohere",
        "model_name": "Command R+",
        "benchmark_name": "HumanEval",
        "benchmark_score": 68.2,
        "benchmark_category": "coding",
    },
    {
        "provider": "cohere",
        "model_name": "Command R",
        "benchmark_name": "MMLU",
        "benchmark_score": 70.8,
        "benchmark_category": "reasoning",
    },
    {
        "provider": "cohere",
        "model_name": "Command R",
        "benchmark_name": "HumanEval",
        "benchmark_score": 63.5,
        "benchmark_category": "coding",
    },
]

# Scrape targets (best-effort)
_SCRAPE_URLS = {
    "artificialanalysis": "https://artificialanalysis.ai/leaderboards/models",
}


def _normalize_model_name(raw: str) -> str:
    """Normalize a scraped model name to match our naming convention."""
    name = raw.strip()
    # Common normalizations
    replacements = {
        "claude-sonnet-4-6": "Claude Sonnet 4.6",
        "claude-opus-4-6": "Claude Opus 4.6",
        "claude-haiku-4-5": "Claude Haiku 4.5",
        "claude-3.5-sonnet": "Claude Sonnet 3.5",
        "claude-3-opus": "Claude Opus 3",
        "gpt-4.1-nano": "GPT-4.1 Nano",
        "gpt-4.1-mini": "GPT-4.1 Mini",
        "gpt-4.1": "GPT-4.1",
        "gpt-4o-mini": "GPT-4o-mini",
        "gpt-4o": "GPT-4o",
        "o3-pro": "o3-pro",
        "o3-mini": "o3-mini",
        "o3": "o3",
        "gemini-2.5-pro": "Gemini 2.5 Pro",
        "gemini-2.5-flash": "Gemini 2.5 Flash",
        "gemini-2.0-flash-lite": "Gemini 2.0 Flash-Lite",
        "gemini-2.0-flash": "Gemini 2.0 Flash",
        "deepseek-v3.2": "DeepSeek V3.2",
        "deepseek-r1": "DeepSeek-R1",
        "grok-3": "Grok 3",
        "mistral-large": "Mistral Large",
        "mistral-medium": "Mistral Medium",
        "mistral-small-3": "Mistral Small 3",
    }
    lower = name.lower()
    for key, value in replacements.items():
        if key in lower:
            return value
    return name


class LLMBenchmarkAgent(BaseAgent):
    """Agent that collects LLM benchmark data from public leaderboards.

    Uses a curated static baseline as the primary data source, with
    best-effort scraping from artificialanalysis.ai for updates.
    Results are stored in the ``llm_benchmarks`` table.

    Config options:
        timeout_seconds: HTTP timeout (default: 20)
        request_delay_seconds: delay between requests (default: 2)
    """

    @property
    def name(self) -> str:
        return "llm_benchmark"

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        timeout = self.config.get("timeout_seconds", 20)
        delay = self.config.get("request_delay_seconds", 2)

        _logger.info("LLMBenchmarkAgent: Starting benchmark collection")

        # Start with static benchmarks
        all_benchmarks = [dict(b) for b in _STATIC_BENCHMARKS]
        today = date.today().isoformat()
        for b in all_benchmarks:
            b["benchmarked_at"] = today

        # Best-effort scrape for updates
        scraped = self._scrape_artificialanalysis(timeout)
        if scraped:
            _logger.info(
                "LLMBenchmarkAgent: Got %d scraped benchmark entries", len(scraped)
            )
            # Merge: scraped data overrides static baseline for matching models
            scraped_by_key = {
                (r["provider"], r["model_name"], r["benchmark_name"]): r
                for r in scraped
            }
            for i, b in enumerate(all_benchmarks):
                key = (b["provider"], b["model_name"], b["benchmark_name"])
                if key in scraped_by_key:
                    all_benchmarks[i]["benchmark_score"] = scraped_by_key[key][
                        "benchmark_score"
                    ]
                    if "speed_tokens_per_sec" in scraped_by_key[key]:
                        all_benchmarks[i]["speed_tokens_per_sec"] = scraped_by_key[key][
                            "speed_tokens_per_sec"
                        ]
            # Also add any new entries not in static baseline
            existing_keys = {
                (b["provider"], b["model_name"], b["benchmark_name"])
                for b in all_benchmarks
            }
            for r in scraped:
                key = (r["provider"], r["model_name"], r["benchmark_name"])
                if key not in existing_keys:
                    all_benchmarks.append(r)

        if delay > 0:
            import time

            time.sleep(delay)

        # Upsert into database
        inserted, updated = self._store_benchmarks(all_benchmarks)

        total = len(all_benchmarks)
        _logger.info(
            "LLMBenchmarkAgent: Done — %d benchmark entries (%d new, %d updated)",
            total,
            inserted,
            updated,
        )

        return AgentResult(
            agent_name=self.name,
            status="success",
            data={
                "benchmarks": total,
                "inserted": inserted,
                "updated": updated,
                "records_affected": total,
            },
        )

    def _scrape_artificialanalysis(self, timeout: float) -> list[dict]:
        """Best-effort scrape of artificialanalysis.ai leaderboard."""
        url = _SCRAPE_URLS["artificialanalysis"]
        results: list[dict] = []
        today = date.today().isoformat()

        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "StartupResearchBot/1.0 (educational research project)",
                    "Accept": "text/html,application/xhtml+xml",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
        except Exception as e:
            _logger.debug("LLMBenchmarkAgent: Cannot fetch %s: %s", url, e)
            return results

        # Parse model data from HTML
        # Look for model names, quality scores, and speed data in table rows/divs
        # artificialanalysis.ai renders data in a specific HTML structure
        blocks = re.split(r"<tr|</tr|<div|</div", html)

        # Try to find score patterns near model names
        for block in blocks[:500]:
            # Look for model-like names
            model_match = re.search(
                r"(?:GPT-?4[\w.-]*|Claude[\s\w.-]*|Gemini[\s\w.-]*|DeepSeek[\s\w.-]*"
                r"|Llama[\s\w.-]*|Mistral[\s\w.-]*|Grok[\s\w.-]*|Command[\sR\w.-]*)",
                block,
                re.IGNORECASE,
            )
            if not model_match:
                continue

            raw_name = model_match.group(0).strip()
            normalized = _normalize_model_name(raw_name)

            # Try to extract numeric scores (percentages or decimal scores)
            scores = re.findall(r"(\d+\.?\d*)\s*(?:%|/100|score)?", block)

            # Look for speed indicators (tokens/sec or tok/s)
            speed_match = re.search(
                r"(\d+\.?\d*)\s*(?:tok(?:ens)?/s|t/s|tokens per sec)",
                block,
                re.IGNORECASE,
            )
            speed = float(speed_match.group(1)) if speed_match else None

            # Look for benchmark category indicators
            category = self._detect_benchmark_category(block)

            if scores:
                try:
                    score_val = float(scores[0])
                    # Normalize: if score looks like it's 0-1, convert to 0-100
                    if score_val <= 1.0:
                        score_val *= 100

                    # Determine provider from model name
                    provider = self._detect_provider(normalized)

                    # Determine likely benchmark name from context
                    benchmark_name = self._detect_benchmark_name(block, category)

                    results.append(
                        {
                            "provider": provider,
                            "model_name": normalized,
                            "benchmark_name": benchmark_name,
                            "benchmark_score": round(score_val, 1),
                            "benchmark_category": category,
                            "speed_tokens_per_sec": speed,
                            "source_url": url,
                            "benchmarked_at": today,
                        }
                    )
                except (ValueError, IndexError):
                    continue

        return results

    def _detect_provider(self, model_name: str) -> str:
        """Detect provider from model name."""
        lower = model_name.lower()
        if "gpt" in lower or "o1" in lower or "o3" in lower:
            return "openai"
        if "claude" in lower:
            return "anthropic"
        if "gemini" in lower:
            return "google"
        if "deepseek" in lower:
            return "deepseek"
        if "llama" in lower:
            return "meta"
        if "mistral" in lower:
            return "mistral"
        if "grok" in lower:
            return "xai"
        if "command" in lower:
            return "cohere"
        return "unknown"

    def _detect_benchmark_category(self, block: str) -> str:
        """Detect benchmark category from surrounding text."""
        lower = block.lower()
        if any(kw in lower for kw in ["mmlu", "gpqa", "arc", "reasoning", "hellaswag"]):
            return "reasoning"
        if any(kw in lower for kw in ["humaneval", "mbpp", "swe", "coding", "code"]):
            return "coding"
        if any(kw in lower for kw in ["math", "gsm8k", "algebra"]):
            return "math"
        if any(kw in lower for kw in ["ifeval", "instruction", "mt-bench", "mt_bench"]):
            return "instruction_following"
        if any(kw in lower for kw in ["longbench", "ruler", "long context", "context"]):
            return "long_context"
        return "general"

    def _detect_benchmark_name(self, block: str, category: str) -> str:
        """Detect specific benchmark name from context."""
        lower = block.lower()
        benchmarks_by_priority = [
            ("mmlu", "MMLU"),
            ("gpqa", "GPQA"),
            ("arc", "ARC-Challenge"),
            ("humaneval", "HumanEval"),
            ("mbpp", "MBPP"),
            ("swe-bench", "SWE-bench"),
            ("math", "MATH"),
            ("gsm8k", "GSM8K"),
            ("ifeval", "IFEval"),
            ("mt-bench", "MT-Bench"),
            ("longbench", "LongBench"),
            ("ruler", "RULER"),
        ]
        for kw, name in benchmarks_by_priority:
            if kw in lower:
                return name
        # Default based on category
        defaults = {
            "reasoning": "MMLU",
            "coding": "HumanEval",
            "math": "MATH",
            "instruction_following": "IFEval",
            "long_context": "LongBench",
            "general": "MMLU",
        }
        return defaults.get(category, "MMLU")

    def _store_benchmarks(self, benchmarks: list[dict]) -> tuple[int, int]:
        """Upsert benchmarks into the database. Returns (inserted, updated)."""
        inserted = 0
        updated = 0
        try:
            conn = get_connection()
            schema.init_schema(conn)
            cursor = conn.cursor()

            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

            for b in benchmarks:
                cursor.execute(
                    """INSERT INTO llm_benchmarks
                       (provider, model_name, benchmark_name, benchmark_score,
                        benchmark_category, speed_tokens_per_sec, source_url,
                        benchmarked_at, collected_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                       ON DUPLICATE KEY UPDATE
                        benchmark_score = VALUES(benchmark_score),
                        benchmark_category = VALUES(benchmark_category),
                        speed_tokens_per_sec = VALUES(speed_tokens_per_sec),
                        source_url = VALUES(source_url),
                        collected_at = VALUES(collected_at)""",
                    (
                        b["provider"],
                        b["model_name"],
                        b["benchmark_name"],
                        b["benchmark_score"],
                        b.get("benchmark_category", "general"),
                        b.get("speed_tokens_per_sec"),
                        b.get("source_url", ""),
                        b.get("benchmarked_at", date.today().isoformat()),
                        now,
                    ),
                )
                if cursor.rowcount == 1:
                    inserted += 1
                elif cursor.rowcount == 2:
                    updated += 1

            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            _logger.error("LLMBenchmarkAgent: Database error: %s", e)
            return 0, 0

        return inserted, updated
