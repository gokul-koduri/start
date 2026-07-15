# Minimal Work Scope — Ship to Production on a Low-Resource Machine

> Purpose: Define exactly what to build, test, and deploy without overloading
> your laptop. Only work on items marked **NOW**. Items marked **LATER** are
> deferred until cloud infrastructure is running.

---

## Development Environment (Your Laptop)

### Run This — ~1.5 GB RAM
```bash
# Start only MySQL + Redis
docker compose -f docker-compose.dev.yml up -d

# Run API server locally
make dev-api

# Run tests
make dev-test
```

### Do NOT Run Locally
| Service | RAM | Why Skip | What To Do Instead |
|---|---|---|---|
| Ollama (LLM) | 4 GB | Use Claude/GPT API in production | Stub LLM calls in dev |
| Kafka/Redpanda | 1 GB | Only needed for real-time streaming | Skip stream_processor |
| Elasticsearch | 1 GB | MySQL fulltext search is sufficient for MVP | Skip in dev |
| ClickHouse | 1 GB | Analytics, not core functionality | Skip in dev |
| TimescaleDB | 512 MB | Time-series, not core functionality | Skip in dev |
| Qdrant | 512 MB | Vector search, nice-to-have | Skip in dev |

**Total saved: ~8 GB RAM**

---

## Work Priority: NOW vs LATER

### Tier 1 — NOW (Ship MVP)

These are the minimum tasks to get a working, deployable product.

#### Sprint 1: Launch MVP (DO THIS)
- [ ] T-001: Commit all current code to git
- [x] T-002: Create LICENSE file (MIT)
- [x] T-003: Fix 12 failing tests
- [x] T-004: Create complete .env.example
- [ ] T-005: Seed database with demo data (pending local MySQL/Docker daemon)
- [ ] T-006: API server runs with MySQL + Redis only (pending local MySQL/Docker daemon)
- [x] T-007: Static dashboard (site/index.html) serves from API
- [ ] T-008: Deploy to Railway (uses railway.Dockerfile)

#### Core Features (Required for V1.0)
- [ ] API endpoints: health, stats, startups, news, score, chat
- [ ] Static dashboard with live data from API
- [ ] Daily pipeline: collect + score + publish to dashboard
- [ ] Email digest of top opportunities
- [ ] Basic auth (JWT) on API endpoints
- [ ] Watchlist + alerts

#### Agents to Keep Active (Core 12)
| Agent | File | Why |
|---|---|---|
| AI Analyst | `ai_analyst_agent.py` | Main chat/query interface |
| Collection Agent | `collection_agent.py` | Data collection orchestrator |
| Failure Pattern | `failure_pattern_agent.py` | Core analysis |
| Opportunity Pipeline | `opportunity_pipeline_agent.py` | Core scoring |
| Sentiment Agent | `sentiment_agent.py` | News sentiment |
| Dashboard Agent | `dashboard_agent.py` | Dashboard updates |
| Email Digest | `email_digest_agent.py` | Email reports |
| Watchlist Alert | `watchlist_alert_agent.py` | User alerts |
| Orchestrator | `orchestrator.py` | Pipeline coordination |
| Risk Scorer | `risk_scorer_agent.py` | Risk scoring |
| Survival Analysis | `survival_analysis_agent.py` | BLS analysis |
| News Intelligence | `news_intelligence_agent.py` | News collection |

### Tier 2 — LATER (After Cloud Deployment)

These are valuable but not required for initial ship.

#### Deferred Sprints
- Sprint 2: Core Infrastructure (Kafka, stream processing) — LATER
- Sprint 3: Feedback + Analytics (ClickHouse) — LATER
- Sprint 4: Auth + Security (full OAuth, rate limiting) — LATER
- Sprint 5: Watchlists + Alerts (real-time) — LATER
- Sprint 6: Export + Integrations — LATER
- Sprint 7: Pro Tier + Billing (Stripe) — LATER
- Sprint 8: Polish + V1 Release — NOW (minimal version)

#### Deferred Agents (50 agents — keep code, don't actively develop)
All NLP, ML, knowledge graph, semantic search, topic modeling, cohort,
competitive landscape, geographic strategy, technology stack, and AI dev team
agents. They work but aren't getting new features until cloud is up.

#### Deferred Infrastructure
- [ ] Kafka/Redpanda event bus
- [ ] Elasticsearch full-text search
- [ ] ClickHouse analytics
- [ ] TimescaleDB time-series
- [ ] Qdrant vector search
- [ ] Bytewax stream processing
- [ ] Ollama local LLM

---

## Production Deployment (Cloud — Railway Recommended)

Railway supports your current `railway.Dockerfile`. Deploy there:

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Deploy
railway up

# Add MySQL plugin in Railway dashboard
# Add Redis plugin in Railway dashboard
```

### Production Architecture (on Railway)
```
railway.Dockerfile → API Server (FastAPI)
                    → Pipeline (daily cron)
                    → Email Worker
Railway MySQL     → Primary database
Railway Redis     → Cache + queue
```

That's it. 3 containers + 2 managed services. No Ollama, no Kafka, no ES.
Use Claude/GPT API for LLM features instead of local Ollama.

---

## RAM Budget

| Environment | Services | RAM |
|---|---|---|
| **Dev (laptop)** | MySQL + Redis | ~1.5 GB |
| **Prod (Railway)** | API + Pipeline + Email + MySQL + Redis | ~2 GB (Railway manages) |
| **Full stack (later)** | All 14 services | ~10 GB (cloud only) |

---

## Quick Commands

```bash
# Development (laptop-friendly)
make dev-up        # Start MySQL + Redis
make dev-api       # Run API server
make dev-test      # Run tests
make dev-down      # Stop containers

# Production (cloud)
make prod-deploy   # Deploy to Railway
make prod-logs     # View production logs

# Original full stack (cloud only, DO NOT run on laptop)
docker compose up -d
```
