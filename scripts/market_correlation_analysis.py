#!/usr/bin/env python3
"""Cross-module market correlation analysis.

Reads live data from MySQL produced by all 7 analysis agents + raw data tables,
computes correlations across modules, and writes a markdown report.

Usage:
    python3 scripts/market_correlation_analysis.py
    python3 scripts/market_correlation_analysis.py --output custom_report.md
"""

import argparse
import json
import logging
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.connection import get_connection

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
_logger = logging.getLogger("correlation_analysis")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_latest_insights(conn, table: str) -> dict:
    """Load the latest insights_json from an analysis_* table."""
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT insights_json FROM {table} ORDER BY analyzed_at DESC LIMIT 1"
    )
    row = cursor.fetchone()
    cursor.close()
    if not row:
        return {}
    try:
        return json.loads(row["insights_json"])
    except (json.JSONDecodeError, TypeError):
        return {}


def pearson(xs: list[float], ys: list[float]) -> float:
    """Compute Pearson correlation coefficient. Returns 0 if undefined."""
    n = min(len(xs), len(ys))
    if n < 2:
        return 0.0
    xs, ys = xs[:n], ys[:n]
    mx, my = mean(xs), mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den_x = sum((x - mx) ** 2 for x in xs) ** 0.5
    den_y = sum((y - my) ** 2 for y in ys) ** 0.5
    if den_x == 0 or den_y == 0:
        return 0.0
    return num / (den_x * den_y)


def fmt_corr(r: float) -> str:
    """Format a correlation coefficient with strength label."""
    a = abs(r)
    if a >= 0.7:
        strength = "strong"
    elif a >= 0.4:
        strength = "moderate"
    elif a >= 0.2:
        strength = "weak"
    else:
        strength = "negligible"
    direction = "positive" if r >= 0 else "negative"
    return f"{r:+.3f} ({strength} {direction})"


def md_table(headers: list[str], rows: list[list]) -> str:
    """Render a small markdown table."""
    out = []
    out.append("| " + " | ".join(headers) + " |")
    out.append("| " + " | ".join("---" for _ in headers) + " |")
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Correlation analyses
# ---------------------------------------------------------------------------


def correlation_1_sector_failure_vs_revival(conn) -> dict:
    """Sector failure counts vs revival industry scores."""
    cursor = conn.cursor()

    # Failure counts by sub_sector
    cursor.execute("""
        SELECT manufacturing_sub_sector, COUNT(*) AS cnt
        FROM failed_startups
        WHERE manufacturing_sub_sector IS NOT NULL
        GROUP BY manufacturing_sub_sector
        ORDER BY cnt DESC
    """)
    failure_counts = {
        r["manufacturing_sub_sector"].lower(): r["cnt"] for r in cursor.fetchall()
    }

    # Revival industry scores from analysis
    revival_data = load_latest_insights(conn, "analysis_revival_opportunities")
    industry_scores = {}
    for item in revival_data.get("top_industries", []) or revival_data.get(
        "industries", []
    ):
        if isinstance(item, dict):
            name = (item.get("industry") or item.get("name") or "").lower()
            score = item.get("revival_score") or item.get("score") or 0
            if name:
                industry_scores[name] = float(score)

    # Match: for each revival industry, find failure count if matching sub_sector
    matches = []
    for industry, score in industry_scores.items():
        fcount = 0
        for sub, cnt in failure_counts.items():
            if (
                industry in sub
                or sub in industry
                or any(word in sub for word in industry.split())
            ):
                fcount += cnt
        matches.append(
            {"industry": industry, "revival_score": score, "failure_count": fcount}
        )

    # Pearson correlation: revival_score vs failure_count
    scores = [m["revival_score"] for m in matches if m["failure_count"] > 0]
    failures = [m["failure_count"] for m in matches if m["failure_count"] > 0]
    r = pearson(scores, failures) if scores else 0.0

    cursor.close()
    return {
        "title": "1. Sector Failure Count vs Revival Opportunity Score",
        "question": "Do sectors with the most failures also have the highest revival scores?",
        "matches": matches,
        "pearson_r": r,
        "interpretation": (
            f"Pearson r = {fmt_corr(r)}. "
            + (
                "Sectors that saw more failures DO tend to have higher revival scores — failure creates opportunity."
                if r > 0.3
                else "Weak or no positive correlation — failures and revival scoring are largely independent signals."
                if r > -0.3
                else "Negative correlation — revival scoring is driven by factors other than past failure volume."
            )
        ),
    }


