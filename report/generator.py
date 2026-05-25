"""Report generator: SQLite -> Markdown.

Reads data from the SQLite database and produces the full markdown report,
mirroring the structure of Failed_Startups_Manufacturing_Revival_Report.md.
"""

import sqlite3
import logging
import tempfile
import shutil
from datetime import datetime, timezone
from pathlib import Path

_logger = logging.getLogger(__name__)


def generate_report(
    conn: sqlite3.Connection,
    config: dict,
    output_path: str,
    section: str | None = None,
) -> str:
    """Generate the full markdown report from database data.

    Args:
        conn: Active SQLite connection (read-only is fine).
        config: Application configuration dict.
        output_path: Where to write the .md file.
        section: If set, only generate that section (e.g., "part1").

    Returns:
        Path to the generated file.
    """
    parts = []

    if section is None or section == "header":
        parts.append(_render_header(conn))

    if section is None or section == "part1":
        parts.append(_render_part1(conn))

    if section is None or section == "part2":
        parts.append(_render_part2(conn))

    if section is None or section == "part3":
        parts.append(_render_part3(conn))

    if section is None or section == "part4":
        parts.append(_render_part4(conn))

    if section is None or section == "news":
        parts.append(_render_news_monitoring(conn))

    if section is None or section == "methodology":
        parts.append(_render_methodology(conn))

    if section is None or section == "sources":
        parts.append(_render_sources(conn))

    if section is None:
        parts.append(_render_footer(conn))

    full_report = "\n".join(parts)

    # Write atomically
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(suffix=".md", dir=out.parent)
    try:
        with open(fd, "w", encoding="utf-8") as f:
            f.write(full_report)
        shutil.move(tmp_path, str(out))
    except Exception:
        Path(tmp_path).unlink(missing_ok=True)
        raise

    _logger.info("Report generated: %s (%d chars, %d sections)",
                 out, len(full_report), len(parts))
    return str(out)


# ── Section Renderers ──────────────────────────────────────────────

def _render_header(conn) -> str:
    return """\
# Research Report: Failed Startups & Revival-Ready Manufacturing Industries

---

## TABLE OF CONTENTS
1. [Part 1: Failed Startups That Got Seed Funding](#part-1)
   - [1A: United States & Global](#part-1a)
   - [1A-Extra: Manufacturing-Specific Startup Failures (2024-2025)](#manufacturing-specific-failures)
   - [1B: India](#part-1b)
   - [1C: China](#part-1c)
   - [1D: Europe](#part-1d)
   - [1E: Africa & Emerging Markets](#part-1e)
   - [1F: Manufacturing Failure Rate Statistics & Patterns](#part-1f)
2. [Part 2: Closed Manufacturing Units with Revival Potential](#part-2)
3. [Cross-Reference: Where Failed Startup Ideas Meet Manufacturing Revival](#part-3)
4. [Actionable Opportunities](#part-4)
4a. [News Monitoring: Manufacturing & Startup Failures](#news)
5. [Methodology](#methodology)
6. [Sources](#sources)

---"""


def _render_part1(conn) -> str:
    sections = []

    # Part 1A: US & Global
    sections.append(_render_part1a(conn))

    # Part 1A-Extra: Manufacturing-Specific Failures
    sections.append(_render_manufacturing_failures(conn))

    # Regional sections
    for region_name, region_id in [("India", "India"), ("China", "China"),
                                   ("Europe", "Europe"), ("Africa", "Africa")]:
        sections.append(_render_regional_section(conn, region_name, region_id))

    # Part 1F: Manufacturing Failure Statistics
    sections.append(_render_failure_statistics(conn))

    return "\n\n".join(sections)


