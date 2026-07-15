#!/usr/bin/env python3
"""LLM-powered insights agent for the report generation system.

Uses the existing OllamaClient with file-based caching to generate
AI-powered insights for the Failed_Startups_Manufacturing_Revival_Report.

Architecture:
- Uses existing utils/ollama_client.OllamaClient for LLM communication
- File cache at data/cache/llm_insights/ with TTL
- Results stored in MySQL report_insights table for report rendering
- Graceful degradation when Ollama is unavailable

Usage:
    from report.llm_insights_agent import run_insights_analysis
    insights = run_insights_analysis(conn, config)
"""

import hashlib
import json
import logging
import time
import requests
from datetime import datetime, timedelta, timezone
from pathlib import Path

# -----------------------------------------------------------------------
# Module-level in-memory cache (survives across calls in same process)
# -----------------------------------------------------------------------

_insights_memory_cache: dict[str, dict] = {}


# -----------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------

DEFAULT_OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "llama3.2:latest"
CACHE_DIR = Path(__file__).parent.parent / "data" / "cache" / "llm_insights"
CACHE_TTL_HOURS = 24

_logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------
# Cache helpers
# -----------------------------------------------------------------------


def _hash_prompt(prompt: str) -> str:
    """Create a stable hash of a prompt for cache key."""
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]


def _get_cache_path(insight_type: str) -> Path:
    """Get cache directory for an insight type."""
    cache_dir = CACHE_DIR / insight_type
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _load_from_file_cache(insight_type: str, prompt_hash: str) -> str | None:
    """Load cached content from file cache if valid."""
    cache_path = _get_cache_path(insight_type)
    cache_file = cache_path / f"{prompt_hash}.json"

    if not cache_file.exists():
        return None

    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Check TTL
        valid_until = data.get("valid_until")
        if valid_until:
            valid_dt = datetime.fromisoformat(valid_until)
            if datetime.now(timezone.utc) > valid_dt:
                _logger.debug("Cache expired for %s/%s", insight_type, prompt_hash)
                return None

        return data.get("content")

    except (json.JSONDecodeError, OSError) as e:
        _logger.warning("Failed to load cache %s/%s: %s", insight_type, prompt_hash, e)
        return None


def _save_to_file_cache(
    insight_type: str,
    prompt_hash: str,
    content: str,
    metadata: dict | None = None,
) -> None:
    """Save content to file cache with TTL."""
    cache_path = _get_cache_path(insight_type)
    cache_file = cache_path / f"{prompt_hash}.json"

    valid_until = datetime.now(timezone.utc) + timedelta(hours=CACHE_TTL_HOURS)

    data = {
        "content": content,
        "valid_until": valid_until.isoformat(),
        "cached_at": datetime.now(timezone.utc).isoformat(),
        "insight_type": insight_type,
        "metadata": metadata or {},
    }

    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except OSError as e:
        _logger.warning("Failed to save cache %s/%s: %s", insight_type, prompt_hash, e)


# -----------------------------------------------------------------------
# Imports (lazy to avoid circular deps)
# -----------------------------------------------------------------------


def _get_ollama_config(config: dict) -> tuple[str, str]:
    """Get Ollama URL and model from config."""
    url = config.get("ollama", {}).get("url", DEFAULT_OLLAMA_URL)
    model = config.get("ollama", {}).get("model", DEFAULT_MODEL)
    return url, model


# -----------------------------------------------------------------------
# Core LLM call with caching
# -----------------------------------------------------------------------


