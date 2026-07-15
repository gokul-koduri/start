"""
Ohio Manufacturing Opportunity Decision Report — Government Version.

Generates a printable PDF-ready markdown report from the manufacturing
opportunities database, formatted for Ohio Economic Development directors.

Run:
    python -m report.government_report --region Ohio --output ohio_report.md
    pandoc ohio_report.md -o ohio_report.pdf

Template follows Government Decision Workflow (from Implementation Plan v2).
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.v2.government import get_ohio_manufacturing_intelligence

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Report configuration
# ---------------------------------------------------------------------------

REGION = "Ohio"
STATE_ABBR = "OH"
REPORT_DATE = datetime.utcnow().strftime("%B %d, %Y")
PREPARED_FOR = "Ohio Development Services Agency"
PREPARED_BY = "Manufacturing Opportunity Intelligence Platform"
MODEL_VERSION = "v2.0.0"

# ---------------------------------------------------------------------------
# Score label helpers
# ---------------------------------------------------------------------------

def score_label(score: float) -> str:
    if score >= 75: return "STRONG RECOMMENDATION"
    if score >= 60: return "Conditional Recommendation"
    if score >= 45: return "Requires Validation"
    return "Not Recommended"


def score_grade(score: float) -> str:
    if score >= 90: return "A+"
    if score >= 85: return "A"
    if score >= 80: return "A-"
    if score >= 75: return "B+"
    if score >= 70: return "B"
    if score >= 65: return "B-"
    if score >= 60: return "C+"
    if score >= 55: return "C"
    if score >= 50: return "C-"
    return "D"


def conf_label(score: float) -> str:
    if score >= 0.75: return "High"
    if score >= 0.50: return "Medium"
    return "Low"


def format_capex(min_v: Optional[float], max_v: Optional[float]) -> str:
    if not min_v and not max_v:
        return "TBD"
    if not max_v:
        return f"${round(min_v / 1e6):.0f}M+"
    if not min_v:
        return f"${round(max_v / 1e6):.0f}M"
    return f"${round(min_v / 1e6):.0f}–${round(max_v / 1e6):.0f}M"


def score_bar(score: float, width: int = 20) -> str:
    filled = int(width * score / 100)
    return "[" + "=" * filled + " " * (width - filled) + "] " + f"{score:.0f}"


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def section_header(title: str, level: int = 1) -> str:
    if level == 1:
        return f"\n\n{'#' * 2} {title}\n\n"
    elif level == 2:
        return f"\n{'#' * 3} {title}\n\n"
    else:
        return f"\n{'#' * 4} {title}\n\n"


def kpi_box(score: float, label: str, detail: str = "") -> str:
    grade = score_grade(score)
    bar = score_bar(score)
    detail_str = f"  *{detail}*" if detail else ""
    return f"| {bar} | **{label}** |\n"


def opportunity_block(opp: dict[str, Any], rank: int) -> str:
    title = opp["title"]
    score = opp["opportunity_score"]
    label = score_label(score)
    grade = score_grade(score)
    confidence = conf_label(opp.get("confidence_score", 0))
    tam = opp.get("total_addressable_market_billion", 0)
    sam = opp.get("service_addressable_market_billion", 0)
    capex = format_capex(opp.get("estimated_capex_min"), opp.get("estimated_capex_max"))
    jobs = opp.get("jobs_creation_estimate", 0)
    t2m = opp.get("time_to_market_months", 0)
    growth = opp.get("expected_growth_rate_pct", 0)
    sector = opp.get("sector", "")
    sub_sector = opp.get("sub_sector", "")
    opp_type = opp.get("opportunity_type", "")
    evidence_raw = opp.get("evidence_json", "{}")
    try:
        evidence = json.loads(evidence_raw)
    except Exception:
        evidence = {}

    # Risk/urgency badge
    if confidence == "Low":
        risk_tag = "⚠️ MEDIUM CONFIDENCE — Validate before action"
    elif score >= 75:
        risk_tag = "✅ HIGH PRIORITY"
    else:
        risk_tag = "🔶 CONDITIONAL PRIORITY"

    lines = [
        section_header(f"#{rank}: {title}", level=3),
        f"**Grade: {grade}** | **Score: {score:.0f}/100** | {label} | Confidence: {confidence}\n",
        f"{risk_tag}\n",
        "---",
        "",
        "### Quick Facts\n",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Sector | {sector} |",
        f"| Sub-sector | {sub_sector} |",
        f"| Type | {opp_type} |",
        f"| Total Addressable Market | ${tam:.0f}B |",
        f"| Serviceable Market | ${sam:.0f}B |",
        f"| Growth Rate | {growth:.0f}%/year |",
        f"| Capital Required | {capex} |",
        f"| Time to Market | {t2m} months |",
        f"| Est. Direct Jobs | {jobs:,} |",
        "",
        "### Multi-Dimensional Scores\n",
        "| Factor | Score | Assessment |",
        "|--------|-------|-------------|",
    ]

    # Score breakdown
    factor_map = [
        ("Market Demand", opp.get("demand_score", 0)),
        ("Supply Gap", opp.get("supply_gap_score", 0)),
        ("Manufacturing Feasibility", opp.get("feasibility_score", 0)),
        ("Timing / Policy Window", opp.get("timing_score", 0)),
        ("Competition Intensity", opp.get("competition_score", 0)),
    ]
    for factor, val in factor_map:
        assess = "Strong" if val >= 70 else "Moderate" if val >= 50 else "Weak"
        lines.append(f"| {factor} | {val:.0f}/100 | {assess} |")

    # Description
    desc = opp.get("description", "")
    if desc:
        lines += ["", "### Business Case\n", desc[:500] + ("..." if len(desc) > 500 else "")]

    # Evidence
    signals = evidence.get("signals", [])
    if signals:
        lines += ["", "### Supporting Evidence\n"]
        for sig in signals[:5]:
            lines.append(f"  • {sig}")

    # Addressable customers
    cust_types = opp.get("addressable_customer_types", [])
    if cust_types:
        lines += ["", "### Addressable Customers\n"]
        for c in cust_types:
            lines.append(f"  • {c}")

    # Confidence note
    if confidence in ("Low", "Medium"):
        lines += [
            "",
            f"> ⚠️ **Confidence: {confidence}** — CAPEX estimates require validation with equipment"
            " suppliers and real estate brokers before investment decisions. Feasibility scores"
            " reflect current data and may change with site-specific assessments."
        ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Report assembly
# ---------------------------------------------------------------------------

def build_report(data: dict[str, Any]) -> str:
    """Assemble full markdown report."""
    opps = data.get("opportunities", [])
    stats = data.get("stats", {})
    meta = data.get("metadata", {})

    # Sort: strong first, then by score
    strong = [o for o in opps if o["opportunity_score"] >= 75]
    conditional = [o for o in opps if 60 <= o["opportunity_score"] < 75]
    validate = [o for o in opps if o["opportunity_score"] < 60]
    sorted_opps = strong + conditional + validate

    lines = [
        "# Ohio Manufacturing Opportunity Intelligence Report",
        "",
        f"**Prepared for:** {PREPARED_FOR}",
        f"**Date:** {REPORT_DATE}",
        f"**Prepared by:** {PREPARED_BY}",
        f"**Model version:** {MODEL_VERSION}",
        f"**Query:** Manufacturing opportunities in {REGION}, EV Battery sector",
        "",
        "> **Mission:** Which manufacturing companies should Ohio build — and why?",
        "",
        "---",
        "",
        "## Executive Summary\n",
        f"{len(opps)} manufacturing opportunities identified across the EV Battery supply chain.",
        f"Average opportunity score: **{stats.get('avg_opportunity_score', 0):.0f}/100**",
        f"Total addressable market: **${stats.get('total_tam_billion', 0):.0f}B**",
        f"Estimated direct job creation: **{stats.get('total_jobs_estimate', 0):,} jobs**",
        "",
        "### Prioritized Recommendation Summary\n",
        "| Priority | Opportunity | Score | Jobs | CAPEX | Confidence |",
        "|----------|-------------|-------|------|-------|------------|",
    ]

    for i, opp in enumerate(sorted_opps, 1):
        capex = format_capex(opp.get("estimated_capex_min"), opp.get("estimated_capex_max"))
        conf = conf_label(opp.get("confidence_score", 0))
        lines.append(
            f"| #{i} | {opp['title'][:45]} | **{opp['opportunity_score']:.0f}** "
            f"| {opp['jobs_creation_estimate']:,} | {capex} | {conf} |"
        )

    lines += [
        "",
        "---",
        "",
        "## Policy Alignment\n",
        "These opportunities align with:\n",
        "  • **CHIPS and Science Act** — Battery manufacturing incentives ($35/kWh production credit)",
        "  • **Inflation Reduction Act** — Domestic content requirements for EVs",
        "  • **Ohio Edison TechCred program** — Workforce training for advanced manufacturing",
        "  • **Bipartisan Infrastructure Law** — Grid energy storage buildout",
        "",
        "---",
    ]

    for i, opp in enumerate(sorted_opps, 1):
        lines.append(opportunity_block(opp, i))

    # Methodology
    lines += [
        "",
        "---",
        section_header("Methodology", level=2),
        "### Scoring Model\n",
        "Each opportunity was scored across 5 dimensions (0-100 scale):\n",
        "  • **Market Demand (25%)**: TAM, growth rate, unmet demand volume",
        "  • **Supply Gap (25%)**: Import dependency, domestic capacity shortage",
        "  • **Manufacturing Feasibility (20%)**: Process complexity, equipment availability, TRL",
        "  • **Timing/Policy Window (15%)**: Policy incentives, technology maturity, market readiness",
        "  • **Competition (15%)**: Lower is better (market concentration, barriers to entry)\n",
        "**Composite Score** = Demand×0.25 + Gap×0.25 + Feasibility×0.20 + Timing×0.15 + (100-Competition)×0.15\n",
        "### Confidence Scoring\n",
        "Confidence (0-1) reflects data completeness, source reliability, and evidence count.",
        "Low-confidence scores (below 0.5) should be validated with real supplier quotes.",
        "",
        "### Data Sources\n",
        "See individual opportunity evidence for source citations. Primary sources:",
        "  • BloombergNEF, DOE Vehicle Technologies Office, IEA Global EV Outlook",
        "  • Benchmark Mineral Intelligence, Argonne National Lab",
        "  • Ohio EDC, Ohio TechCred, IMEC workforce data",
        "  • Company filings (LG Energy Solution, SK On, CATL announcements)",
        "",
        "---",
        "",
        f"*Report generated: {datetime.utcnow().isoformat()} UTC | {PREPARED_BY} | {MODEL_VERSION}*",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(
    output_path: str = "Ohio_Mfg_Opportunity_Report.md",
    api_url: str | None = None,
) -> None:
    """Build the government decision report."""
    _logger.info("Building %s Manufacturing Opportunity Report...", REGION)

    # Fetch data via API or direct
    try:
        import os
        base_url = api_url or os.environ.get(
            "NEXT_PUBLIC_API_URL",
            "http://localhost:8001"
        )
        resp = requests.get(
            f"{base_url}/api/v2/government/ohio-manufacturing",
            timeout=30,
        )
        resp.raise_for_status()
        raw = resp.json()
        _logger.info("Fetched %d opportunities from API", len(raw.get("opportunities", [])))
    except Exception as e:
        _logger.warning("Failed to fetch from API (%s), using direct function", e)
        result = get_ohio_manufacturing_intelligence()
        body = result.body.decode()
        raw = json.loads(body)

    # Build report
    report_text = build_report(raw)

    # Write output
    output_path = Path(output_path)
    output_path.write_text(report_text)
    _logger.info(
        "Report written to %s (%d lines, %d bytes)",
        output_path,
        report_text.count('\n'),
        len(report_text),
    )

    print(f"\n✅ Report generated: {output_path}")
    print(f"   Opportunities: {len(raw.get('opportunities', []))}")
    print(f"   Total TAM: ${raw.get('stats', {}).get('total_tam_billion', 0):.0f}B")
    print(f"   Est. jobs: {raw.get('stats', {}).get('total_jobs_estimate', 0):,}")
    print("\n   To convert to PDF:")
    print(f"   pandoc {output_path} -o {output_path.with_suffix('.pdf')}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate Ohio Manufacturing Opportunity Report")
    parser.add_argument("--region", default=REGION)
    parser.add_argument("--output", default="Ohio_Mfg_Opportunity_Report.md")
    parser.add_argument("--api-url")
    args = parser.parse_args()
    main(output_path=args.output, api_url=args.api_url)