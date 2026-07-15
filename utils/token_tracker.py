"""Unified token tracking for all LLM providers.

Tracks token usage across Ollama, Codex, and other providers in a single location.
Stores in data/cache/token_tracker.json

Usage:
    from utils.token_tracker import TokenTracker

    tracker = TokenTracker()
    tracker.track("ollama", "llama3", 100, 50)

    # Get totals
    totals = tracker.get_totals()
    print(totals["total_tokens"])
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from config import get_project_root

_logger = logging.getLogger(__name__)

# Default storage path
DEFAULT_STORAGE_PATH = "data/cache/token_tracker.json"
MAX_ENTRIES = 10_000


@dataclass
class TokenUsageEntry:
    """A single token usage entry."""
    timestamp: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    task: Optional[str] = None
    cost_usd: Optional[float] = None


@dataclass
class TokenTotals:
    """Aggregated token usage totals."""
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    inference_count: int = 0
    estimated_cost_usd: float = 0.0
    by_provider: dict = field(default_factory=dict)
    by_model: dict = field(default_factory=dict)


class TokenTracker:
    """Unified token tracking for all LLM providers.

    Stores usage data in a JSON file for persistence and analysis.
    """

    def __init__(self, storage_path: Optional[str] = None):
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            self.storage_path = get_project_root() / DEFAULT_STORAGE_PATH

        self._ensure_storage_dir()

    def _ensure_storage_dir(self) -> None:
        """Ensure storage directory exists."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    def track(
        self,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        task: Optional[str] = None,
        cost_usd: Optional[float] = None,
    ) -> None:
        """Record token usage for a provider.

        Args:
            provider: Provider name (e.g., 'ollama', 'codex', 'nvidia_nim').
            model: Model identifier.
            prompt_tokens: Number of input tokens.
            completion_tokens: Number of output tokens.
            task: Optional task type.
            cost_usd: Optional cost estimate in USD.
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "provider": provider,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        }

        if task:
            entry["task"] = task
        if cost_usd is not None:
            entry["cost_usd"] = cost_usd

        try:
            data = self._load_data()
            entries = data.get("entries", [])
            entries.append(entry)

            # Limit entries to prevent unbounded growth
            if len(entries) > MAX_ENTRIES:
                entries = entries[-MAX_ENTRIES:]

            # Recompute totals
            data["entries"] = entries
            data["totals"] = self._compute_totals(entries)
            data["updated_at"] = datetime.now(timezone.utc).isoformat()

            self._save_data(data)

            _logger.debug(
                "Tracked %s tokens (%s provider, %s model)",
                entry["total_tokens"], provider, model
            )

        except Exception as e:
            _logger.warning("Token tracking failed: %s", e)

    def get_totals(self) -> TokenTotals:
        """Get aggregated token usage totals.

        Returns:
            TokenTotals with aggregated data.
        """
        try:
            data = self._load_data()
            totals = data.get("totals", {})
            return TokenTotals(**totals) if totals else TokenTotals()
        except Exception as e:
            _logger.warning("Failed to get totals: %s", e)
            return TokenTotals()

    def get_usage_snapshot(self, provider: Optional[str] = None) -> dict:
        """Get a snapshot of usage for a provider or all providers.

        Args:
            provider: Optional provider name to filter by.

        Returns:
            dict with usage statistics.
        """
        try:
            data = self._load_data()
            entries = data.get("entries", [])

            if provider:
                entries = [e for e in entries if e.get("provider") == provider]

            if not entries:
                return {
                    "provider": provider or "all",
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "inference_count": 0,
                    "estimated_cost_usd": 0.0,
                }

            return {
                "provider": provider or "all",
                "prompt_tokens": sum(e["prompt_tokens"] for e in entries),
                "completion_tokens": sum(e["completion_tokens"] for e in entries),
                "total_tokens": sum(e["total_tokens"] for e in entries),
                "inference_count": len(entries),
                "estimated_cost_usd": sum(e.get("cost_usd", 0) for e in entries),
                "models": list(set(e["model"] for e in entries)),
            }

        except Exception as e:
            _logger.warning("Failed to get usage snapshot: %s", e)
            return {}

    def clear(self) -> None:
        """Clear all tracked data."""
        try:
            self._save_data({"entries": [], "totals": {}, "updated_at": None})
            _logger.info("Token tracker cleared")
        except Exception as e:
            _logger.warning("Failed to clear tracker: %s", e)

    def _load_data(self) -> dict:
        """Load tracking data from JSON file."""
        if self.storage_path.exists():
            try:
                return json.loads(self.storage_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass

        return {"entries": [], "totals": {}}

    def _save_data(self, data: dict) -> None:
        """Save tracking data to JSON file."""
        self.storage_path.write_text(
            json.dumps(data, indent=2, default=str),
            encoding="utf-8"
        )

    def _compute_totals(self, entries: list[dict]) -> dict:
        """Compute aggregated totals from entries."""
        totals = {
            "total_prompt_tokens": sum(e["prompt_tokens"] for e in entries),
            "total_completion_tokens": sum(e["completion_tokens"] for e in entries),
            "total_tokens": sum(e["total_tokens"] for e in entries),
            "inference_count": len(entries),
            "estimated_cost_usd": sum(e.get("cost_usd", 0) for e in entries),
            "by_provider": {},
            "by_model": {},
        }

        # Group by provider
        for e in entries:
            provider = e.get("provider", "unknown")
            if provider not in totals["by_provider"]:
                totals["by_provider"][provider] = {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "inference_count": 0,
                }
            totals["by_provider"][provider]["prompt_tokens"] += e["prompt_tokens"]
            totals["by_provider"][provider]["completion_tokens"] += e["completion_tokens"]
            totals["by_provider"][provider]["total_tokens"] += e["total_tokens"]
            totals["by_provider"][provider]["inference_count"] += 1

            # Group by model within provider
            model = e.get("model", "unknown")
            model_key = f"{provider}:{model}"
            if model_key not in totals["by_model"]:
                totals["by_model"][model_key] = {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "inference_count": 0,
                }
            totals["by_model"][model_key]["prompt_tokens"] += e["prompt_tokens"]
            totals["by_model"][model_key]["completion_tokens"] += e["completion_tokens"]
            totals["by_model"][model_key]["total_tokens"] += e["total_tokens"]
            totals["by_model"][model_key]["inference_count"] += 1

        return totals


# Module-level convenience functions (for backward compatibility)


def track_inference(
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    task: Optional[str] = None,
) -> None:
    """Convenience function to track inference."""
    tracker = TokenTracker()
    tracker.track(provider, model, prompt_tokens, completion_tokens, task)


def get_inference_totals() -> TokenTotals:
    """Convenience function to get totals."""
    tracker = TokenTracker()
    return tracker.get_totals()


def compute_cost_equivalence(prompt_tokens: int, completion_tokens: int,
                             pricing_data: list[dict]) -> dict[str, float]:
    """Compute what the given tokens would cost across providers.

    Args:
        prompt_tokens: Number of input tokens.
        completion_tokens: Number of output tokens.
        pricing_data: List of pricing data with provider, model_name,
                     input_price_per_1m, output_price_per_1m.

    Returns:
        dict mapping display names to estimated USD cost.
    """
    costs: dict[str, float] = {}
    seen_providers: set[str] = set()

    for row in sorted(
        pricing_data, key=lambda r: (r["provider"], r["input_price_per_1m"])
    ):
        provider = row["provider"]
        if provider in seen_providers:
            continue
        seen_providers.add(provider)

        input_cost = (prompt_tokens / 1_000_000) * row["input_price_per_1m"]
        output_cost = (completion_tokens / 1_000_000) * row["output_price_per_1m"]
        costs[f"{provider.title()} — {row['model_name']}"] = round(
            input_cost + output_cost, 4
        )

    return costs