def _render_part1a(conn) -> str:
    lines = [
        "## Part 1: Failed Startups That Got Seed Funding {#part-1}",
        "",
        "### Part 1A: United States & Global {#part-1a}",
        "",
    ]

    # Big Picture stats
    stats = _query_startup_stats(conn, "US & Global")
    lines.append("### The Big Picture")
    if stats:
        lines.append(f"- **{stats['total_startups']} tracked US/Global tech startups in the database**")
        lines.append(f"- **{stats['manufacturing_count']} are manufacturing-specific** ({stats['manufacturing_pct']}%)")
        lines.append(f"- **{stats['latest_year']} is the most recent shutdown year with data**")
    lines.append("")

    # Notable failed startups table
    startups = conn.execute("""
        SELECT name, sector, funding_description, year_shutdown, failure_reason
        FROM failed_startups
        WHERE region = 'US & Global' AND notable = 1
        ORDER BY year_shutdown DESC, funding_raised_usd DESC
    """).fetchall()

    lines.append("### Notable Failed Startups (2023–2025) With Funding")
    lines.append("")
    lines.append("| # | Startup | Sector | Funding Raised | Year Shutdown | Primary Failure Reason |")
    lines.append("|---|---------|--------|---------------|---------------|----------------------|")
    for i, s in enumerate(startups, 1):
        name = _bold(s["name"])
        funding = s["funding_description"] or "N/A"
        lines.append(f"| {i} | {name} | {s['sector'] or 'N/A'} | {funding} | {s['year_shutdown']} | {s['failure_reason']} |")

    # CB Insights failure reasons
    reasons = conn.execute("""
        SELECT reason, percentage, rank_order
        FROM failure_reasons_taxonomy
        ORDER BY rank_order
    """).fetchall()

    if reasons:
        lines.append("")
        lines.append("### Top Reasons Startups Fail (CB Insights Data)")
        lines.append("")
        lines.append("| Rank | Reason | % of Failures |")
        lines.append("|------|--------|--------------|")
        for r in reasons:
            lines.append(f"| {r['rank_order']} | {r['reason']} | {r['percentage']}% |")

    # Failure idea patterns
    patterns = conn.execute("""
        SELECT idea_category, example_startups, why_failed, market_reality
        FROM failure_idea_patterns
    """).fetchall()

    if patterns:
        lines.append("")
        lines.append("### Failed Ideas That Got Funding — Patterns to Learn From")
        lines.append("")
        lines.append("| Idea Category | Examples | Why It Failed | Market Reality |")
        lines.append("|---------------|----------|---------------|----------------|")
        for p in patterns:
            lines.append(f"| {p['idea_category']} | {p['example_startups'] or 'Various'} | {p['why_failed']} | {p['market_reality']} |")

    lines.append("")
    lines.append("### Key Lessons for New Founders")
    lines.append("1. **Validate demand BEFORE building** — 42% fail because nobody wants the product")
    lines.append("2. **Run lean** — don't assume Series A will arrive (85% don't raise it)")
    lines.append("3. **Build financial discipline early** — proper books, unit economics from day one")
    lines.append("4. **Growth on borrowed money != product-market fit**")
    lines.append("5. **Have a clear shutdown plan** — know what happens to IP, employees, obligations")
    lines.append("6. **Don't compete with platforms that can ship your feature for free** (critical for AI startups)")

    return "\n".join(lines)


def _render_manufacturing_failures(conn) -> str:
    startups = conn.execute("""
        SELECT name, manufacturing_sub_sector, funding_description, year_shutdown, failure_reason
        FROM failed_startups
        WHERE manufacturing_sub_sector IS NOT NULL
        ORDER BY year_shutdown DESC, funding_raised_usd DESC
    """).fetchall()

    if not startups:
        return ""

    lines = [
        "### Manufacturing-Specific Startup Failures (2024-2025) {#manufacturing-specific-failures}",
        "",
        "Manufacturing startups face uniquely brutal economics: long R&D cycles, massive capital requirements, "
        "hardware reliability challenges, and the \"pilot-to-scale\" gap.",
        "",
        "| # | Startup | Manufacturing Sub-Sector | Funding | Shutdown Year | Primary Failure Reason |",
        "|---|---------|------------------------|---------|---------------|----------------------|",
    ]

    for i, s in enumerate(startups, 1):
        funding = s["funding_description"] or "N/A"
        lines.append(
            f"| {i} | {_bold(s['name'])} | {s['manufacturing_sub_sector']} | {funding} | "
            f"{s['year_shutdown']} | {s['failure_reason']} |"
        )

    lines.append("")
    lines.append("**Common manufacturing failure patterns:** Capital intensity and long cash conversion cycles "
                 "make manufacturing startups highly vulnerable to funding downturns. The SPAC era (2020-2021) "
                 "was particularly damaging. The \"pilot-to-scale\" chasm is another recurring theme.")
    lines.append("")

    return "\n".join(lines)


