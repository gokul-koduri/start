#!/usr/bin/env python3
"""Global Market Viability Analysis.

Uses a local Ollama LLM to evaluate whether products from failed startups
could work in different global markets based on current market standards.

Usage:
    python3 scripts/global_market_viability.py
    python3 scripts/global_market_viability.py --output Global_Market_Viability.md
    python3 scripts/global_market_viability.py --sectors "EV/Automotive,Robotics" --countries "US,India"
    python3 scripts/global_market_viability.py --no-cache
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.connection import get_connection
from db import schema

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
_logger = logging.getLogger("global_market_viability")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "llama3"
DEFAULT_DELAY_SECONDS = 3.0
TOP_COMBINATIONS_FOR_DEEP_DIVE = 15

CACHE_DIR = Path(__file__).parent.parent / "data" / "cache"
CACHE_FILE = CACHE_DIR / "ollama_market_viability_cache.json"

TARGET_COUNTRIES = {
    "US": "United States",
    "UK": "United Kingdom",
    "Germany": "Germany",
    "India": "India",
    "China": "China",
    "Japan": "Japan",
    "Brazil": "Brazil",
    "Southeast_Asia": "Southeast Asia (Indonesia, Vietnam, Thailand, Philippines)",
    "Middle_East": "Middle East (UAE, Saudi Arabia, Qatar)",
    "Africa": "Africa (Nigeria, Kenya, South Africa, Egypt)",
}

SYSTEM_PROMPT = (
    "You are a senior market research analyst specializing in global manufacturing "
    "and technology markets. You evaluate whether products and business models "
    "from failed startups could succeed in different countries. "
    "Always respond with valid JSON only. No markdown, no code fences, "
    "no explanatory text outside the JSON object."
)


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------


def load_cache(cache_file: Path) -> dict:
    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            _logger.warning("Failed to load cache: %s", e)
    return {}


def save_cache(cache_file: Path, cache: dict) -> None:
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(
        json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Database queries
# ---------------------------------------------------------------------------


def query_unique_sectors(conn) -> list[dict]:
    """Query all unique sectors with counts and sub-sectors."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT sector, COUNT(*) AS count,
               GROUP_CONCAT(DISTINCT manufacturing_sub_sector) AS sub_sectors
        FROM failed_startups
        WHERE sector IS NOT NULL
        GROUP BY sector
        ORDER BY count DESC
    """)
    rows = cursor.fetchall()
    cursor.close()
    return [
        {
            "sector": r["sector"],
            "count": r["count"],
            "sub_sectors": r["sub_sectors"] or "",
        }
        for r in rows
    ]


def query_example_companies(conn, sector: str, limit: int = 3) -> list[dict]:
    """Query top-funded failed startups in a sector."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT name, sector, manufacturing_sub_sector, country,
               funding_raised_usd, year_founded, year_shutdown, failure_reason
        FROM failed_startups
        WHERE sector = %s AND funding_raised_usd IS NOT NULL
        ORDER BY funding_raised_usd DESC
        LIMIT %s
    """,
        (sector, limit),
    )
    rows = cursor.fetchall()
    cursor.close()
    return [
        {
            "name": r["name"],
            "sector": r["sector"],
            "manufacturing_sub_sector": r["manufacturing_sub_sector"] or "",
            "country": r["country"] or "",
            "funding_raised_usd": r["funding_raised_usd"],
            "year_founded": r["year_founded"],
            "year_shutdown": r["year_shutdown"],
            "failure_reason": (r["failure_reason"] or "")[:200],
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Ollama LLM integration
# ---------------------------------------------------------------------------


def call_ollama(
    prompt: str,
    model: str = DEFAULT_MODEL,
    url: str = DEFAULT_OLLAMA_URL,
    timeout: int = 300,
    max_retries: int = 2,
) -> str:
    """Call Ollama chat API and return the response text."""
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "options": {"temperature": 0.3},
    }

    for attempt in range(max_retries + 1):
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "")
        except requests.exceptions.ConnectionError:
            _logger.error(
                "Ollama not reachable at %s (attempt %d/%d)",
                url,
                attempt + 1,
                max_retries + 1,
            )
            if attempt == max_retries:
                raise ConnectionError(
                    f"Ollama not reachable at {url}. "
                    "Install Ollama from https://ollama.com and pull a model: ollama pull llama3"
                )
            time.sleep(5)
        except requests.exceptions.Timeout:
            _logger.error(
                "Ollama request timed out (attempt %d/%d)", attempt + 1, max_retries + 1
            )
            if attempt == max_retries:
                raise
            time.sleep(5)
        except requests.exceptions.HTTPError as e:
            _logger.error(
                "Ollama HTTP error: %s (attempt %d/%d)", e, attempt + 1, max_retries + 1
            )
            if attempt == max_retries:
                raise
            time.sleep(5)

    return ""  # unreachable but satisfies type checkers


def parse_llm_response(raw: str) -> dict | None:
    """Parse LLM JSON response into a structured dict."""
    try:
        # Strip markdown code fences if present
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
        data = json.loads(text)
    except (json.JSONDecodeError, AttributeError):
        _logger.warning("Failed to parse LLM JSON response: %s...", raw[:100])
        return None

    # Validate and clamp scores
    for key in ("market_demand_score", "overall_viability_score"):
        if key in data:
            try:
                data[key] = max(1, min(10, int(data[key])))
            except (TypeError, ValueError):
                data[key] = 0

    # Clean up values that look like Python lists (['a','b'] -> a, b)
    for key in ("key_competitors", "local_competitors", "risk_factors"):
        if key in data and isinstance(data[key], str):
            val = data[key].strip()
            if val.startswith("[") and val.endswith("]"):
                try:
                    parsed_list = json.loads(val)
                    if isinstance(parsed_list, list):
                        data[key] = ", ".join(str(x) for x in parsed_list)
                except (json.JSONDecodeError, TypeError):
                    pass

    return data


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------


def build_sector_prompt(
    sector: str,
    sub_sectors: list[str],
    example_companies: list[dict],
    country_code: str,
    country_name: str,
) -> str:
    """Build the LLM prompt for a sector x country evaluation."""
    companies_text = ""
    for c in example_companies[:2]:  # Max 2 companies to keep prompt short
        funding_str = (
            f"${c['funding_raised_usd'] / 1e6:.0f}M" if c["funding_raised_usd"] else "?"
        )
        companies_text += (
            f"- {c['name']} (${funding_str}, failed {c['year_shutdown']})\n"
        )

    return f"""Rate market viability for "{sector}" in {country_name}.
