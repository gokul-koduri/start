#!/usr/bin/env python3
"""Centralized prompt templates for LLM-powered report insights.

All prompts are designed to output structured JSON for reliable parsing.
Use these templates with the LLMReportClient.
"""

# =============================================================================
# System Prompts - Set the LLM's role and output format requirements
# =============================================================================

EXECUTIVE_SUMMARY_SYSTEM = """You are a senior market research analyst for the Opportunity Intelligence Platform.
You analyze startup failures and manufacturing revival opportunities to provide actionable intelligence.

Your output MUST be:
- Specific with numbers, company names, and dates
- Analytical with clear reasoning chains
- Actionable with concrete recommendations

ALWAYS respond with valid JSON only. No markdown, no code fences, no explanatory text.
"""

FAILURE_ANALYSIS_SYSTEM = """You are an expert analyst specializing in manufacturing startup failures.
You identify actionable patterns that can prevent future failures.

Your analysis should:
- Focus on root causes, not symptoms
- Provide specific warning signs founders missed
- Suggest concrete prevention strategies

ALWAYS respond with valid JSON only. No markdown, no code fences, no explanatory text.
"""

REVIVAL_ANALYSIS_SYSTEM = """You are a manufacturing industry analyst evaluating revival opportunities.
You assess industries making a comeback based on fundamental changes, not hype.

Your evaluation should:
- Distinguish between genuine structural changes and temporary factors
- Identify what enabling conditions existed before and what changed NOW
- Assess realistic timelines and success factors

ALWAYS respond with valid JSON only. No markdown, no code fences, no explanatory text.
"""

CROSS_REFERENCE_SYSTEM = """You identify non-obvious connections between data points.
Your insights should be surprising but analytically sound.

Find connections that others miss:
- How past failures inform current opportunities
- Unexpected industry adjacencies
- Timing insights (why NOW is different)

ALWAYS respond with valid JSON only. No markdown, no code fences, no explanatory text.
"""

OPPORTUNITY_RANKING_SYSTEM = """You rank manufacturing opportunities by genuine potential, not hype.
Be skeptical and conservative. Only rank highly if fundamentals support it.

Your rankings should:
- Consider capital requirements vs available funding
- Factor in competitive landscape realistically
- Identify key risks alongside potential rewards
- Suggest practical approaches

ALWAYS respond with valid JSON only. No markdown, no code fences, no explanatory text.
"""

NEWS_INTELLIGENCE_SYSTEM = """You synthesize news articles into actionable intelligence.
You identify patterns, themes, and implications across multiple sources.

Your synthesis should:
- Identify emerging trends before they become obvious
- Distinguish signal from noise
- Connect individual stories to larger patterns

ALWAYS respond with valid JSON only. No markdown, no code fences, no explanatory text.
"""

# =============================================================================
# User Prompts - Contextual queries with data placeholders
# =============================================================================

# -----------------------------------------------------------------------------
# Executive Summary Prompt
# -----------------------------------------------------------------------------

EXECUTIVE_SUMMARY_USER = """Generate an executive summary for a research report on Failed Startups and Manufacturing Revival.
Base your analysis strictly on the provided data. Do not invent or assume information.

DATA OVERVIEW:
- Total failed startups tracked: {total_startups}
- Manufacturing-specific failures: {mfg_count} ({mfg_pct}% of total)
- Failure rate (5-year): ~{failure_rate}%
- Total news articles: {news_count}
- Industries with revival potential: {revival_count}
- Top failure reasons: {top_reasons}
- Revival industries: {revival_industries}
- Top opportunities: {top_opportunities}
- Top funded failures: {top_funded}

Reply with JSON:
{{
  "summary_paragraph": "<3 sentence overview of key findings>",
  "key_themes": ["<theme 1>", "<theme 2>", "<theme 3>"],
  "top_opportunity": "<most compelling opportunity with 1-sentence justification>",
  "risk_factors": ["<risk 1>", "<risk 2>"],
  "market_outlook": "<1 sentence on overall market timing>",
  "recommendations": ["<recommendation 1>", "<recommendation 2>"]
}}"""


# -----------------------------------------------------------------------------
# Failure Pattern Analysis Prompt
# -----------------------------------------------------------------------------

FAILURE_ANALYSIS_USER = """Analyze these manufacturing startup failures and identify actionable patterns.
Base your analysis strictly on the provided data. Do not invent or assume information.

MANUFACTURING FAILURES:
{startup_list}

SECTORS IN DATA: {sectors}

Reply with JSON:
{{
  "failure_pattern_analysis": [
    {{
      "sector": "<sector name>",
      "failure_mode": "<primary failure mode>",
      "frequency": <count of failures in this sector>,
      "warning_signs": ["<sign 1 from data>", "<sign 2 from data>"],
      "root_causes": ["<cause 1>", "<cause 2>"],
      "lessons_learned": ["<lesson 1>", "<lesson 2>"],
      "prevention_tips": ["<tip 1>", "<tip 2>"]
    }}
  ],
  "cross_sector_patterns": ["<pattern that appears across multiple sectors>"]
}}"""


# -----------------------------------------------------------------------------
# Revival Opportunity Analysis Prompt
# -----------------------------------------------------------------------------