def _render_regional_section(conn, region_name: str, region_id: str) -> str:
    startups = conn.execute("""
        SELECT name, sector, funding_description, year_shutdown, failure_reason
        FROM failed_startups
        WHERE region = ? AND notable = 1
        ORDER BY year_shutdown DESC, funding_raised_usd DESC
    """, (region_id,)).fetchall()

    if not startups:
        return ""

    _part_labels = ['', 'B', 'C', 'D', 'E']
    _region_ids = ['India', 'China', 'Europe', 'Africa']
    _idx = _region_ids.index(region_id) + 1 if region_id in _region_ids else 0
    _label = _part_labels[_idx] if _idx < len(_part_labels) else ''

    lines = [
        f"### Part 1{_label}: "
        f"{region_name} — Startup Failures {{#part-1{_label.lower()}}}",
        "",
        f"| # | Startup | Sector | Funding Raised | Year Shutdown | Primary Failure Reason |",
        "|---|---------|--------|---------------|---------------|----------------------|",
    ]

    for i, s in enumerate(startups, 1):
        funding = s["funding_description"] or "N/A"
        lines.append(f"| {i} | {_bold(s['name'])} | {s['sector'] or 'N/A'} | {funding} | {s['year_shutdown']} | {s['failure_reason']} |")

    return "\n".join(lines)


def _render_failure_statistics(conn) -> str:
    lines = [
        "## Part 1F: Manufacturing-Specific Failure Rate Statistics & Patterns {#part-1f}",
        "",
        "### The Scale of Manufacturing Startup Failures",
        "",
    ]

    # BLS data
    bls_rows = conn.execute("""
        SELECT year, quarter, age_5_yr_survival
        FROM bls_survival_rates
        WHERE naics_code = '31-33' AND age_5_yr_survival IS NOT NULL
        ORDER BY year DESC, quarter DESC
        LIMIT 10
    """).fetchall()

    if bls_rows:
        avg_survival = sum(r["age_5_yr_survival"] for r in bls_rows if r["age_5_yr_survival"]) / len([r for r in bls_rows if r["age_5_yr_survival"]])
        failure_rate = round(100 - avg_survival, 1)
        lines.append(f"- **~{failure_rate}% of manufacturing startups fail** within 5 years (BLS Business Employment Dynamics data)")

    lines.append("- **2 out of 3 digital manufacturing pilots fail to scale** beyond pilot stage (McKinsey / Industry 4.0 survey data)")

    # Failure categories
    cats = conn.execute("""
        SELECT failure_category, description, estimated_pct, example_startups
        FROM manufacturing_failure_categories
        ORDER BY estimated_pct DESC
    """).fetchall()

    if cats:
        lines.append("")
        lines.append("### Why Manufacturing Startups Fail: Root Cause Analysis")
        lines.append("")
        lines.append("| Failure Category | Description | % of Mfg Failures (est.) | Examples |")
        lines.append("|------------------|-------------|------------------------|----------|")
        for c in cats:
            lines.append(f"| {c['failure_category']} | {c['description']} | ~{int(c['estimated_pct'])}% | {c['example_startups'] or 'Various'} |")

    lines.append("")
    lines.append("### Key Insight: The \"Pilot-to-Scale\" Chasm")
    lines.append("")
    lines.append("The single most distinctive pattern in manufacturing startup failures is the gap between "
                 "successful pilot/prototype and commercial-scale deployment. Software startups can iterate "
                 "after launch; manufacturing startups must get it right *before* scale because physical "
                 "production is unforgiving.")
    lines.append("")

    return "\n".join(lines)