def _call_llm_with_cache(
    system_prompt: str,
    user_prompt: str,
    insight_type: str,
    config: dict,
    force_refresh: bool = False,
) -> str | None:
    """Call Ollama with system+user prompt, using file cache.

    Returns the LLM response content, or None if unavailable.
    """
    url, model = _get_ollama_config(config)
    prompt_hash = _hash_prompt(user_prompt)

    # Check in-memory cache first
    memory_key = f"{insight_type}:{prompt_hash}"
    if not force_refresh and memory_key in _insights_memory_cache:
        return _insights_memory_cache[memory_key]["content"]

    # Check file cache
    if not force_refresh:
        cached = _load_from_file_cache(insight_type, prompt_hash)
        if cached:
            _logger.debug("Cache hit for %s", insight_type)
            _insights_memory_cache[memory_key] = {"content": cached}
            return cached

    # Call LLM using requests directly
    _logger.info("Generating LLM insight: %s", insight_type)
    start_time = time.time()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.3},
    }

    try:
        resp = requests.post(url, json=payload, timeout=300)
        resp.raise_for_status()
        data = resp.json()
        content = data.get("message", {}).get("content", "")
        elapsed_ms = int((time.time() - start_time) * 1000)
    except Exception as e:
        _logger.error("LLM call failed for %s: %s", insight_type, e)
        return None

    if content:
        _logger.info("LLM insight generated: %s (took %dms)", insight_type, elapsed_ms)
        _insights_memory_cache[memory_key] = {"content": content}
        _save_to_file_cache(
            insight_type, prompt_hash, content, metadata={"elapsed_ms": elapsed_ms}
        )
        return content
    else:
        _logger.warning("LLM returned empty for %s", insight_type)
        return None


# -----------------------------------------------------------------------
# JSON response parsing
# -----------------------------------------------------------------------


def _parse_llm_json(raw: str) -> dict | None:
    """Parse LLM JSON response into a dict, tolerating markdown fences."""
    if not raw:
        return None
    try:
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
        if text.startswith("json"):
            text = text[4:].strip()
        return json.loads(text)
    except json.JSONDecodeError as e:
        _logger.warning("Failed to parse LLM JSON: %s... (raw: %s)", str(e), raw[:100])
        return None


# -----------------------------------------------------------------------
# Database helpers for storing insights
# -----------------------------------------------------------------------


def _store_insight(
    conn,
    insight_type: str,
    section: str,
    content: str,
    raw_json: dict | None = None,
    model_used: str = DEFAULT_MODEL,
    elapsed_ms: int = 0,
) -> None:
    """Store an LLM-generated insight in the database."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO report_insights
                (insight_type, section, content, raw_response, model_used,
                 generation_ms, cached, generated_at, valid_until)
            VALUES (%s, %s, %s, %s, %s, %s, 0, %s, %s)
            ON DUPLICATE KEY UPDATE
                content = VALUES(content),
                raw_response = VALUES(raw_response),
                model_used = VALUES(model_used),
                generation_ms = VALUES(generation_ms),
                generated_at = VALUES(generated_at)
            """,
            (
                insight_type,
                section,
                content,
                json.dumps(raw_json) if raw_json else None,
                model_used,
                elapsed_ms,
                datetime.now(timezone.utc).isoformat(),
                (
                    datetime.now(timezone.utc) + timedelta(hours=CACHE_TTL_HOURS)
                ).isoformat(),
            ),
        )
        conn.commit()
    except Exception as e:
        _logger.error("Failed to store insight %s: %s", insight_type, e)
    finally:
        cursor.close()


