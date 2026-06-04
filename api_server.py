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
    GET  /api/news/sentiment        — Sentiment distribution
    GET  /api/risk-scores           — ML-generated risk scores
    POST /api/score                 — Score a startup (ML + heuristic)
    POST /api/ml/predict            — Predict failure with trained ML model
    POST /api/ml/train              — Trigger ML model training
    GET  /api/ml/models             — List trained ML models
    GET  /api/survival-rates        — BLS survival rate data
    GET  /api/revival-opportunities — Revival industry data
    GET  /api/models                — List available Ollama models
    POST /api/models/pull           — Pull/download a GGUF model
    GET  /api/models/token-usage    — Ollama token usage stats
    GET  /api/alerts                — Active alerts
    POST /api/chat                  — AI Analyst natural language query
    GET  /api/pipeline-runs         — Recent pipeline execution history
    GET  /ws/live                  — WebSocket live dashboard updates
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
    from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
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

    @app.get("/api/news/sentiment")
    def news_sentiment():
        """Sentiment distribution across scored news articles."""
        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()

        cursor.execute(
            """SELECT sentiment_label, COUNT(*) as cnt, AVG(sentiment_score) as avg_score
               FROM news_articles
               WHERE sentiment_score IS NOT NULL
               GROUP BY sentiment_label"""
        )
        distribution = [dict(r) for r in cursor.fetchall()]

        cursor.execute("SELECT COUNT(*) as total FROM news_articles WHERE sentiment_score IS NOT NULL")
        total_scored = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) as total FROM news_articles")
        total_articles = cursor.fetchone()["total"]

        cursor.close()
        conn.close()
        return {
            "distribution": distribution,
            "total_scored": total_scored,
            "total_articles": total_articles,
            "coverage_pct": round(total_scored / max(total_articles, 1) * 100, 1),
        }


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
        """Score a single startup's failure risk using ML + heuristic (no DB write).

        Uses trained ML model if available, falls back to rule-based heuristic.
        Request body:
            {"sector": "EV", "funding_usd": 50000000, "country": "US", "year_founded": 2019}
        """
        from agents.risk_scorer import score_startup

        heuristic = score_startup(
            sector=body.get("sector", ""),
            funding_usd=body.get("funding_usd"),
            country=body.get("country", ""),
            region=body.get("region", ""),
            year_founded=body.get("year_founded"),
            failure_reason=body.get("failure_reason", ""),
        )

        # Try ML model for blended scoring
        try:
            from agents.ml_trainer import MLTrainer, _build_features
            trainer = MLTrainer({})
            model, model_name, features = trainer.load_best_model()
            if model is not None:
                feat_dict = _build_features(body)
                feat_vector = [[feat_dict[col] for col in features]]
                proba = model.predict_proba(feat_vector)[0]
                ml_score = proba[1] if len(proba) > 1 else proba[0]
                blended = min(1.0, max(0.0, 0.7 * ml_score + 0.3 * heuristic["risk_score"]))
                heuristic["risk_score"] = round(blended, 3)
                heuristic["model_used"] = model_name
                heuristic["ml_confidence"] = round(float(ml_score), 3)
                heuristic["scoring_method"] = "blended_ml_heuristic"
        except Exception:
            pass

        heuristic["scoring_method"] = heuristic.get("scoring_method", "heuristic_only")
        return heuristic


    # ── ML Model Management ──────────────────────────────────

    @app.get("/api/ml/models")
    def ml_models():
        """List trained ML models from the ml_models table."""
        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()
        cursor.execute(
            """SELECT model_name, model_type, model_path, trained_at, training_rows,
                      features_used, accuracy, f1_score, precision_score, recall_score, is_active
               FROM ml_models ORDER BY trained_at DESC"""
        )
        rows = [dict(r) for r in cursor.fetchall()]
        cursor.close()
        conn.close()
        return {"models": rows}

    @app.post("/api/ml/train")
    def ml_train(
        min_samples: int = Query(50, ge=10, description="Minimum training rows"),
        test_split: float = Query(0.2, ge=0.1, le=0.5, description="Train/test split ratio"),
    ):
        """Trigger ML model training on existing startup data."""
        try:
            from agents.ml_trainer import MLTrainer
            from db.connection import get_connection as _gc

            conn = _gc()
            schema.init_schema(conn)
            trainer = MLTrainer({
                "min_training_samples": min_samples,
                "test_split": test_split,
            })
            result = trainer.train(conn)
            conn.close()
            return result
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    @app.post("/api/ml/predict")
    def ml_predict(body: dict):
        """Predict failure risk for a single startup using trained ML model.

        Requires a trained model. Returns blended ML + heuristic score.
        Falls back to heuristic-only if no model is available.

        Request body:
            {"sector": "EV", "funding_usd": 50000000, "country": "US", "year_founded": 2019}
        """
        from agents.risk_scorer import score_startup

        heuristic = score_startup(
            sector=body.get("sector", ""),
            funding_usd=body.get("funding_usd"),
            country=body.get("country", ""),
            region=body.get("region", ""),
            year_founded=body.get("year_founded"),
            failure_reason=body.get("failure_reason", ""),
        )

        try:
            from agents.ml_trainer import MLTrainer, _build_features
            trainer = MLTrainer({})
            model, model_name, features = trainer.load_best_model()
            if model is None:
                return {
                    **heuristic,
                    "model_used": None,
                    "confidence": None,
                    "scoring_method": "heuristic_only",
                    "message": "No trained model available — using heuristic. Train a model via POST /api/ml/train.",
                }

            feat_dict = _build_features(body)
            feat_vector = [[feat_dict[col] for col in features]]
            proba = model.predict_proba(feat_vector)[0]
            ml_score = float(proba[1] if len(proba) > 1 else proba[0])
            blended = min(1.0, max(0.0, 0.7 * ml_score + 0.3 * heuristic["risk_score"]))

            if blended >= 0.75:
                risk_level = "critical"
            elif blended >= 0.60:
                risk_level = "high"
            elif blended >= 0.45:
                risk_level = "moderate"
            else:
                risk_level = "low"

            return {
                "risk_score": round(blended, 3),
                "risk_level": risk_level,
                "factors": heuristic["factors"],
                "recommendation": heuristic["recommendation"],
                "model_used": model_name,
                "confidence": round(ml_score, 3),
                "scoring_method": "blended_ml_heuristic",
            }
        except Exception as e:
            return {**heuristic, "scoring_method": "heuristic_only", "error": str(e)}


    # ── Ollama / LLM Model Management ─────────────────────────

    @app.get("/api/models")
    def list_ollama_models():
        """List locally available Ollama models."""
        try:
            from agents.model_manager import ModelManager
            mgr = ModelManager({})
            models = mgr.list_local_models()
            return {"models": models, "count": len(models)}
        except Exception as e:
            return {"models": [], "error": str(e)}

    @app.post("/api/models/pull")
    def pull_ollama_model(body: dict):
        """Download a GGUF model from HuggingFace via Ollama.

        Request body: {"model_name": "llama3.2:1b"}
        """
        model_name = body.get("model_name", "")
        if not model_name:
            raise HTTPException(status_code=400, detail="model_name is required")

        try:
            from agents.model_manager import ModelManager
            mgr = ModelManager({})
            success = mgr.pull_model(model_name)
            if success:
                return {"status": "success", "model": model_name, "message": f"Model '{model_name}' downloaded successfully."}
            else:
                return {"status": "failed", "model": model_name, "message": f"Failed to download model '{model_name}'."}
        except Exception as e:
            return {"status": "error", "model": model_name, "message": str(e)}

    @app.get("/api/models/token-usage")
    def token_usage():
        """Ollama token usage statistics from local tracker."""
        import json as _json
        tracker_path = Path("data/cache/ollama_token_tracker.json")

        if not tracker_path.exists():
            return {"total_tokens": 0, "total_runs": 0, "by_model": {}}

        try:
            data = _json.loads(tracker_path.read_text())
            if not isinstance(data, list):
                return {"total_tokens": 0, "total_runs": 0, "by_model": {}}

            total_tokens = sum(r.get("total_tokens", 0) for r in data)
            by_model = {}
            for r in data:
                m = r.get("model", "unknown")
                if m not in by_model:
                    by_model[m] = {"runs": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
                by_model[m]["runs"] += 1
                by_model[m]["prompt_tokens"] += r.get("prompt_tokens", 0)
                by_model[m]["completion_tokens"] += r.get("completion_tokens", 0)
                by_model[m]["total_tokens"] += r.get("total_tokens", 0)

            return {
                "total_tokens": total_tokens,
                "total_runs": len(data),
                "by_model": by_model,
            }
        except Exception as e:
            return {"total_tokens": 0, "total_runs": 0, "error": str(e)}

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


    # ── Real-time WebSocket ───────────────────────────────────

    import asyncio

    class ConnectionManager:
        """Manages active WebSocket connections for broadcasting live updates."""

        def __init__(self):
            self.active: list[WebSocket] = []

        async def connect(self, ws: WebSocket):
            await ws.accept()
            self.active.append(ws)

        def disconnect(self, ws: WebSocket):
            if ws in self.active:
                self.active.remove(ws)

        async def broadcast(self, data: dict):
            dead = []
            for ws in self.active:
                try:
                    await ws.send_json(data)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.disconnect(ws)

    ws_manager = ConnectionManager()

    @app.websocket("/ws/live")
    async def ws_live(websocket: WebSocket):
        """WebSocket endpoint for live dashboard data updates.

        Connects the client and pushes DB stats periodically.
        Events: stats_update, news_update, pipeline_status.
        """
        await ws_manager.connect(websocket)
        try:
            while True:
                # Collect current stats
                try:
                    conn = get_connection()
                    cursor = conn.cursor()

                    cursor.execute("SELECT COUNT(*) as cnt FROM failed_startups")
                    startup_count = cursor.fetchone()["cnt"]

                    cursor.execute("SELECT COUNT(*) as cnt FROM news_articles")
                    news_count = cursor.fetchone()["cnt"]

                    cursor.execute(
                        """SELECT risk_level, COUNT(*) as cnt
                           FROM startup_risk_scores
                           GROUP BY risk_level"""
                    )
                    risk_dist = {dict(r)["risk_level"]: dict(r)["cnt"] for r in cursor.fetchall()}

                    cursor.execute(
                        """SELECT sentiment_label, COUNT(*) as cnt
                           FROM news_articles
                           WHERE sentiment_score IS NOT NULL
                           GROUP BY sentiment_label"""
                    )
                    sentiment_dist = {dict(r)["sentiment_label"]: dict(r)["cnt"] for r in cursor.fetchall()}

                    cursor.execute(
                        """SELECT agent_name, status, completed_at
                           FROM agent_runs
                           ORDER BY completed_at DESC LIMIT 5"""
                    )
                    recent_runs = [dict(r) for r in cursor.fetchall()]

                    cursor.close()
                    conn.close()

                    await ws_manager.broadcast({
                        "type": "stats_update",
                        "data": {
                            "startup_count": startup_count,
                            "news_count": news_count,
                            "risk_distribution": risk_dist,
                            "sentiment_distribution": sentiment_dist,
                            "recent_pipeline_runs": recent_runs,
                        },
                    })
                except Exception:
                    pass

                await asyncio.sleep(30)  # Poll every 30 seconds

        except WebSocketDisconnect:
            ws_manager.disconnect(websocket)


    @app.get("/api/stats/summary")
    def stats_summary():
        """Lightweight stats endpoint for quick polling."""
        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as cnt FROM failed_startups")
        startup_count = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) as cnt FROM news_articles")
        news_count = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) as cnt FROM news_articles WHERE sentiment_score IS NOT NULL")
        sentiment_scored = cursor.fetchone()["cnt"]

        cursor.execute(
            """SELECT risk_level, COUNT(*) as cnt
               FROM startup_risk_scores GROUP BY risk_level"""
        )
        risk_dist = {dict(r)["risk_level"]: dict(r)["cnt"] for r in cursor.fetchall()}

        cursor.close()
        conn.close()

        return {
            "startups": startup_count,
            "news": news_count,
            "sentiment_scored": sentiment_scored,
            "risk_distribution": risk_dist,
        }

    # ── Phase 1: Opportunity Intelligence Endpoints ──────────

    @app.get("/api/opportunities")
    def list_opportunities(
        limit: int = 50,
        offset: int = 0,
        min_score: float = 0,
        trend: str | None = None,
        entity_type: str | None = None,
    ):
        """List scored opportunities sorted by composite_score descending.

        Query params:
            limit: Max results (default 50)
            offset: Pagination offset
            min_score: Filter by minimum composite_score (0-100)
            trend: Filter by trend_direction (rising, falling, stable)
            entity_type: Filter by entity_type (company, technology, market)
        """
        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()

        query = "SELECT * FROM opportunity_scores WHERE composite_score >= %s"
        params = [min_score]

        if trend:
            query += " AND trend_direction = %s"
            params.append(trend)
        if entity_type:
            query += " AND entity_type = %s"
            params.append(entity_type)

        query += " ORDER BY composite_score DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        cursor.execute(query, params)
        rows = cursor.fetchall()

        opportunities = []
        for row in rows:
            opp = dict(row)
            if opp.get("attribution_json"):
                try:
                    opp["attribution"] = json.loads(opp["attribution_json"])
                except (json.JSONDecodeError, TypeError):
                    opp["attribution"] = []
            else:
                opp["attribution"] = []
            if opp.get("signal_types_json"):
                try:
                    opp["signal_types"] = json.loads(opp["signal_types_json"])
                except (json.JSONDecodeError, TypeError):
                    opp["signal_types"] = []
            else:
                opp["signal_types"] = []
            opportunities.append(opp)

        # Get total count for pagination
        count_query = "SELECT COUNT(*) as cnt FROM opportunity_scores WHERE composite_score >= %s"
        count_params = [min_score]
        if trend:
            count_query += " AND trend_direction = %s"
            count_params.append(trend)
        if entity_type:
            count_query += " AND entity_type = %s"
            count_params.append(entity_type)
        cursor.execute(count_query, count_params)
        total = cursor.fetchone()["cnt"]

        cursor.close()
        conn.close()

        return {
            "opportunities": opportunities,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    @app.get("/api/opportunities/{entity_name}")
    def get_opportunity(entity_name: str):
        """Get detailed opportunity data for a specific entity."""
        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM opportunity_scores WHERE entity_name = %s",
            (entity_name,),
        )
        row = cursor.fetchone()

        if not row:
            cursor.close()
            conn.close()
            return {"error": f"Entity '{entity_name}' not found"}, 404

        opp = dict(row)
        if opp.get("attribution_json"):
            try:
                opp["attribution"] = json.loads(opp["attribution_json"])
            except (json.JSONDecodeError, TypeError):
                opp["attribution"] = []
        if opp.get("signal_weights_json"):
            try:
                opp["signal_weights"] = json.loads(opp["signal_weights_json"])
            except (json.JSONDecodeError, TypeError):
                opp["signal_weights"] = []

        # Get recent signals for this entity
        cursor.execute(
            """SELECT signal_type, title, source_url, published_at
               FROM raw_signals
               WHERE entity_name = %s
               ORDER BY published_at DESC LIMIT 20""",
            (entity_name,),
        )
        opp["recent_signals"] = [dict(r) for r in cursor.fetchall()]

        cursor.close()
        conn.close()
        return opp

    @app.get("/api/signals")
    def list_signals(
        limit: int = 50,
        offset: int = 0,
        signal_type: str | None = None,
        entity_name: str | None = None,
        processed: int | None = None,
    ):
        """List raw signals with filtering.

        Query params:
            limit: Max results
            signal_type: Filter by signal type (sec_filing, job_posting_spike, etc.)
            entity_name: Filter by entity name
            processed: Filter by processed status (0=pending, 1=enriched, 2=scored)
        """
        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()

        query = "SELECT * FROM raw_signals WHERE 1=1"
        params = []

        if signal_type:
            query += " AND signal_type = %s"
            params.append(signal_type)
        if entity_name:
            query += " AND entity_name = %s"
            params.append(entity_name)
        if processed is not None:
            query += " AND processed = %s"
            params.append(processed)

        query += " ORDER BY collected_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        cursor.execute(query, params)
        signals = [dict(r) for r in cursor.fetchall()]

        cursor.close()
        conn.close()
        return {"signals": signals, "limit": limit, "offset": offset}

    @app.get("/api/signals/stats")
    def signal_stats():
        """Get statistics about signal collection."""
        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()

        stats = {}

        # Signal counts by type
        cursor.execute(
            "SELECT signal_type, COUNT(*) as cnt FROM raw_signals GROUP BY signal_type ORDER BY cnt DESC"
        )
        stats["by_type"] = {dict(r)["signal_type"]: dict(r)["cnt"] for r in cursor.fetchall()}

        # Processing status
        cursor.execute(
            "SELECT processed, COUNT(*) as cnt FROM raw_signals GROUP BY processed"
        )
        stats["processing_status"] = {
            str(dict(r)["processed"]): dict(r)["cnt"] for r in cursor.fetchall()
        }

        # Top entities by signal count
        cursor.execute(
            """SELECT entity_name, COUNT(*) as cnt, COUNT(DISTINCT signal_type) as types
               FROM raw_signals
               WHERE entity_name IS NOT NULL AND entity_name != ''
               GROUP BY entity_name
               ORDER BY cnt DESC LIMIT 20"""
        )
        stats["top_entities"] = [dict(r) for r in cursor.fetchall()]

        # Opportunity score distribution
        cursor.execute(
            """SELECT
                 COUNT(*) as total,
                 AVG(composite_score) as avg_score,
                 MAX(composite_score) as max_score,
                 SUM(CASE WHEN composite_score >= 70 THEN 1 ELSE 0 END) as high_value
               FROM opportunity_scores"""
        )
        row = cursor.fetchone()
        stats["opportunity_summary"] = dict(row) if row else {}

        cursor.close()
        conn.close()
        return stats


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
