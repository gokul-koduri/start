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
    GET  /api/search                — Unified semantic/fulltext/hybrid search
    GET  /api/entities/{name}/connections — Knowledge graph connections
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
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

    # CORS — allow dashboard to call API (restrict in production via CORS_ORIGIN env var)
    _cors_origin = os.environ.get("CORS_ORIGIN", "*")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[_cors_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Security Headers (T-060) ──
    from starlette.middleware.base import BaseHTTPMiddleware

    class SecurityHeadersMiddleware(BaseHTTPMiddleware):
        """Add security headers to all responses."""
        async def dispatch(self, request, call_next):
            response = await call_next(request)
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "connect-src 'self' ws: wss:"
            )
            if request.url.hostname not in ("localhost", "127.0.0.1"):
                response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            return response

    app.add_middleware(SecurityHeadersMiddleware)

    # ── Input Sanitization (T-010) ──
    import html
    from starlette.requests import Request

    class InputSanitizerMiddleware(BaseHTTPMiddleware):
        """Reject oversized payloads and strip HTML from query params."""
        MAX_BODY_SIZE = 1_000_000  # 1 MB

        async def dispatch(self, request: Request, call_next):
            # Block oversized request bodies
            if request.method in ("POST", "PUT", "PATCH"):
                content_length = request.headers.get("content-length")
                if content_length and int(content_length) > self.MAX_BODY_SIZE:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": "Request body too large (max 1 MB)"},
                    )
            # Sanitize query parameters (strip HTML tags)
            for key in list(request.query_params.keys()):
                val = request.query_params[key]
                sanitized = html.escape(val)
                if sanitized != val:
                    return JSONResponse(
                        status_code=400,
                        content={"detail": f"HTML detected in query parameter '{key}'"},
                    )
            return await call_next(request)

    app.add_middleware(InputSanitizerMiddleware)

    # ── Rate Limiting (T-059) ──
    try:
        from slowapi import Limiter, _rate_limit_exceeded_handler
        from slowapi.util import get_remote_address
        from slowapi.errors import RateLimitExceeded
        from slowapi.middleware import SlowAPIMiddleware

        _limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
        app.state.limiter = _limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        app.add_middleware(SlowAPIMiddleware)
        logging.getLogger("api_server").info("Rate limiting enabled: 60 req/min per IP")
    except ImportError:
        logging.getLogger("api_server").warning("slowapi not installed — rate limiting disabled")

    # ── Sentry/GlitchTip integration (optional, env-driven) (T-048) ──
    _sentry_dsn = os.environ.get("SENTRY_DSN", "")
    if _sentry_dsn:
        try:
            import sentry_sdk
            sentry_sdk.init(dsn=_sentry_dsn, traces_sample_rate=0.1)
            _logger.info("Sentry/GlitchTip error tracking enabled")
        except ImportError:
            _logger.warning("SENTRY_DSN set but sentry-sdk not installed. pip install sentry-sdk")

    # ── Global exception handler — logs to error_log table (T-047) ──
    import traceback as _traceback
    import hashlib as _hashlib

    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        """Catch all unhandled exceptions, log to error_log table, return JSON."""
        _logger.error("Unhandled exception on %s: %s", request.url.path, exc)

        # Log to error_log table (best-effort)
        try:
            conn = get_connection()
            schema.init_schema(conn)
            tb = _traceback.format_exc()
            fp = _hashlib.sha256(
                f"{type(exc).__name__}:{str(exc)[:100]}".encode()
            ).hexdigest()[:16]
            with conn.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO error_log
                       (error_type, error_message, traceback_text, endpoint,
                        request_method, request_path, severity, fingerprint)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        type(exc).__name__,
                        str(exc)[:2000],
                        tb[:5000],
                        "api_server",
                        request.method,
                        str(request.url.path)[:500],
                        "error",
                        fp,
                    ),
                )
            conn.commit()
            conn.close()
        except Exception:
            pass  # Never fail the error handler itself

        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "error_type": type(exc).__name__},
        )

    # ── API v2 Routers ─────────────────────────────────────────
    try:
        from api.v2.opportunities import router as v2_opportunities_router
        from api.v2.signals import router as v2_signals_router
        from api.v2.webhooks import router as v2_webhooks_router
        from api.v2.export import router as v2_export_router
        from api.v2.feedback import router as v2_feedback_router
        app.include_router(v2_opportunities_router, prefix="/api")
        app.include_router(v2_signals_router, prefix="/api")
        app.include_router(v2_webhooks_router, prefix="/api")
        app.include_router(v2_export_router, prefix="/api")
        app.include_router(v2_feedback_router, prefix="/api")
    except ImportError as e:
        _logger.warning("Could not import API v2 routers: %s", e)

    # Auth router (T-054, T-055, T-057)
    try:
        from api.v2.auth import router as v2_auth_router
        app.include_router(v2_auth_router, prefix="/api")
    except ImportError as e:
        logging.getLogger("api_server").warning("Could not import auth router: %s", e)


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


    # ── Collection Status (Sprint 2) ──────────────────────

    @app.get("/api/collection/status")
    def collection_status(
        collector: str | None = Query(None, description="Filter by collector name"),
    ):
        """Show last run status for each collector."""
        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()

        if collector:
            cursor.execute(
                "SELECT * FROM collection_runs WHERE collector_name = %s "
                "ORDER BY started_at DESC LIMIT 1",
                (collector,),
            )
            rows = cursor.fetchall()
        else:
            # Get latest run per collector
            cursor.execute(
                "SELECT cr.* FROM collection_runs cr "
                "INNER JOIN ("
                "  SELECT collector_name, MAX(started_at) as max_started "
                "  FROM collection_runs GROUP BY collector_name"
                ") latest ON cr.collector_name = latest.collector_name "
                "AND cr.started_at = latest.max_started "
                "ORDER BY cr.started_at DESC"
            )
            rows = cursor.fetchall()

        cursor.close()
        conn.close()

        # Load scheduler config for next-run estimates
        sched_config = load_config().get("scheduler", {})
        groups = sched_config.get("groups", {})
        intervals = {}
        for group_def in groups.values():
            interval = group_def.get("interval_minutes", 360)
            for name in group_def.get("collectors", []):
                intervals[name] = interval

        statuses = []
        for row in rows:
            entry = dict(row)
            name = entry.get("collector_name", "")
            if name in intervals:
                entry["interval_minutes"] = intervals[name]
            statuses.append(entry)

        return {"collectors": statuses, "count": len(statuses)}


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
                ORDER BY funding_raised_usd DESC
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
        from agents.risk_scorer_agent import score_startup

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
            from agents.ml_trainer_agent import MLTrainer, _build_features
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
            from agents.ml_trainer_agent import MLTrainer
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
        from agents.risk_scorer_agent import score_startup

        heuristic = score_startup(
            sector=body.get("sector", ""),
            funding_usd=body.get("funding_usd"),
            country=body.get("country", ""),
            region=body.get("region", ""),
            year_founded=body.get("year_founded"),
            failure_reason=body.get("failure_reason", ""),
        )

        try:
            from agents.ml_trainer_agent import MLTrainer, _build_features
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
            from agents.model_manager_agent import ModelManager
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
            from agents.model_manager_agent import ModelManager
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


    # ── Alert Preferences ──────────────────────────────────────

    @app.get("/api/alerts/preferences")
    def get_alert_preferences():
        """Get current alert notification preferences."""
        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM alert_preferences ORDER BY updated_at DESC LIMIT 1")
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            prefs = dict(row)
            # Convert INT booleans to actual booleans
            for key in ("email_enabled", "slack_enabled", "discord_enabled", "webhook_enabled"):
                prefs[key] = bool(prefs.get(key, 1))
            return prefs
        # Return defaults
        return {
            "email_enabled": True, "slack_enabled": True,
            "discord_enabled": True, "webhook_enabled": True,
            "min_score_threshold": 80.0, "max_alerts_per_hour": 20,
            "quiet_hours_start": None, "quiet_hours_end": None,
        }

    @app.put("/api/alerts/preferences")
    def update_alert_preferences(body: dict):
        """Update alert notification preferences.

        Request body (all fields optional):
            {
                "email_enabled": true,
                "slack_enabled": true,
                "min_score_threshold": 85.0,
                "quiet_hours_start": "22:00",
                "quiet_hours_end": "08:00",
                "max_alerts_per_hour": 10
            }
        """
        allowed = {
            "email_enabled", "slack_enabled", "discord_enabled", "webhook_enabled",
            "min_score_threshold", "quiet_hours_start", "quiet_hours_end",
            "max_alerts_per_hour",
        }
        updates = {k: v for k, v in body.items() if k in allowed}
        if not updates:
            return {"status": "no_changes", "message": "No valid fields to update"}

        # Convert booleans to ints for MySQL
        for key in ("email_enabled", "slack_enabled", "discord_enabled", "webhook_enabled"):
            if key in updates and isinstance(updates[key], bool):
                updates[key] = int(updates[key])

        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()

        # Check if preferences exist
        cursor.execute("SELECT id FROM alert_preferences ORDER BY updated_at DESC LIMIT 1")
        existing = cursor.fetchone()

        if existing:
            set_clause = ", ".join(f"{k} = %s" for k in updates)
            values = list(updates.values()) + [existing["id"]]
            cursor.execute(f"UPDATE alert_preferences SET {set_clause} WHERE id = %s", values)
        else:
            cols = ", ".join(updates.keys())
            placeholders = ", ".join(["%s"] * len(updates))
            cursor.execute(f"INSERT INTO alert_preferences ({cols}) VALUES ({placeholders})", list(updates.values()))

        conn.commit()
        cursor.close()
        conn.close()
        return {"status": "updated", "preferences": updates}

    @app.get("/api/alerts/dead-letters")
    def list_dead_letters(limit: int = Query(20, ge=1, le=100)):
        """List failed alerts in the dead letter queue."""
        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()
        try:
            cursor.execute(
                """SELECT id, alert_type, entity_name, composite_score,
                          error_message, attempts, last_attempt_at, created_at
                   FROM alert_dead_letters
                   ORDER BY created_at DESC LIMIT %s""",
                (limit,),
            )
            rows = [dict(r) for r in cursor.fetchall()]
        except Exception:
            rows = []  # Table may not exist yet
        cursor.close()
        conn.close()
        return {"results": rows, "count": len(rows)}

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

        answer = result.data.get("answer", "")
        _log_chat("api", query, answer)
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

    # ── Phase 2: Unified Search ────────────────────────────

    def _log_query(query: str, search_mode: str, results_count: int):
        """Log search query to query_log table (best-effort, never fails)."""
        try:
            conn = get_connection()
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO query_log (query, search_mode, results_count, source) "
                    "VALUES (%s, %s, %s, %s)",
                    (query[:500], search_mode, results_count, "api"),
                )
            conn.commit()
            conn.close()
        except Exception:
            pass  # Never break search on logging failure

    def _log_chat(session_id: str, user_message: str, ai_response: str, response_ms: int = 0):
        """Log chat conversation to chat_log table (best-effort)."""
        try:
            conn = get_connection()
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO chat_log (session_id, user_message, ai_response, response_ms) "
                    "VALUES (%s, %s, %s, %s)",
                    (session_id, user_message, ai_response[:5000] if ai_response else None, response_ms),
                )
            conn.commit()
            conn.close()
        except Exception:
            pass

    @app.get("/api/search")
    def unified_search(
        q: str = Query(..., description="Search query"),
        mode: str = Query("hybrid", description="Search mode: semantic, fulltext, hybrid"),
        entity_type: str | None = Query(None, description="Filter by entity_type"),
        signal_type: str | None = Query(None, description="Filter by signal_type"),
        limit: int = Query(20, ge=1, le=100),
    ):
        """Unified search across vector and full-text indexes.

        Modes:
            semantic — Qdrant vector search (requires embeddings + Qdrant)
            fulltext — Elasticsearch BM25 search
            hybrid — Blend of both (default)

        Returns ranked results with scores and highlights.
        Falls back gracefully if backends are unavailable.
        """
        if mode not in ("semantic", "fulltext", "hybrid"):
            raise HTTPException(status_code=400, detail="mode must be semantic, fulltext, or hybrid")

        # Build filter dict
        filters = {}
        if entity_type:
            filters["entity_type"] = entity_type
        if signal_type:
            filters["signal_type"] = signal_type

        results = []
        search_mode_used = mode

        try:
            if mode in ("semantic", "hybrid"):
                from db.vector_store import VectorStore
                from nlp.embedding_generator import EmbeddingGenerator

                vs_config = {}
                vector_store = VectorStore(vs_config)
                vector_store.connect()

                embedder = EmbeddingGenerator()
                embedder.load()

                if vector_store.is_connected:
                    vector_results = vector_store.search_by_text(
                        q, embedder, limit=limit, filters=filters if filters else None,
                    )
                    results.extend([r.to_dict() for r in vector_results])

                    if mode == "semantic":
                        return {
                            "query": q,
                            "mode": "semantic",
                            "total": len(results),
                            "results": results,
                        }
                else:
                    search_mode_used = "fulltext"

        except ImportError:
            search_mode_used = "fulltext"
        except Exception as e:
            search_mode_used = "fulltext"

        # Full-text search (Elasticsearch)
        try:
            from db.search_index import SearchIndex
            search_index = SearchIndex({})
            search_index.connect()

            if search_index.is_connected:
                es_results = search_index.search(q, limit=limit, filters=filters if filters else None)
                for r in es_results:
                    results.append({
                        "id": r.id,
                        "score": r.score,
                        "source": r.source,
                        "highlights": r.highlights,
                        "search_engine": "elasticsearch",
                    })
        except ImportError:
            pass
        except Exception:
            pass

        if not results:
            return {
                "query": q,
                "mode": mode,
                "mode_used": search_mode_used,
                "total": 0,
                "results": [],
                "message": "No search backends available. Install qdrant-client and/or elasticsearch.",
            }

        # Deduplicate by ID and sort by score
        seen = {}
        for r in results:
            rid = r.get("id", "")
            if rid not in seen or r.get("score", 0) > seen[rid].get("score", 0):
                seen[rid] = r
        results = sorted(seen.values(), key=lambda x: x.get("score", 0), reverse=True)[:limit]

        _log_query(q, search_mode_used, len(results))
        return {
            "query": q,
            "mode": mode,
            "mode_used": search_mode_used,
            "total": len(results),
            "results": results,
        }


    # ── Phase 2: Entity Connections (Graph Traversal) ────────

    @app.get("/api/entities/{entity_name}/connections")
    def entity_connections(
        entity_name: str,
        depth: int = Query(1, ge=1, le=3, description="Graph traversal depth (1-3)"),
        relationship_type: str | None = Query(None, description="Filter by relationship type"),
        limit: int = Query(50, ge=1, le=200, description="Max nodes to return"),
    ):
        """Get knowledge graph connections for an entity.

        Traverses the knowledge graph from the given entity name, returning
        nodes and edges suitable for visualization (D3.js, G6, Cytoscape).

        Response format:
            nodes: [{id, name, type, mentions}]
            edges: [{source, target, relationship_type, weight}]
        """
        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()

        # Resolve entity by name (check aliases too)
        entity_id = None
        cursor.execute(
            """SELECT e.id, e.name, t.type_name, e.mention_count
               FROM kg_entities e, kg_entity_types t
               WHERE e.entity_type_id = t.id AND e.name = %s""",
            (entity_name,),
        )
        row = cursor.fetchone()
        if not row:
            # Try alias lookup
            try:
                cursor.execute(
                    """SELECT canonical_entity_id FROM kg_entity_aliases
                       WHERE alias_name = %s OR normalized_alias = %s""",
                    (entity_name, entity_name.lower().replace(" ", "")),
                )
                alias_row = cursor.fetchone()
                if alias_row:
                    cursor.execute("SELECT id, name, mention_count FROM kg_entities WHERE id = %s", (alias_row["canonical_entity_id"],))
                    row = cursor.fetchone()
            except Exception:
                pass

        if not row:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail=f"Entity '{entity_name}' not found in knowledge graph")

        entity_id = row["id"]

        # BFS traversal
        nodes = {}  # id -> node dict
        edges = []

        def add_node(nid, name, ntype, mentions):
            if nid not in nodes:
                nodes[nid] = {
                    "id": nid,
                    "name": name,
                    "type": ntype,
                    "mentions": mentions or 0,
                }

        # Add the starting entity
        add_node(entity_id, row["name"], row.get("type_name", "unknown"), row.get("mention_count"))

        visited = {entity_id}
        frontier = [entity_id]

        for d in range(depth):
            if not frontier or len(nodes) >= limit:
                break

            next_frontier = []
            for fid in frontier:
                # Outgoing relationships
                rel_query = """SELECT r.target_entity_id, r.relationship_type, r.weight,
                                      e2.name, t.type_name, e2.mention_count
                               FROM kg_relationships r
                               JOIN kg_entities e2 ON r.target_entity_id = e2.id
                               JOIN kg_entity_types t ON e2.entity_type_id = t.id
                               WHERE r.source_entity_id = %s"""
                rel_params = [fid]
                if relationship_type:
                    rel_query += " AND r.relationship_type = %s"
                    rel_params.append(relationship_type)
                cursor.execute(rel_query, rel_params)

                for r in cursor.fetchall():
                    tid = r["target_entity_id"]
                    if tid not in visited and len(nodes) < limit:
                        visited.add(tid)
                        next_frontier.append(tid)
                        add_node(tid, r["name"], r["type_name"], r["mention_count"])
                    edges.append({
                        "source": fid,
                        "target": tid,
                        "relationship_type": r["relationship_type"],
                        "weight": r["weight"],
                    })

                # Incoming relationships
                rel_query = """SELECT r.source_entity_id, r.relationship_type, r.weight,
                                      e2.name, t.type_name, e2.mention_count
                               FROM kg_relationships r
                               JOIN kg_entities e2 ON r.source_entity_id = e2.id
                               JOIN kg_entity_types t ON e2.entity_type_id = t.id
                               WHERE r.target_entity_id = %s"""
                rel_params = [fid]
                if relationship_type:
                    rel_query += " AND r.relationship_type = %s"
                    rel_params.append(relationship_type)
                cursor.execute(rel_query, rel_params)

                for r in cursor.fetchall():
                    sid = r["source_entity_id"]
                    if sid not in visited and len(nodes) < limit:
                        visited.add(sid)
                        next_frontier.append(sid)
                        add_node(sid, r["name"], r["type_name"], r["mention_count"])
                    # Avoid duplicate edge (undirected)
                    if not any(e["source"] == sid and e["target"] == fid for e in edges):
                        edges.append({
                            "source": sid,
                            "target": fid,
                            "relationship_type": r["relationship_type"],
                            "weight": r["weight"],
                        })

            frontier = next_frontier

        cursor.close()
        conn.close()

        return {
            "entity_name": entity_name,
            "entity_id": entity_id,
            "depth": depth,
            "nodes": list(nodes.values()),
            "edges": edges,
            "total_nodes": len(nodes),
            "total_edges": len(edges),
        }


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
        """Manages active WebSocket connections for broadcasting live updates.

        Features:
            - Connection tracking with metadata (connected_at, client_id, last_ping)
            - Heartbeat: server sends ping every 30s, expects pong within 10s
            - Broadcasting to all clients or filtered subsets
        """

        def __init__(self):
            self.active: dict[WebSocket, dict] = {}
            self._started_at = datetime.now(timezone.utc)

        async def connect(self, ws: WebSocket, client_id: str | None = None):
            await ws.accept()
            self.active[ws] = {
                "connected_at": datetime.now(timezone.utc),
                "client_id": client_id,
                "last_ping": datetime.now(timezone.utc),
                "last_pong": datetime.now(timezone.utc),
            }

        def disconnect(self, ws: WebSocket):
            self.active.pop(ws, None)

        async def broadcast(self, data: dict):
            dead = []
            for ws in self.active:
                try:
                    await ws.send_json(data)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.disconnect(ws)

        async def send_heartbeat(self):
            """Send ping to all connections, check for stale ones."""
            now = datetime.now(timezone.utc)
            dead = []
            for ws, info in list(self.active.items()):
                # Check if we received a pong recently (10 second tolerance)
                pong_age = (now - info.get("last_pong", now)).total_seconds()
                if pong_age > 40:  # Missed 2+ heartbeats
                    dead.append(ws)
                    continue
                try:
                    await ws.send_json({"type": "ping"})
                    info["last_ping"] = now
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.disconnect(ws)

        def handle_pong(self, ws: WebSocket):
            """Record a pong response from a client."""
            if ws in self.active:
                self.active[ws]["last_pong"] = datetime.now(timezone.utc)

        @property
        def connection_count(self) -> int:
            return len(self.active)

        def get_status(self) -> dict:
            """Return connection manager status for monitoring."""
            now = datetime.now(timezone.utc)
            uptime = (now - self._started_at).total_seconds()
            return {
                "active_connections": self.connection_count,
                "uptime_seconds": int(uptime),
                "connections": [
                    {
                        "client_id": info.get("client_id"),
                        "connected_at": info["connected_at"].isoformat(),
                        "connected_for_seconds": int((now - info["connected_at"]).total_seconds()),
                    }
                    for info in self.active.values()
                ],
            }

    ws_manager = ConnectionManager()

    # Background task: heartbeat loop
    _heartbeat_task = None

    async def _heartbeat_loop():
        """Send periodic heartbeats to all WebSocket connections."""
        while True:
            await asyncio.sleep(30)
            try:
                await ws_manager.send_heartbeat()
            except Exception:
                pass

    # Background task: score push loop
    _score_push_task = None
    _score_queue: asyncio.Queue | None = None

    def _kafka_score_reader():
        """Sync thread: read from Kafka scores.updates and push to async queue."""
        import threading
        topic = "scores.updates"
        try:
            from kafka import KafkaConsumer
            consumer = KafkaConsumer(
                topic,
                bootstrap_servers=os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").split(","),
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                auto_offset_reset="latest",
                consumer_timeout_ms=5000,
            )
            _logger.info("Score push: Kafka consumer connected to %s", topic)
            while True:
                messages = consumer.poll(timeout_ms=3000)
                for tp, msgs in messages.items():
                    for msg in msgs:
                        if _score_queue is not None:
                            _score_queue.put_nowait(msg.value)
            consumer.close()
        except ImportError:
            _logger.info("Score push: kafka-python not installed, using DB poll fallback")
        except Exception as e:
            _logger.warning("Score push: Kafka consumer failed: %s", e)

    async def _score_push_loop():
        """Background task: push score updates to WebSocket clients.

        Tries Kafka first, falls back to DB polling.
        """
        global _score_queue
        _score_queue = asyncio.Queue()

        # Start Kafka reader in a thread
        import threading
        kafka_thread = threading.Thread(target=_kafka_score_reader, daemon=True)
        kafka_thread.start()

        last_seen_ids: set[int] = set()

        while True:
            # Check for Kafka messages
            try:
                while not _score_queue.empty():
                    score_data = _score_queue.get_nowait()
                    await ws_manager.broadcast({
                        "type": "score_update",
                        "data": score_data,
                    })
                    _logger.debug("Pushed score update: %s (%.1f)",
                                  score_data.get("entity_name", ""),
                                  score_data.get("composite_score", 0))
            except Exception:
                pass

            # DB poll fallback: check for recently updated scores
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    """SELECT id, entity_name, entity_type, composite_score,
                              signal_count, trend_direction, attribution_json
                       FROM opportunity_scores
                       WHERE last_updated >= DATE_SUB(NOW(), INTERVAL 60 SECOND)
                       ORDER BY last_updated DESC LIMIT 20"""
                )
                rows = cursor.fetchall()
                cursor.close()
                conn.close()

                for row in rows:
                    if row["id"] not in last_seen_ids:
                        last_seen_ids.add(row["id"])
                        await ws_manager.broadcast({
                            "type": "score_update",
                            "data": {
                                "entity_name": row["entity_name"],
                                "entity_type": row["entity_type"],
                                "composite_score": row["composite_score"],
                                "signal_count": row["signal_count"],
                                "trend_direction": row["trend_direction"],
                            },
                        })
                        # Also try to broadcast score delta
                        try:
                            conn2 = get_connection()
                            cursor2 = conn2.cursor()
                            cursor2.execute(
                                """SELECT entity_name, entity_type, old_score, new_score,
                                          delta, trend_previous, trend_current, signal_breakdown_json
                                   FROM score_deltas
                                   WHERE entity_name = %s AND entity_type = %s
                                   ORDER BY detected_at DESC LIMIT 1""",
                                (row["entity_name"], row["entity_type"]),
                            )
                            delta_row = cursor2.fetchone()
                            cursor2.close()
                            conn2.close()
                            if delta_row:
                                import json as _json
                                await ws_manager.broadcast({
                                    "type": "score_delta",
                                    "data": {
                                        "entity_name": delta_row["entity_name"],
                                        "old_score": delta_row["old_score"],
                                        "new_score": delta_row["new_score"],
                                        "change": delta_row["delta"],
                                        "trend_previous": delta_row["trend_previous"],
                                        "trend_current": delta_row["trend_current"],
                                        "signal_deltas": _json.loads(delta_row.get("signal_breakdown_json", "{}")),
                                    },
                                })
                        except Exception:
                            pass

                # Trim seen IDs
                if len(last_seen_ids) > 500:
                    last_seen_ids = set(list(last_seen_ids)[-200:])

            except Exception:
                pass

            await asyncio.sleep(5)  # Check every 5 seconds

    @app.websocket("/ws/live")
    async def ws_live(websocket: WebSocket):
        """WebSocket endpoint for live dashboard data updates.

        Connects the client and pushes:
        - stats_update: DB statistics every 30 seconds
        - score_update: Real-time score changes (from Kafka or DB poll)
        - score_delta: Score change details with breakdown
        - ping/pong: Heartbeat every 30 seconds
        """
        global _heartbeat_task, _score_push_task

        await ws_manager.connect(websocket)

        # Start background tasks on first connection
        if _heartbeat_task is None:
            _heartbeat_task = asyncio.create_task(_heartbeat_loop())
        if _score_push_task is None:
            _score_push_task = asyncio.create_task(_score_push_loop())

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

                # Wait for incoming messages (pong, subscribe) or timeout for stats poll
                try:
                    data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
                    if isinstance(data, dict) and data.get("type") == "pong":
                        ws_manager.handle_pong(websocket)
                except asyncio.TimeoutError:
                    pass  # Normal — just means no client message, continue to next stats poll
                except Exception:
                    break  # Connection lost

        except WebSocketDisconnect:
            ws_manager.disconnect(websocket)
        finally:
            ws_manager.disconnect(websocket)

    # WebSocket status endpoint
    @app.get("/api/ws/status")
    def ws_status():
        """WebSocket connection manager status."""
        return ws_manager.get_status()


    # ── Score Deltas ────────────────────────────────────────────

    @app.get("/api/scores/deltas")
    def list_score_deltas(
        limit: int = Query(20, ge=1, le=100),
        entity: str | None = None,
        hours: int = Query(1, ge=1, le=72),
    ):
        """Recent score changes with delta breakdown.

        Query params:
            limit: Max results (default 20)
            entity: Filter by entity name
            hours: Look back N hours (default 1)
        """
        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()
        try:
            if entity:
                cursor.execute(
                    """SELECT id, entity_name, entity_type, old_score, new_score,
                              delta, trend_previous, trend_current, signal_breakdown_json,
                              detected_at
                       FROM score_deltas
                       WHERE entity_name = %s AND detected_at >= DATE_SUB(NOW(), INTERVAL %s HOUR)
                       ORDER BY detected_at DESC LIMIT %s""",
                    (entity, hours, limit),
                )
            else:
                cursor.execute(
                    """SELECT id, entity_name, entity_type, old_score, new_score,
                              delta, trend_previous, trend_current, signal_breakdown_json,
                              detected_at
                       FROM score_deltas
                       WHERE detected_at >= DATE_SUB(NOW(), INTERVAL %s HOUR)
                       ORDER BY detected_at DESC LIMIT %s""",
                    (hours, limit),
                )
            rows = [dict(r) for r in cursor.fetchall()]
            # Parse signal_breakdown_json
            for row in rows:
                try:
                    row["signal_deltas"] = json.loads(row.pop("signal_breakdown_json", "{}") or "{}")
                except (json.JSONDecodeError, TypeError):
                    row["signal_deltas"] = {}
        except Exception:
            rows = []
        cursor.close()
        conn.close()
        return {"results": rows, "count": len(rows)}

    # ── Score Accuracy ──────────────────────────────────────────

    @app.get("/api/score/accuracy")
    def score_accuracy(
        weeks: int = Query(4, ge=1, le=52),
        run_validation_now: bool = Query(False, alias="run"),
    ):
        """Scoring accuracy metrics with weekly trend.

        Query params:
            weeks: Look back N weeks for accuracy history (default 4)
            run: If true, run validation now and store result
        """
        # Optionally run validation and persist
        if run_validation_now:
            try:
                from scoring.validate import run_validation
                report = run_validation()
                conn = get_connection()
                schema.init_schema(conn)
                cursor = conn.cursor()
                weights_json = json.dumps({k: v for k, v in report.weights_used.items()})
                cursor.execute(
                    """INSERT INTO score_accuracy_runs
                       (accuracy_pct, total_tested, correct,
                        true_positives, false_positives, true_negatives, false_negatives,
                        precision_pct, recall_pct, f1_score, threshold_used, weights_snapshot, run_notes)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (report.accuracy, report.total, report.correct,
                     report.true_positives, report.false_positives,
                     report.true_negatives, report.false_negatives,
                     report.precision, report.recall, report.f1_score,
                     report.threshold, weights_json,
                     f"Auto-run via API: {report.correct}/{report.total} correct"),
                )
                conn.commit()
                cursor.close()
                conn.close()
            except Exception as e:
                _logger.warning("Score accuracy run failed: %s", e)

        # Fetch accuracy history
        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()
        try:
            cursor.execute(
                """SELECT id, accuracy_pct, total_tested, correct,
                          true_positives, false_positives, true_negatives, false_negatives,
                          precision_pct, recall_pct, f1_score, threshold_used, run_at
                   FROM score_accuracy_runs
                   WHERE run_at >= DATE_SUB(NOW(), INTERVAL %s WEEK)
                   ORDER BY run_at DESC""",
                (weeks,),
            )
            history = [dict(r) for r in cursor.fetchall()]
        except Exception:
            history = []

        # Also return latest validation result (always available)
        latest = None
        if history:
            latest = history[0]

        cursor.close()
        conn.close()
        return {
            "latest": latest,
            "history": history,
            "total_runs": len(history),
            "weeks_covered": weeks,
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


    # ── In-Memory Cache ───────────────────────────────────
    # Simple TTL cache to avoid repeated COUNT(*) queries on stats endpoints.
    # Falls back gracefully — no external Redis required for basic operation.

    _cache: dict[str, tuple] = {}  # key -> (json_bytes, expiry_timestamp)

    def _cache_get(key: str, ttl: int = 60) -> dict | None:
        """Return cached value if still fresh, else None."""
        import time
        entry = _cache.get(key)
        if entry and entry[1] > time.time():
            return entry[0]
        _cache.pop(key, None)
        return None

    def _cache_set(key: str, value: dict, ttl: int = 60):
        import time
        _cache[key] = (value, time.time() + ttl)

    # ── Redis-Backed Cache (T-050) ─────────────────────────
    # Two-tier cache: Redis first (shared across workers), then in-memory fallback.

    _REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    def _redis_cache_get(key: str) -> dict | None:
        """Try Redis first, fall back to in-memory cache."""
        try:
            import redis as _redis
            r = _redis.from_url(_REDIS_URL, socket_connect_timeout=2, decode_responses=True)
            raw = r.get(f"api:{key}")
            r.close()
            if raw:
                import json as _json
                return _json.loads(raw)
        except Exception:
            pass
        # Fallback to in-memory
        return _cache_get(key)

    def _redis_cache_set(key: str, value: dict, ttl: int = 60):
        """Set both Redis and in-memory cache."""
        _cache_set(key, value, ttl)
        try:
            import redis as _redis
            import json as _json
            r = _redis.from_url(_REDIS_URL, socket_connect_timeout=2, decode_responses=True)
            r.setex(f"api:{key}", ttl, _json.dumps(value, default=str))
            r.close()
        except Exception:
            pass

    def _redis_cache_invalidate(pattern: str = "api:*"):
        """Clear matching keys from both Redis and in-memory cache."""
        _cache.clear()
        try:
            import redis as _redis
            r = _redis.from_url(_REDIS_URL, socket_connect_timeout=2, decode_responses=True)
            for key in r.scan_iter(pattern):
                r.delete(key)
            r.close()
        except Exception:
            pass

    # ── Cached Stats Endpoints ───────────────────────────

    @app.get("/api/stats/summary")
    def stats_summary():
        """Lightweight stats endpoint for quick polling (Redis-backed, 60s TTL)."""
        CACHED_KEY = "stats:summary"
        cached = _redis_cache_get(CACHED_KEY)
        if cached:
            return cached

        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as cnt FROM failed_startups")
        startup_count = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) as cnt FROM news_articles")
        news_count = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) as cnt FROM news_articles WHERE sentiment_score IS NOT NULL")
        sentiment_scored = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) as cnt FROM opportunity_scores WHERE composite_score >= 60")
        opportunities_count = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) as cnt FROM raw_signals WHERE DATE(collected_at) = CURDATE()")
        signals_today = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) as cnt FROM raw_signals")
        total_signals = cursor.fetchone()["cnt"]

        cursor.execute(
            """SELECT risk_level, COUNT(*) as cnt
               FROM startup_risk_scores GROUP BY risk_level"""
        )
        risk_dist = {dict(r)["risk_level"]: dict(r)["cnt"] for r in cursor.fetchall()}

        cursor.close()
        conn.close()

        result = {
            "startups": startup_count,
            "news": news_count,
            "sentiment_scored": sentiment_scored,
            "opportunities": opportunities_count,
            "signals_today": signals_today,
            "total_signals": total_signals,
            "risk_distribution": risk_dist,
        }

        _redis_cache_set(CACHED_KEY, result, ttl=60)
        return result

    @app.get("/api/cache/clear")
    def cache_clear():
        """Clear all cached responses — both Redis and in-memory (admin endpoint)."""
        _redis_cache_invalidate()
        return {"status": "cleared", "message": "All cache entries removed (Redis + in-memory)"}

    # ── Performance Analytics (T-052) ────────────────────

    @app.get("/api/performance")
    def performance_analytics(hours: int = Query(24, ge=1, le=168, description="Lookback window in hours")):
        """Performance analytics: latencies, error rates, cache stats.

        Returns query/chat latency percentiles, error counts, and cache metrics.
        Each section degrades gracefully if the underlying query fails.
        """
        result = {"hours": hours}

        # Query latency from query_log
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """SELECT response_ms FROM query_log
                   WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s HOUR)
                     AND response_ms IS NOT NULL AND response_ms > 0
                   ORDER BY response_ms""",
                (hours,),
            )
            rows = [r["response_ms"] for r in cursor.fetchall()]
            cursor.close()
            conn.close()
            if rows:
                n = len(rows)
                result["query_latency"] = {
                    "count": n,
                    "min_ms": rows[0],
                    "max_ms": rows[-1],
                    "avg_ms": round(sum(rows) / n, 1),
                    "p50_ms": rows[int(n * 0.50)],
                    "p95_ms": rows[int(n * 0.95)],
                    "p99_ms": rows[min(int(n * 0.99), n - 1)],
                }
            else:
                result["query_latency"] = {"count": 0}
        except Exception as e:
            result["query_latency"] = {"error": str(e)}

        # Chat latency
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """SELECT COUNT(*) as cnt, AVG(response_ms) as avg_ms
                   FROM chat_log
                   WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s HOUR)
                     AND response_ms IS NOT NULL""",
                (hours,),
            )
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            result["chat_latency"] = {
                "total": row["cnt"],
                "avg_ms": round(row["avg_ms"], 1) if row["avg_ms"] else 0,
            }
        except Exception as e:
            result["chat_latency"] = {"error": str(e)}

        # Error rate from error_log
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM error_log "
                "WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s HOUR)",
                (hours,),
            )
            error_count = cursor.fetchone()["cnt"]
            cursor.close()
            conn.close()
            # Estimate total requests from query_log + chat_log
            query_count = result.get("query_latency", {}).get("count", 0)
            chat_count = result.get("chat_latency", {}).get("total", 0)
            total_requests = query_count + chat_count
            rate = round((error_count / total_requests) * 100, 2) if total_requests > 0 else 0
            result["error_rate"] = {
                "errors": error_count,
                "total_requests": total_requests,
                "rate_percent": rate,
            }
        except Exception as e:
            result["error_rate"] = {"error": str(e)}

        # Cache stats
        result["cache"] = {
            "in_memory_entries": len(_cache),
            "redis_available": False,
        }
        try:
            import redis as _redis_check
            r = _redis_check.from_url(_REDIS_URL, socket_connect_timeout=1)
            r.ping()
            api_keys = list(r.scan_iter("api:*"))
            result["cache"]["redis_available"] = True
            result["cache"]["redis_api_keys"] = len(api_keys)
            r.close()
        except Exception:
            pass

        # Slowest endpoints (by request_path from error_log as proxy)
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """SELECT request_path, COUNT(*) as cnt
                   FROM error_log
                   WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s HOUR)
                     AND request_path IS NOT NULL
                   GROUP BY request_path ORDER BY cnt DESC LIMIT 10""",
                (hours,),
            )
            result["slowest_endpoints"] = [
                {"path": r["request_path"], "errors": r["cnt"]}
                for r in cursor.fetchall()
            ]
            cursor.close()
            conn.close()
        except Exception as e:
            result["slowest_endpoints"] = {"error": str(e)}

        return result

    # ── Stream Processing Status ──────────────────────────

    @app.get("/api/stream/status")
    def stream_status():
        """Health check for stream processing pipeline — reads live metrics from Redis."""
        import json
        import time
        redis_ok = False
        pipeline_metrics = {}

        try:
            import redis as redis_client
            r = redis_client.from_url(
                "redis://localhost:6379/0",
                socket_connect_timeout=2,
                decode_responses=True,
            )
            redis_ok = r.ping()

            # Read pipeline metrics published by stream/pipeline.py
            raw_metrics = r.get("stream:metrics")
            if raw_metrics:
                try:
                    pipeline_metrics = json.loads(raw_metrics)
                except (json.JSONDecodeError, TypeError):
                    pass
            r.close()
        except Exception:
            pass

        # Determine overall status from pipeline metrics
        signals_processed = pipeline_metrics.get("signals_processed", 0)
        last_processed = pipeline_metrics.get("last_processed_at", 0)
        pipeline_active = signals_processed > 0 and (time.time() - last_processed) < 300

        if not redis_ok:
            overall = "degraded"
        elif pipeline_active:
            overall = "healthy"
        elif signals_processed > 0:
            overall = "stale"
        else:
            overall = "not_started"

        return {
            "status": overall,
            "timestamp": time.time(),
            "pipeline": pipeline_metrics,
            "components": {
                "redis": {"status": "connected" if redis_ok else "disconnected"},
                "kafka": {"status": "connected" if pipeline_active else "unknown"},
                "bytewax": {"status": "running" if pipeline_active else "stopped"},
                "clickhouse": {"status": "not_configured", "ingestion_rate": 0},
                "timescaledb": {"status": "not_configured", "hypertables": 0},
            },
            "cache_entries": len(_cache),
        }


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

    # ── Startup secrets validation (T-010) ──
    _required_secrets = ["MYSQL_PASSWORD", "JWT_SECRET"]
    _missing = [s for s in _required_secrets if not os.environ.get(s)]
    if _missing:
        _logger.warning(
            "⚠ Missing required environment variables: %s. "
            "Set these in .env before deploying to production.",
            ", ".join(_missing),
        )

    _logger.info("Starting API server on http://%s:%d", args.host, args.port)
    _logger.info("Dashboard:  http://%s:%d/", args.host, args.port)
    _logger.info("API docs:   http://%s:%d/docs", args.host, args.port)

    uvicorn.run("api_server:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