def _get_cached_insight(conn, insight_type: str) -> str | None:
    """Get a cached insight from the database."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT content FROM report_insights
            WHERE insight_type = %s
              AND (valid_until IS NULL OR valid_until > NOW())
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (insight_type,),
        )
        row = cursor.fetchone()
        return row["content"] if row else None
    except Exception as e:
        _logger.warning("Failed to get cached insight %s: %s", insight_type, e)
        return None
    finally:
        cursor.close()


# -----------------------------------------------------------------------
# Data gathering helpers
# -----------------------------------------------------------------------


def _gather_executive_summary_data(conn) -> dict:
    """Gather all data needed for the executive summary prompt."""
    cursor = conn.cursor()

    # Basic stats
    cursor.execute("SELECT COUNT(*) as cnt FROM failed_startups")
    total_startups = cursor.fetchone()["cnt"]

    cursor.execute(
        "SELECT COUNT(*) as cnt FROM failed_startups WHERE manufacturing_sub_sector IS NOT NULL"
    )
    mfg_count = cursor.fetchone()["cnt"]

    mfg_pct = round(mfg_count / total_startups * 100, 1) if total_startups else 0

    cursor.execute("SELECT COUNT(*) as cnt FROM news_articles")
    news_count = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM revival_industries")
    revival_count = cursor.fetchone()["cnt"]

    # Top failure reasons
    cursor.execute("""
        SELECT reason, percentage
        FROM failure_reasons_taxonomy
        ORDER BY rank_order
        LIMIT 5
    """)
    reasons = cursor.fetchall()
    top_reasons = "; ".join(f"{r['reason']} ({r['percentage']}%)" for r in reasons) if reasons else "N/A"

    cursor.close()

    # Revial industries
    cursor = conn.cursor()
    cursor.execute(
        "SELECT industry FROM revival_industries ORDER BY industry LIMIT 5"
    )
    industries = cursor.fetchall()
    revival_industries = (
        ", ".join(i["industry"] for i in industries) if industries else "N/A"
    )
    cursor.close()

    # Top opportunities
    cursor = conn.cursor()
    cursor.execute("""
        SELECT GROUP_CONCAT(manufacturing_sub_sector SEPARATOR ', ') AS subs
        FROM failed_startups
        WHERE manufacturing_sub_sector IS NOT NULL
        GROUP BY manufacturing_sub_sector
        ORDER BY COUNT(*) DESC
        LIMIT 5
    """)
    opps = cursor.fetchall()
    top_opportunities = (
        ", ".join(o["subs"] for o in opps[:3]) if opps else "Various manufacturing sectors"
    )
    cursor.close()

    # Top funded failures
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name, funding_description
        FROM failed_startups
        WHERE notable = 1
        ORDER BY funding_raised_usd DESC
        LIMIT 5
    """)
    funded = cursor.fetchall()
    top_funded = (
        "; ".join(
            f"{f['name']} ({f['funding_description']})" for f in funded
        )
        if funded
        else "N/A"
    )
    cursor.close()

    return {
        "total_startups": total_startups,
        "mfg_count": mfg_count,
        "mfg_pct": mfg_pct,
        "failure_rate": 41.2,  # BLS data
        "news_count": news_count,
        "revival_count": revival_count,
        "top_reasons": top_reasons,
        "revival_industries": revival_industries,
        "top_opportunities": top_opportunities,
        "top_funded": top_funded,
    }


def _gather_failure_analysis_data(conn) -> str:
    """Gather failure data formatted for LLM prompt."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name, manufacturing_sub_sector, sector,
               funding_description, year_shutdown, failure_reason
        FROM failed_startups
        WHERE manufacturing_sub_sector IS NOT NULL
        ORDER BY funding_raised_usd DESC
        LIMIT 30
    """)
    startups = cursor.fetchall()
    cursor.close()

    if not startups:
        return "No manufacturing failures found in database."

    lines = []
    for s in startups:
        lines.append(
            f"- {s['name']} ({s['manufacturing_sub_sector']}): "
            f"{s['funding_description']}, failed {s['year_shutdown']}: "
            f"{s['failure_reason']}"
        )

    return "\n".join(lines)


