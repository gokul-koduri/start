# 🏗️ Opportunity Intelligence Platform — Architecture Analysis & Design Plan

> **Generated:** 2026-06-08
> **Source:** Full system audit of all 42 API endpoints, 92 DB tables, 72 agents, 27 collectors

---

## 1. API ENDPOINT HEALTH CHECK RESULTS

### ✅ Working (36/42)

| Status | Endpoint | Response |
|--------|----------|----------|
| ✅ 200 | `GET /` | Dashboard HTML (71KB) |
| ✅ 200 | `GET /api/health` | `{"status":"healthy","database":"connected"}` |
| ✅ 200 | `GET /api/stats` | 163 startups, 943 news, 31 BLS, 6 revival, 12 hotspots |
| ✅ 200 | `GET /api/collection/status` | 105 collection runs, 22 collectors |
| ✅ 200 | `GET /api/startups` | 163 failed startups (filterable) |
| ✅ 200 | `GET /api/news` | 943 articles (TechCrunch, Google News) |
| ✅ 200 | `GET /api/risk-scores` | `[]` — no scored startups yet |
| ✅ 200 | `GET /api/survival-rates` | 31 BLS data points |
| ✅ 200 | `GET /api/revival-opportunities` | 6 revival industries |
| ✅ 200 | `GET /api/models` | 2 Ollama models (llama3.2:1b, llama3:latest) |
| ✅ 200 | `GET /api/models/token-usage` | `{"total_tokens":0,"total_runs":0}` |
| ✅ 200 | `GET /api/alerts` | `[]` — no active alerts |
| ✅ 200 | `GET /api/alerts/preferences` | Email/Slack/Discord/Webhook all enabled |
| ✅ 200 | `GET /api/alerts/dead-letters` | `[]` — no dead letters |
| ✅ 200 | `GET /api/pipeline-runs` | 175 agent runs logged |
| ✅ 200 | `GET /api/ml/models` | 1 model entry (trained on 326 rows) |
| ✅ 200 | `GET /api/search?q=bitcoin` | Working (fulltext mode fallback) |
| ✅ 200 | `GET /api/knowledge-graph` | `{"entities":[],"relationships":[]}` |
| ✅ 200 | `GET /api/license/metrics` | `{"free_users":0,"pro_users":0,"enterprise_users":0}` |
| ✅ 200 | `GET /api/ws/status` | `{"active_connections":0,"uptime_seconds":87111}` |
| ✅ 200 | `GET /api/scores/deltas` | `[]` — no deltas yet |
| ✅ 200 | `GET /api/score/accuracy` | `{"latest":null,"total_runs":0}` |
| ✅ 200 | `GET /api/opportunities` | `[]` — no opportunities scored |
| ✅ 200 | `GET /api/signals` | 157 signals (hn_live, arxiv, package_trend) |
| ✅ 200 | `GET /api/signals/stats` | arxiv:102, hn_live:53, package_trend:2 |
| ✅ 200 | `GET /api/cache/clear` | Redis + in-memory cache cleared |
| ✅ 200 | `GET /api/performance` | Query/chat/error latency metrics |
| ✅ 200 | `GET /api/stream/status` | `{"status":"degraded"}` — Redis/Kafka disconnected |
| ✅ 200 | `POST /api/score` | Heuristic scoring works (risk: 0.578) |
| ✅ 200 | `POST /api/ml/train` | Trained RF model on 326 rows, 7 features |
| ✅ 200 | `POST /api/ml/predict` | Falls back to heuristic (no trained model loaded) |
| ✅ 200 | `POST /api/license/generate` | Generates license keys |
| ✅ 200 | `POST /api/license/validate` | Validates license + returns features |
| ✅ 200 | `PUT /api/alerts/preferences` | Updates preferences |

### ❌ Broken (6/42)

