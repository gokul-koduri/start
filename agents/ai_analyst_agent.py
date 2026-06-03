"""AI Analyst Agent — natural language query interface over the startup research database.

Uses Ollama to:
1. Classify query intent
2. Generate SQL from the schema
3. Interpret query results

Invoked via: python run_agent.py --chat "What are the top 5 failure reasons in e-commerce?"

NOT part of any automated pipeline. Runs directly from CLI.
"""

import json
import logging
import re
import urllib.request
import urllib.error

from agents.base import AgentResult, BaseAgent
from agents.ollama_usage_tracker import _track_inference
from db.connection import get_connection
from db import schema

_logger = logging.getLogger(__name__)

# Compact schema description for SQL generation prompt
_SCHEMA_SUMMARY = """
Key tables in the startup_research database:
- failed_startups: id, name, sector, manufacturing_sub_sector, country, region, funding_raised_usd, peak_valuation_usd, year_founded, year_shutdown, failure_reason, failure_category, notable, source
- news_articles: id, title, url, source_name, published_at, summary, is_manufacturing, mentions_failure, startup_name_extracted
- bls_survival_rates: id, naics_code, industry_name, year, quarter, age_1_yr_survival, age_2_yr_survival, age_3_yr_survival, age_5_yr_survival, establishment_count
- revival_industries: id, industry, died_period, why_returning, market_fit, key_investors, market_size_2030
- geographic_hotspots: id, region, closed_facility_types, revival_potential
- failure_reasons_taxonomy: id, reason, percentage, rank_order
- failure_idea_patterns: id, idea_category, example_startups, why_failed, market_reality
- reshoring_data: id, report_year, data_year, industry, jobs_created, project_count, success_rate_pct
- reshoring_summary_stats: id, stat_year, total_jobs, headline
- llm_pricing: id, provider, model_name, input_price_per_1m, output_price_per_1m, context_window, modality
- llm_portfolio: id, task_category, provider, model_name, allocation_pct, composite_score, cost_per_1m_tokens
- llm_benchmarks: id, provider, model_name, benchmark_name, benchmark_score, benchmark_category
- llm_price_changes: id, provider, model_name, input_change_pct, output_change_pct, detected_at
- llm_optimization_alerts: id, alert_type, title, description, priority, estimated_savings_pct
- kg_entities: id, name, normalized_name, entity_type_id, mention_count
- kg_relationships: id, source_entity_id, target_entity_id, relationship_type, weight
- analysis_failure_patterns, analysis_survival_trends, analysis_revival_opportunities, analysis_geographic_strategy, analysis_news_intelligence, analysis_opportunity_pipeline, analysis_whale_investors, analysis_global_market_viability: all have (id, analysis_type, insights_json, analyzed_at, record_count)
"""

# SQL safety — reject any mutation statements
_SQL_BLACKLIST = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|REPLACE|GRANT|REVOKE|LOCK|UNLOCK)\b",
    re.IGNORECASE,
)

_INTENT_CATEGORIES = [
    "failure_patterns", "market_analysis", "news", "survival_rates",
    "revival_industries", "geographic", "llm_pricing", "pipeline_status", "general",
]