def _render_part2(conn) -> str:
    lines = [
        "## Part 2: Closed Manufacturing Units (5+ Years) With Revival Potential {#part-2}",
        "",
        "### The Reshoring Mega-Trend",
        "- Tariffs, supply chain fragility, and geopolitical risk are driving **manufacturing back to the U.S. and allied nations**",
        "- **CHIPS Act** ($52B) and **Inflation Reduction Act (IRA)** ($369B) are creating massive incentives",
        "- **22 million people needed** for new U.S. factories but only **7.2 million unemployed** — automation is essential",
        "",
    ]

    # Reshoring summary stats
    stats = conn.execute("""
        SELECT stat_year, total_jobs, success_rate_pct, key_policy, headline
        FROM reshoring_summary_stats
        ORDER BY stat_year DESC
    """).fetchall()

    if stats:
        lines.append("### Latest Reshoring Data")
        for s in stats:
            parts = []
            if s["total_jobs"]:
                parts.append(f"**{s['total_jobs']:,} jobs announced/created**")
            if s["success_rate_pct"]:
                parts.append(f"**{int(s['success_rate_pct'])}% success rate**")
            if s["key_policy"]:
                parts.append(f"**{s['key_policy']}**")
            if parts:
                lines.append("- " + "; ".join(parts) + f" ({s['stat_year']})")

    # Revival industries
    industries = conn.execute("""
        SELECT industry, died_period, why_returning, closed_site_types, market_fit, key_investors, market_size_2030
        FROM revival_industries
    """).fetchall()

    if industries:
        lines.append("")
        lines.append("### Industries With Revival Potential")
        for ind in industries:
            lines.append(f"#### {ind['industry']}")
            if ind["died_period"]:
                lines.append(f"- **When it died:** {ind['died_period']}")
            lines.append(f"- **Why it's back:** {ind['why_returning']}")
            if ind["closed_site_types"]:
                lines.append(f"- **Closed sites:** {ind['closed_site_types']}")
            lines.append(f"- **Market fit:** {ind['market_fit']}")
            lines.append("")

    # Geographic hotspots
    hotspots = conn.execute("""
        SELECT region, closed_facility_types, revival_potential
        FROM geographic_hotspots
    """).fetchall()

    if hotspots:
        lines.append("### Geographic Hotspots for Revival")
        lines.append("")
        lines.append("| Region | Closed Facilities | Revival Potential |")
        lines.append("|--------|-----------------|-------------------|")
        for h in hotspots:
            lines.append(f"| {h['region']} | {h['closed_facility_types']} | {h['revival_potential']} |")

    lines.append("")
    return "\n".join(lines)


def _render_part3(conn) -> str:
    lines = [
        "## Part 3: Where Failed Startup Ideas Meet Manufacturing Revival {#part-3}",
        "",
        "### High-Potential Intersections",
        "",
        "| Failed Startup Category | Manufacturing Revival Match | Opportunity |",
        "|------------------------|---------------------------|-------------|",
    ]

    # Get manufacturing failures grouped by sub-sector
    mfg_failures = conn.execute("""
        SELECT manufacturing_sub_sector, GROUP_CONCAT(name, ', ') as names
        FROM failed_startups
        WHERE manufacturing_sub_sector IS NOT NULL
        GROUP BY manufacturing_sub_sector
        ORDER BY COUNT(*) DESC
    """).fetchall()

    for f in mfg_failures:
        sub = f["manufacturing_sub_sector"]
        names = f["names"][:80] + "..." if len(f["names"]) > 80 else f["names"]
        lines.append(f"| **{sub}** ({names}) | Closed specialty manufacturing facilities | Learn from failures, apply to revival opportunities |")

    lines.append("")
    return "\n".join(lines)


def _render_part4(conn) -> str:
    lines = [
        "## Part 4: Actionable Opportunities {#part-4}",
        "",
        "### Ideas Worth Exploring (Based on Research)",
        "",
        "1. **Convert closed textile mills into advanced materials manufacturing** — carbon fiber, technical textiles for EVs and aerospace",
        "2. **Repurpose closed auto plants for EV battery recycling** — 10M+ EV batteries will need recycling by 2030",
        "3. **Turn closed pharma plants into API manufacturing for generic drugs** — U.S. imports 87% of APIs; Biosecure Act will force change",
        "4. **Convert closed steel mills into green hydrogen production** — hydrogen steel requires existing industrial infrastructure",
        "5. **Use closed electronics factories for edge computing hardware assembly** — AI needs physical compute closer to users",
        "6. **Repurpose closed paper mills into sustainable packaging/bioproducts** — plastic replacement demand is massive",
        "7. **Convert closed warehouse/distribution centers into automated micro-fulfillment** — e-commerce demand keeps growing",
        "8. **Turn former chemical plants into rare earth processing facilities** — DOE grants available; strategic necessity",
        "",
    ]

    # Data-driven opportunities based on recent failures
    mfg_count = conn.execute("SELECT COUNT(*) as c FROM failed_startups WHERE manufacturing_sub_sector IS NOT NULL").fetchone()
    news_count = conn.execute("SELECT COUNT(*) as c FROM news_articles WHERE is_manufacturing = 1 AND mentions_failure = 1").fetchone()

    lines.append("### Data-Driven Opportunities (from collected data)")
    lines.append(f"- **{mfg_count['c']} manufacturing startup failures** in database suggest clear patterns to avoid")
    lines.append(f"- **{news_count['c']} recent news articles** about manufacturing startup failures signal active market churn")
    lines.append("")

    return "\n".join(lines)