| Status | Endpoint | Root Cause | Fix |
|--------|----------|------------|-----|
| ❌ 500 | `GET /api/news/sentiment` | `news_articles` table missing `sentiment_label` & `sentiment_score` columns | **ALTER TABLE** to add columns, then run sentiment scoring |
| ❌ 500 | `GET /api/stats/summary` | References `startup_risk_scores` table which has 0 rows + same sentiment issue | Populate risk scores, add sentiment columns |
| ❌ 500 | `POST /api/chat` | `BrokenPipeError` in `agents/ai_analyst_agent.py` line 277 | Fix print statement in agent, handle Ollama connection |
| ❌ 404 | `GET /api/startups/1` | Startup IDs don't start at 1 (start at 333+) | Fix ID lookup or return all available IDs |
| ❌ 404 | `GET /api/entities/Northvolt/connections` | `kg_entities` table is empty (0 rows) | Run knowledge graph entity extraction pipeline |
| ❌ timeout | `POST /api/models/pull` | Pulling GGUF models takes >15s | Expected behavior, add async/progress endpoint |

---

## 2. DATA PIPELINE ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DATA COLLECTION LAYER                            │
│                    (22 Collectors)                                  │
├─────────────┬──────────────┬──────────────┬────────────────────────┤
│  Web Scrapers│  RSS Feeds   │  Public APIs │  Real-time Streams     │
├─────────────┼──────────────┼──────────────┼────────────────────────┤
│ Failory     │ Google News  │ BLS Stats    │ Reddit Stream           │
│ Crunchbase  │ TechCrunch   │ SEC EDGAR    │ HN Live (53 signals)    │
│ Website Mon │ Newsletter   │ OpenCorp     │ Social Media (53 posts) │
│             │ arXiv (102)  │ Product Hunt │ Twitter                 │
│             │              │ GitHub Deep  │ Stack Overflow          │
│             │              │ Patents      │ NPM/PyPI Trends         │
│             │              │ Regulatory   │ Job Postings            │
└──────┬──────┴──────┬───────┴──────┬───────┴────────────┬───────────┘
       │             │              │                    │
       ▼             ▼              ▼                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    PROCESSING LAYER (72 Agents)                     │
├────────────┬───────────┬──────────┬──────────┬─────────────────────┤
│ Orchestrate│ AI/NLP    │ ML/Score │ Analysis │ Knowledge Graph     │
├────────────┼───────────┼──────────┼──────────┼─────────────────────┤
│ Orchestrator│ AI Analyst│ Risk Sc. │ Failure  │ Entity Extract      │
│ Pipeline    │ NLP Sent. │ Scoring  │ Patterns │ Relationship Ext.   │
│ Scheduler   │ Summarizer│ ML Train │ Cohort   │ Graph Traversal     │
│ Collector   │ Topic     │ Predict  │ Geographic│ Community Det.     │
│ 22 collectors│ Entity   │ Accuracy │ Survival │ Influence Prop.     │
└──────┬─────┴─────┬─────┴────┬─────┴────┬─────┴─────────┬───────────┘
       │           │          │          │               │
       ▼           ▼          ▼          ▼               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    STORAGE LAYER                                    │
├──────────────┬────────────────┬──────────────┬─────────────────────┤
│   MySQL DB   │  Ollama (LLM)  │  File System │    Cache            │
├──────────────┼────────────────┼──────────────┼─────────────────────┤
│ 92 tables    │ llama3.2:1b    │ data/models/ │ Redis (disconnected) │
│ 163 startups │ llama3:latest  │ data/pdfs/   │ In-memory dict      │
│ 943 news     │                │ data/reports/│                     │
│ 157 signals  │                │ data/cache/  │                     │
│ 31 BLS rates │                │              │                     │
└──────┬───────┴────────┬───────┴──────┬───────┴─────────┬───────────┘
       │                │              │                 │
       ▼                ▼              ▼                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                               │
├────────────┬──────────────┬──────────────┬─────────────────────────┤
│ FastAPI    │ Next.js      │ WebSocket    │ Email                   │
├────────────┼──────────────┼──────────────┼─────────────────────────┤
│ 42 APIs    │ dashboard/   │ /ws/live     │ Templates               │
│ Swagger    │ app/         │ Real-time    │ Alert dispatch          │
│ ReDoc      │ React-based  │ push         │ SMTP                    │
│ Dashboard  │              │              │                         │
└────────────┴──────────────┴──────────────┴─────────────────────────┘
```

### Data Flow Summary

```
External Sources (22)
    → Collectors (27 .py files in collectors/)
        → MySQL Tables (92 tables)
            → AI/ML Agents (72 .py files in agents/)
                → Analysis Tables (analysis_*)
                    → API Endpoints (42)
                        → Dashboard / Next.js / WebSocket