def _gather_revial_analysis_data(conn) -> tuple[str, str]:
    """Gather revival industry data and related failures."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT industry, died_period, why_returning, closed_site_types, market_fit
        FROM revival_industries
    """)
    industries = cursor.fetchall()
    cursor.close()

    industries_text = "\n".join(
        f"- {i['industry']}: died during {i['died_period']}, "
        f"returning because: {i['why_returning']}. "
        f"Available sites: {i['closed_site_types']}. "
        f"Market fit: {i['market_fit']}"
        for i in industries
    )

    # Related failures
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name, manufacturing_sub_sector
        FROM failed_startups
        WHERE manufacturing_sub_sector IS NOT NULL
        ORDER BY funding_raised_usd DESC
        LIMIT 10
    """)
    failures = cursor.fetchall()
    cursor.close()

    failures_text = "\n".join(
        f"- {f['name']} ({f['manufacturing_sub_sector']})" for f in failures
    )

    return industries_text, failures_text


def _gather_cross_reference_data(conn) -> tuple[str, str, str]:
    """Gather data for cross-reference analysis."""
    # Failure patterns
    cursor = conn.cursor()
    cursor.execute("""
        SELECT manufacturing_sub_sector, COUNT(*) as cnt,
               GROUP_CONCAT(DISTINCT failure_reason SEPARATOR '; ') AS failure_reason
        FROM failed_startups
        WHERE manufacturing_sub_sector IS NOT NULL
        GROUP BY manufacturing_sub_sector
        ORDER BY cnt DESC
    """)
    patterns = cursor.fetchall()
    cursor.close()

    pattern_text = "\n".join(
        f"- {p['manufacturing_sub_sector']} ({p['cnt']} failures): {p['failure_reason']}"
        for p in patterns[:10]
    )

    # Opportunities
    cursor = conn.cursor()
    cursor.execute("SELECT industry, why_returning FROM revival_industries")
    opps = cursor.fetchall()
    cursor.close()

    opp_text = "\n".join(
        f"- {o['industry']}: {o['why_returning']}" for o in opps
    )

    # Geographic hotspots
    cursor = conn.cursor()
    cursor.execute("SELECT region, closed_facility_types FROM geographic_hotspots")
    hotspots = cursor.fetchall()
    cursor.close()

    facility_text = "\n".join(
        f"- {h['region']}: {h['closed_facility_types']}" for h in hotspots
    )

    return pattern_text, opp_text, facility_text


def _gather_opportunity_ranking_data(conn) -> tuple[str, str]:
    """Gather data for opportunity ranking."""
    # Hardcoded opportunities from Part 4
    opportunities = [
        "Convert closed textile mills into advanced materials manufacturing — carbon fiber, technical textiles for EVs and aerospace",
        "Repurpose closed auto plants for EV battery recycling — 10M+ EV batteries will need recycling by 2030",
        "Turn closed pharma plants into API manufacturing for generic drugs — U.S. imports 87% of APIs",
        "Convert closed steel mills into green hydrogen production — hydrogen steel requires existing industrial infrastructure",
        "Use closed electronics factories for edge computing hardware assembly — AI needs physical compute closer to users",
        "Repurpose closed paper mills into sustainable packaging/bioproducts — plastic replacement demand is massive",
        "Convert closed warehouse/distribution centers into automated micro-fulfillment — e-commerce demand keeps growing",
        "Turn former chemical plants into rare earth processing facilities — DOE grants available; strategic necessity",
    ]

    opp_text = "\n".join(f"- {o}" for o in opportunities)

    # Related failures
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name, manufacturing_sub_sector, failure_reason
        FROM failed_startups
        WHERE manufacturing_sub_sector IS NOT NULL
        ORDER BY funding_raised_usd DESC
        LIMIT 10
    """)
    failures = cursor.fetchall()
    cursor.close()

    failures_text = "\n".join(
        f"- {f['name']} ({f['manufacturing_sub_sector']}): {f['failure_reason']}"
        for f in failures
    )

    return opp_text, failures_text


def _gather_news_intelligence_data(conn) -> tuple[str, int]:
    """Gather recent news articles for intelligence synthesis."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT title, summary, source_name
        FROM news_articles
        WHERE is_manufacturing = 1 AND mentions_failure = 1
        ORDER BY published_at DESC
        LIMIT 15
    """
    )
    articles = cursor.fetchall()
    cursor.close()

    count = len(articles)

    if not articles:
        return "No relevant news articles found.", 0

    lines = []
    for a in articles:
        title = a["title"][:100] if a["title"] else "Untitled"
        source = a["source_name"] or "Unknown"
        summary = (a["summary"] or "")[:200]
        lines.append(f"- [{source}] {title}: {summary}")

    return "\n".join(lines), count