REVIVAL_ANALYSIS_USER = """Evaluate these manufacturing industries with revival potential.
Base your analysis strictly on the provided data. Do not invent or assume information.

INDUSTRIES:
{industries}

FAILED STARTUPS IN RELATED SECTORS (for context):
{related_failures}

Reply with JSON:
{{
  "revival_evaluation": [
    {{
      "industry": "<name>",
      "why_now": "<reasoning - why is this returning NOW vs before>",
      "structural_changes": ["<change 1 from data>", "<change 2 from data>"],
      "available_assets": ["<asset type mentioned in data>"],
      "success_factors": ["<factor 1>", "<factor 2>"],
      "time_to_market": "<estimation based on data>",
      "confidence": <0-1 based on data quality>,
      "opportunity_score": <1-10>
    }}
  ]
}}"""


# -----------------------------------------------------------------------------
# Cross-Reference Analysis Prompt
# -----------------------------------------------------------------------------

CROSS_REFERENCE_USER = """Find non-obvious connections between failed startup patterns and revival opportunities.
Base your analysis strictly on the provided data. Do not invent or assume information.

FAILED STARTUP PATTERNS:
{pattern_summary}

REVIVAL OPPORTUNITIES:
{opportunity_summary}

CLOSED FACILITIES BY TYPE:
{facility_summary}

Reply with JSON:
{{
  "direct_opportunities": [
    {{
      "from_pattern": "<failure pattern from data>",
      "to_opportunity": "<revival opportunity from data>",
      "connection_strength": "<strong|medium|weak>",
      "rationale": "<explanation connecting the two>"
    }}
  ],
  "unexpected_connections": [
    {{
      "connection": "<description>",
      "surprise_factor": <1-10>,
      "evidence": "<supporting reasoning from data>"
    }}
  ],
  "timing_insights": ["<insight 1>", "<insight 2>"]
}}"""


# -----------------------------------------------------------------------------
# Opportunity Ranking Prompt
# -----------------------------------------------------------------------------

OPPORTUNITY_RANKING_USER = """Rank these manufacturing opportunities by viability.
Base your analysis strictly on the provided data. Do not invent or assume information.

OPPORTUNITIES:
{opportunities}

RELATED MANUFACTURING FAILURES (learn from past):
{related_failures}

Reply with JSON:
{{
  "ranked_opportunities": [
    {{
      "rank": <position>,
      "opportunity": "<name from data>",
      "viability_score": <1-10 based on data>,
      "justification": "<reasoning>",
      "key_risks": ["<risk 1 from data>", "<risk 2>"],
      "recommended_approach": "<1-2 sentences>",
      "capital_requirement": "<amount or 'varies'>",
      "time_to_revenue": "<months>"
    }}
  ]
}}"""


# -----------------------------------------------------------------------------
# News Intelligence Prompt
# -----------------------------------------------------------------------------

NEWS_INTELLIGENCE_USER = """Synthesize these recent news articles about manufacturing and startup failures.
Base your analysis strictly on the provided data. Do not invent or assume information.

RECENT ARTICLES ({count} total):
{articles}

Reply with JSON:
{{
  "key_themes": ["<theme 1>", "<theme 2>", "<theme 3>"],
  "emerging_trends": ["<trend 1>", "<trend 2>"],
  "notable_companies": ["<company mentioned in articles>"],
  "sentiment_analysis": "<overall tone of coverage (positive/negative/mixed)>",
  "actionable_insights": ["<insight 1>", "<insight 2>"]
}}"""


# =============================================================================
# Helper function to format prompts with data
# =============================================================================

def format_executive_summaryprompt(
    total_startups: int,
    mfg_count: int,
    mfg_pct: float,
    failure_rate: float,
    news_count: int,
    revival_count: int,
    top_reasons: str,
    revival_industries: str,
    top_opportunities: str,
    top_funded: str,
) -> str:
    """Format the executive summary prompt with data."""
    return EXECUTIVE_SUMMARY_USER.format(
        total_startups=total_startups,
        mfg_count=mfg_count,
        mfg_pct=mfg_pct,
        failure_rate=failure_rate,
        news_count=news_count,
        revival_count=revival_count,
        top_reasons=top_reasons,
        revival_industries=revival_industries,
        top_opportunities=top_opportunities,
        top_funded=top_funded,
    )


def format_failure_analysis_prompt(startup_list: str, sectors: str) -> str:
    """Format the failure analysis prompt with data."""
    return FAILURE_ANALYSIS_USER.format(
        startup_list=startup_list,
        sectors=sectors,
    )


def format_revial_analysis_prompt(industries: str, related_failures: str) -> str:
    """Format the revival analysis prompt with data."""
    return REVIVAL_ANALYSIS_USER.format(
        industries=industries,
        related_failures=related_failures,
    )


def format_cross_reference_prompt(
    pattern_summary: str,
    opportunity_summary: str,
    facility_summary: str,
) -> str:
    """Format the cross-reference analysis prompt with data."""
    return CROSS_REFERENCE_USER.format(
        pattern_summary=pattern_summary,
        opportunity_summary=opportunity_summary,
        facility_summary=facility_summary,
    )


def format_opportunity_ranking_prompt(opportunities: str, related_failures: str) -> str:
    """Format the opportunity ranking prompt with data."""
    return OPPORTUNITY_RANKING_USER.format(
        opportunities=opportunities,
        related_failures=related_failures,
    )


def format_news_intelligence_prompt(articles: str, count: int) -> str:
    """Format the news intelligence prompt with data."""
    return NEWS_INTELLIGENCE_USER.format(
        articles=articles,
        count=count,
    )