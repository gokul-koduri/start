# 🚀 Quick Start Guide — Opportunity Intelligence Platform

> Get the platform running in under 10 minutes.

---

## What You Already Have ✅

Your environment is already set up:

| Component | Status |
|---|---|
| MySQL 8.0 | ✅ Running (database `startup_research` with 85 tables, 163 startups, 943 news articles) |
| Ollama + llama3 | ✅ Running (2 models: `llama3` 8B + `llama3.2:1b`) |
| Python 3.12 | ✅ Installed with all dependencies |
| Tests | ✅ 964 passing, 0 failing |
| `.env` | ✅ Configured |
| LICENSE | ✅ MIT |

---

## Option 1: Run Locally (Recommended — You're Already Ready)

### Start the API Server

```bash
# From the project root:
python api_server.py
```

Opens:
- **Dashboard**: http://localhost:8000/
- **API docs**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/api/health

### Run the Daily Pipeline (Collect + Analyze + Publish)

```bash
python run_agent.py --pipeline daily
```

### Run All Data Collectors

```bash
python run_collectors.py --all
```

### Generate a Report

```bash
python run_report.py
```

### Ask the AI Analyst a Question

```bash
python run_agent.py --chat "Why do most EV startups fail?"
python run_agent.py --chat "Which manufacturing sectors have revival opportunities?"
```

### Run the Streamlit Dashboard

```bash
streamlit run streamlit_app.py
```

Opens http://localhost:8501

---

## Option 2: Run with Docker (For Deployment)

> ⚠️ Docker is not installed on your machine. Install it first if you want this option.

```bash
# 1. Install Docker Desktop (one-time)
#    Download from: https://docs.docker.com/get-docker/

# 2. Set required environment variables
cp .env.example .env
# Edit .env — set MYSQL_PASSWORD, JWT_SECRET, TIMESCALEDB_PASSWORD

# 3. Start all 14 services
docker compose up -d

# 4. Pull the LLM model (first time only)
docker compose exec ollama ollama pull llama3

# 5. Seed the database (first time only)
docker compose exec api python seed_data.py

# 6. Check all services are healthy
docker compose ps

# 7. View logs
docker compose logs -f api
```

### Docker Services Started

| Service | Port | Purpose |
|---|---|---|
| **MySQL** | 3306 | Database |
| **Ollama** | 11434 | Local LLM (llama3) |
| **API** | 8000 | FastAPI REST server |
| **Streamlit** | 8501 | Web dashboard |
| **Pipeline** | — | Daily cron (runs at 8 AM) |
| **Scheduler** | — | 24/7 data collection |
| **Stream Processor** | — | Real-time signal processing |
| **Redis** | 6379 | Cache + pub/sub |
| **Kafka** | 9092 | Event streaming |
| **Qdrant** | 6333 | Vector search |
| **Elasticsearch** | 9200 | Full-text search |
| **ClickHouse** | 8123 | OLAP analytics |
| **TimescaleDB** | 5433 | Time-series data |
| **Caddy** | 80/443 | Reverse proxy + HTTPS |

---

## All Available Commands

### Agent Pipelines

```bash
python run_agent.py --pipeline daily         # Fast collectors + report + publish (5 agents)
python run_agent.py --pipeline weekly        # Full analysis + deep research (13 agents)
python run_agent.py --pipeline analysis      # All intelligence agents (19 agents)
python run_agent.py --pipeline full          # Everything: collect → analyze → publish (18 agents)
python run_agent.py --pipeline dev-team      # AI development team (7 agents)
python run_agent.py --pipeline collect-only  # Data collection only
python run_agent.py --pipeline report-only   # Report generation only
python run_agent.py --pipeline publish-only  # License + dashboard + git publish
python run_agent.py --agent product_manager  # Run a single agent
python run_agent.py --chat "your question"   # AI analyst Q&A
python run_agent.py --dry-run --pipeline daily  # Preview without changes
```

### Data Collectors

```bash
python run_collectors.py --all                          # Run all collectors
python run_collectors.py --collector google_news_rss    # Run one collector
python run_collectors.py --all --dry-run                # Preview only
python run_collectors.py --all --force                  # Ignore incremental state
```

Available collectors: `google_news_rss`, `techcrunch_rss`, `bls_survival_rates`, `failory_scraper`, `reshoring_pdf`, `github_deep`, `reddit_stream`, `hn_live`, `arxiv`, `stackoverflow`, `producthunt`, `twitter`, `website_monitor`, `npm_pypi`, `opencorporates`, `regulatory`, `sec_edgar`, `newsletter`, `funding_events`, `patent`, `social_media`, `github_trends`, `crunchbase`, `job_postings`

### Reports

```bash
python run_report.py                              # Generate full report
python run_report.py --output my_report.md        # Custom output path
```

### Tests

```bash
python -m pytest tests/ -v                        # Run all 968 tests
python -m pytest tests/test_twitter.py -v         # Run specific test file
python -m pytest tests/ -k "test_search" -v       # Run tests matching pattern
python -m pytest tests/ --tb=short                # Shorter tracebacks
```

---

## Your Current Database

```
┌──────────────────────────────────────────────────────────┐
│  DATABASE: startup_research                              │
│  TABLES: 85                                              │
│                                                          │
│  Data loaded:                                            │
│    • 163 failed startups                                 │
│    • 943 news articles                                   │
│    • 105 collection runs                                 │
│    • BLS survival rates                                  │
│    • Failure reason taxonomy                             │
│    • Reshoring data                                      │
│    • Revival industries                                  │
│    • Geographic hotspots                                 │
│                                                          │
│  Schema version: 22                                      │
│  Connection: root@localhost:3306 (no password)           │
└──────────────────────────────────────────────────────────┘
```

---

## Quick Test — Verify Everything Works

```bash
# 1. Tests pass
python -m pytest tests/ --tb=no -q
# Expected: 964 passed, 4 skipped

# 2. API server starts
python api_server.py &
curl http://localhost:8000/api/health
# Expected: {"status":"healthy","database":"connected"}
# Then: Ctrl+C to stop

# 3. Chat with AI analyst (requires Ollama running)
python run_agent.py --chat "What are the top failure reasons?"

# 4. Run a quick collection
python run_collectors.py --collector google_news_rss
```

---

## What To Do Next (Sprint 1 — Parallel Plan)

Per the parallel sprint plan at `docs/sprints/parallel-sprint-plan.md`:

| Stream | Agent | First Tasks |
|---|---|---|
| **A: DevOps** | `devops_engineer` | T-001 Git commit, T-003 .gitignore, T-004-T-006 backup |
| **B: Software** | `software_engineer` | T-007 Fix tests ✅ (done), T-008 Fix warnings ✅ (done), T-011 Seed data |
| **C: UX** | `ux_designer` | T-002 LICENSE ✅ (exists), T-010 .env.example ✅ (exists), T-019 Feedback |
| **D: PM** | `product_manager` | T-009 .env.example, T-021 Launch post, T-023 HN post |

---

*Last updated: June 6, 2026*