def correlation_2_failure_reason_vs_survival(conn) -> dict:
    """Failure category distribution vs BLS survival rates by year."""
    cursor = conn.cursor()

    cursor.execute("""
        SELECT failure_category, COUNT(*) AS cnt
        FROM failed_startups
        WHERE failure_category IS NOT NULL
        GROUP BY failure_category
        ORDER BY cnt DESC
    """)
    cat_counts = [
        {"category": r["failure_category"], "count": r["cnt"]}
        for r in cursor.fetchall()
    ]

    cursor.execute("""
        SELECT year, AVG(age_5_yr_survival) AS avg_survival
        FROM bls_survival_rates
        WHERE age_5_yr_survival IS NOT NULL
        GROUP BY year
        ORDER BY year
    """)
    survival_by_year = [
        {"year": r["year"], "avg_5yr": float(r["avg_survival"])}
        for r in cursor.fetchall()
    ]

    cursor.execute("""
        SELECT year_shutdown, COUNT(*) AS cnt
        FROM failed_startups
        WHERE year_shutdown IS NOT NULL
        GROUP BY year_shutdown
        ORDER BY year_shutdown
    """)
    failures_by_year = {r["year_shutdown"]: r["cnt"] for r in cursor.fetchall()}

    # Pearson: shutdown-year failure count vs same-year survival rate
    years = sorted(set(failures_by_year.keys()) & {s["year"] for s in survival_by_year})
    fail_counts = [failures_by_year[y] for y in years]
    surv = [
        next(s["avg_5yr"] for s in survival_by_year if s["year"] == y) for y in years
    ]
    r = pearson(fail_counts, surv) if years else 0.0

    cursor.close()
    return {
        "title": "2. Failure Reason Distribution vs BLS Survival Rates",
        "question": "Are failure categories concentrated in low-survival years?",
        "category_counts": cat_counts,
        "survival_by_year": survival_by_year,
        "pearson_r": r,
        "interpretation": (
            f"Pearson r (failures vs survival rate by year) = {fmt_corr(r)}. "
            + (
                "Higher failure counts cluster in years with LOWER survival rates — external conditions matter."
                if r < -0.3
                else "No strong relationship — failures are driven more by company-specific factors than macro survival rates."
                if abs(r) < 0.3
                else "Surprising positive correlation — more failures recorded in higher-survival years (likely because more firms exist)."
            )
        ),
    }