def _render_methodology(conn) -> str:
    lines = [
        "## Methodology {#methodology}",
        "",
        "### Research Approach",
        "This report was compiled using a **two-pronged research approach**:",
        "",
        "**Prong A: Failed Manufacturing Startups (2024-2025)**",
        "- Deep-dive into manufacturing-specific startup failures across sub-sectors",
        "- Focus on companies that raised significant venture or SPAC capital ($10M+) and subsequently failed",
        "- Data sources: Failory scraper (400+ profiles), Google News RSS, TechCrunch RSS",
        "",
        "**Prong B: Manufacturing Revival & Reshoring**",
        "- Latest reshoring statistics, government incentive programs, Industry 4.0 adoption",
        "- Data sources: BLS Public API (survival rates), Reshoring Initiative PDF reports",
        "",
        "### Data Freshness",
    ]

    # Show last collection runs
    runs = conn.execute("""
        SELECT collector_name, started_at, status, records_collected
        FROM collection_runs
        ORDER BY started_at DESC
    """).fetchall()

    if runs:
        lines.append("")
        lines.append("| Collector | Last Run | Status | Records |")
        lines.append("|-----------|----------|--------|---------|")
        for r in runs[:10]:
            started = r["started_at"][:19] if r["started_at"] else "N/A"
            lines.append(f"| {r['collector_name']} | {started} | {r['status']} | {r['records_collected']} |")

    # Data source counts
    src_counts = conn.execute("""
        SELECT source, COUNT(*) as cnt FROM failed_startups GROUP BY source ORDER BY cnt DESC
    """).fetchall()

    if src_counts:
        lines.append("")
        lines.append("### Data Sources")
        lines.append("| Source | Records |")
        lines.append("|--------|---------|")
        for s in src_counts:
            lines.append(f"| {s['source']} | {s['cnt']} |")

    lines.append("")
    return "\n".join(lines)


def _render_sources(conn) -> str:
    lines = ["## Sources {#sources}", ""]

    # Group sources by feed/type
    sources = conn.execute("""
        SELECT source, source_url, COUNT(*) as cnt
        FROM failed_startups
        WHERE source_url IS NOT NULL
        GROUP BY source, source_url
        ORDER BY source, cnt DESC
    """).fetchall()

    if sources:
        current_source = None
        for s in sources:
            if s["source"] != current_source:
                current_source = s["source"]
                lines.append(f"### {current_source.title()}")
            lines.append(f"- [{s['source_url']}]({s['source_url']}) ({s['cnt']} records)")

    lines.append("")
    return "\n".join(lines)