Failed examples: {companies_text.strip()}
Sub-sectors: {', '.join(sub_sectors[:3]) if sub_sectors else 'N/A'}

Reply with JSON only:
{{"market_demand_score":<1-10>,"competition_level":"<low|medium|high>","regulatory_barriers":"<low|medium|high>","cultural_fit":"<low|medium|high>","overall_viability_score":<1-10>,"reasoning":"<1 sentence>","key_competitors":"<names>","estimated_market_size":"<size>"}}"""


def build_company_drilldown_prompt(
    company: dict,
    sector: str,
    country_code: str,
    country_name: str,
    sector_context: str,
) -> str:
    """Build prompt for specific company evaluation in a market."""
    funding_str = (
        f"${company['funding_raised_usd'] / 1e6:.0f}M"
        if company["funding_raised_usd"]
        else "?"
    )

    return f"""Could "{company['name']}" ({company['sector']}, ${funding_str}, failed {company['year_shutdown']}: {company['failure_reason'][:80]}) work in {country_name}?
Context: {sector_context[:100]}

Reply with JSON only:
{{"adaptation_needed":"<changes needed>","local_competitors":"<names>","estimated_timeline":"<time>","funding_needs":"<amount>","specific_opportunity":"<1 sentence>","risk_factors":"<risks>","go_no_go":"<go|cautious|no-go>"}}"""


# ---------------------------------------------------------------------------
# Evaluation functions
# ---------------------------------------------------------------------------


def evaluate_sector_country(
    sector: str,
    sub_sectors: list[str],
    companies: list[dict],
    country_code: str,
    country_name: str,
    model: str,
    url: str,
    delay: float,
    cache: dict,
) -> dict:
    """Evaluate one sector-country combination using the LLM."""
    cache_key = f"{sector}|{country_code}"

    if cache_key in cache:
        cached = cache[cache_key].copy()
        cached["cached"] = True
        return cached

    prompt = build_sector_prompt(
        sector, sub_sectors, companies, country_code, country_name
    )

    try:
        raw = call_ollama(prompt, model=model, url=url)
        parsed = parse_llm_response(raw)

        if parsed is None:
            _logger.warning(
                "Failed to parse LLM response for %s in %s", sector, country_code
            )
            result = _make_default_result(sector, country_code, country_name)
        else:
            result = {
                "sector": sector,
                "country_code": country_code,
                "country_name": country_name,
                "market_demand_score": parsed.get("market_demand_score", 0),
                "competition_level": parsed.get("competition_level", "unknown"),
                "regulatory_barriers": parsed.get("regulatory_barriers", "unknown"),
                "cultural_fit": parsed.get("cultural_fit", "unknown"),
                "overall_viability_score": parsed.get("overall_viability_score", 0),
                "reasoning": parsed.get("reasoning", ""),
                "key_competitors": parsed.get("key_competitors", ""),
                "entry_strategy": parsed.get("entry_strategy", ""),
                "estimated_market_size": parsed.get("estimated_market_size", ""),
                "example_companies": [c["name"] for c in companies],
                "evaluated_at": datetime.now(timezone.utc).isoformat(),
                "cached": False,
            }
    except Exception as e:
        _logger.error("LLM call failed for %s in %s: %s", sector, country_code, e)
        result = _make_default_result(sector, country_code, country_name)
        result["reasoning"] = f"LLM call failed: {e}"

    cache[cache_key] = {k: v for k, v in result.items() if k != "cached"}
    time.sleep(delay)
    return result


def deep_dive_company(
    company: dict,
    sector: str,
    country_code: str,
    country_name: str,
    sector_context: str,
    model: str,
    url: str,
    delay: float,
    cache: dict,
) -> dict:
    """Evaluate a specific company in a specific market."""
    cache_key = f"{company['name']}|{country_code}"

    if cache_key in cache:
        cached = cache[cache_key].copy()
        cached["cached"] = True
        return cached

    prompt = build_company_drilldown_prompt(
        company, sector, country_code, country_name, sector_context
    )
    try:
        raw = call_ollama(prompt, model=model, url=url)
        parsed = parse_llm_response(raw)

        if parsed is None:
            _logger.warning(
                "Failed to parse deep-dive response for %s in %s",
                company["name"],
                country_code,
            )
            result = _make_default_deep_dive(
                company["name"], country_code, country_name
            )
        else:
            result = {
                "company_name": company["name"],
                "sector": sector,
                "country_code": country_code,
                "country_name": country_name,
                "adaptation_needed": parsed.get("adaptation_needed", ""),
                "local_competitors": parsed.get("local_competitors", ""),
                "estimated_timeline": parsed.get("estimated_timeline", ""),
                "funding_needs": parsed.get("funding_needs", ""),
                "specific_opportunity": parsed.get("specific_opportunity", ""),
                "risk_factors": parsed.get("risk_factors", ""),
                "go_no_go": parsed.get("go_no_go", "unknown"),
                "evaluated_at": datetime.now(timezone.utc).isoformat(),
                "cached": False,
            }
    except Exception as e:
        _logger.error(
            "Deep-dive failed for %s in %s: %s", company["name"], country_code, e
        )
        result = _make_default_deep_dive(company["name"], country_code, country_name)
        result["specific_opportunity"] = f"Analysis failed: {e}"

    cache[cache_key] = {k: v for k, v in result.items() if k != "cached"}
    time.sleep(delay)
    return result


def _make_default_result(sector: str, country_code: str, country_name: str) -> dict:
    return {
        "sector": sector,
        "country_code": country_code,
        "country_name": country_name,
        "market_demand_score": 0,
        "competition_level": "unknown",
        "regulatory_barriers": "unknown",
        "cultural_fit": "unknown",
        "overall_viability_score": 0,
        "reasoning": "LLM evaluation failed",
        "key_competitors": "",
        "entry_strategy": "",
        "estimated_market_size": "",
        "example_companies": [],
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "cached": False,
    }


def _make_default_deep_dive(
    company_name: str, country_code: str, country_name: str
) -> dict:
    return {
        "company_name": company_name,
        "sector": "",
        "country_code": country_code,
        "country_name": country_name,
        "adaptation_needed": "",
        "local_competitors": "",
        "estimated_timeline": "",
        "funding_needs": "",
        "specific_opportunity": "",
        "risk_factors": "",
        "go_no_go": "unknown",
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "cached": False,
    }


# ---------------------------------------------------------------------------
# DB storage
# ---------------------------------------------------------------------------


def store_results_in_db(
    conn,
    all_results: list[dict],
    deep_dive_results: list[dict],
    model: str,
    errors: list[str],
) -> None:
    """Store results in the analysis_global_market_viability table."""
    now = datetime.now(timezone.utc).isoformat()
    store_data = {
        "analysis_type": "global_market_viability_full",
        "model": model,
        "total_evaluations": len(all_results),
        "total_deep_dives": len(deep_dive_results),
        "avg_viability_score": round(
            mean(
                [
                    r["overall_viability_score"]
                    for r in all_results
                    if r["overall_viability_score"] > 0
                ]
            ),
            1,
        )
        if [r for r in all_results if r["overall_viability_score"] > 0]
        else 0,
        "top_combinations": [
            {
                "sector": r["sector"],
                "country": r["country_name"],
                "score": r["overall_viability_score"],
            }
            for r in sorted(
                all_results, key=lambda x: x["overall_viability_score"], reverse=True
            )[:10]
        ],
        "sector_results": all_results,
        "deep_dive_results": deep_dive_results,
        "errors": errors,
    }

    cursor = conn.cursor()
    cursor.execute("DELETE FROM analysis_global_market_viability")
    cursor.execute(
        """INSERT INTO analysis_global_market_viability
           (analysis_type, insights_json, analyzed_at, record_count)
           VALUES (%s, %s, %s, %s)""",
        (
            "global_market_viability_full",
            json.dumps(store_data, default=str, ensure_ascii=False),
            now,
            len(all_results) + len(deep_dive_results),
        ),
    )
    conn.commit()
    cursor.close()


# ---------------------------------------------------------------------------
# Summary computation
# ---------------------------------------------------------------------------


def compute_summary(all_results: list[dict], deep_dive_results: list[dict]) -> dict:
    valid = [r for r in all_results if r["overall_viability_score"] > 0]
    sectors = list(set(r["sector"] for r in all_results))
    countries = list(set(r["country_code"] for r in all_results))

    top = sorted(all_results, key=lambda x: x["overall_viability_score"], reverse=True)

    # Country-level averages
    country_avgs = {}
    for r in valid:
        cc = r["country_code"]
        cn = r["country_name"]
        if cc not in country_avgs:
            country_avgs[cc] = {"name": cn, "scores": [], "high_viability": 0}
        country_avgs[cc]["scores"].append(r["overall_viability_score"])
        if r["overall_viability_score"] >= 7:
            country_avgs[cc]["high_viability"] += 1

    top_combo = top[0] if top else {}

    return {
        "sectors_analyzed": len(sectors),
        "countries_analyzed": len(countries),
        "total_evaluations": len(all_results),
        "total_deep_dives": len(deep_dive_results),
        "avg_viability_score": round(
            mean(r["overall_viability_score"] for r in valid), 1
        )
        if valid
        else 0,
        "top_combination": {
            "label": f"{top_combo.get('sector', 'N/A')} in {top_combo.get('country_name', 'N/A')}",
            "score": top_combo.get("overall_viability_score", 0),
        }
        if top_combo
        else {},
        "top_10": top[:10],
        "country_avgs": {
            cc: {
                "name": v["name"],
                "avg_score": round(mean(v["scores"]), 1),
                "high_viability_count": v["high_viability"],
                "best_sector": max(
                    (r for r in valid if r["country_code"] == cc),
                    key=lambda r: r["overall_viability_score"],
                    default={},
                ).get("sector", "N/A"),
            }
            for cc, v in country_avgs.items()
        },
    }


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def md_table(headers: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(headers) + " |"]
    out.append("| " + " | ".join("---" for _ in headers) + " |")
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def build_report(
    all_results: list[dict], deep_dive_results: list[dict], summary: dict
) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Global Market Viability Analysis",
        "",
        f"_Generated: {now}_",
        "",
        "This report evaluates whether products from failed startups could succeed "
        "in 10 major global markets, using local LLM analysis (Ollama).",
        "",
        "## Executive Summary",
        "",
        f"- **Sectors Analyzed**: {summary['sectors_analyzed']}",
        f"- **Markets Evaluated**: {summary['countries_analyzed']}",
        f"- **Total LLM Evaluations**: {summary['total_evaluations']} sector-level + "
        f"{summary['total_deep_dives']} company deep-dives",
        f"- **Average Viability Score**: {summary['avg_viability_score']}/10",
    ]

    top = summary.get("top_combination", {})
    if top:
        lines.append(f"- **Top Opportunity**: {top['label']} ({top['score']}/10)")

    lines.append("")

    # Top 10 opportunities table
    lines.append("### Top 10 Sector-Market Opportunities")
    lines.append("")
    top10 = summary.get("top_10", [])
    if top10:
        lines.append(
            md_table(
                [
                    "Rank",
                    "Sector",
                    "Market",
                    "Viability",
                    "Demand",
                    "Competition",
                    "Barriers",
                    "Cultural Fit",
                ],
                [
                    [
                        i + 1,
                        r["sector"],
                        r["country_name"],
                        f"{r['overall_viability_score']}/10",
                        f"{r['market_demand_score']}/10",
                        r["competition_level"].title(),
                        r["regulatory_barriers"].title(),
                        r["cultural_fit"].title(),
                    ]
                    for i, r in enumerate(top10)
                ],
            )
        )
    lines.append("")

    # Markets ranked by average opportunity
    lines.append("### Markets Ranked by Average Opportunity")
    lines.append("")
    country_avgs = summary.get("country_avgs", {})
    if country_avgs:
        sorted_countries = sorted(
            country_avgs.values(), key=lambda x: x["avg_score"], reverse=True
        )
        lines.append(
            md_table(
                ["Market", "Avg Viability", "High-Viability Sectors", "Best Sector"],
                [
                    [
                        c["name"],
                        f"{c['avg_score']}/10",
                        c["high_viability_count"],
                        c["best_sector"],
                    ]
                    for c in sorted_countries
                ],
            )
        )
    lines.append("")

    # Deep-dive results (top opportunities with company analysis)
    if deep_dive_results:
        lines.append("---")
        lines.append("")
        lines.append("## Company Deep-Dive Analysis")
        lines.append("")
        lines.append(
            "Detailed analysis of specific failed-startup products in their "
            "most promising alternative markets."
        )
        lines.append("")

        # Group deep-dives by sector and country
        grouped: dict[str, list[dict]] = {}
        for d in deep_dive_results:
            key = f"{d['sector']} in {d['country_name']}"
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(d)

        for group_key, dives in grouped.items():
            lines.append(f"### {group_key}")
            lines.append("")
            for d in dives:
                gng = d["go_no_go"].upper()
                lines.append(f"**{d['company_name']}** -- {gng}")
                if d["adaptation_needed"]:
                    lines.append(f"- **Adaptation Needed**: {d['adaptation_needed']}")
                if d["local_competitors"]:
                    lines.append(f"- **Local Competitors**: {d['local_competitors']}")
                if d["estimated_timeline"]:
                    lines.append(f"- **Timeline**: {d['estimated_timeline']}")
                if d["funding_needs"]:
                    lines.append(f"- **Funding Needs**: {d['funding_needs']}")
                if d["specific_opportunity"]:
                    lines.append(f"- **Opportunity**: {d['specific_opportunity']}")
                if d["risk_factors"]:
                    lines.append(f"- **Risk Factors**: {d['risk_factors']}")
                lines.append("")

    # Sector-by-sector summary
    lines.append("---")
    lines.append("")
    lines.append("## Sector-by-Sector Summary")
    lines.append("")

    sectors_seen = list(dict.fromkeys(r["sector"] for r in all_results))
    for sector in sectors_seen:
        sector_results = [r for r in all_results if r["sector"] == sector]
        best = max(sector_results, key=lambda r: r["overall_viability_score"])
        valid_scores = [
            r["overall_viability_score"]
            for r in sector_results
            if r["overall_viability_score"] > 0
        ]
        avg = round(mean(valid_scores), 1) if valid_scores else 0

        lines.append(f"### {sector}")
        lines.append("")
        lines.append(f"- **Avg Viability**: {avg}/10")
        lines.append(
            f"- **Best Market**: {best['country_name']} ({best['overall_viability_score']}/10)"
        )
        lines.append("")

        lines.append(
            md_table(
                [
                    "Market",
                    "Demand",
                    "Competition",
                    "Barriers",
                    "Cultural",
                    "Viability",
                ],
                [
                    [
                        r["country_name"],
                        f"{r['market_demand_score']}/10",
                        r["competition_level"].title(),
                        r["regulatory_barriers"].title(),
                        r["cultural_fit"].title(),
                        f"{r['overall_viability_score']}/10",
                    ]
                    for r in sorted(
                        sector_results,
                        key=lambda x: x["overall_viability_score"],
                        reverse=True,
                    )
                ],
            )
        )
        lines.append("")

    # Methodology
    lines.append("---")
    lines.append("")
    lines.append("## Methodology")
    lines.append("")
    lines.append("- **LLM Model**: Local Ollama inference (no API costs)")
    lines.append("- **Scoring Scale**: 1-10 (1 = very poor fit, 10 = excellent fit)")
    lines.append("- **Competition/Barriers/Cultural Fit**: low/medium/high")
    lines.append(
        "- **Data Source**: Failed startups from the `failed_startups` database"
    )
    lines.append("- **Cache**: Results cached locally; use `--no-cache` to re-evaluate")
    lines.append(
        "- **Limitations**: LLM-based analysis reflects model training data; "
        "market conditions may have changed; regulatory details should be "
        "verified with local counsel"
    )
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Core analysis (called by both CLI and agent)
# ---------------------------------------------------------------------------


def run_analysis(
    conn,
    model: str = DEFAULT_MODEL,
    url: str = DEFAULT_OLLAMA_URL,
    delay: float = DEFAULT_DELAY_SECONDS,
    top_combinations: int = TOP_COMBINATIONS_FOR_DEEP_DIVE,
    sectors_filter: list[str] | None = None,
    countries_filter: list[str] | None = None,
    use_cache: bool = True,
) -> tuple[list[dict], list[dict], dict]:
    """Core analysis logic. Returns (sector_results, deep_dive_results, summary)."""
    schema.init_schema(conn)

    cache = load_cache(CACHE_FILE) if use_cache else {}
    _logger.info("Cache loaded: %d entries", len(cache))

    # Query sectors
    sectors = query_unique_sectors(conn)
    if sectors_filter:
        sectors = [s for s in sectors if s["sector"] in sectors_filter]

    _logger.info(
        "Analyzing %d sectors across %d markets", len(sectors), len(TARGET_COUNTRIES)
    )

    # Phase 1: Sector-level evaluations
    all_results = []
    errors = []

    for sector_info in sectors:
        sector = sector_info["sector"]
        sub_sectors = [
            s.strip() for s in sector_info["sub_sectors"].split(",") if s.strip()
        ]
        companies = query_example_companies(conn, sector)

        for cc, cname in TARGET_COUNTRIES.items():
            if countries_filter and cc not in countries_filter:
                continue
            try:
                result = evaluate_sector_country(
                    sector,
                    sub_sectors,
                    companies,
                    cc,
                    cname,
                    model,
                    url,
                    delay,
                    cache,
                )
                all_results.append(result)
                _logger.info(
                    "  %s in %s: viability=%d/10%s",
                    sector[:25],
                    cname,
                    result["overall_viability_score"],
                    " (cached)" if result["cached"] else "",
                )
            except Exception as e:
                _logger.error("Failed: %s/%s: %s", sector, cc, e)
                errors.append(f"{sector}/{cc}: {e}")

    # Save cache after sector evaluations
    save_cache(CACHE_FILE, cache)
    _logger.info(
        "Sector evaluations complete: %d results, %d errors",
        len(all_results),
        len(errors),
    )

    # Phase 2: Deep-dive into top combinations
    scored = sorted(
        all_results, key=lambda x: x["overall_viability_score"], reverse=True
    )
    top_combos = scored[:top_combinations]

    deep_dive_results = []
    for combo in top_combos:
        companies = query_example_companies(conn, combo["sector"])
        for company in companies:
            try:
                dive = deep_dive_company(
                    company,
                    combo["sector"],
                    combo["country_code"],
                    combo["country_name"],
                    combo["reasoning"],
                    model,
                    url,
                    delay,
                    cache,
                )
                deep_dive_results.append(dive)
                _logger.info(
                    "  Deep-dive: %s in %s: %s",
                    company["name"],
                    combo["country_name"],
                    dive["go_no_go"],
                )
            except Exception as e:
                _logger.error(
                    "Deep-dive failed: %s/%s: %s",
                    company["name"],
                    combo["country_code"],
                    e,
                )
                errors.append(
                    f"deep-dive/{company['name']}/{combo['country_code']}: {e}"
                )

    # Save cache after deep-dives
    save_cache(CACHE_FILE, cache)

    # Store in DB
    store_results_in_db(conn, all_results, deep_dive_results, model, errors)
    _logger.info("Results stored in database")

    # Compute summary
    summary = compute_summary(all_results, deep_dive_results)

    return all_results, deep_dive_results, summary


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Global Market Viability Analysis using local Ollama LLM"
    )
    parser.add_argument(
        "--output",
        default="Global_Market_Viability.md",
        help="Output markdown report path",
    )
    parser.add_argument(
        "--model", default=DEFAULT_MODEL, help="Ollama model name (default: llama3)"
    )
    parser.add_argument(
        "--ollama-url", default=DEFAULT_OLLAMA_URL, help="Ollama API endpoint"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY_SECONDS,
        help="Delay between LLM calls in seconds (default: 3.0)",
    )
    parser.add_argument(
        "--sectors",
        default=None,
        help="Comma-separated sectors to analyze (default: all)",
    )
    parser.add_argument(
        "--countries", default=None, help="Comma-separated country codes (default: all)"
    )
    parser.add_argument(
        "--no-cache", action="store_true", help="Ignore and invalidate cache"
    )
    args = parser.parse_args()

    conn = get_connection()
    _logger.info("Connected to MySQL. Starting Global Market Viability Analysis...")

    all_results, deep_dive_results, summary = run_analysis(
        conn=conn,
        model=args.model,
        url=args.ollama_url,
        delay=args.delay,
        sectors_filter=args.sectors.split(",") if args.sectors else None,
        countries_filter=args.countries.split(",") if args.countries else None,
        use_cache=not args.no_cache,
    )
    conn.close()

    # Build and write report
    report = build_report(all_results, deep_dive_results, summary)
    out_path = Path(__file__).parent.parent / args.output
    out_path.write_text(report, encoding="utf-8")
    _logger.info("Report written to %s (%d bytes)", out_path, len(report))

    # Print summary
    print("\n" + "=" * 70)
    print("GLOBAL MARKET VIABILITY ANALYSIS SUMMARY")
    print("=" * 70)
    print(f"Sectors analyzed: {summary['sectors_analyzed']}")
    print(f"Markets evaluated: {summary['countries_analyzed']}")
    print(f"Total evaluations: {summary['total_evaluations']}")
    print(f"Company deep-dives: {summary['total_deep_dives']}")
    print(f"Average viability: {summary['avg_viability_score']}/10")
    top = summary.get("top_combination", {})
    if top:
        print(f"Top opportunity: {top['label']} ({top['score']}/10)")
    print(f"\nFull report: {out_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
