"""
Export the Ohio Manufacturing Intelligence Report as HTML (printable to PDF).

Run:
    python -m report.gov_report_html --output Ohio_Report.html
    # Then print to PDF from browser

HTML report is designed for:
- A4 paper (printable)
- Professional government-style formatting
- Color-coded urgency badges (green/yellow/amber)
- Score visualizations inline
"""


import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.v2.government import get_ohio_manufacturing_intelligence

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)

HEAD = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ohio Manufacturing Opportunity Intelligence Report</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  * { box-sizing: border-box; margin: 0; padding: 0; }
  @media print {
    @page { margin: 1.5cm 2cm; size: A4; }
    body { font-size: 10pt; }
  }
  body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 11pt;
    color: #1a1a2e;
    max-width: 900px;
    margin: 0 auto;
    padding: 20px;
    background: #fff;
    line-height: 1.5;
  }
  /* Header */
  .report-header {
    border-bottom: 3px solid #1e3a5f;
    padding-bottom: 12px;
    margin-bottom: 24px;
  }
  .report-header h1 {
    font-size: 20pt;
    font-weight: 700;
    color: #1e3a5f;
    letter-spacing: -0.5px;
  }
  .report-meta {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 6px 16px;
    font-size: 9pt;
    color: #555;
    margin-top: 6px;
    background: #f8f9fa;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    padding: 8px 12px;
  }
  .report-meta strong { color: #1e3a5f; }

  /* KPI strip */
  .kpi-strip {
    display: flex;
    gap: 12px;
    margin-bottom: 20px;
    flex-wrap: wrap;
  }
  .kpi-box {
    flex: 1;
    min-width: 100px;
    background: #1e3a5f;
    color: white;
    border-radius: 8px;
    padding: 10px 14px;
    text-align: center;
  }
  .kpi-box.green { background: #065f46; }
  .kpi-box.blue { background: #1e40af; }
  .kpi-box.purple { background: #5b21b6; }
  .kpi-box.orange { background: #92400e; }
  .kpi-value { font-size: 18pt; font-weight: 700; color: #fff; }
  .kpi-label { font-size: 8pt; color: #cbd5e1; text-transform: uppercase; letter-spacing: 0.5px; }

  /* Recommendation table */
  .rec-table { width: 100%; border-collapse: collapse; margin-bottom: 24px; font-size: 9.5pt; }
  .rec-table th {
    background: #1e3a5f;
    color: white;
    padding: 8px 10px;
    text-align: left;
    font-weight: 600;
    font-size: 8.5pt;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .rec-table td {
    padding: 8px 10px;
    border-bottom: 1px solid #e5e7eb;
    vertical-align: middle;
  }
  .rec-table tr:hover { background: #f8fafc; }
  .rec-table .rank { font-weight: 700; color: #1e3a5f; width: 30px; text-align: center; }
  .rec-table .score-cell { font-weight: 700; white-space: nowrap; }
  .score-high { color: #065f46; }
  .score-mid { color: #92400e; }
  .score-low { color: #991b1b; }
  .badge {
    display: inline-block;
    padding: 2px 7px;
    border-radius: 99px;
    font-size: 8pt;
    font-weight: 600;
  }
  .badge-green { background: #d1fae5; color: #065f46; }
  .badge-yellow { background: #fef3c7; color: #92400e; }
  .badge-orange { background: #fed7aa; color: #c2410c; }
  .badge-gray { background: #f3f4f6; color: #6b7280; }

  /* Confidence indicator */
  .conf-dot {
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    margin-right: 4px;
  }
  .conf-high { background: #10b981; }
  .conf-mid { background: #f59e0b; }
  .conf-low { background: #ef4444; }

  /* Opportunity cards */
  .opp-card {
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 14px 16px;
    margin-bottom: 16px;
    page-break-inside: avoid;
  }
  .opp-header {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    margin-bottom: 10px;
  }
  .opp-rank {
    width: 28px; height: 28px;
    border-radius: 50%;
    background: #1e3a5f;
    color: white;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 11pt;
    flex-shrink: 0;
  }
  .opp-rank.gold { background: #b45309; }
  .opp-rank.green { background: #065f46; }
  .opp-rank.yellow { background: #92400e; }
  .opp-title {
    font-size: 12pt; font-weight: 600; color: #1e3a5f;
    flex: 1;
  }
  .opp-grade {
    font-size: 14pt; font-weight: 800; color: #1e3a5f;
    min-width: 30px; text-align: right;
  }
  .opp-grade.gold { color: #b45309; }
  .opp-grade.green { color: #065f46; }
  .opp-title-sub { font-size: 9pt; color: #6b7280; margin-top: 2px; }
  .opp-scores-row {
    display: flex; gap: 6px; margin-bottom: 8px; flex-wrap: wrap;
  }
  .score-chip {
    display: inline-flex; align-items: center; gap: 4px;
    background: #f1f5f9;
    border: 1px solid #cbd5e1;
    border-radius: 99px;
    padding: 3px 8px;
    font-size: 8.5pt;
    font-weight: 600;
  }
  .score-chip.demand { background: #dcfce7; border-color: #86efac; }
  .score-chip.gap { background: #dbeafe; border-color: #93c5fd; }
  .score-chip.feas { background: #f3e8ff; border-color: #d8b4fe; }
  .score-chip.timing { background: #ccfbf1; border-color: #5eead4; }
  .score-chip.comp { background: #fee2e2; border-color: #fca5a5; }
  .opp-meta-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
    gap: 6px;
    margin-bottom: 8px;
  }
  .meta-item {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 6px 8px;
    font-size: 8.5pt;
  }
  .meta-item .meta-label {
    color: #6b7280; font-size: 7.5pt; text-transform: uppercase; letter-spacing: 0.3px;
  }
  .meta-item .meta-val { font-weight: 700; color: #1e3a5f; font-size: 9pt; }
  .opp-desc {
    font-size: 9pt; color: #374151;
    background: #fffbeb;
    border-left: 3px solid #fbbf24;
    border-radius: 0 4px 4px 0;
    padding: 6px 10px;
    margin-bottom: 8px;
  }
  .opp-actions {
    background: #f0fdf4;
    border: 1px solid #86efac;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 9pt;
    color: #065f46;
  }
  .evidence-list { margin-top: 6px; }
  .evidence-list li { margin-left: 14px; font-size: 8.5pt; color: #374151; }

  /* Policy section */
  .policy-grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 8px; margin-bottom: 16px;
  }
  .policy-item {
    background: #eff6ff;
    border: 1px solid #93c5fd;
    border-radius: 6px;
    padding: 8px 10px;
    font-size: 9pt;
  }
  .policy-item strong { color: #1e40af; }
  .policy-item span { color: #374151; }

  /* Footer */
  .report-footer {
    border-top: 2px solid #1e3a5f;
    padding-top: 10px;
    margin-top: 30px;
    font-size: 8pt;
    color: #6b7280;
  }
  .section-label {
    font-size: 9pt;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #9ca3af;
    font-weight: 600;
    margin-bottom: 8px;
    border-bottom: 1px solid #e5e7eb;
    padding-bottom: 4px;
  }
</style>
</head>
<body>
"""


FOOT = """\
<div class="report-footer">
  <p>Report generated: {timestamp} UTC | Manufacturing Opportunity Intelligence Platform v{model_version} |
     Data sources: BloombergNEF, DOE, IEA, Benchmark Mineral Intelligence, Argonne National Lab, Ohio EDC |
     Confidence note: CAPEX estimates require supplier validation. Scores are directional.</p>
</div>
</body>
</html>"""


def score_badge(score: float) -> str:
    if score >= 75: return "badge-green"
    if score >= 60: return "badge-yellow"
    return "badge-orange"


def conf_html(score: float) -> str:
    if score >= 0.75: c, label = "conf-high", "High"
    elif score >= 0.5: c, label = "conf-mid", "Medium"
    else: c, label = "conf-low", "Low"
    return f'<span class="conf-dot {c}"></span>{label}'


def grade_html(score: float) -> str:
    if score >= 90: return "A+", "gold"
    if score >= 75: return "A", "green"
    if score >= 65: return "B", "green"
    if score >= 55: return "C", "gold"
    return "D", ""


def chip(color: str, label: str, val: float) -> str:
    return f'<span class="score-chip {color}">{label}: <b>{val:.0f}</b></span>'


def opp_card_html(opp: dict[str, Any], rank: int) -> str:
    score = opp.get("opportunity_score", 0)
    grade, grade_color = grade_html(score)
    desc = opp.get("description", "")

    # Evidence
    ev = {}
    try:
        ev = json.loads(opp.get("evidence_json", "{}"))
    except Exception:
        pass
    sigs = ev.get("signals", [])[:4]
    ev_html = ""
    if sigs:
        ev_lis = "".join(f"<li>{s}</li>" for s in sigs)
        ev_html = f'<p class="evidence-list"><b>Evidence:</b><ul>{ev_lis}</ul></p>'

    # Customers
    cust = opp.get("addressable_customer_types", [])
    if cust:
        cust_str = ", ".join(cust[:3])
    else:
        cust_str = "—"

    # CAPEX formatting
    capex_min = opp.get("estimated_capex_min") or 0
    capex_max = opp.get("estimated_capex_max") or 0
    capex_str = f"${capex_min/1e6:.0f}–${capex_max/1e6:.0f}M"

    tam = opp.get("total_addressable_market_billion", 0)
    sam = opp.get("service_addressable_market_billion", 0)
    jobs = opp.get("jobs_creation_estimate", 0)
    t2m = opp.get("time_to_market_months", 0)
    growth = opp.get("expected_growth_rate_pct", 0)

    badge_class = score_badge(score)
    badge_text = "STRONG" if score >= 75 else "CONDITIONAL" if score >= 60 else "VALIDATE"
    badge_color = "green" if score >= 75 else "yellow" if score >= 60 else "orange"

    return f"""\
<div class="opp-card">
  <div class="opp-header">
    <div class="opp-rank {"gold" if rank <= 3 else ("green" if rank <= 5 else "yellow")}">{rank}</div>
    <div>
      <div class="opp-title">{opp.get('title', '')}</div>
      <div class="opp-title-sub">{opp.get('sector', '')} &middot; {opp.get('sub_sector', '')} &middot; {opp.get('opportunity_type', '')}</div>
    </div>
    <div class="opp-grade" style="{'color:#b45309' if grade == 'A+' else 'color:#065f46' if grade in ('A','B') else 'color:#92400e'}">{grade}</div>
    <span class="badge badge-{badge_color}">{badge_text}</span>
  </div>

  <div class="opp-scores-row">
    {chip("demand", "Demand", opp.get("demand_score", 0))}
    {chip("gap", "Supply Gap", opp.get("supply_gap_score", 0))}
    {chip("feas", "Feasibility", opp.get("feasibility_score", 0))}
    {chip("timing", "Timing", opp.get("timing_score", 0))}
    {chip("comp", "Competition", 100 - opp.get("competition_score", 0))}
  </div>

  <div class="opp-meta-grid">
    <div class="meta-item">
      <div class="meta-label">Total Market (TAM)</div>
      <div class="meta-val">${tam:.0f}B</div>
    </div>
    <div class="meta-item">
      <div class="meta-label">Serviceable Mkt</div>
      <div class="meta-val">${sam:.0f}B</div>
    </div>
    <div class="meta-item">
      <div class="meta-label">Growth Rate</div>
      <div class="meta-val">{growth:.0f}%/yr</div>
    </div>
    <div class="meta-item">
      <div class="meta-label">Est. CAPEX</div>
      <div class="meta-val">{capex_str}</div>
    </div>
    <div class="meta-item">
      <div class="meta-label">Time to Market</div>
      <div class="meta-val">{t2m} months</div>
    </div>
    <div class="meta-item">
      <div class="meta-label">Est. Direct Jobs</div>
      <div class="meta-val">{jobs:,}</div>
    </div>
    <div class="meta-item">
      <div class="meta-label">Confidence</div>
      <div class="meta-val">{conf_html(opp.get("confidence_score", 0))}</div>
    </div>
    <div class="meta-item">
      <div class="meta-label">Addressable Customers</div>
      <div class="meta-val">{cust_str}</div>
    </div>
  </div>

  {f'<div class="opp-desc">{desc[:400]}{"..." if len(desc) > 400 else ""}</div>' if desc else ""}
  {ev_html}
</div>
"""


def build_html(data: dict[str, Any]) -> str:
    opps = data.get("opportunities", [])
    stats = data.get("stats", {})
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M")

    # Sort by score
    def sort_key(o):
        s = o.get("opportunity_score", 0)
        c = o.get("confidence_score", 0)
        return (s >= 75, s >= 60, s >= 45, s)
    sorted_opps = sorted(opps, key=sort_key, reverse=True)

    # Recommendation table rows
    rec_rows = []
    for i, opp in enumerate(sorted_opps, 1):
        score = opp.get("opportunity_score", 0)
        capex_min = opp.get("estimated_capex_min") or 0
        capex_max = opp.get("estimated_capex_max") or 0
        capex_str = f"${capex_min/1e6:.0f}–{capex_max/1e6:.0f}M"
        badge_class = score_badge(score)
        badge_text = "Strong" if score >= 75 else "Conditional" if score >= 60 else "Validate"
        conf = conf_html(opp.get("confidence_score", 0))
        score_cls = "score-high" if score >= 75 else "score-mid"
        rec_rows.append(
            f'<tr>'
            f'<td class="rank">{i}</td>'
            f'<td>{opp.get("title", "")[:60]}</td>'
            f'<td class="score-cell {score_cls}"><b>{score:.0f}</b></td>'
            f'<td>{opp.get("jobs_creation_estimate", 0):,}</td>'
            f'<td>{capex_str}</td>'
            f'<td>{conf}</td>'
            f'<td><span class="badge {badge_class}">{badge_text}</span></td>'
            f'</tr>'
        )
    rec_table_html = "\n".join(rec_rows)

    # Opportunity cards
    cards_html = "".join(
        opp_card_html(opp, i+1)
        for i, opp in enumerate(sorted_opps)
    )

    return (
        HEAD +
        f"""
  <div class="report-header">
    <h1>Ohio Manufacturing Opportunity Intelligence Report</h1>
    <div class="report-meta">
      <div><strong>Prepared for:</strong> Ohio Development Services Agency</div>
      <div><strong>Date:</strong> {datetime.utcnow().strftime("%B %d, %Y")}</div>
      <div><strong>Model:</strong> v2.0.0</div>
      <div><strong>Sector:</strong> EV Battery Manufacturing</div>
      <div><strong>Region:</strong> Ohio, USA</div>
    </div>
  </div>

  <div class="kpi-strip">
    <div class="kpi-box green">
      <div class="kpi-value">{stats.get("total_opportunities", 0)}</div>
      <div class="kpi-label">Opportunities</div>
    </div>
    <div class="kpi-box purple">
      <div class="kpi-value">{stats.get("avg_opportunity_score", 0):.0f}</div>
      <div class="kpi-label">Avg Score /100</div>
    </div>
    <div class="kpi-box blue">
      <div class="kpi-value">${stats.get("total_tam_billion", 0):.0f}B</div>
      <div class="kpi-label">Total Market</div>
    </div>
    <div class="kpi-box green">
      <div class="kpi-value">{stats.get("total_jobs_estimate", 0):,}</div>
      <div class="kpi-label">Est. Direct Jobs</div>
    </div>
  </div>

  <p class="section-label">Recommendation Summary</p>
  <table class="rec-table">
    <thead>
      <tr>
        <th>#</th><th>Opportunity</th><th>Score</th><th>Jobs</th><th>CAPEX</th><th>Confidence</th><th>Recommendation</th>
      </tr>
    </thead>
    <tbody>{rec_table_html}</tbody>
  </table>

  <p class="section-label">Policy Alignment</p>
  <div class="policy-grid">
    <div class="policy-item"><strong>CHIPS & Science Act</strong><br><span>Battery manufacturing credits ($35/kWh production credit)</span></div>
    <div class="policy-item"><strong>Inflation Reduction Act</strong><br><span>Domestic content requirements for EVs</span></div>
    <div class="policy-item"><strong>Ohio TechCred Program</strong><br><span>Workforce training for advanced manufacturing</span></div>
    <div class="policy-item"><strong>Bipartisan Infrastructure Law</strong><br><span>Grid energy storage buildout</span></div>
  </div>

  <p class="section-label">Detailed Opportunity Analysis</p>
  {cards_html}

  <div class="report-footer">
    Report generated: {ts} UTC | Manufacturing Opportunity Intelligence Platform v2.0.0 |
    Data sources: BloombergNEF, DOE Vehicle Technologies Office, IEA Global EV Outlook, Benchmark Mineral Intelligence,
    Argonne National Lab, Ohio EDC, Ohio TechCred. |
    <strong>IMPORTANT:</strong> CAPEX estimates require validation with equipment suppliers and real estate
    brokers. Scores are directional. Low-confidence recommendations (confidence < 50%) should be validated
    with on-site assessments before any investment decisions.
  </div>
</body>
</html>"""
    )


def main(output_path: str = "Ohio_Mfg_Opportunity_Report.html") -> None:
    result = get_ohio_manufacturing_intelligence()
    body = result.body.decode()
    data = json.loads(body)

    html = build_html(data)
    path = Path(output_path)
    path.write_text(html)
    _logger.info("HTML report written to %s (%d bytes)", path, len(html))
    print(f"\n✅ HTML report generated: {path}")
    print("   Open in browser and print to PDF for government distribution.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="Ohio_Mfg_Opportunity_Report.html")
    main(output_path=parser.parse_args().output)