# -----------------------------------------------------------------------
# Insight generation functions
# -----------------------------------------------------------------------


def generate_executive_summary(
    conn,
    config: dict,
    force_refresh: bool = False,
) -> str | None:
    """Generate AI executive summary insight."""
    from report.insight_prompts import (
        EXECUTIVE_SUMMARY_SYSTEM,
        EXECUTIVE_SUMMARY_USER,
    )

    data = _gather_executive_summary_data(conn)

    user_prompt = EXECUTIVE_SUMMARY_USER.format(
        total_startups=data["total_startups"],
        mfg_count=data["mfg_count"],
        mfg_pct=data["mfg_pct"],
        failure_rate=data["failure_rate"],
        news_count=data["news_count"],
        revival_count=data["revival_count"],
        top_reasons=data["top_reasons"],
        revival_industries=data["revival_industries"],
        top_opportunities=data["top_opportunities"],
        top_funded=data["top_funded"],
    )

    content = _call_llm_with_cache(
        EXECUTIVE_SUMMARY_SYSTEM,
        user_prompt,
        "executive_summary",
        config,
        force_refresh=force_refresh,
    )

    if content:
        parsed = _parse_llm_json(content)
        human_readable = _format_executive_summary(parsed)
        _store_insight(conn, "executive_summary", "header", human_readable, parsed)
        return human_readable

    return None


def _format_executive_summary(data: dict | None) -> str:
    """Format executive summary JSON into readable markdown."""
    if not data:
        return "**Executive Summary**\n\n*AI analysis unavailable.*"

    themes = data.get("key_themes", [])
    themes_text = "\n".join(f"- {t}" for t in themes) if themes else ""

    risks = data.get("risk_factors", [])
    risks_text = "\n".join(f"- {r}" for r in risks) if risks else ""

    recommendations = data.get("recommendations", [])
    recs_text = "\n".join(f"- {r}" for r in recommendations) if recommendations else ""

    return f"""\
**AI Executive Summary**

{data.get("summary_paragraph", "")}

### Key Themes

{themes_text}

### Top Opportunity

**{data.get("top_opportunity", "N/A")}**

### Risk Factors

{risks_text}

### Market Outlook

{data.get("market_outlook", "N/A")}

### Recommendations

{recs_text}
"""


def analyze_failure_patterns(
    conn,
    config: dict,
    force_refresh: bool = False,
) -> str | None:
    """Generate failure pattern analysis insight."""
    from report.insight_prompts import (
        FAILURE_ANALYSIS_SYSTEM,
        FAILURE_ANALYSIS_USER,
    )

    
    startups_text = _gather_failure_analysis_data(conn)

    # Get unique sectors
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DISTINCT manufacturing_sub_sector FROM failed_startups WHERE manufacturing_sub_sector IS NOT NULL"
    )
    sectors = [r["manufacturing_sub_sector"] for r in cursor.fetchall()]
    cursor.close()
    sectors_text = ", ".join(sectors[:10])

    user_prompt = FAILURE_ANALYSIS_USER.format(
        startup_list=startups_text,
        sectors=sectors_text,
    )

    content = _call_llm_with_cache(
        FAILURE_ANALYSIS_SYSTEM,
        user_prompt,
        "failure_patterns",
        config,
        force_refresh=force_refresh,
    )

    if content:
        parsed = _parse_llm_json(content)
        human_readable = _format_failure_analysis(parsed)
        _store_insight(conn, "failure_patterns", "part1", human_readable, parsed)
        return human_readable

    return None


