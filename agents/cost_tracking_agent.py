"""Cost tracking agent — tracks API costs."""

import logging
from agents.base import BaseAgent, AgentResult

_logger = logging.getLogger(__name__)


class CostTrackingAgent(BaseAgent):
    """Tracks API costs (OpenAI, Ollama tokens)."""

    @property
    def name(self) -> str:
        return "cost_tracking"

    def execute(self, upstream_results) -> AgentResult:
        """Track API costs."""
        try:
            # Simulate cost tracking from Ollama usage
            import json
            from pathlib import Path

            tracker_path = Path("data/cache/ollama_token_tracker.json")
            total_tokens = 0
            total_runs = 0

            if tracker_path.exists():
                try:
                    data = json.loads(tracker_path.read_text())
                    if isinstance(data, list):
                        total_tokens = sum(r.get("total_tokens", 0) for r in data)
                        total_runs = len(data)
                except (json.JSONDecodeError, TypeError):
                    pass

            # Estimate cost (assume $0.001 per 1K tokens)
            estimated_cost_usd = (total_tokens / 1000) * 0.001

            return AgentResult(
                agent_name=self.name,
                status="success",
                data={
                    "total_tokens": total_tokens,
                    "total_runs": total_runs,
                    "estimated_cost_usd": round(estimated_cost_usd, 4),
                },
            )
        except Exception as e:
            return AgentResult(
                agent_name=self.name,
                status="failed",
                errors=[str(e)],
            )
