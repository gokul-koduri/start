"""Correlation Agent — wraps the cross-module correlation analysis as a pipeline stage.

This agent is a thin wrapper around ``scripts/market_correlation_analysis.py``.
It runs the 7 correlation analyses, writes ``Market_Correlation_Analysis.md``,
and reports a summary back to the orchestrator.

Runs LAST in the analysis pipeline so it can report on the freshly-computed
opportunity_pipeline results (including whale-backing boosts).
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


class CorrelationAgent(BaseAgent):
    """Agent that runs the cross-module market correlation analysis.

    Config options:
        output_filename: name of the markdown report file (default:
            ``Market_Correlation_Analysis.md``) written to the project root.
    """

    @property
    def name(self) -> str:
        return "correlation"

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        # Late import so the script's top-level ``logging.basicConfig`` and
        # ``sys.path`` manipulations don't run unless this agent is activated.
        import market_correlation_analysis as mca

        from db.connection import get_connection

        output_filename = self.config.get(
            "output_filename", "Market_Correlation_Analysis.md"
        )
        out_path = Path(__file__).parent.parent / output_filename

        _logger.info("CorrelationAgent: Running 7 correlation analyses")

        errors: list[str] = []
        results: dict[str, dict] = {}

        try:
            conn = get_connection()
        except Exception as e:
            return AgentResult(
                agent_name=self.name,
                status="failed",
                errors=[f"DB connection failed: {e}"],
            )

        try:
            # Run each correlation directly so we capture the returned dicts.
            # ``main()`` in the script doesn't return, so we call the
            # individual ``correlation_N_*`` functions ourselves.
            correl_funcs = [
                ("c1", mca.correlation_1_sector_failure_vs_revival),
                ("c2", mca.correlation_2_failure_reason_vs_survival),
                ("c3", mca.correlation_3_geo_failures_vs_whale),
                ("c4", mca.correlation_4_funding_vs_year),
                ("c5", mca.correlation_5_news_vs_failures),
                ("c6", mca.correlation_6_reshoring_vs_revival),
                ("c7", mca.correlation_7_opportunity_vs_whale),
            ]

            for key, fn in correl_funcs:
                try:
                    results[key] = fn(conn)
                except Exception as e:
                    _logger.warning("CorrelationAgent: %s failed: %s", key, e)
                    errors.append(f"{key}: {e}")
                    results[key] = {
                        "title": key,
                        "interpretation": f"FAILED: {e}",
                        "r": None,
                    }
        finally:
            conn.close()

        # Build and write the report (uses the script's own build_report)
        try:
            report = mca.build_report(results)
            out_path.write_text(report, encoding="utf-8")
            _logger.info(
                "CorrelationAgent: Wrote %s (%d bytes)",
                out_path.name,
                len(report),
            )
        except Exception as e:
            _logger.error("CorrelationAgent: Failed to write report: %s", e)
            errors.append(f"write_report: {e}")
            return AgentResult(
                agent_name=self.name,
                status="failed",
                errors=errors,
            )

        # Build a compact summary for the orchestrator / agent_runs table.
        # c1-c6 return ``pearson_r``; c7 returns ``delta`` (no Pearson).
        def abs_r(res: dict) -> float | None:
            v = res.get("pearson_r")
            return abs(v) if isinstance(v, (int, float)) else None

        strong, moderate, weak = [], [], []
        for k, res in results.items():
            ar = abs_r(res)
            if ar is None:
                continue
            if ar >= 0.7:
                strong.append(k)
            elif ar >= 0.4:
                moderate.append(k)
            elif ar >= 0.2:
                weak.append(k)

        # Pull whale-backing summary directly from c7
        c7 = results.get("c7", {})
        whale_backed_count = c7.get("whale_backed_count")
        total_opps = c7.get("total_opportunities")
        delta = c7.get("delta")

        top_insight = (
            f"{len(strong)} strong, {len(moderate)} moderate, {len(weak)} weak "
            f"correlations; whale_backed={whale_backed_count}/{total_opps} "
            f"(Δscore={delta:+.1f})"
            if isinstance(whale_backed_count, int)
            else f"{len(strong)} strong, {len(moderate)} moderate, {len(weak)} weak correlations"
        )

        data = {
            "strong_correlations": strong,
            "moderate_correlations": moderate,
            "weak_correlations": weak,
            "correlation_count": len(results),
            "report_path": str(out_path.name),
            "report_size_bytes": out_path.stat().st_size if out_path.exists() else 0,
            "whale_backed_opportunities": whale_backed_count,
            "total_opportunities": total_opps,
            "score_delta_whale_vs_not": delta,
            "records_affected": len(results),
            "top_insight": top_insight,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

        return AgentResult(
            agent_name=self.name,
            status="success" if not errors else "partial",
            data=data,
            errors=errors,
        )