```

### Key Data Stores

| Store | Status | Data |
|-------|--------|------|
| **MySQL** | ✅ Connected | 92 tables, ~1,500+ total rows |
| **Ollama** | ✅ Running | 2 models (llama3.2:1b, llama3:latest) |
| **Redis** | ❌ Disconnected | Cache/streaming not available |
| **Kafka** | ❌ Not running | Stream processing degraded |
| **Vector DB** | ❌ Empty | `vector_embeddings` = 0 rows |

---

## 3. ISSUES FOUND & FIXES NEEDED

### Critical (P0) — Features Broken

| # | Issue | Impact | Fix |
|---|-------|--------|-----|
| 1 | `news_articles` missing `sentiment_label`, `sentiment_score` columns | `/api/news/sentiment` returns 500 | `ALTER TABLE news_articles ADD COLUMN sentiment_label VARCHAR(20), ADD COLUMN sentiment_score FLOAT;` |
| 2 | `/api/chat` BrokenPipeError in `ai_analyst_agent.py:277` | AI Analyst chat broken | Fix stdout usage in agent, add error handling for Ollama connection |
| 3 | `startup_risk_scores` table empty | `/api/risk-scores` returns `[]`, scoring pipeline incomplete | Run risk scoring pipeline on all 163 startups |
| 4 | `kg_entities` / `kg_relationships` empty | Knowledge graph, entity connections return empty | Run knowledge graph extraction pipeline |

### High (P1) — Features Incomplete

| # | Issue | Impact | Fix |
|---|-------|--------|-----|
| 5 | `opportunity_scores` empty | `/api/opportunities` returns `[]` | Run opportunity scoring pipeline |
| 6 | `vector_embeddings` empty | `/api/search` can't do semantic search | Run embedding pipeline |
| 7 | Redis disconnected | Cache, streaming, real-time features degraded | Start Redis server |
| 8 | Kafka not running | Stream processing degraded | Start Kafka or disable gracefully |
| 9 | `/api/models/pull` blocks for >15s | Model download times out | Add async pull with progress tracking |

### Medium (P2) — UX Polish

| # | Issue | Impact | Fix |
|---|-------|--------|-----|
| 10 | `score_deltas`, `score_accuracy` empty | No scoring history | Run scoring pipeline periodically |
| 11 | `funding_events`, `sec_filings` empty | Collectors not producing data | Trigger collection runs |
| 12 | Dashboard JS had curl string quoting bug | Data page cards broke | Already fixed ✅ |

---

## 4. UI/UX REDESIGN PLAN

### Current State
- **5-page SPA** with dark theme converted to `#add8e3` light blue
- Pages: Overview, Architecture, Agents, Data & APIs, Report
- Chart.js for visualizations
- Live API data fetching
- Click-to-test endpoint cards

### Proposed Redesign — 7-Page Dashboard

```
┌─────────────────────────────────────────────────┐
│  🏠 Overview  │  📊 Analytics  │  🗂️ Startups  │  📰 News  │  🧠 AI Lab  │  ⚙️ System  │  📈 Pipeline  │
└─────────────────────────────────────────────────┘
```

#### Page 1: 🏠 Overview (Hero Dashboard)
- **Live stats cards** — startups, news, signals, collectors (pulled from `/api/stats/summary`)
- **Trend sparklines** — last 7 days signal count
- **Quick search** — calls `/api/search` in real-time
- **Recent activity feed** — last 10 pipeline runs, alerts
- **Health indicators** — DB, Ollama, Redis, Kafka status dots

#### Page 2: 📊 Analytics (Data Visualization)
- **Sector breakdown** — doughnut chart (startup sectors)
- **Geographic heatmap** — startup locations on a map
- **Timeline** — startup failures by year (bar chart)
- **BLS survival rates** — line chart with year-by-year trends
- **News sentiment** — pie chart (when sentiment columns fixed)
- **Risk score distribution** — histogram

