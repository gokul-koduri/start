"""FastAPI web server — exposes AI Analyst chat and data API over HTTP.

Run:
    python api_server.py                    # Start on http://localhost:8000
    python api_server.py --port 5000        # Custom port
    python api_server.py --host 0.0.0.0     # Allow external access

Endpoints:
    GET  /                          — Dashboard (serves site/index.html)
    GET  /api/health                — Health check
    GET  /api/stats                 — Database statistics
    GET  /api/startups              — List failed startups (with filters)
    GET  /api/startups/{id}         — Single startup details
    GET  /api/news                  — Recent news articles
    GET  /api/survival-rates        — BLS survival rate data
    GET  /api/revival-opportunities — Revival industry data
    GET  /api/alerts                — Active alerts
    POST /api/chat                  — AI Analyst natural language query
    GET  /api/pipeline-runs         — Recent pipeline execution history
"""

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import setup_logging, load_config, get_project_root
from db.connection import get_connection
from db import schema

# FastAPI imports (graceful fallback)
try:
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

if HAS_FASTAPI:
    app = FastAPI(
        title="Startup Research Report API",
        description="AI-powered startup failure research & analysis API",
        version="1.0.0",
    )

    # CORS — allow dashboard to call API
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


    # ── Dashboard ─────────────────────────────────────────────

    @app.get("/", response_class=HTMLResponse)
    def dashboard():
        """Serve the interactive dashboard."""
        site_dir = get_project_root() / "site"
        index = site_dir / "index.html"
        if index.exists():
            return FileResponse(str(index))
        return HTMLResponse("<h1>Dashboard not built yet. Run: python run_agent.py --pipeline daily</h1>", status_code=404)


    # ── Health ────────────────────────────────────────────────

    @app.get("/api/health")
    def health():
        """Health check — confirms DB connectivity."""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
            return {"status": "healthy", "database": "connected"}
        except Exception as e:
            return JSONResponse({"status": "unhealthy", "error": str(e)}, status_code=503)


    # ── Stats ─────────────────────────────────────────────────

    @app.get("/api/stats")
    def stats():
        """Database statistics summary."""
        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()

        counts = {}
        for table in ["failed_startups", "news_articles", "bls_survival_rates",
                       "revival_industries", "geographic_hotspots", "llm_pricing",
                       "kg_entities", "kg_relationships", "llm_optimization_alerts"]:
            try:
                cursor.execute(f"SELECT COUNT(*) as cnt FROM {table}")
                counts[table] = cursor.fetchone()["cnt"]
            except Exception:
                counts[table] = 0

        cursor.close()
        conn.close()
        return counts


    # ── Startups ──────────────────────────────────────────────

    @app.get("/api/startups")
    def list_startups(
        sector: str | None = Query(None, description="Filter by sector"),
        country: str | None = Query(None, description="Filter by country"),
        region: str | None = Query(None, description="Filter by region"),
        failure_category: str | None = Query(None, description="Filter by failure category"),
        manufacturing: bool | None = Query(None, description="Manufacturing startups only"),
        limit: int = Query(20, ge=1, le=100, description="Max results"),
        offset: int = Query(0, ge=0, description="Pagination offset"),
    ):
        """List failed startups with optional filters."""
        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()

        conditions = []
        params = []

        if sector:
            conditions.append("sector LIKE %s")
            params.append(f"%{sector}%")
        if country:
            conditions.append("country = %s")
            params.append(country)
        if region:
            conditions.append("region = %s")
            params.append(region)
        if failure_category:
            conditions.append("failure_category = %s")
            params.append(failure_category)
        if manufacturing is True:
            conditions.append("manufacturing_sub_sector IS NOT NULL")

        where = " AND ".join(conditions)
        where_clause = f"WHERE {where}" if where else ""

        cursor.execute(
            f"SELECT COUNT(*) as cnt FROM failed_startups {where_clause}",
            params,
        )
        total = cursor.fetchone()["cnt"]

        cursor.execute(
            f"""SELECT id, name, sector, manufacturing_sub_sector, country, region,
                       funding_raised_usd, funding_description, year_founded, year_shutdown,
                       failure_reason, failure_category, notable, source
                FROM failed_startups {where_clause}
                ORDER BY funding_raised_usd DESC NULLS LAST
                LIMIT %s OFFSET %s""",
            params + [limit, offset],
        )
        rows = [dict(r) for r in cursor.fetchall()]

        cursor.close()
        conn.close()

        return {"total": total, "offset": offset, "limit": limit, "results": rows}


    @app.get("/api/startups/{startup_id}")
    def get_startup(startup_id: int):
        """Get a single startup by ID."""
        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM failed_startups WHERE id = %s", (startup_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail="Startup not found")
        return dict(row)


    # ── News ──────────────────────────────────────────────────

    @app.get("/api/news")
    def list_news(
        limit: int = Query(20, ge=1, le=100),
        offset: int = Query(0, ge=0),
        manufacturing: bool | None = Query(None),
    ):
        """Recent news articles."""
        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()

        where = "WHERE is_manufacturing = 1" if manufacturing else ""
        cursor.execute(f"SELECT COUNT(*) as cnt FROM news_articles {where}")
        total = cursor.fetchone()["cnt"]

        cursor.execute(
            f"""SELECT id, title, url, source_name, published_at, summary,
                       is_manufacturing, mentions_failure
                FROM news_articles {where}
                ORDER BY published_at DESC
                LIMIT %s OFFSET %s""",
            [limit, offset],
        )
        rows = [dict(r) for r in cursor.fetchall()]

        cursor.close()
        conn.close()
        return {"total": total, "offset": offset, "limit": limit, "results": rows}


    # ── Survival Rates ───────────────────────────────────────

    # ── Risk Scores ──────────────────────────────────────────

    @app.get("/api/risk-scores")
    def risk_scores(
        risk_level: str | None = Query(None, description="Filter: low, moderate, high, critical"),
        limit: int = Query(20, ge=1, le=100),
        offset: int = Query(0, ge=0),
    ):
        """Startup failure risk scores."""
        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()

        where = "WHERE r.risk_level = %s" if risk_level else ""
        params = [risk_level] if risk_level else []

        cursor.execute(
            f"""SELECT r.id, s.name, s.sector, s.country, s.funding_raised_usd,
                      r.risk_score, r.risk_level, r.factors_json, r.recommendation, r.scored_at
               FROM startup_risk_scores r
               JOIN failed_startups s ON r.startup_id = s.id
               {where}
               ORDER BY r.risk_score DESC
               LIMIT %s OFFSET %s""",
            params + [limit, offset],
        )
        rows = [dict(r) for r in cursor.fetchall()]

        # Parse factors JSON
        for row in rows:
            if isinstance(row.get("factors_json"), str):
                try:
                    row["factors"] = json.loads(row["factors_json"])
                except json.JSONDecodeError:
                    row["factors"] = []
            else:
                row["factors"] = row.get("factors_json", [])
            del row["factors_json"]

        cursor.close()
        conn.close()
        return {"results": rows}

    @app.post("/api/score")
    def score_a_startup(body: dict):
        """Score a single startup's failure risk (no DB write).

        Request body:
            {"sector": "EV", "funding_usd": 50000000, "country": "US", "year_founded": 2019}
        """
        from agents.risk_scorer import score_startup
        return score_startup(
            sector=body.get("sector", ""),
            funding_usd=body.get("funding_usd"),
            country=body.get("country", ""),
            region=body.get("region", ""),
            year_founded=body.get("year_founded"),
        )

    @app.get("/api/survival-rates")
    def survival_rates(
        naics: str | None = Query(None, description="NAICS code filter"),
        year: int | None = Query(None, description="Year filter"),
        limit: int = Query(20, ge=1, le=100),
    ):
        """BLS survival rate data."""
        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()

        conditions = []
        params = []
        if naics:
            conditions.append("naics_code = %s")
            params.append(naics)
        if year:
            conditions.append("year = %s")
            params.append(year)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        cursor.execute(
            f"""SELECT naics_code, industry_name, year, quarter,
                       age_1_yr_survival, age_2_yr_survival, age_3_yr_survival,
                       age_5_yr_survival, establishment_count
                FROM bls_survival_rates {where}
                ORDER BY year DESC, naics_code
                LIMIT %s""",
            params + [limit],
        )
        rows = [dict(r) for r in cursor.fetchall()]

        cursor.close()
        conn.close()
        return {"results": rows}


    # ── Revival Opportunities ─────────────────────────────────

    @app.get("/api/revival-opportunities")
    def revival_opportunities(limit: int = Query(20, ge=1, le=50)):
        """Revival industry opportunities."""
        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM revival_industries LIMIT %s", (limit,))
        rows = [dict(r) for r in cursor.fetchall()]
        cursor.close()
        conn.close()
        return {"results": rows}


    # ── Alerts ────────────────────────────────────────────────

    @app.get("/api/alerts")
    def list_alerts(limit: int = Query(20, ge=1, le=50)):
        """Active optimization and pipeline alerts."""
        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()
        cursor.execute(
            """SELECT id, alert_type, title, description, priority,
                      estimated_savings_pct, created_at
               FROM llm_optimization_alerts
               WHERE dismissed = 0
               ORDER BY priority DESC, created_at DESC LIMIT %s""",
            (limit,),
        )
        rows = [dict(r) for r in cursor.fetchall()]
        cursor.close()
        conn.close()
        return {"results": rows}


    # ── Pipeline Runs ─────────────────────────────────────────

    @app.get("/api/pipeline-runs")
    def pipeline_runs(limit: int = Query(20, ge=1, le=100)):
        """Recent pipeline execution history."""
        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()
        cursor.execute(
            """SELECT id, pipeline_name, agent_name, started_at, completed_at,
                      status, records_affected, error_message
               FROM agent_runs
               ORDER BY started_at DESC LIMIT %s""",
            (limit,),
        )
        rows = [dict(r) for r in cursor.fetchall()]
        cursor.close()
        conn.close()
        return {"results": rows}


    # ── AI Chat ───────────────────────────────────────────────

    @app.post("/api/chat")
    async def chat(request_body: dict):
        """AI Analyst — ask a natural language question about the data.

        Request body:
            {"query": "What are the top 5 failure reasons for EV startups?"}

        Response:
            {"answer": "...", "intent": "...", "sql": "...", "rows": 42}
        """
        query = request_body.get("query", "").strip()
        if not query:
            raise HTTPException(status_code=400, detail="Missing 'query' field")

        config = load_config()
        analyst_config = config.get("agents", {}).get("ai_analyst", {})
        analyst_config["_pipeline_name"] = "chat"
        analyst_config["_scheduled"] = False

        from agents.ai_analyst_agent import AIAnalystAgent
        analyst = AIAnalystAgent(config=analyst_config, dry_run=False, query=query)
        result = analyst.run()

        if result.status == "failed":
            raise HTTPException(status_code=500, detail=result.errors)

        return {
            "answer": result.data.get("answer", ""),
            "intent": result.data.get("intent", ""),
            "sql": result.data.get("sql", ""),
            "rows": result.data.get("rows_returned", 0),
            "status": result.status,
        }


    # ── Knowledge Graph ────────────────────────────────────

    @app.get("/api/knowledge-graph")
    def knowledge_graph(
        entity_type: str | None = Query(None, description="Filter by entity type"),
        limit: int = Query(100, ge=1, le=500),
    ):
        """Knowledge graph entities and relationships."""
        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()

        where = "WHERE e.entity_type_id = t.id" if not entity_type else (
            "WHERE e.entity_type_id = t.id AND t.type_name = %s"
        )
        params = [entity_type] if entity_type else []

        cursor.execute(
            f"""SELECT e.id, e.name, t.type_name as type, e.mention_count as mentions
               FROM kg_entities e, kg_entity_types t
               {where}
               ORDER BY e.mention_count DESC LIMIT %s""",
            params + [limit],
        )
        entities = [dict(r) for r in cursor.fetchall()]

        cursor.execute(
            """SELECT r.source_entity_id, r.target_entity_id,
                      r.relationship_type, r.weight
               FROM kg_relationships r
               ORDER BY r.weight DESC LIMIT %s""",
            (limit * 2,),
        )
        relationships = []
        for r in cursor.fetchall():
            relationships.append({
                "source_id": r["source_entity_id"],
                "target_id": r["target_entity_id"],
                "relationship_type": r["relationship_type"],
                "weight": r["weight"],
            })

        cursor.close()
        conn.close()
        return {"entities": entities, "relationships": relationships}

    # ── License Validation ───────────────────────────────────

    @app.post("/api/license/validate")
    def validate_license(body: dict):
        """Validate a license key and return tier + features.

        Request body: {"license_key": "PRO-XXXX-XXXX-XXXX"}
        """
        key = body.get("license_key", "").strip()
        if not key:
            raise HTTPException(status_code=400, detail="Missing license_key")

        import re
        if not re.match(r"^(PRO|ENT)-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$", key):
            return {"valid": False, "error": "Invalid key format"}

        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT tier, status, expires_at FROM user_licenses WHERE license_key = %s",
            (key,),
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if not row:
            return {"valid": False, "error": "Key not found"}

        if row["status"] != "active":
            return {"valid": False, "error": f"Key is {row['status']}"}

        from datetime import datetime, timezone
        if row["expires_at"]:
            try:
                expires = datetime.strptime(str(row["expires_at"]), "%Y-%m-%d %H:%M:%S")
                if expires < datetime.now():
                    return {"valid": False, "error": "Key expired"}
            except ValueError:
                pass

        from agents.license_agent import TIER_FEATURES, TIER_PRICING
        tier = row["tier"]
        return {
            "valid": True,
            "tier": tier,
            "features": TIER_FEATURES.get(tier, []),
            "pricing": TIER_PRICING.get(tier, {}),
        }

    @app.post("/api/license/generate")
    def generate_license_key(body: dict):
        """Generate a new license key (admin only).

        Request body: {"tier": "pro", "expiry_days": 365}
        """
        tier = body.get("tier", "pro")
        expiry_days = body.get("expiry_days", 365)

        from agents.license_agent import generate_license
        key = generate_license(tier, expiry_days)
        return {"license_key": key, "tier": tier, "expiry_days": expiry_days}

    @app.get("/api/license/metrics")
    def license_metrics():
        """Subscription and license metrics."""
        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()

        metrics = {}
        for tier in ["free", "pro", "enterprise"]:
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM user_licenses WHERE tier = %s AND status = 'active'",
                (tier,),
            )
            metrics[f"{tier}_users"] = cursor.fetchone()["cnt"]

        cursor.execute(
            "SELECT COALESCE(SUM(amount_usd), 0) as total FROM payment_events WHERE status = 'completed'"
        )
        metrics["total_revenue_usd"] = cursor.fetchone()["total"]

        cursor.close()
        conn.close()
        return metrics


# ── Main ─────────────────────────────────────────────────────

def main():
    if not HAS_FASTAPI:
        print("Error: FastAPI and uvicorn are required.")
        print("Install with: pip install fastapi uvicorn")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Startup Research Report API Server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    setup_logging()
    _logger = logging.getLogger("api_server")
    _logger.info("Starting API server on http://%s:%d", args.host, args.port)
    _logger.info("Dashboard:  http://%s:%d/", args.host, args.port)
    _logger.info("API docs:   http://%s:%d/docs", args.host, args.port)

    uvicorn.run("api_server:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
