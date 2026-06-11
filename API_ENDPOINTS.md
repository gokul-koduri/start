# 📡 Opportunity Intelligence Platform — Complete API Reference

> **Base URL:** `http://localhost:8000`
> **Server:** FastAPI + Uvicorn
> **Database:** MySQL
> **LLM:** Ollama
> **Last Updated:** 2026-06-08
> **Total Endpoints:** 42

---

## 📖 Interactive Documentation

| Name | URL |
|------|-----|
| 🟢 Swagger UI | [http://localhost:8000/docs](http://localhost:8000/docs) |
| 📚 ReDoc | [http://localhost:8000/redoc](http://localhost:8000/redoc) |
| 🌐 Dashboard | [http://localhost:8000/](http://localhost:8000/) |

---

## 📥 GET Endpoints

| # | Method | Endpoint | Description | Parameters |
|---|--------|----------|-------------|------------|
| 1 | GET | `http://localhost:8000/` | Serve the interactive dashboard. | — |
| 2 | GET | `http://localhost:8000/api/health` | Health check — confirms DB connectivity. | — |
| 3 | GET | `http://localhost:8000/api/stats` | Database statistics summary. | — |
| 4 | GET | `http://localhost:8000/api/collection/status` | Show last run status for each collector. | `collector` (str | None, default: Query(None) |
| 5 | GET | `http://localhost:8000/api/startups` | List failed startups with optional filters. | `sector` (str | None, default: Query(None) |
| 6 | GET | `http://localhost:8000/api/startups/{startup_id}` | Get a single startup by ID. | — |
| 7 | GET | `http://localhost:8000/api/news` | Recent news articles. | `limit` (int, default: Query(20) |
| 8 | GET | `http://localhost:8000/api/news/sentiment` | Sentiment distribution across scored news articles. | — |
| 9 | GET | `http://localhost:8000/api/risk-scores` | Startup failure risk scores. | `risk_level` (str | None, default: Query(None)<br>`Filter` (low) |
| 10 | GET | `http://localhost:8000/api/ml/models` | List trained ML models from the ml_models table. | — |
| 11 | GET | `http://localhost:8000/api/models` | List locally available Ollama models. | — |
| 12 | GET | `http://localhost:8000/api/models/token-usage` | Ollama token usage statistics from local tracker. | — |
| 13 | GET | `http://localhost:8000/api/survival-rates` | BLS survival rate data. | `naics` (str | None, default: Query(None) |
| 14 | GET | `http://localhost:8000/api/revival-opportunities` | Revival industry opportunities. | `limit` (int, default: Query(20) |
| 15 | GET | `http://localhost:8000/api/alerts` | Active optimization and pipeline alerts. | `limit` (int, default: Query(20) |
| 16 | GET | `http://localhost:8000/api/alerts/preferences` | Get current alert notification preferences. | — |
| 17 | GET | `http://localhost:8000/api/alerts/dead-letters` | List failed alerts in the dead letter queue. | `limit` (int, default: Query(20) |
| 18 | GET | `http://localhost:8000/api/pipeline-runs` | Recent pipeline execution history. | `limit` (int, default: Query(20) |
| 19 | GET | `http://localhost:8000/api/knowledge-graph` | Knowledge graph entities and relationships. | `entity_type` (str | None, default: Query(None) |
| 20 | GET | `http://localhost:8000/api/search` | Unified search across vector and full-text indexes. | `q` (str, default: Query(...) |
| 21 | GET | `http://localhost:8000/api/entities/{entity_name}/connections` | Get knowledge graph connections for an entity. | `depth` (int, default: Query(1) |
| 22 | GET | `http://localhost:8000/api/license/metrics` | Subscription and license metrics. | — |
| 23 | GET | `http://localhost:8000/api/ws/status` | WebSocket connection manager status. | — |
| 24 | GET | `http://localhost:8000/api/scores/deltas` | Recent score changes with delta breakdown. | `limit` (int, default: Query(20) |
| 25 | GET | `http://localhost:8000/api/score/accuracy` | Scoring accuracy metrics with weekly trend. | `weeks` (int, default: Query(4) |
| 26 | GET | `http://localhost:8000/api/opportunities` | List scored opportunities sorted by composite_score descending. | `limit` (int, default: 50)<br>`offset` (int, default: 0)<br>`min_score` (float, default: 0)<br>`trend` (str | None, default: None)<br>`entity_type` (str | None, default: None) |
| 27 | GET | `http://localhost:8000/api/opportunities/{entity_name}` | Get detailed opportunity data for a specific entity. | — |
| 28 | GET | `http://localhost:8000/api/signals` | List raw signals with filtering. | `limit` (int, default: 50)<br>`offset` (int, default: 0)<br>`signal_type` (str | None, default: None)<br>`processed` (int | None, default: None) |
| 29 | GET | `http://localhost:8000/api/signals/stats` | Get statistics about signal collection. | — |
| 30 | GET | `http://localhost:8000/api/stats/summary` | Lightweight stats endpoint for quick polling (Redis-backed, 60s TTL). | — |
| 31 | GET | `http://localhost:8000/api/cache/clear` | Clear all cached responses — both Redis and in-memory (admin endpoint). | — |
| 32 | GET | `http://localhost:8000/api/performance` | Performance analytics: latencies, error rates, cache stats. | `hours` (int, default: Query(24) |
| 33 | GET | `http://localhost:8000/api/stream/status` | Health check for stream processing pipeline — reads live metrics from Redis. | — |

---

## 📤 POST Endpoints

| # | Method | Endpoint | Description | Parameters |
|---|--------|----------|-------------|------------|
| 1 | POST | `http://localhost:8000/api/score` | Score a single startup's failure risk using ML + heuristic (no DB write). | `body` (dict):) |
| 2 | POST | `http://localhost:8000/api/ml/train` | Trigger ML model training on existing startup data. | `min_samples` (int, default: Query(50) |
| 3 | POST | `http://localhost:8000/api/ml/predict` | Predict failure risk for a single startup using trained ML model. | `body` (dict):) |
| 4 | POST | `http://localhost:8000/api/models/pull` | Download a GGUF model from HuggingFace via Ollama. | `body` (dict):) |
| 5 | POST | `http://localhost:8000/api/chat` | AI Analyst — ask a natural language question about the data. | `request_body` (dict):) |
| 6 | POST | `http://localhost:8000/api/license/validate` | Validate a license key and return tier + features. | `body` (dict):) |
| 7 | POST | `http://localhost:8000/api/license/generate` | Generate a new license key (admin only). | `body` (dict):) |

---

## ✏️ PUT Endpoints

| # | Method | Endpoint | Description | Parameters |
|---|--------|----------|-------------|------------|
| 1 | PUT | `http://localhost:8000/api/alerts/preferences` | Update alert notification preferences. | `body` (dict):) |

---

## 🔌 WebSocket

| # | Protocol | Endpoint | Description |
|---|----------|----------|-------------|
| 1 | WebSocket | `ws://localhost:8000/ws/live` | WebSocket endpoint for live dashboard data updates. |

---

## 📋 Detailed Endpoint Reference

### 1. `GET` `/`

- **Function:** `dashboard`
- **Description:** Serve the interactive dashboard.
- **Full URL:** `http://localhost:8000/`
- **Source:** `api_server.py` line 224

### 2. `GET` `/api/health`

- **Function:** `health`
- **Description:** Health check — confirms DB connectivity.
- **Full URL:** `http://localhost:8000/api/health`
- **Source:** `api_server.py` line 236

### 3. `GET` `/api/stats`

- **Function:** `stats`
- **Description:** Database statistics summary.
- **Full URL:** `http://localhost:8000/api/stats`
- **Source:** `api_server.py` line 252

### 4. `GET` `/api/collection/status`

- **Function:** `collection_status`
- **Description:** Show last run status for each collector.
- **Full URL:** `http://localhost:8000/api/collection/status`
- **Source:** `api_server.py` line 276
- **Query/Body Parameters:**
  - `collector` (str | None, default: Query(None)

### 5. `GET` `/api/startups`

- **Function:** `list_startups`
- **Description:** List failed startups with optional filters.
- **Full URL:** `http://localhost:8000/api/startups`
- **Source:** `api_server.py` line 330
- **Query/Body Parameters:**
  - `sector` (str | None, default: Query(None)

### 6. `GET` `/api/startups/{startup_id}`

- **Function:** `get_startup`
- **Description:** Get a single startup by ID.
- **Full URL:** `http://localhost:8000/api/startups/{startup_id}`
- **Source:** `api_server.py` line 389
- **Path Parameters:** `startup_id`

### 7. `GET` `/api/news`

- **Function:** `list_news`
- **Description:** Recent news articles.
- **Full URL:** `http://localhost:8000/api/news`
- **Source:** `api_server.py` line 407
- **Query/Body Parameters:**
  - `limit` (int, default: Query(20)

### 8. `GET` `/api/news/sentiment`

- **Function:** `news_sentiment`
- **Description:** Sentiment distribution across scored news articles.
- **Full URL:** `http://localhost:8000/api/news/sentiment`
- **Source:** `api_server.py` line 436

### 9. `GET` `/api/risk-scores`

- **Function:** `risk_scores`
- **Description:** Startup failure risk scores.
- **Full URL:** `http://localhost:8000/api/risk-scores`
- **Source:** `api_server.py` line 471
- **Query/Body Parameters:**
  - `risk_level` (str | None, default: Query(None)
  - `Filter` (low)

### 10. `POST` `/api/score`

- **Function:** `score_a_startup`
- **Description:** Score a single startup's failure risk using ML + heuristic (no DB write).
- **Full URL:** `http://localhost:8000/api/score`
- **Source:** `api_server.py` line 512
- **Query/Body Parameters:**
  - `body` (dict):)

### 11. `GET` `/api/ml/models`

- **Function:** `ml_models`
- **Description:** List trained ML models from the ml_models table.
- **Full URL:** `http://localhost:8000/api/ml/models`
- **Source:** `api_server.py` line 555

### 12. `POST` `/api/ml/train`

- **Function:** `ml_train`
- **Description:** Trigger ML model training on existing startup data.
- **Full URL:** `http://localhost:8000/api/ml/train`
- **Source:** `api_server.py` line 571
- **Query/Body Parameters:**
  - `min_samples` (int, default: Query(50)

### 13. `POST` `/api/ml/predict`

- **Function:** `ml_predict`
- **Description:** Predict failure risk for a single startup using trained ML model.
- **Full URL:** `http://localhost:8000/api/ml/predict`
- **Source:** `api_server.py` line 593
- **Query/Body Parameters:**
  - `body` (dict):)

### 14. `GET` `/api/models`

- **Function:** `list_ollama_models`
- **Description:** List locally available Ollama models.
- **Full URL:** `http://localhost:8000/api/models`
- **Source:** `api_server.py` line 657

### 15. `POST` `/api/models/pull`

- **Function:** `pull_ollama_model`
- **Description:** Download a GGUF model from HuggingFace via Ollama.
- **Full URL:** `http://localhost:8000/api/models/pull`
- **Source:** `api_server.py` line 668
- **Query/Body Parameters:**
  - `body` (dict):)

### 16. `GET` `/api/models/token-usage`

- **Function:** `token_usage`
- **Description:** Ollama token usage statistics from local tracker.
- **Full URL:** `http://localhost:8000/api/models/token-usage`
- **Source:** `api_server.py` line 689

### 17. `GET` `/api/survival-rates`

- **Function:** `survival_rates`
- **Description:** BLS survival rate data.
- **Full URL:** `http://localhost:8000/api/survival-rates`
- **Source:** `api_server.py` line 722
- **Query/Body Parameters:**
  - `naics` (str | None, default: Query(None)

### 18. `GET` `/api/revival-opportunities`

- **Function:** `revival_opportunities`
- **Description:** Revival industry opportunities.
- **Full URL:** `http://localhost:8000/api/revival-opportunities`
- **Source:** `api_server.py` line 762
- **Query/Body Parameters:**
  - `limit` (int, default: Query(20)

### 19. `GET` `/api/alerts`

- **Function:** `list_alerts`
- **Description:** Active optimization and pipeline alerts.
- **Full URL:** `http://localhost:8000/api/alerts`
- **Source:** `api_server.py` line 777
- **Query/Body Parameters:**
  - `limit` (int, default: Query(20)

### 20. `GET` `/api/alerts/preferences`

- **Function:** `get_alert_preferences`
- **Description:** Get current alert notification preferences.
- **Full URL:** `http://localhost:8000/api/alerts/preferences`
- **Source:** `api_server.py` line 799

### 21. `PUT` `/api/alerts/preferences`

- **Function:** `update_alert_preferences`
- **Description:** Update alert notification preferences.
- **Full URL:** `http://localhost:8000/api/alerts/preferences`
- **Source:** `api_server.py` line 823
- **Query/Body Parameters:**
  - `body` (dict):)

### 22. `GET` `/api/alerts/dead-letters`

- **Function:** `list_dead_letters`
- **Description:** List failed alerts in the dead letter queue.
- **Full URL:** `http://localhost:8000/api/alerts/dead-letters`
- **Source:** `api_server.py` line 873
- **Query/Body Parameters:**
  - `limit` (int, default: Query(20)

### 23. `GET` `/api/pipeline-runs`

- **Function:** `pipeline_runs`
- **Description:** Recent pipeline execution history.
- **Full URL:** `http://localhost:8000/api/pipeline-runs`
- **Source:** `api_server.py` line 896
- **Query/Body Parameters:**
  - `limit` (int, default: Query(20)

### 24. `POST` `/api/chat`

- **Function:** `chat`
- **Description:** AI Analyst — ask a natural language question about the data.
- **Full URL:** `http://localhost:8000/api/chat`
- **Source:** `api_server.py` line 917
- **Query/Body Parameters:**
  - `request_body` (dict):)

### 25. `GET` `/api/knowledge-graph`

- **Function:** `knowledge_graph`
- **Description:** Knowledge graph entities and relationships.
- **Full URL:** `http://localhost:8000/api/knowledge-graph`
- **Source:** `api_server.py` line 956
- **Query/Body Parameters:**
  - `entity_type` (str | None, default: Query(None)

### 26. `GET` `/api/search`

- **Function:** `unified_search`
- **Description:** Unified search across vector and full-text indexes.
- **Full URL:** `http://localhost:8000/api/search`
- **Source:** `api_server.py` line 1032
- **Query/Body Parameters:**
  - `q` (str, default: Query(...)

### 27. `GET` `/api/entities/{entity_name}/connections`

- **Function:** `entity_connections`
- **Description:** Get knowledge graph connections for an entity.
- **Full URL:** `http://localhost:8000/api/entities/{entity_name}/connections`
- **Source:** `api_server.py` line 1147
- **Path Parameters:** `entity_name`
- **Query/Body Parameters:**
  - `depth` (int, default: Query(1)

### 28. `POST` `/api/license/validate`

- **Function:** `validate_license`
- **Description:** Validate a license key and return tier + features.
- **Full URL:** `http://localhost:8000/api/license/validate`
- **Source:** `api_server.py` line 1295
- **Query/Body Parameters:**
  - `body` (dict):)

### 29. `POST` `/api/license/generate`

- **Function:** `generate_license_key`
- **Description:** Generate a new license key (admin only).
- **Full URL:** `http://localhost:8000/api/license/generate`
- **Source:** `api_server.py` line 1344
- **Query/Body Parameters:**
  - `body` (dict):)

### 30. `GET` `/api/license/metrics`

- **Function:** `license_metrics`
- **Description:** Subscription and license metrics.
- **Full URL:** `http://localhost:8000/api/license/metrics`
- **Source:** `api_server.py` line 1357

### 31. `WEBSOCKET` `/ws/live`

- **Function:** `ws_live`
- **Description:** WebSocket endpoint for live dashboard data updates.
- **Full URL:** `ws://localhost:8000/ws/live`
- **Source:** `api_server.py` line 1608

### 32. `GET` `/api/ws/status`

- **Function:** `ws_status`
- **Description:** WebSocket connection manager status.
- **Full URL:** `http://localhost:8000/api/ws/status`
- **Source:** `api_server.py` line 1695

### 33. `GET` `/api/scores/deltas`

- **Function:** `list_score_deltas`
- **Description:** Recent score changes with delta breakdown.
- **Full URL:** `http://localhost:8000/api/scores/deltas`
- **Source:** `api_server.py` line 1703
- **Query/Body Parameters:**
  - `limit` (int, default: Query(20)

### 34. `GET` `/api/score/accuracy`

- **Function:** `score_accuracy`
- **Description:** Scoring accuracy metrics with weekly trend.
- **Full URL:** `http://localhost:8000/api/score/accuracy`
- **Source:** `api_server.py` line 1755
- **Query/Body Parameters:**
  - `weeks` (int, default: Query(4)

### 35. `GET` `/api/opportunities`

- **Function:** `list_opportunities`
- **Description:** List scored opportunities sorted by composite_score descending.
- **Full URL:** `http://localhost:8000/api/opportunities`
- **Source:** `api_server.py` line 1828
- **Query/Body Parameters:**
  - `limit` (int, default: 50)
  - `offset` (int, default: 0)
  - `min_score` (float, default: 0)
  - `trend` (str | None, default: None)
  - `entity_type` (str | None, default: None)

### 36. `GET` `/api/opportunities/{entity_name}`

- **Function:** `get_opportunity`
- **Description:** Get detailed opportunity data for a specific entity.
- **Full URL:** `http://localhost:8000/api/opportunities/{entity_name}`
- **Source:** `api_server.py` line 1906
- **Path Parameters:** `entity_name`

### 37. `GET` `/api/signals`

- **Function:** `list_signals`
- **Description:** List raw signals with filtering.
- **Full URL:** `http://localhost:8000/api/signals`
- **Source:** `api_server.py` line 1950
- **Query/Body Parameters:**
  - `limit` (int, default: 50)
  - `offset` (int, default: 0)
  - `signal_type` (str | None, default: None)
  - `processed` (int | None, default: None)

### 38. `GET` `/api/signals/stats`

- **Function:** `signal_stats`
- **Description:** Get statistics about signal collection.
- **Full URL:** `http://localhost:8000/api/signals/stats`
- **Source:** `api_server.py` line 1993

### 39. `GET` `/api/stats/summary`

- **Function:** `stats_summary`
- **Description:** Lightweight stats endpoint for quick polling (Redis-backed, 60s TTL).
- **Full URL:** `http://localhost:8000/api/stats/summary`
- **Source:** `api_server.py` line 2108

### 40. `GET` `/api/cache/clear`

- **Function:** `cache_clear`
- **Description:** Clear all cached responses — both Redis and in-memory (admin endpoint).
- **Full URL:** `http://localhost:8000/api/cache/clear`
- **Source:** `api_server.py` line 2160

### 41. `GET` `/api/performance`

- **Function:** `performance_analytics`
- **Description:** Performance analytics: latencies, error rates, cache stats.
- **Full URL:** `http://localhost:8000/api/performance`
- **Source:** `api_server.py` line 2168
- **Query/Body Parameters:**
  - `hours` (int, default: Query(24)

### 42. `GET` `/api/stream/status`

- **Function:** `stream_status`
- **Description:** Health check for stream processing pipeline — reads live metrics from Redis.
- **Full URL:** `http://localhost:8000/api/stream/status`
- **Source:** `api_server.py` line 2294

---

## 🧪 Quick Test Commands

```bash
# Health check
curl http://localhost:8000/api/health

# Database stats
curl http://localhost:8000/api/stats

# Failed startups (with filters)
curl 'http://localhost:8000/api/startups?sector=Fintech&year=2023'

# News articles
curl http://localhost:8000/api/news

# News sentiment
curl http://localhost:8000/api/news/sentiment

# Risk scores
curl http://localhost:8000/api/risk-scores

# Survival rates (BLS)
curl http://localhost:8000/api/survival-rates

# Revival opportunities
curl http://localhost:8000/api/revival-opportunities

# Search (semantic + fulltext)
curl 'http://localhost:8000/api/search?q=battery+failure&mode=hybrid'

# Knowledge graph
curl http://localhost:8000/api/knowledge-graph

# Entity connections
curl http://localhost:8000/api/entities/Northvolt/connections

# AI Chat Analyst
curl -X POST http://localhost:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"message": "Why did Northvolt fail?"}'

# Score a startup
curl -X POST http://localhost:8000/api/score \
  -H 'Content-Type: application/json' \
  -d '{"startup_id": 1}'

# ML Predict
curl -X POST http://localhost:8000/api/ml/predict \
  -H 'Content-Type: application/json' \
  -d '{"features": {"funding": 5000000}}'

# Train ML model
curl -X POST http://localhost:8000/api/ml/train \
  -H 'Content-Type: application/json' \
  -d '{"model_type": "xgboost"}'

# Pull Ollama model
curl -X POST http://localhost:8000/api/models/pull \
  -H 'Content-Type: application/json' \
  -d '{"name": "llama3.2"}'

# Opportunities
curl http://localhost:8000/api/opportunities

# Signals
curl http://localhost:8000/api/signals

# Performance metrics
curl http://localhost:8000/api/performance

# Pipeline runs
curl http://localhost:8000/api/pipeline-runs

# Alerts
curl http://localhost:8000/api/alerts

# License metrics
curl http://localhost:8000/api/license/metrics

# Cache clear (admin)
curl http://localhost:8000/api/cache/clear
```

---

## 📊 Data Collectors (22 Sources)

| # | Collector | Category |
|---|-----------|----------|
| 1 | Failory Scraper | Web scraping |
| 2 | Crunchbase | Funding data |
| 3 | Google News RSS | News aggregator |
| 4 | TechCrunch RSS | Tech news |
| 5 | BLS Public API | Survival stats |
| 6 | SEC EDGAR | SEC filings |
| 7 | GitHub Trends | Repo activity |
| 8 | GitHub Deep | Deep analysis |
| 9 | Reddit Stream | Real-time posts |
| 10 | HN Live | Hacker News |
| 11 | arXiv Papers | Research papers |
| 12 | Product Hunt | Product launches |
| 13 | Stack Overflow | Dev trends |
| 14 | OpenCorporates | Company data |
| 15 | Patent Collector | Patent filings |
| 16 | Regulatory | Regulations |
| 17 | Social Media | Social signals |
| 18 | Twitter | Tweets |
| 19 | Website Monitor | Site changes |
| 20 | Newsletter | Email digests |
| 21 | NPM/PyPI Trends | Package trends |
| 22 | Job Postings | Hiring data |

---

*Auto-generated from `api_server.py` — Opportunity Intelligence Platform*