#### Page 3: 🗂️ Startups (Data Table)
- **Searchable/sortable table** — all 163 startups
- **Column filters** — sector, country, year, funding range
- **Expandable rows** — click to see full details
- **Inline scoring** — "Score This" button per row → calls `/api/score`
- **Export** — CSV/JSON download

#### Page 4: 📰 News & Signals
- **News feed** — latest articles from `/api/news`
- **Signal stream** — real-time from `/api/signals`
- **Source filter** — TechCrunch, HN, arXiv, Reddit
- **Sentiment badges** — when sentiment data available
- **Auto-refresh** — polls `/api/news` every 30s

#### Page 5: 🧠 AI Lab
- **Chat interface** — sidebar chat → calls `/api/chat`
- **ML Models** — list trained models from `/api/ml/models`
- **Train button** — trigger training via `/api/ml/train`
- **Predict form** — input features → `/api/ml/predict`
- **Ollama models** — list, pull new models
- **Token usage stats** — usage visualization

#### Page 6: ⚙️ System (Ops Dashboard)
- **Health check** — DB, Redis, Kafka, Ollama status
- **Pipeline runs** — table with status, duration, agent name
- **Alerts** — active alerts, dead letters, preferences
- **Cache management** — clear cache button
- **Performance** — latency charts from `/api/performance`
- **WebSocket status** — connection count, uptime
- **License info** — current license, features

#### Page 7: 📈 Data Pipeline Architecture
- **Interactive flow diagram** — SVG showing data flow
- **Collector status grid** — 22 collectors with last run time, status
- **Agent graph** — 72 agents grouped by category
- **DB table browser** — 92 tables with row counts
- **Schema viewer** — click table → see columns

### Design System

```
Colors:
  Background:     #add8e3 (light blue — user preference)
  Cards:          #ffffff (white)
  Sidebar:        #9cc8d8 (deeper blue)
  Primary:        #4f46e5 (indigo)
  Success:        #059669 (emerald)
  Warning:        #d97706 (amber)
  Danger:         #dc2626 (red)
  Text:           #1e293b (slate-900)
  Text secondary: #475569 (slate-600)
  Border:         #c8d8e0 (blue-gray)

Typography:
  Headings: Inter 700
  Body: Inter 400
  Code: SF Mono / Fira Code

Components:
  Cards: 12px radius, 1px border, hover shadow
  Badges: Pill-shaped with category colors
  Tables: Striped rows, sticky header
  Charts: Chart.js with matching color palette
  Animations: 200ms transitions, fade-in on load
```

---

## 5. ACTION ITEMS

### Phase 1: Fix Broken APIs (1-2 hours)
- [ ] Add `sentiment_label` + `sentiment_score` columns to `news_articles`
- [ ] Fix `ai_analyst_agent.py` BrokenPipeError
- [ ] Run risk scoring pipeline → populate `startup_risk_scores`
- [ ] Run knowledge graph extraction → populate `kg_entities`/`kg_relationships`

### Phase 2: Data Enrichment (2-4 hours)
- [ ] Run sentiment analysis on 943 news articles
- [ ] Run opportunity scoring pipeline
- [ ] Generate vector embeddings for semantic search
- [ ] Start Redis for caching/streaming
- [ ] Trigger all collectors to populate empty tables

### Phase 3: UI/UX Redesign (4-8 hours)
- [ ] Build 7-page dashboard from design plan above
- [ ] Add interactive data tables with search/sort/filter
- [ ] Add real-time WebSocket updates
- [ ] Add AI chat sidebar
- [ ] Add export functionality (CSV/JSON)
- [ ] Mobile responsive layout

### Phase 4: Advanced Features (ongoing)
- [ ] WebSocket live data push
- [ ] Email alert dispatch
- [ ] Next.js frontend migration
- [ ] License tier enforcement
- [ ] Rate limiting per API key

---

*Generated from full system audit — `/Users/kodurigokul/Desktop/Startup_Research_Report/`*