class AIAnalystAgent(BaseAgent):
    """Natural language query interface over the startup research database.

    This agent does NOT participate in automated pipelines. Invoked directly
    by the CLI ``--chat`` flag and prints results to stdout.

    Config options:
        ollama_url: Ollama API endpoint (default: http://localhost:11434/api/chat)
        ollama_model: model name (default: llama3)
        timeout_seconds: HTTP timeout for Ollama calls (default: 120)
        max_context_exchanges: prior exchanges in context (default: 3)
    """

    _conversation_history: list[dict] = []

    @property
    def name(self) -> str:
        return "ai_analyst"

    def __init__(self, config: dict | None = None, dry_run: bool = False, query: str = ""):
        super().__init__(config=config, dry_run=dry_run)
        self.query = query

    # ── Ollama communication ──

    def _call_ollama(self, messages: list[dict], timeout: float = 120) -> str | None:
        """Send messages to Ollama /api/chat and return response content."""
        url = self.config.get("ollama_url", "http://localhost:11434/api/chat")
        model = self.config.get("ollama_model", "llama3")
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.3},
        }
        try:
            data = json.dumps(payload).encode()
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                result = json.loads(resp.read().decode())

            prompt_tokens = result.get("prompt_eval_count", 0)
            completion_tokens = result.get("eval_count", 0)
            if prompt_tokens or completion_tokens:
                _track_inference(model, prompt_tokens, completion_tokens)

            return result.get("message", {}).get("content", "")
        except Exception as e:
            _logger.error("AIAnalystAgent: Ollama call failed: %s", e)
            return None

    # ── Intent classification ──

    def _classify_intent(self, query: str) -> str:
        """Classify the user query into a category using Ollama."""
        system_msg = {
            "role": "system",
            "content": (
                "You are a query classifier for a startup failure research database. "
                "Classify the user's question into exactly ONE of these categories:\n"
                "- failure_patterns: questions about why startups fail, failure reasons, sector failures\n"
                "- market_analysis: questions about market trends, industries, funding\n"
                "- news: questions about news articles, recent events\n"
                "- survival_rates: questions about business survival, BLS data, industry survival\n"
                "- revival_industries: questions about industries making a comeback\n"
                "- geographic: questions about regions, countries, locations\n"
                "- llm_pricing: questions about LLM model pricing, costs, benchmarks\n"
                "- pipeline_status: questions about data collection runs, agent runs\n"
                "- general: questions that span multiple categories or are unclear\n\n"
                "Respond with ONLY the category name, nothing else."
            ),
        }
        result = self._call_ollama([system_msg, {"role": "user", "content": query}], timeout=30)
        if result:
            for cat in _INTENT_CATEGORIES:
                if cat in result.lower():
                    return cat
        return "general"

    # ── SQL generation ──

    def _generate_sql(self, query: str, intent: str) -> str | None:
        """Generate a SQL SELECT query from the user's natural language question."""
        system_msg = {
            "role": "system",
            "content": (
                "You are a SQL expert for a MySQL database about startup failures and market research. "
                "Generate a single SELECT query to answer the user's question.\n\n"
                f"{_SCHEMA_SUMMARY}\n\n"
                "Rules:\n"
                "1. ONLY generate SELECT statements. Never INSERT, UPDATE, DELETE, DROP, etc.\n"
                "2. Use LIMIT to keep results manageable (default LIMIT 20 unless user asks for more).\n"
                "3. Use proper MySQL syntax.\n"
                "4. Use appropriate JOINs when needed.\n"
                "5. Respond with ONLY the SQL query, no explanation, no markdown fences.\n"
                "6. If insights_json column is needed, use JSON_EXTRACT for specific fields.\n"
            ),
        }
        result = self._call_ollama(
            [system_msg, {"role": "user", "content": f"Intent: {intent}\n\nQuestion: {query}"}],
            timeout=60,
        )
        if not result:
            return None

        sql = result.strip()
        # Strip markdown fences
        if sql.startswith("```"):
            sql = sql.split("\n", 1)[1] if "\n" in sql else sql[3:]
            if sql.endswith("```"):
                sql = sql[:-3]
            sql = sql.strip()
            if sql.lower().startswith("sql"):
                sql = sql[3:].strip()

        # Safety checks
        if _SQL_BLACKLIST.search(sql):
            _logger.warning("AIAnalystAgent: Rejected SQL with forbidden operations")
            return None
        if not sql.strip().upper().startswith("SELECT"):
            _logger.warning("AIAnalystAgent: Rejected non-SELECT SQL")
            return None

        return sql

    # ── SQL execution (read-only) ──

    def _execute_sql(self, sql: str) -> tuple[list[dict] | None, str | None]:
        """Execute read-only SQL and return (results, error_message)."""
        try:
            conn = get_connection()
            conn.begin()
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = [dict(r) for r in cursor.fetchall()]
            conn.rollback()
            cursor.close()
            conn.close()
            return rows, None
        except Exception as e:
            _logger.error("AIAnalystAgent: SQL error: %s", e)
            return None, str(e)

    # ── Result formatting ──

    def _format_results_as_markdown(self, rows: list[dict]) -> str:
        """Format query results as a compact markdown table."""
        if not rows:
            return "No results found."

        display = rows[:50]
        headers = list(display[0].keys())

        lines = []
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join("---" for _ in headers) + " |")
        for row in display:
            vals = []
            for h in headers:
                v = row.get(h)
                if v is None:
                    vals.append("N/A")
                elif isinstance(v, float):
                    vals.append(f"{v:,.2f}")
                elif isinstance(v, int):
                    vals.append(f"{v:,}")
                else:
                    s = str(v)
                    vals.append(s[:100] + "..." if len(s) > 100 else s)
            lines.append("| " + " | ".join(vals) + " |")

        if len(rows) > 50:
            lines.append(f"\n... and {len(rows) - 50} more rows (showing first 50)")
        return "\n".join(lines)

    # ── Answer generation ──

    def _generate_answer(self, query: str, sql: str, results_md: str) -> str:
        """Generate a natural language answer from query and results."""
        system_msg = {
            "role": "system",
            "content": (
                "You are a startup research analyst. Based on the SQL query results, "
                "answer the user's question clearly and concisely.\n\n"
                "Guidelines:\n"
                "- Cite specific numbers from the data\n"
                "- Provide actionable insights\n"
                "- Mention limitations if data is incomplete\n"
                "- Keep the answer focused and to the point\n"
                "- Format with markdown for readability\n"
            ),
        }
        result = self._call_ollama(
            [system_msg, {
                "role": "user",
                "content": (
                    f"Question: {query}\n\n"
                    f"SQL:\n```sql\n{sql}\n```\n\n"
                    f"Results:\n{results_md}\n\n"
                    "Provide a clear, data-driven answer."
                ),
            }],
            timeout=90,
        )
        return result or "Unable to generate an answer."

    # ── Execute ──

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        if not self.query:
            return AgentResult(
                agent_name=self.name,
                status="failed",
                errors=["No query provided. Use --chat flag."],
            )

        # Step 1: Classify intent
        print(f"\n{'─'*60}", flush=True)
        print(f"Analyzing query...", flush=True)
        intent = self._classify_intent(self.query)
        _logger.info("AIAnalystAgent: Intent=%s Query=%s", intent, self.query[:80])

        # Step 2: Generate SQL
        sql = self._generate_sql(self.query, intent)
        if not sql:
            answer = "Could not generate a valid SQL query. Try rephrasing."
            print(f"\n{answer}", flush=True)
            return AgentResult(agent_name=self.name, status="partial", errors=["SQL generation failed"])

        _logger.info("AIAnalystAgent: SQL=%s", sql[:200])

        # Step 3: Execute SQL
        rows, error = self._execute_sql(sql)
        if error:
            answer = f"Error executing query: {error}"
            print(f"\n{answer}", flush=True)
            return AgentResult(agent_name=self.name, status="partial", errors=[error])

        # Step 4: Format + answer
        results_md = self._format_results_as_markdown(rows)
        answer = self._generate_answer(self.query, sql, results_md)

        # Output
        print(f"\n{'═'*60}", flush=True)
        print(f"  Intent:  {intent}", flush=True)
        print(f"  SQL:     {sql[:200]}", flush=True)
        print(f"  Rows:    {len(rows)}", flush=True)
        print(f"{'═'*60}\n", flush=True)
        print(answer, flush=True)
        print()

        return AgentResult(
            agent_name=self.name,
            status="success",
            data={
                "query": self.query,
                "intent": intent,
                "sql": sql,
                "rows_returned": len(rows),
                "records_affected": len(rows),
            },
        )
