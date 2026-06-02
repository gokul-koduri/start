"""Global Market Viability Agent — evaluates failed startup products in
global markets using a local Ollama LLM.

This agent is a thin wrapper around ``scripts/global_market_viability.py``.
It evaluates every sector against 10 global markets, writes
``Global_Market_Viability.md``, and reports a summary back to the orchestrator.

Runs after the correlation agent in the analysis pipeline so it can reference
the latest database state.
"""

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from agents.base import AgentResult, BaseAgent

_logger = logging.getLogger(__name__)

# Ensure scripts/ is importable
_SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


class GlobalMarketViabilityAgent(BaseAgent):
    """Agent that runs the global market viability analysis using Ollama LLM.

    Config options:
        output_filename: name of the markdown report file (default:
            ``Global_Market_Viability.md``) written to the project root.
        ollama_url: Ollama API endpoint (default:
            ``http://localhost:11434/api/chat``)
        ollama_model: model name (default: ``llama3``)
        delay_seconds: delay between LLM calls (default: 3.0)
        top_combinations: number of top sector-country combos for deep dive
            (default: 15)
    """

    @property
    def name(self) -> str:
        return "global_market_viability"

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        # Late import so the script's top-level logging.basicConfig and
        # sys.path manipulations don't run unless this agent is activated.
        import global_market_viability as gmv

        from db.connection import get_connection

        output_filename = self.config.get(
            "output_filename", "Global_Market_Viability.md"
        )
        out_path = Path(__file__).parent.parent / output_filename

        _logger.info(
            "GlobalMarketViabilityAgent: Starting LLM-based market viability analysis"
        )

        errors: list[str] = []

        try:
            conn = get_connection()
        except Exception as e:
            return AgentResult(
                agent_name=self.name,
                status="failed",
                errors=[f"DB connection failed: {e}"],
            )

        model = self.config.get("ollama_model", "llama3")
        url = self.config.get("ollama_url", "http://localhost:11434/api/chat")
        delay = float(self.config.get("delay_seconds", 3.0))
        top_n = int(self.config.get("top_combinations", 15))

        try:
            all_results, deep_dive_results, summary = gmv.run_analysis(
                conn=conn,
                model=model,
                url=url,
                delay=delay,
                top_combinations=top_n,
            )

            report = gmv.build_report(all_results, deep_dive_results, summary)
            out_path.write_text(report, encoding="utf-8")
            _logger.info(
                "GlobalMarketViabilityAgent: Wrote %s (%d bytes)",
                out_path.name,
                len(report),
            )
        except Exception as e:
            _logger.error("GlobalMarketViabilityAgent: Failed: %s", e)
            errors.append(str(e))
            return AgentResult(
                agent_name=self.name,
                status="failed",
                errors=errors,
            )
        finally:
            conn.close()

        top_combo = summary.get("top_combination", {})

        data = {
            "sectors_analyzed": summary.get("sectors_analyzed", 0),
            "countries_analyzed": summary.get("countries_analyzed", 0),
            "total_evaluations": len(all_results),
            "total_deep_dives": len(deep_dive_results),
            "avg_viability_score": summary.get("avg_viability_score", 0),
            "top_sector_country": top_combo.get("label", "N/A"),
            "top_viability_score": top_combo.get("score", 0),
            "report_path": str(out_path.name),
            "report_size_bytes": out_path.stat().st_size if out_path.exists() else 0,
            "records_affected": len(all_results),
            "top_insight": (
                f"{summary.get('sectors_analyzed', 0)} sectors x "
                f"{summary.get('countries_analyzed', 0)} markets; "
                f"avg viability={summary.get('avg_viability_score', 0):.1f}/10; "
                f"top: {top_combo.get('label', 'N/A')} "
                f"({top_combo.get('score', 0)}/10)"
            ),
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

        return AgentResult(
            agent_name=self.name,
            status="success" if not errors else "partial",
            data=data,
            errors=errors,
        )