def _format_failure_analysis(data: dict | None) -> str:
    """Format failure analysis JSON into readable markdown."""
    if not data:
        return "\n### AI Failure Analysis\n\n*AI analysis unavailable.*"

    patterns = data.get("failure_pattern_analysis", [])
    cross_patterns = data.get("cross_sector_patterns", [])

    lines = ["\n### AI Failure Analysis"]

    if patterns:
        lines.append("")
        lines.append("**Root Cause Patterns by Sector:**")
        for p in patterns[:5]:
            lines.append("")
            lines.append(f"**{p.get('sector', 'Unknown')}** ({p.get('frequency', 0)} failures)")
            lines.append(f"- Failure mode: {p.get('failure_mode', 'N/A')}")
            if p.get("warning_signs"):
                lines.append("- Warning signs: " + ", ".join(p["warning_signs"][:3]))
            if p.get("lessons_learned"):
                lines.append("- Lessons: " + "; ".join(p["lessons_learned"][:2]))
            if p.get("prevention_tips"):
                lines.append("- Prevention: " + "; ".join(p["prevention_tips"][:2]))

    if cross_patterns:
        lines.append("")
        lines.append("**Cross-Sector Patterns:**")
        for pattern in cross_patterns[:3]:
            lines.append(f"- {pattern}")

    return "\n".join(lines)


def analyze_revial_opportunities(
    conn,
    config: dict,
    force_refresh: bool = False,
) -> str | None:
    """Generate revival opportunity analysis insight."""
    from report.insight_prompts import (
        REVIVAL_ANALYSIS_SYSTEM,
        REVIVAL_ANALYSIS_USER,
    )

    industries_text, related_failures = _gather_revial_analysis_data(conn)

    user_prompt = REVIVAL_ANALYSIS_USER.format(
        industries=industries_text,
        related_failures=related_failures,
    )

    content = _call_llm_with_cache(
        REVIVAL_ANALYSIS_SYSTEM,
        user_prompt,
        "revival_opportunities",
        config,
        force_refresh=force_refresh,
    )

    if content:
        parsed = _parse_llm_json(content)
        human_readable = _format_revial_analysis(parsed)
        _store_insight(conn, "revival_opportunities", "part2", human_readable, parsed)
        return human_readable

    return None


def _format_revial_analysis(data: dict | None) -> str:
    """Format revival analysis JSON into readable markdown."""
    if not data:
        return "\n### AI Revival Opportunities Analysis\n\n*AI analysis unavailable.*"

    evaluations = data.get("revival_evaluation", [])

    lines = ["\n### AI Revival Opportunities Analysis"]

    if evaluations:
        lines.append("")
        for e in evaluations[:6]:
            score = e.get("opportunity_score", 0)
            lines.append("")
            lines.append(
                f"**{e.get('industry', 'Unknown')}** (Viability Score: {score}/10)"
            )
            lines.append(f"- Why now: {e.get('why_now', 'N/A')}")
            if e.get("structural_changes"):
                changes = e.get("structural_changes", [])[:3]
                lines.append("- Structural changes: " + ", ".join(changes))
            if e.get("time_to_market"):
                lines.append(f"- Time to market: {e.get('time_to_market')}")
            confidence = e.get("confidence", 0)
            lines.append(f"- Confidence: {int(confidence * 100)}%")

    return "\n".join(lines)


def analyze_cross_references(
    conn,
    config: dict,
    force_refresh: bool = False,
) -> str | None:
    """Generate cross-reference analysis insight."""
    from report.insight_prompts import (
        CROSS_REFERENCE_SYSTEM,
        CROSS_REFERENCE_USER,
    )

    pattern_text, opp_text, facility_text = _gather_cross_reference_data(conn)

    user_prompt = CROSS_REFERENCE_USER.format(
        pattern_summary=pattern_text,
        opportunity_summary=opp_text,
        facility_summary=facility_text,
    )

    content = _call_llm_with_cache(
        CROSS_REFERENCE_SYSTEM,
        user_prompt,
        "cross_references",
        config,
        force_refresh=force_refresh,
    )

    if content:
        parsed = _parse_llm_json(content)
        human_readable = _format_cross_reference(parsed)
        _store_insight(conn, "cross_references", "part3", human_readable, parsed)
        return human_readable

    return None