def _render_news_monitoring(conn) -> str:
    """Render a news monitoring section from collected articles."""
    lines = [
        "## News Monitoring: Manufacturing & Startup Failures {#news}",
        "",
    ]

    # Summary stats
    total = conn.execute("SELECT COUNT(*) FROM news_articles").fetchone()[0]
    mfg = conn.execute("SELECT COUNT(*) FROM news_articles WHERE is_manufacturing = 1").fetchone()[0]
    fail = conn.execute("SELECT COUNT(*) FROM news_articles WHERE mentions_failure = 1").fetchone()[0]
    both = conn.execute("SELECT COUNT(*) FROM news_articles WHERE is_manufacturing = 1 AND mentions_failure = 1").fetchone()[0]

    lines.append("### Coverage Summary")
    lines.append(f"- **{total}** articles collected from Google News and TechCrunch RSS feeds")
    lines.append(f"- **{mfg}** mention manufacturing ({round(mfg/total*100, 1)}%)")
    lines.append(f"- **{fail}** mention startup failures ({round(fail/total*100, 1)}%)")
    lines.append(f"- **{both}** are in the intersection (manufacturing + failure)")
    lines.append("")

    # By source
    by_source = conn.execute("""
        SELECT source_feed, COUNT(*) as cnt
        FROM news_articles
        GROUP BY source_feed ORDER BY cnt DESC
    """).fetchall()
    if by_source:
        lines.append("### Articles by Source")
        lines.append("| Source | Articles |")
        lines.append("|--------|----------|")
        for s in by_source:
            lines.append(f"| {s[0]} | {s[1]} |")
        lines.append("")

    # Top manufacturing + failure articles (most relevant)
    mfg_fail_articles = conn.execute("""
        SELECT title, url, source_name, published_at, summary
        FROM news_articles
        WHERE is_manufacturing = 1 AND mentions_failure = 1
        ORDER BY published_at DESC
        LIMIT 20
    """).fetchall()

    if mfg_fail_articles:
        lines.append("### Recent Manufacturing Startup Failures (News)")
        lines.append("")
        for a in mfg_fail_articles:
            pub = a["published_at"][:10] if a["published_at"] else ""
            source = a["source_name"] or ""
            summary = (a["summary"] or "")[:120].strip()
            if summary:
                summary = summary.rstrip(".") + "."
            lines.append(f"**[{pub}] {a['title']}**")
            lines.append(f"- *{source}* — {summary}")
            lines.append(f"- [Read more]({a['url']})")
            lines.append("")

    # Articles with extracted startup names
    named = conn.execute("""
        SELECT title, startup_name_extracted, source_name, published_at, url
        FROM news_articles
        WHERE startup_name_extracted IS NOT NULL AND startup_name_extracted != ''
        ORDER BY published_at DESC
        LIMIT 15
    """).fetchall()

    if named:
        lines.append("### Identified Startup Names in News")
        lines.append("")
        lines.append("| Startup | Article | Source | Date |")
        lines.append("|---------|---------|--------|------|")
        for n in named:
            pub = n["published_at"][:10] if n["published_at"] else ""
            title = n["title"][:50] + "..." if len(n["title"]) > 50 else n["title"]
            lines.append(f"| {n[0]} | [{title}]({n[3]}) | {n[1]} | {pub} |")
        lines.append("")

    return "\n".join(lines)


def _render_footer(conn) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Count total data points
    startup_count = conn.execute("SELECT COUNT(*) FROM failed_startups").fetchone()[0]
    news_count = conn.execute("SELECT COUNT(*) FROM news_articles").fetchone()[0]
    bls_count = conn.execute("SELECT COUNT(*) FROM bls_survival_rates").fetchone()[0]

    return f"""---

*Report generated on {now} from the Startup Research automated data collection system.*

*Database contains: {startup_count} startups, {news_count} news articles, {bls_count} BLS data points.*

*This report uses a two-pronged research approach: **Prong A** (Failed Manufacturing Startups 2024-2025) and **Prong B** (Manufacturing Revival & Reshoring). See [Methodology](#methodology) section for full details.*"""


# ── Helpers ────────────────────────────────────────────────────────

def _bold(text: str) -> str:
    return f"**{text}**"


def _query_startup_stats(conn, region: str) -> dict | None:
    row = conn.execute("""
        SELECT
            COUNT(*) as total_startups,
            SUM(CASE WHEN manufacturing_sub_sector IS NOT NULL THEN 1 ELSE 0 END) as manufacturing_count,
            MAX(year_shutdown) as latest_year
        FROM failed_startups
        WHERE region = ?
    """, (region,)).fetchone()

    if not row or row["total_startups"] == 0:
        return None

    total = row["total_startups"]
    mfg = row["manufacturing_count"] or 0
    pct = round(mfg / total * 100, 1)

    return {
        "total_startups": total,
        "manufacturing_count": mfg,
        "manufacturing_pct": pct,
        "latest_year": row["latest_year"],
    }