def correlation_3_geo_failures_vs_whale(conn) -> dict:
    """Geographic failure density vs whale investor activity."""
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COALESCE(region, country, 'Unknown') AS area, COUNT(*) AS cnt
        FROM failed_startups
        GROUP BY area
        ORDER BY cnt DESC
        LIMIT 10
    """)
    geo_failures = [
        {"region": r["area"], "failure_count": r["cnt"]} for r in cursor.fetchall()
    ]

    # Whale investor findings: count by sector mentioned
    whale_data = load_latest_insights(conn, "analysis_whale_investors")
    whale_data.get("findings_by_sector", {})
    top_findings = whale_data.get("top_findings", [])

    # Count whale findings URLs mentioning each region
    region_mentions = Counter()
    for f in top_findings:
        text = (f.get("query", "") + " " + f.get("url", "")).lower()
        for gf in geo_failures:
            region = gf["region"].lower()
            if region and region != "unknown" and region in text:
                region_mentions[gf["region"]] += 1

    # Compute correlation
    failure_vals = [gf["failure_count"] for gf in geo_failures]
    whale_vals = [region_mentions.get(gf["region"], 0) for gf in geo_failures]
    r = pearson(failure_vals, whale_vals) if geo_failures else 0.0

    cursor.close()
    return {
        "title": "3. Geographic Failure Density vs Whale Investor Activity",
        "question": "Do whale investors target regions with high failure density?",
        "geo_failures": geo_failures,
        "whale_region_mentions": dict(region_mentions),
        "pearson_r": r,
        "interpretation": (
            f"Pearson r (failure density vs whale mentions) = {fmt_corr(r)}. "
            + (
                "Whale investors DO cluster around regions with past failures — they're buying distressed assets."
                if r > 0.3
                else "Whale investor activity and failure density are NOT strongly linked at the regional level."
                if abs(r) < 0.3
                else "Negative correlation — whales are avoiding high-failure regions, seeking greenfield opportunities."
            )
        ),
    }


def correlation_4_funding_vs_year(conn) -> dict:
    """Average funding raised vs year of shutdown."""
    cursor = conn.cursor()

    cursor.execute("""
        SELECT year_shutdown, AVG(funding_raised_usd) AS avg_funding, COUNT(*) AS cnt
        FROM failed_startups
        WHERE year_shutdown IS NOT NULL AND funding_raised_usd IS NOT NULL
        GROUP BY year_shutdown
        ORDER BY year_shutdown
    """)
    rows = cursor.fetchall()
    by_year = [
        {
            "year": r["year_shutdown"],
            "avg_funding": float(r["avg_funding"]),
            "count": r["cnt"],
        }
        for r in rows
    ]

    years = [r["year"] for r in by_year]
    funds = [r["avg_funding"] for r in by_year]
    r = pearson(years, funds) if len(years) > 1 else 0.0

    cursor.close()
    return {
        "title": "4. Average Funding Raised vs Year of Shutdown",
        "question": "Are recent failures better-funded than older ones (bubble inflating)?",
        "by_year": by_year,
        "pearson_r": r,
        "interpretation": (
            f"Pearson r (year vs avg funding) = {fmt_corr(r)}. "
            + (
                "Strong positive trend — recent failures had MORE capital to burn. The funding bubble is real."
                if r > 0.5
                else "Moderate upward trend — failures are getting more capital-intensive."
                if r > 0.3
                else "Flat — funding amounts haven't changed significantly across failure years."
                if abs(r) < 0.3
                else "Recent failures had LESS funding — capital is drying up for risky ventures."
            )
        ),
    }


def correlation_5_news_vs_failures(conn) -> dict:
    """News article volume vs failure timing."""
    cursor = conn.cursor()

    cursor.execute("""
        SELECT YEAR(STR_TO_DATE(published_at, '%%Y-%%m-%%d')) AS y, COUNT(*) AS cnt
        FROM news_articles
        WHERE published_at IS NOT NULL
          AND published_at != ''
          AND STR_TO_DATE(published_at, '%%Y-%%m-%%d') IS NOT NULL
        GROUP BY y
        ORDER BY y
    """)
    news_by_year = [
        {"year": r["y"], "count": r["cnt"]} for r in cursor.fetchall() if r["y"]
    ]

    cursor.execute("""
        SELECT year_shutdown, COUNT(*) AS cnt
        FROM failed_startups
        WHERE year_shutdown IS NOT NULL
        GROUP BY year_shutdown
        ORDER BY year_shutdown
    """)
    fail_by_year = {r["year_shutdown"]: r["cnt"] for r in cursor.fetchall()}

    # Compare overlapping years
    news_years = {n["year"] for n in news_by_year}
    fail_years = set(fail_by_year.keys())
    overlap = sorted(news_years & fail_years)

    if overlap:
        news_vals = [
            next(n["count"] for n in news_by_year if n["year"] == y) for y in overlap
        ]
        fail_vals = [fail_by_year[y] for y in overlap]
        r = pearson(news_vals, fail_vals)
    else:
        r = 0.0

    cursor.close()
    return {
        "title": "5. News Volume vs Failure Timing",
        "question": "Does news coverage volume correlate with shutdown counts by year?",
        "news_by_year": news_by_year,
        "fail_by_year": fail_by_year,
        "overlap_years": overlap,
        "pearson_r": r,
        "interpretation": (
            f"Pearson r (news volume vs failure count by year) = {fmt_corr(r)}. "
            + (
                "News coverage tracks failure volume closely — media is a reliable signal."
                if r > 0.4
                else "News volume and failure timing are NOT strongly correlated — coverage is driven by other factors."
                if abs(r) < 0.4
                else "Inverse — more news in years with FEWER recorded failures (media focus shifts away during quiet periods)."
            )
        ),
    }


def correlation_6_reshoring_vs_revival(conn) -> dict:
    """Reshoring jobs by industry vs revival industry scores."""
    cursor = conn.cursor()

    # Filter out the generic "Total"/"Reshoring"/"FDI" rows
    cursor.execute("""
        SELECT industry, jobs_created, jobs_announced, project_count, data_year
        FROM reshoring_data
        WHERE industry IS NOT NULL
          AND industry NOT LIKE '%%Total%%'
          AND industry != 'Reshoring'
          AND industry != 'FDI'
        ORDER BY jobs_created DESC
    """)
    reshoring = [
        {
            "industry": r["industry"],
            "jobs": r["jobs_created"],
            "jobs_announced": r["jobs_announced"],
            "projects": r["project_count"],
            "year": r["data_year"],
        }
        for r in cursor.fetchall()
    ]

    revival_data = load_latest_insights(conn, "analysis_revival_opportunities")
    industry_scores = {}
    # Try several possible keys
    score_list = (
        revival_data.get("industry_revival_scores")
        or revival_data.get("top_industries")
        or revival_data.get("industries")
        or []
    )
    for item in score_list:
        if isinstance(item, dict):
            name = (item.get("industry") or item.get("name") or "").lower()
            score = item.get("revival_score") or item.get("score") or 0
            if name:
                industry_scores[name] = float(score)

    # Match reshoring industries to revival scores via keyword overlap
    matches = []
    for r in reshoring:
        ind_lower = (r["industry"] or "").lower()
        best_match = None
        best_score = 0
        for revival_ind, score in industry_scores.items():
            # Match any keyword overlap (e.g., "battery" matches "Battery Cell Manufacturing")
            ind_words = set(ind_lower.split())
            rev_words = set(revival_ind.split())
            # Also do substring matching
            if (
                ind_words & rev_words
                or revival_ind in ind_lower
                or ind_lower in revival_ind
            ):
                if score > best_score:
                    best_score = score
                    best_match = revival_ind
        matches.append(
            {
                "reshoring_industry": r["industry"],
                "jobs": r["jobs"],
                "jobs_announced": r["jobs_announced"],
                "projects": r["projects"],
                "matched_revival": best_match,
                "revival_score": best_score,
                "year": r["year"],
            }
        )

    # Correlation: jobs vs revival score
    matched = [m for m in matches if m["matched_revival"]]
    if matched:
        jobs = [float(m["jobs"] or 0) for m in matched]
        scores = [m["revival_score"] for m in matched]
        r = pearson(jobs, scores)
    else:
        r = 0.0

    cursor.close()
    return {
        "title": "6. Reshoring Jobs vs Revival Industry Match",
        "question": "Are industries scored as 'reviving' actually creating reshoring jobs?",
        "matches": matches,
        "pearson_r": r,
        "interpretation": (
            f"Pearson r (jobs vs revival score) = {fmt_corr(r)}. "
            + (
                f"Matched {len(matched)}/{len(matches)} reshoring industries to revival scores. "
                + (
                    "Higher-scoring revival industries ARE creating more jobs — scoring reflects reality."
                    if r > 0.3
                    else "Revival scoring doesn't match actual job creation — scores need recalibration."
                    if r < -0.3
                    else "No clear link between score and job count."
                )
            )
        ),
    }


def correlation_7_opportunity_vs_whale(conn) -> dict:
    """Opportunity pipeline scores vs whale investor backing."""
    cursor = conn.cursor()

    opp_data = load_latest_insights(conn, "analysis_opportunity_pipeline")
    whale_data = load_latest_insights(conn, "analysis_whale_investors")

    opportunities = opp_data.get("opportunities", [])
    cross_refs = whale_data.get("cross_referenced_opportunities", [])

    # Build whale backing map
    whale_backed = {cr["opportunity"]: cr for cr in cross_refs}

    # Match each opportunity to whale backing
    enriched = []
    for o in opportunities:
        name = o.get("startup") or o.get("region") or "unknown"
        wb = whale_backed.get(name, {})
        enriched.append(
            {
                "name": name,
                "type": o.get("type"),
                "opp_score": o.get("opportunity_score", 0),
                "risk_level": o.get("risk_level"),
                "whale_backed": wb.get("whale_backed", False),
                "matched_sectors": wb.get("matched_sectors", []),
                "matched_investors": wb.get("matched_investors", []),
            }
        )

    # Compare avg score: whale-backed vs not
    backed_scores = [e["opp_score"] for e in enriched if e["whale_backed"]]
    not_backed_scores = [e["opp_score"] for e in enriched if not e["whale_backed"]]

    avg_backed = mean(backed_scores) if backed_scores else 0
    avg_not_backed = mean(not_backed_scores) if not_backed_scores else 0
    delta = avg_backed - avg_not_backed

    cursor.close()
    return {
        "title": "7. Opportunity Score vs Whale Investor Backing",
        "question": "Do our highest-scored opportunities have whale backing?",
        "total_opportunities": len(opportunities),
        "whale_backed_count": len(backed_scores),
        "avg_score_whale_backed": round(avg_backed, 1),
        "avg_score_not_backed": round(avg_not_backed, 1),
        "delta": round(delta, 1),
        "enriched": enriched,
        "interpretation": (
            f"{len(backed_scores)}/{len(opportunities)} opportunities have whale backing. "
            f"Avg score: {avg_backed:.1f} (backed) vs {avg_not_backed:.1f} (not backed), Δ={delta:+.1f}. "
            + (
                "Whale-backed opportunities have HIGHER scores — our scoring aligns with institutional interest."
                if delta > 5
                else "Scores are similar regardless of backing — whale activity is independent of our scoring."
                if abs(delta) <= 5
                else "Whale-backed opportunities have LOWER scores — whales may be pursuing different opportunities than our model captures."
            )
        ),
    }


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def build_report(results: dict) -> str:
    """Assemble all correlation findings into a markdown report."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Cross-Module Market Correlation Analysis",
        "",
        f"_Generated: {now}_",
        "",
        "This report analyzes data across all 7 analysis modules to find which signals reinforce each other.",
        "",
        "## Executive Summary",
        "",
    ]

    # Rank correlations by absolute value
    ranked = []
    for key, res in results.items():
        r = res.get("pearson_r", 0)
        ranked.append((key, res["title"], r, abs(r)))
    ranked.sort(key=lambda x: x[3], reverse=True)

    lines.append("Correlations ranked by strength:")
    lines.append("")
    lines.append(
        md_table(
            ["Rank", "Correlation", "Pearson r", "Strength"],
            [
                [
                    i + 1,
                    t[1].split(".")[1].strip(),
                    fmt_corr(t[2]),
                    "★★★" if t[3] >= 0.5 else "★★" if t[3] >= 0.3 else "★",
                ]
                for i, t in enumerate(ranked)
            ],
        )
    )
    lines.append("")

    # Top findings
    lines.append("### Top Findings")
    lines.append("")
    for i, (key, title, r, _) in enumerate(ranked[:3], 1):
        lines.append(f"**{i}. {title}**: {results[key]['interpretation']}")
        lines.append("")

    # Detailed sections
    for key in sorted(results.keys()):
        res = results[key]
        lines.append("---")
        lines.append("")
        lines.append(f"## {res['title']}")
        lines.append("")
        lines.append(f"**Question**: {res['question']}")
        lines.append("")
        lines.append(f"**Finding**: {res['interpretation']}")
        lines.append("")

        # Per-correlation tables
        if key == "c1":
            rows = [
                [m["industry"], m["revival_score"], m["failure_count"]]
                for m in res["matches"]
            ]
            lines.append(md_table(["Industry", "Revival Score", "Failure Count"], rows))
        elif key == "c2":
            rows = [[c["category"], c["count"]] for c in res["category_counts"]]
            lines.append("Failure category distribution:")
            lines.append("")
            lines.append(md_table(["Failure Category", "Count"], rows))
            lines.append("")
            rows = [
                [s["year"], f"{s['avg_5yr']:.1f}%"] for s in res["survival_by_year"]
            ]
            lines.append("Average 5-year survival rate by year:")
            lines.append("")
            lines.append(md_table(["Year", "Avg 5yr Survival"], rows))
        elif key == "c3":
            rows = [
                [
                    g["region"],
                    g["failure_count"],
                    res["whale_region_mentions"].get(g["region"], 0),
                ]
                for g in res["geo_failures"]
            ]
            lines.append(md_table(["Region", "Failure Count", "Whale Mentions"], rows))
        elif key == "c4":
            rows = [
                [r["year"], f"${r['avg_funding']/1e6:.1f}M", r["count"]]
                for r in res["by_year"]
            ]
            lines.append(md_table(["Year Shutdown", "Avg Funding", "# Failures"], rows))
        elif key == "c5":
            fail_by_year = res["fail_by_year"]
            rows = [[y, fail_by_year.get(y, 0)] for y in sorted(fail_by_year.keys())]
            lines.append("Failures by year:")
            lines.append("")
            lines.append(md_table(["Year", "Failure Count"], rows))
            lines.append("")
            rows = [[n["year"], n["count"]] for n in res["news_by_year"]]
            lines.append("News articles by year:")
            lines.append("")
            lines.append(md_table(["Year", "Article Count"], rows))
        elif key == "c6":
            rows = [
                [
                    m["reshoring_industry"],
                    m["jobs"],
                    m["matched_revival"] or "—",
                    m["revival_score"],
                ]
                for m in res["matches"]
            ]
            lines.append(
                md_table(
                    ["Reshoring Industry", "Jobs", "Matched Revival", "Score"], rows
                )
            )
        elif key == "c7":
            rows = [
                [
                    e["name"],
                    e["opp_score"],
                    e["risk_level"],
                    "Yes" if e["whale_backed"] else "No",
                    ", ".join(e["matched_investors"]) or "—",
                ]
                for e in res["enriched"]
            ]
            lines.append(
                md_table(
                    ["Opportunity", "Score", "Risk", "Whale Backed", "Investors"], rows
                )
            )

        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Methodology")
    lines.append("")
    lines.append(
        "- **Pearson correlation** is used for numeric pairs (e.g., funding vs year)."
    )
    lines.append(
        "- r ≥ 0.7 = strong; r ≥ 0.4 = moderate; r ≥ 0.2 = weak; |r| < 0.2 = negligible."
    )
    lines.append(
        "- All data sourced from the live MySQL database populated by the 7 analysis agents."
    )
    lines.append(
        "- Sample sizes are small (163 startups, 31 BLS records, 6 revival industries) so treat correlations as exploratory."
    )
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Run cross-module correlation analysis"
    )
    parser.add_argument(
        "--output",
        default="Market_Correlation_Analysis.md",
        help="Output markdown report path",
    )
    args = parser.parse_args()

    conn = get_connection()
    _logger.info("Connected to MySQL. Running 7 correlation analyses...")

    results = {
        "c1": correlation_1_sector_failure_vs_revival(conn),
        "c2": correlation_2_failure_reason_vs_survival(conn),
        "c3": correlation_3_geo_failures_vs_whale(conn),
        "c4": correlation_4_funding_vs_year(conn),
        "c5": correlation_5_news_vs_failures(conn),
        "c6": correlation_6_reshoring_vs_revival(conn),
        "c7": correlation_7_opportunity_vs_whale(conn),
    }

    conn.close()

    report = build_report(results)
    out_path = Path(__file__).parent.parent / args.output
    out_path.write_text(report, encoding="utf-8")
    _logger.info("Report written to %s (%d bytes)", out_path, len(report))

    # Print summary to console
    print("\n" + "=" * 70)
    print("CORRELATION ANALYSIS SUMMARY")
    print("=" * 70)
    for key, res in results.items():
        print(f"\n{res['title']}")
        print(f"  {res['interpretation']}")
    print("\n" + "=" * 70)
    print(f"Full report: {out_path}")


if __name__ == "__main__":
    main()