def _format_cross_reference(data: dict | None) -> str:
    """Format cross-reference analysis JSON into readable markdown."""
    if not data:
        return "\n### AI Connection Analysis\n\n*AI analysis unavailable.*"

    direct = data.get("direct_opportunities", [])
    unexpected = data.get("unexpected_connections", [])
    timing = data.get("timing_insights", [])

    lines = ["\n### AI Connection Analysis"]

    if direct:
        lines.append("")
        lines.append("**Direct Opportunities (Failure → Revival):**")
        for d in direct[:4]:
            strength_emoji = {"strong": "🟢", "medium": "🟡", "weak": "🔴"}.get(
                d.get("connection_strength", ""), "⚪"
            )
            lines.append(f"- {strength_emoji} {d.get('from_pattern', '')} → {d.get('to_opportunity', '')}")
            lines.append(f"  {d.get('rationale', '')}")

    if unexpected:
        lines.append("")
        lines.append("**Unexpected Connections:**")
        for u in unexpected[:3]:
            surprise = u.get("surprise_factor", 5)
            stars = "⭐" * min(int(surprise / 2), 5)
            lines.append(f"- {stars} {u.get('connection', '')}")
            lines.append(f"  Evidence: {u.get('evidence', '')}")

    if timing:
        lines.append("")
        lines.append("**Timing Insights:**")
        for t in timing[:3]:
            lines.append(f"- {t}")

    return "\n".join(lines)


def rank_opportunities(
    conn,
    config: dict,
    force_refresh: bool = False,
) -> str | None:
    """Generate ranked opportunities insight."""
    from report.insight_prompts import (
        OPPORTUNITY_RANKING_SYSTEM,
        OPPORTUNITY_RANKING_USER,
    )

    opp_text, failures_text = _gather_opportunity_ranking_data(conn)

    user_prompt = OPPORTUNITY_RANKING_USER.format(
        opportunities=opp_text,
        related_failures=failures_text,
    )

    content = _call_llm_with_cache(
        OPPORTUNITY_RANKING_SYSTEM,
        user_prompt,
        "opportunity_rankings",
        config,
        force_refresh=force_refresh,
    )

    if content:
        parsed = _parse_llm_json(content)
        human_readable = _format_opportunity_rankings(parsed)
        _store_insight(conn, "opportunity_rankings", "part4", human_readable, parsed)
        return human_readable

    return None


def _format_opportunity_rankings(data: dict | None) -> str:
    """Format opportunity rankings JSON into readable markdown."""
    if not data:
        return "\n### AI-Recommended Opportunity Rankings\n\n*AI analysis unavailable.*"

    ranked = data.get("ranked_opportunities", [])

    lines = ["\n### AI-Recommended Opportunity Rankings"]

    if ranked:
        lines.append("")
        lines.append("| Rank | Opportunity | Viability | Key Risks | Time to Revenue |")
        lines.append("|------|-------------|-----------|-----------|-----------------|")
        for r in ranked:
            opp = r.get("opportunity", "Unknown")[:50]
            risks = ", ".join(r.get("key_risks", [])[:2])
            lines.append(
                f"| {r.get('rank', '?')} | {opp} | "
                f"{r.get('viability_score', '?')}/10 | {risks} | {r.get('time_to_revenue', 'N/A')} |"
            )
        lines.append("")
        lines.append("**Detailed Analysis:**")
        for r in ranked[:5]:
            lines.append("")
            lines.append(f"**#{r.get('rank')} {r.get('opportunity', 'Unknown')}**")
            lines.append(f"- Score: {r.get('viability_score', '?')}/10")
            lines.append(f"- Justification: {r.get('justification', 'N/A')}")
            if r.get("recommended_approach"):
                lines.append(f"- Approach: {r.get('recommended_approach')}")

    return "\n".join(lines)


def summarize_news_themes(
    conn,
    config: dict,
    force_refresh: bool = False,
) -> str | None:
    """Generate news intelligence insight."""
    from report.insight_prompts import (
        NEWS_INTELLIGENCE_SYSTEM,
        NEWS_INTELLIGENCE_USER,
    )

    articles_text, count = _gather_news_intelligence_data(conn)

    user_prompt = NEWS_INTELLIGENCE_USER.format(
        articles=articles_text,
        count=count,
    )

    content = _call_llm_with_cache(
        NEWS_INTELLIGENCE_SYSTEM,
        user_prompt,
        "news_intelligence",
        config,
        force_refresh=force_refresh,
    )

    if content:
        parsed = _parse_llm_json(content)
        human_readable = _format_news_intelligence(parsed)
        _store_insight(conn, "news_intelligence", "news", human_readable, parsed)
        return human_readable

    return None


def _format_news_intelligence(data: dict | None) -> str:
    """Format news intelligence JSON into readable markdown."""
    if not data:
        return "\n### AI News Intelligence\n\n*AI analysis unavailable.*"

    themes = data.get("key_themes", [])
    trends = data.get("emerging_trends", [])
    companies = data.get("notable_companies", [])
    sentiment = data.get("sentiment_analysis", "N/A")
    insights = data.get("actionable_insights", [])

    lines = ["\n### AI News Intelligence"]

    if sentiment:
        sentiment_icon = {
            "positive": "📈",
            "negative": "📉",
            "mixed": "↔️",
        }.get(sentiment.lower().strip(), "📊")
        lines.append(f"\n**Coverage Sentiment:** {sentiment_icon} {sentiment}")

    if themes:
        lines.append("")
        lines.append("**Key Themes:**")
        for t in themes:
            lines.append(f"- {t}")

    if trends:
        lines.append("")
        lines.append("**Emerging Trends:**")
        for t in trends:
            lines.append(f"- {t}")

    if companies:
        lines.append("")
        lines.append("**Notable Companies Mentioned:**")
        lines.append(", ".join(companies[:8]))

    if insights:
        lines.append("")
        lines.append("**Actionable Insights:**")
        for i in insights:
            lines.append(f"- {i}")

    return "\n".join(lines)


# -----------------------------------------------------------------------
# Main orchestration
# -----------------------------------------------------------------------


def run_insights_analysis(
    conn,
    config: dict,
    section: str | None = None,
    force_refresh: bool = False,
) -> dict[str, str | None]:
    """Run all (or selected) LLM insights analysis.

    Args:
        conn: Database connection
        config: Application config dict
        section: If set, only run that insight (e.g. "executive_summary")
        force_refresh: If True, ignore cache and regenerate

    Returns:
        Dict mapping insight_type -> content (or None if failed)
    """
    results: dict[str, str | None] = {}

    insight_map = {
        "executive_summary": generate_executive_summary,
        "failure_patterns": analyze_failure_patterns,
        "revival_opportunities": analyze_revial_opportunities,
        "cross_references": analyze_cross_references,
        "opportunity_rankings": rank_opportunities,
        "news_intelligence": summarize_news_themes,
    }

    # Run all or selected
    if section:
        insight_map = {section: insight_map.get(section)}
        insight_map = {k: v for k, v in insight_map.items() if v}

    for insight_type, func in insight_map.items():
        try:
            _logger.info("Running insight: %s", insight_type)
            result = func(conn, config, force_refresh=force_refresh)
            results[insight_type] = result
        except Exception as e:
            _logger.error("Insight %s failed: %s", insight_type, e)
            results[insight_type] = None

    return results


def clear_insights_cache() -> None:
    """Clear the in-memory and file cache for insights."""
    _insights_memory_cache.clear()

    if CACHE_DIR.exists():

        for item in CACHE_DIR.rglob("*"):
            if item.is_file():
                item.unlink()
        _logger.info("Insights file cache cleared")