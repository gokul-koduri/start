# 📝 Document Important Things — Architecture, APIs, Deployment, Troubleshooting

> "Code tells you HOW. Documentation tells you WHY."
> — Every senior engineer who had to maintain someone else's code

---

## Why This Document Exists

Your project has **1 contributor**, **bus factor = 1**, and **40 of 40 commits** by one person.
That person is you. In 6 months, you won't remember why you chose Bytewax over Flink, why MySQL instead of PostgreSQL, or why the WebSocket polls MySQL instead of consuming Kafka.

**Documentation isn't for other people. It's for future-you.**

---

## What You Already Have

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  37+ MARKDOWN FILES IN THIS PROJECT (930 KB+)                       │
│                                                                      │
│  ✅ DECISION DOCUMENTS                                               │
│     DOCUMENT_DECISIONS.md  — 20 FRs, 12 NFRs, 11 ADRs              │
│     CODING_STANDARDS.md    — Naming, structure, reuse, comments     │
│     VERSION_CONTROL.md     — Git conventions, branching, commits    │
│                                                                      │
│  ✅ ARCHITECTURE DOCS                                                │
│     DESIGN_BEFORE_CODING.md — System design, DB, API, security      │
│     SOLUTION_DESIGN.md       — 7-layer architecture                 │
│     REALTIME_ARCHITECTURE.md — Real-time technical blueprint        │
│     OPPORTUNITY_INTELLIGENCE_PLATFORM.md — Project vision           │
│     ARCHITECTURE_PLAN.md     — Architecture overview                │
│                                                                      │
│  ✅ PROCESS DOCS                                                     │
│     DEPLOYMENT_GUIDE.md    — Local/Docker/production deployment     │
│     MAINTENANCE_PLAN.md    — Bug fixes, updates, patches            │
│     TESTING_STRATEGY.md    — 7-stage testing, 699 tests             │
│     RISK_MANAGEMENT.md     — 21 risks, mitigation plans             │
│     WORK_PLAN.md           — 107 tasks, 8 sprints, 16 weeks        │
│     MVP_PLAN.md            — 2-week MVP build plan                  │
│                                                                      │
│  ✅ USER/DEV DOCS                                                    │
│     API_DOCUMENTATION.md   — 34 endpoints with examples             │
│     AGENT_DEVELOPMENT_GUIDE.md — How to build/test agents          │
│     HOW_IT_WORKS.md        — Step-by-step process                   │
│     USE_CASES.md           — 10 real-world scenarios                │
│     GLOSSARY.md            — Every term explained                   │
│     CONTRIBUTING.md        — Community contribution guide           │
│                                                                      │
│  ✅ BUSINESS DOCS                                                    │
│     PLAN_AND_MODEL.md      — Business plan + model                  │
│     PITCH_DECK.md          — 15-slide investor deck                 │
│     FINANCIAL_MODEL.md     — 5-year P&L                             │
│     ONE_PAGER.md           — Executive summary                      │
│     COMPETITIVE_ANALYSIS.md — vs Crunchbase, PitchBook, Tracxn      │
│     GTM_STRATEGY.md        — Go-to-market playbook                  │
│                                                                      │
│  ✅ PROBLEM/FEATURE DOCS                                             │
│     PROBLEM_DEFINITION.md  — 3 connected problems                   │
│     PROBLEM_FEATURE_MAP.md — Every feature mapped to a problem     │
│     GOALS_AND_PRIORITIES.md — 5 goals, 25 outcomes                 │
│     BUILD_PLAN.md          — 53 FRs + 14 NFRs                      │
│                                                                      │
│  ✅ SECURITY/MONITORING                                              │
│     SECURITY_FROM_DAY_ONE.md — Auth, encryption, secrets           │
│     MONITOR_PRODUCTION.md    — Logs, errors, metrics, alerts       │
│     PROGRESS_MONITORING_TOOLS.md — Free Jira alternatives          │
│                                                                      │
│  ✅ SCRIPTS                                                          │
│     scripts/backup_db.sh        — Daily MySQL backup               │
│     scripts/restore_db.sh       — Database restore                  │
│     scripts/security_scan.sh    — pip-audit + bandit + trivy        │
│                                                                      │
│  ✅ GITHUB                                                           │
│     .github/ISSUE_TEMPLATE/bug_report.yml     — Bug form           │
│     .github/ISSUE_TEMPLATE/feature_request.yml — Feature form      │
│     .github/dependabot.yml       — Auto dependency updates         │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

**But here's the gap:** These are all *planning* documents. What's missing is the **living documentation** — the docs that get updated with every deploy, every incident, every architectural change.

---

## Part 1: Architecture Decisions — ADRs

---

### 1.1 What ADRs Are

An **Architecture Decision Record** (ADR) captures a single decision:

```
1. WHAT we decided
2. WHY we decided it
3. WHAT alternatives we considered
4. WHAT consequences this creates
```

### 1.2 Your 11 Existing ADRs (from DOCUMENT_DECISIONS.md)

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  ADR       DECISION                    STATUS                       │
│  ───       ─────────                   ──────                       │
│  ADR-001   Python 3.12                 ✅ Accepted                  │
│  ADR-002   MySQL 8.0                   ✅ Accepted                  │
│  ADR-003   FastAPI                      ✅ Accepted                  │
│  ADR-004   Ollama for LLM              ✅ Accepted                  │
│  ADR-005   Bytewax for streaming       ✅ Accepted                  │
│  ADR-006   Kappa architecture          ✅ Accepted                  │
│  ADR-007   Redpanda (Kafka-compatible) ✅ Accepted                  │
│  ADR-008   Qdrant for vectors          ✅ Accepted                  │
│  ADR-009   all-MiniLM-L6-v2 embeddings ✅ Accepted                  │
│  ADR-010   spaCy for NER              ✅ Accepted                  │
│  ADR-011   Docker Compose             ✅ Accepted                  │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 1.3 ADR Template — Use For Every New Decision

```markdown
# ADR-NNN: [TITLE]

**Date**: YYYY-MM-DD
**Status**: Proposed | Accepted | Deprecated | Superseded by ADR-XXX
**Decision maker**: [Name]

## Context

[What is the issue that we're seeing that is motivating this decision?]

## Decision

[What is the change that we're proposing/making?]

## Alternatives Considered

### Option A: [Name]
- Pros: ...
- Cons: ...
- Verdict: ...

### Option B: [Name]
- Pros: ...
- Cons: ...
- Verdict: ...

## Consequences

### Positive
- ...

### Negative
- ...

### Risks
- ...

## References
- [Link to relevant discussion, issue, or document]
```

### 1.4 ADRs Still Needed

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  ADR       DECISION TO DOCUMENT          WHEN TO WRITE              │
│  ───       ──────────────────          ──────────────              │
│  ADR-012   bcrypt for passwords         Before auth implementation  │
│  ADR-013   slowapi for rate limiting    Before rate limiting work   │
│  ADR-014   Caddy for TLS               Before HTTPS setup          │
│  ADR-015   Stripe for payments          Before Pro tier (Sprint 7)  │
│  ADR-016   Pydantic for validation      Before input validation     │
│  ADR-017   Agent auto-discovery         Before orchestrator refactor│
│  ADR-018   Connection pooling           Before DB pool work         │
│  ADR-019   Structured JSON logging      Before monitoring setup     │
│  ADR-020   MySQL error_log for errors   Before error tracking       │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 1.5 ADR Workflow

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  WHEN                         ACTION                                │
│  ────                         ──────                                │
│  Before making a decision     Write ADR as "Proposed"               │
│  After team discussion        Update ADR as "Accepted"              │
│  If decision reversed         Mark as "Deprecated", link to new     │
│  Every sprint review          Check: any undocumented decisions?    │
│                                                                      │
│  RULE: If you spent >30 minutes deciding something, write an ADR.   │
│  RULE: If someone asks "why did we...", the answer is in an ADR.    │
│  RULE: ADRs are immutable — never edit an Accepted ADR.             │
│        If context changes, write a new ADR that supersedes it.      │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Part 2: API Specifications — Living Documentation

---

### 2.1 Current State

```
✅ API_DOCUMENTATION.md — 34 endpoints documented with curl examples
✅ DESIGN_BEFORE_CODING.md — 34 existing + 25 new endpoints listed

❌ No OpenAPI/Swagger spec file (FastAPI auto-generates, but no custom docs)
❌ No response schemas (only example curl commands)
❌ No error response documentation
❌ No authentication documentation in API docs
❌ No changelog for API changes
```

### 2.2 FastAPI Auto-Docs — Enhance What You Have

FastAPI generates Swagger UI at `/docs` and ReDoc at `/redoc`. Enhance it:

```python
# ═══ Add to api_server.py ═══

from fastapi import FastAPI

app = FastAPI(
    title="Opportunity Intelligence Platform API",
    description="""
    Real-time startup intelligence: scores, failure patterns, market signals.

    ## Authentication
    - **Public endpoints**: No auth needed (search, browse, chat with limits)
    - **Authenticated endpoints**: Send `Authorization: Bearer <jwt_token>`
    - **API keys**: Send `X-API-Key: oip_xxxxxxxx` header

    ## Rate Limits
    | Tier | Requests/min | Chat/min | Score/min |
    |---|---|---|---|
    | Anonymous | 30 | 2 | 2 |
    | Free | 60 | 5 | 5 |
    | Pro | 1000 | 100 | 100 |

    ## Quick Start
    ```bash
    # Search for a startup
    curl http://localhost:8000/api/search?q=Tesla

    # Chat about startup failures
    curl -X POST http://localhost:8000/api/chat \\
      -H "Content-Type: application/json" \\
      -d '{"question": "Why do EV startups fail?"}'

    # Score a startup
    curl -X POST http://localhost:8000/api/score \\
      -H "Content-Type: application/json" \\
      -d '{"sector": "EV", "funding_usd": 50000000}'
    ```
    """,
    version="1.0.0",
    contact={
        "name": "Opportunity Intelligence Platform",
        "url": "https://github.com/gokul-koduri/start",
    },
    license_info={
        "name": "MIT",
    },
    servers=[
        {"url": "http://localhost:8000", "description": "Local development"},
        {"url": "https://yourdomain.com", "description": "Production"},
    ],
)
```

### 2.3 API Changelog — Track Every Change

```markdown
# ═══ API_CHANGELOG.md — New file ═══

# API Changelog

All notable changes to the API are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
- POST /api/auth/register — User registration
- POST /api/auth/login — User login with JWT
- POST /api/auth/logout — Session invalidation
- GET /api/watchlist — List user's watchlist (auth required)
- POST /api/watchlist — Add to watchlist (auth required)
- GET /api/metrics/business — Business metrics (admin only)
- GET /api/health?detailed=1 — Extended health check

### Changed
- POST /api/score now accepts Pydantic ScoreRequest (not raw dict)
- POST /api/chat now accepts Pydantic ChatRequest (not raw dict)
- GET /api/health now checks MySQL, Redis, Kafka, Ollama, Qdrant, ES
- POST /api/auth/login rate limited to 10/min

### Fixed
- CORS now uses whitelist from CORS_ORIGINS env var (not *)
- WebSocket /ws/live now requires JWT token in query param

## [0.9.0] - 2026-06-05

### Added
- 34 API endpoints for search, score, chat, data access
- WebSocket /ws/live for real-time updates
- Prometheus metrics registry
- Health check endpoint

### Known Issues
- WebSocket polls MySQL instead of consuming Kafka
- No input validation on POST /api/score, /api/chat, /api/ml/predict
- CORS allows all origins (*)
```

### 2.4 Endpoint Documentation Template

For every new endpoint, fill this in:

```markdown
### POST /api/watchlist

**Purpose**: Add a startup to the authenticated user's watchlist.

**Authentication**: Required (JWT Bearer token)

**Rate Limit**: 60 requests/minute (Free tier)

**Request Body**:
```json
{
  "entity_name": "Neuromorphic Labs",
  "entity_type": "company",        // optional, default "company"
  "notes": "Interesting AI chip startup",  // optional
  "alert_threshold": 75.0           // optional, default 10.0
}
```

**Response 201**:
```json
{
  "data": {
    "id": 42,
    "entity_name": "Neuromorphic Labs",
    "added_at": "2026-06-05T12:00:00Z"
  },
  "meta": {"request_id": "uuid"}
}
```

**Response 401**: `{ "error": {"code": "UNAUTHORIZED", "message": "Authentication required"} }`
**Response 409**: `{ "error": {"code": "CONFLICT", "message": "Already on watchlist"} }`
**Response 422**: `{ "error": {"code": "VALIDATION_ERROR", "message": "..."} }`

**curl**:
```bash
curl -X POST http://localhost:8000/api/watchlist \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"entity_name": "Neuromorphic Labs"}'
```
```

---

## Part 3: Deployment Process — Step by Step

---

### 3.1 Deployment Checklist — Every Release

```markdown
# ═══ DEPLOYMENT_CHECKLIST.md — New file ═══

# Deployment Checklist

Use this checklist for EVERY deployment to production.

## Pre-Deploy (30 minutes before)

- [ ] All tests pass: `python -m pytest tests/ -v`
- [ ] Security scan clean: `bash scripts/security_scan.sh`
- [ ] Database backup completed: `bash scripts/backup_db.sh`
- [ ] Review git diff since last deploy: `git log --oneline v0.9.0..HEAD`
- [ ] Check for new environment variables in .env.example
- [ ] Verify .env.production has all required variables
- [ ] Check disk space: `df -h` (need >20% free)
- [ ] Notify users if there will be downtime (even 1 minute)

## Deploy

- [ ] SSH into production server
- [ ] `cd /path/to/project`
- [ ] `git pull origin main`
- [ ] `git checkout v1.x.x` (use tag, not branch)
- [ ] Install new dependencies: `pip install -r requirements.txt`
- [ ] Run database migrations: `python scripts/migrate_v16_to_v17.sql`
- [ ] Restart services: `docker compose down && docker compose up -d`
- [ ] Wait 30 seconds for services to start
- [ ] Check health: `curl http://localhost:8000/api/health?detailed=1`

## Post-Deploy (immediately after)

- [ ] Verify API responds: `curl http://localhost:8000/api/health`
- [ ] Verify dashboard loads: `curl http://localhost:8501`
- [ ] Check MySQL connectivity: `docker exec oip-mysql mysql -e "SELECT 1"`
- [ ] Check Redis: `docker exec oip-redis redis-cli ping`
- [ ] Check Ollama: `curl http://localhost:11434/api/tags`
- [ ] Watch logs for 5 minutes: `docker compose logs -f --tail=100`
- [ ] Run smoke test: search, chat, score, WebSocket
- [ ] Check error_log for new errors: `SELECT * FROM error_log WHERE timestamp > NOW() - INTERVAL 10 MINUTE`
- [ ] Tag the release: `git tag -a v1.x.x -m "Release v1.x.x: description"`

## Rollback (if something goes wrong)

- [ ] `docker compose down`
- [ ] `git checkout v0.9.0` (previous tag)
- [ ] `docker compose up -d`
- [ ] Restore database if migration ran: `bash scripts/restore_db.sh <backup_file>`
- [ ] Verify rollback: `curl http://localhost:8000/api/health`
- [ ] Post-mortem within 24 hours
```

### 3.2 Deployment Runbook — First Production Deploy

```markdown
# ═══ DEPLOYMENT_RUNBOOK.md — New file ═══

# First Production Deployment Runbook

This is a step-by-step guide for the VERY FIRST deployment to a new VPS.

## Server Setup (one-time, 60 minutes)

### 1. Provision VPS
```bash
# DigitalOcean droplet: 4 CPU, 8 GB RAM, Ubuntu 22.04 ($24/mo)
# Or: Hetzner CX32 (4 vCPU, 8 GB, €8/mo — best value)
ssh root@your-server-ip
```

### 2. Install Docker
```bash
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker
```

### 3. Create deploy user
```bash
adduser deploy
usermod -aG docker deploy
su - deploy
```

### 4. Clone repository
```bash
git clone https://github.com/gokul-koduri/start.git ~/oip
cd ~/oip
```

### 5. Configure environment
```bash
cp .env.example .env
nano .env
# Set ALL variables (see .env.example for descriptions)
# CRITICAL: MYSQL_PASSWORD, JWT_SECRET, BACKUP_ENCRYPTION_KEY
```

### 6. Generate secrets
```bash
python3 -c "import secrets; print('JWT_SECRET=' + secrets.token_urlsafe(32))"
python3 -c "import secrets; print('BACKUP_ENCRYPTION_KEY=' + secrets.token_urlsafe(32))"
# Copy these into .env
```

### 7. Start services
```bash
docker compose up -d
docker compose logs -f  # Watch for errors
```

### 8. Verify
```bash
curl http://localhost:8000/api/health
# Should return {"status": "healthy", "database": "connected"}
```

### 9. Set up HTTPS with Caddy
```bash
# Add Caddy service to docker-compose.yml (see SECURITY_FROM_DAY_ONE.md)
# Set DOMAIN=yourdomain.com in .env
docker compose up -d caddy
# Caddy auto-provisions TLS certificate via Let's Encrypt
```

### 10. Set up cron jobs
```bash
crontab -e
# Add:
# Daily backup at 2 AM UTC
0 2 * * * cd /home/deploy/oip && bash scripts/backup_db.sh >> data/logs/cron.log 2>&1
# Daily metrics at 00:05 UTC
5 0 * * * cd /home/deploy/oip && python3 scripts/compute_daily_metrics.py >> data/logs/cron.log 2>&1
# Security scan weekly (Sunday 3 AM)
0 3 * * 0 cd /home/deploy/oip && bash scripts/security_scan.sh >> data/logs/cron.log 2>&1
# Alert checks every 5 minutes
*/5 * * * * cd /home/deploy/oip && python3 scripts/check_alerts.py >> data/logs/cron.log 2>&1
```

### 11. Set up UptimeRobot (5 minutes)
1. Go to https://uptimerobot.com
2. Create free account
3. Add monitor: `https://yourdomain.com/api/health` every 5 min
4. Add alert contact: your email

### 12. Done!
Your platform is live at `https://yourdomain.com`
```

### 3.3 Environment Matrix

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  ENVIRONMENT    PURPOSE         URL                    BRANCH        │
│  ───────────   ────────        ────                   ──────        │
│  Local          Development     http://localhost:8000   feature/*    │
│  Staging        Pre-release     https://stg.domain.com  develop      │
│  Production     Live            https://domain.com      main (tag)   │
│                                                                      │
│  ENVIRONMENT     ENVIRONMENT VAR   DB NAME             SECRETS       │
│  ──────────      ──────────────   ───────              ───────       │
│  Local           development       startup_research     .env file    │
│  Staging         staging           startup_staging      .env.staging │
│  Production      production        startup_prod         .env.prod    │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Part 4: Troubleshooting Steps — Incident Response

---

### 4.1 Incident Response Process

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  STEP    ACTION                     TIME TARGET                     │
│  ────    ───────                     ────────                       │
│  1.      DETECT — Alert fires        0 min (automated)             │
│  2.      ACKNOWLEDGE — Start investigating    <5 min               │
│  3.      DIAGNOSE — Find root cause         <15 min                │
│  4.      MITIGATE — Restore service         <30 min                │
│  5.      RESOLVE — Fix root cause          <24 hours               │
│  6.      POST-MORTEM — Document lessons    <48 hours               │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 4.2 Troubleshooting Playbook — Common Issues

```markdown
# ═══ TROUBLESHOOTING.md — New file ═══

# Troubleshooting Guide

## Quick Diagnostics (run these first)

```bash
# Check all service health
curl -s http://localhost:8000/api/health?detailed=1 | python3 -m json.tool

# Check Docker containers
docker compose ps

# Check recent logs
docker compose logs --tail=50 api
docker compose logs --tail=50 mysql
docker compose logs --tail=50 ollama

# Check disk space
df -h

# Check memory
free -h

# Check MySQL connections
docker exec oip-mysql mysql -e "SHOW PROCESSLIST"
docker exec oip-mysql mysql -e "SHOW STATUS LIKE 'Threads_connected'"
```

---

## Issue T-001: API Returns 503 "Database Unavailable"

**Symptoms**: All endpoints return 503, health check shows MySQL unhealthy

**Diagnosis**:
```bash
# Check if MySQL container is running
docker compose ps mysql

# Check MySQL logs
docker compose logs --tail=100 mysql

# Try connecting manually
docker exec oip-mysql mysql -u root -p$MYSQL_PASSWORD -e "SELECT 1"
```

**Common Causes**:

1. **MySQL crashed** (out of memory)
   ```bash
   # Check memory
   free -h
   # Restart MySQL
   docker compose restart mysql
   # Wait for healthcheck
   sleep 15
   curl http://localhost:8000/api/health
   ```

2. **Too many connections** (connection leak)
   ```bash
   # Check active connections
   docker exec oip-mysql mysql -e "SHOW STATUS LIKE 'Threads_connected'"
   # If >150, kill sleeping connections
   docker exec oip-mysql mysql -e "
     SELECT GROUP_CONCAT(CONCAT('KILL ',id,';') SEPARATOR ' ')
     FROM information_schema.processlist
     WHERE Command='Sleep' AND Time > 300
     INTO @kill_stmt;
     PREPARE stmt FROM @kill_stmt;
     EXECUTE stmt;
   "
   ```

3. **Schema migration needed**
   ```bash
   # Check current schema version
   docker exec oip-mysql mysql -e "SELECT * FROM schema_metadata"
   # Run migration
   docker exec oip-mysql mysql < scripts/migrate_v16_to_v17.sql
   ```

---

## Issue T-002: Ollama Timeout / Chat Not Responding

**Symptoms**: `/api/chat` returns 504 or hangs for >30 seconds

**Diagnosis**:
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Check if model is loaded
docker exec oip-ollama ollama list

# Check Ollama resource usage
docker stats oip-ollama --no-stream
```

**Common Causes**:

1. **Model not pulled**
   ```bash
   docker exec oip-ollama ollama pull llama3:8b
   # Takes ~5 minutes on first pull (4.7 GB)
   ```

2. **Out of memory** (llama3:8b needs ~6 GB RAM)
   ```bash
   # Check if OOM killed
   dmesg | grep -i "oom\|killed"
   # Solution: reduce context or use smaller model
   docker exec oip-ollama ollama pull llama3:instruct  # smaller
   ```

3. **GPU contention** (if using GPU)
   ```bash
   nvidia-smi
   # If another process is using GPU, wait or stop it
   ```

---

## Issue T-003: Collectors Not Running

**Symptoms**: No new data in `raw_signals` table for hours

**Diagnosis**:
```bash
# Check last collection run
docker exec oip-mysql mysql -e "
  SELECT collector_name, status, started_at, error_message
  FROM collection_runs
  ORDER BY started_at DESC LIMIT 10
"

# Check if scheduler is running (once built)
docker compose ps scheduler
docker compose logs --tail=50 scheduler
```

**Common Causes**:

1. **Scheduler crashed**
   ```bash
   docker compose restart scheduler
   ```

2. **API rate limited** (429 from external API)
   ```bash
   # Check collector logs for "429" or "rate limit"
   grep -i "rate\|429\|forbidden" data/logs/collector.log | tail -20
   # Solution: Reduce collector frequency in config/settings.yaml
   ```

3. **Network connectivity**
   ```bash
   # Test external API from container
   docker exec oip-api curl -s https://hacker-news.firebaseio.com/v0/newstories.json | head -100
   ```

---

## Issue T-004: High Memory Usage / OOM Killed

**Symptoms**: Docker containers restarting, `docker compose ps` shows unhealthy

**Diagnosis**:
```bash
# Check per-container memory
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.CPUPerc}}"

# Check system memory
free -h

# Check for OOM kills
dmesg | grep -i "oom\|killed process" | tail -10
```

**Solutions**:

| Container | Limit | If OOM | Fix |
|---|---|---|---|
| MySQL | 2 GB | Queries too large | Add `LIMIT` to queries |
| Ollama | 8 GB | Model too large | Use `llama3:instruct` (smaller) |
| Redis | 512 MB | Cache too full | Set `maxmemory-policy allkeys-lru` |
| API | 1 GB | Connection leak | Check connection pool |
| Streamlit | 512 MB | Caching too much | Reduce `@st.cache_data` TTL |

---

## Issue T-005: Disk Full

**Symptoms**: "No space left on device" errors, services crashing

**Diagnosis**:
```bash
# Check disk usage
df -h

# Find large files
du -sh /var/lib/docker/* | sort -rh | head -10
du -sh data/* | sort -rh | head -10

# Check Docker image sizes
docker images --format "table {{.Repository}}\t{{.Size}}"
```

**Solutions**:
```bash
# Clean Docker (safe, removes unused images/containers)
docker system prune -a --volumes

# Clean old logs
find data/logs/ -name "*.log" -mtime +30 -delete
find data/logs/ -name "*.log" -size +100M -exec truncate -s 0 {} \;

# Clean Docker logs
docker compose down
find /var/lib/docker/containers/ -name "*-json.log" -exec truncate -s 0 {} \;
docker compose up -d
```

---

## Issue T-006: WebSocket Disconnects

**Symptoms**: Dashboard not updating in real-time

**Diagnosis**:
```bash
# Check WebSocket endpoint
curl -i -N \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" \
  -H "Sec-WebSocket-Key: test" \
  http://localhost:8000/ws/live

# Check if Redis has stream metrics
docker exec oip-redis redis-cli GET stream:metrics
```

**Common Causes**:

1. **Redis down** (metrics source)
   ```bash
   docker compose restart redis
   ```

2. **WebSocket polls MySQL too slowly** (current architecture)
   - Fix: Implement Kafka consumer (see DESIGN_BEFORE_CODING.md R4)

3. **Proxy timeout** (if behind nginx/Caddy)
   - Add WebSocket timeout config to proxy

---

## Issue T-007: Tests Failing After Changes

**Symptoms**: `python -m pytest` shows failures

**Diagnosis**:
```bash
# Run with verbose output
python -m pytest tests/ -v --tb=long

# Run just the failing tests
python -m pytest tests/test_semantic_search.py -v

# Check if MySQL is accessible
python3 -c "from db.connection import get_connection; c=get_connection(); print('OK')"
```

**Common Causes**:

1. **Schema mismatch** (code expects v16, DB has v15)
   ```bash
   python3 -c "from db import schema; conn=get_connection(); schema.init_schema(conn)"
   ```

2. **Missing environment variables**
   ```bash
   # Compare .env with .env.example
   diff <(grep -v '^#' .env.example | grep -v '^$' | cut -d= -f1) \
        <(grep -v '^#' .env | grep -v '^$' | cut -d= -f1)
   ```

3. **Stale Python cache**
   ```bash
   find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
   python -m pytest tests/ -v
   ```
```

### 4.3 Post-Mortem Template

```markdown
# ═══ POST_MORTEM_YYYY-MM-DD.md — New file per incident ═══

# Post-Mortem: [INCIDENT TITLE]

**Date**: YYYY-MM-DD
**Duration**: X minutes/hours
**Severity**: P1 (critical) / P2 (high) / P3 (medium)
**Resolved by**: [Name]

## Timeline (all times UTC)

| Time | Event |
|---|---|
| HH:MM | Alert fired: [description] |
| HH:MM | Investigation started |
| HH:MM | Root cause identified: [description] |
| HH:MM | Mitigation applied: [what you did] |
| HH:MM | Service restored |
| HH:MM | Post-mortem written |

## Root Cause

[2-3 sentences explaining what went wrong and why]

## Impact

- **Users affected**: X users (Y% of active)
- **Data affected**: [any data loss or corruption]
- **Revenue affected**: $X (if applicable)
- **Error count**: X errors over Y minutes

## What Went Wrong

[The technical failure — be specific]

## What Went Right

[What monitoring/alerting caught it quickly]

## Action Items

| # | Action | Owner | Due Date | Status |
|---|---|---|---|---|
| 1 | [Fix the root cause] | [Name] | YYYY-MM-DD | TODO |
| 2 | [Add monitoring for this case] | [Name] | YYYY-MM-DD | TODO |
| 3 | [Update runbook with this scenario] | [Name] | YYYY-MM-DD | TODO |

## Lessons Learned

[1-3 sentences about what to do differently next time]
```

---

## Part 5: Documentation Maintenance — Keep It Alive

---

### 5.1 The Documentation Rot Problem

Documentation goes stale in weeks. Code changes daily. Without a system, docs become lies.

### 5.2 Documentation Review Schedule

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  FREQUENCY    WHAT TO REVIEW          WHO        WHEN               │
│  ──────────   ──────────────          ────        ────               │
│                                                                      │
│  Every PR     README.md quick check   Author     Before merge       │
│  Weekly       API_CHANGELOG.md        Author     Monday morning     │
│  Biweekly     TROUBLESHOOTING.md      Author     After incidents    │
│  Monthly      All ADRs (new needed?)  Author     1st of month       │
│  Monthly      DEPLOYMENT_CHECKLIST    Author     1st of month       │
│  Quarterly    Full doc audit          Author     Start of quarter   │
│  On release   VERSION in API docs     Author     Tag time           │
│  On incident  TROUBLESHOOTING.md      Author     Within 48 hours    │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 5.3 Freshness Check — Automated

```python
# ═══ NEW FILE: scripts/check_doc_freshness.py ═══

"""Check if documentation is up to date. Run weekly via cron."""

import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

DOCS_DIR = Path(".")

# Files that should be updated at least monthly
MONTHLY_DOCS = [
    "STATUS.md",
    "API_CHANGELOG.md",
    "TROUBLESHOOTING.md",
]

# Files that should exist
REQUIRED_DOCS = [
    "README.md",
    "DEPLOYMENT_GUIDE.md",
    "API_DOCUMENTATION.md",
    "CONTRIBUTING.md",
    ".env.example",
    "TROUBLESHOOTING.md",
    "API_CHANGELOG.md",
]

def check_freshness():
    """Check doc freshness and print report."""
    print("=" * 60)
    print("DOCUMENTATION FRESHNESS CHECK")
    print("=" * 60)

    # Check required files exist
    print("\n📄 Required files:")
    for doc in REQUIRED_DOCS:
        path = DOCS_DIR / doc
        if path.exists():
            age_days = (datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)).days
            status = "✅" if age_days < 60 else "⚠️ STALE"
            print(f"  {status} {doc} ({age_days} days old)")
        else:
            print(f"  ❌ MISSING {doc}")

    # Check monthly docs
    print("\n📅 Monthly freshness:")
    for doc in MONTHLY_DOCS:
        path = DOCS_DIR / doc
        if path.exists():
            age_days = (datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)).days
            status = "✅" if age_days < 31 else "⚠️ NEEDS UPDATE"
            print(f"  {status} {doc} ({age_days} days old)")

    # Check README has installation instructions
    print("\n📋 README sections:")
    readme = (DOCS_DIR / "README.md").read_text() if (DOCS_DIR / "README.md").exists() else ""
    sections = ["Installation", "Usage", "API", "Contributing", "License"]
    for section in sections:
        if section.lower() in readme.lower():
            print(f"  ✅ Has '{section}' section")
        else:
            print(f"  ⚠️ Missing '{section}' section")

    # Check .env.example has all env vars used in code
    print("\n🔐 .env.example coverage:")
    env_example = (DOCS_DIR / ".env.example").read_text() if (DOCS_DIR / ".env.example").exists() else ""
    env_vars_in_example = set(re.findall(r'^([A-Z_]+)=', env_example, re.MULTILINE))
    env_vars_in_code = set()
    for pyfile in Path(".").rglob("*.py"):
        if ".git" in str(pyfile) or "__pycache__" in str(pyfile):
            continue
        try:
            content = pyfile.read_text()
            env_vars_in_code.update(re.findall(r'environ\.get\("([A-Z_]+)"', content))
            env_vars_in_code.update(re.findall(r'os\.environ\["([A-Z_]+)"\]', content))
        except:
            pass

    missing = env_vars_in_code - env_vars_in_example
    if missing:
        print(f"  ⚠️ {len(missing)} env vars used in code but missing from .env.example:")
        for var in sorted(missing):
            print(f"    - {var}")
    else:
        print(f"  ✅ All {len(env_vars_in_code)} env vars documented")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    check_freshness()
```

### 5.4 New Document Template

Every new document starts with this header:

```markdown
# [EMOJI] [TITLE]

> One-line description of what this document covers.

---

## Metadata

| Field | Value |
|---|---|
| **Owner** | [Name] |
| **Created** | YYYY-MM-DD |
| **Last Updated** | YYYY-MM-DD |
| **Review Frequency** | Monthly / Quarterly / On-change |
| **Related Docs** | [Links to related documents] |

---

## [Content starts here]
```

---

## Part 6: Documentation Index — Master Map

---

### 6.1 Complete Documentation Map

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  CATEGORY          FILE                              SIZE    AUDIENCE│
│  ────────          ────                              ────    ────────│
│                                                                      │
│  ▶ GETTING STARTED                                                   │
│                    README.md                          25 KB   Everyone│
│                    ONE_PAGER.md                        2 KB   Execs   │
│                    STATUS.md                           5 KB   Team    │
│                    GLOSSARY.md                        11 KB   Everyone│
│                    CONTRIBUTING.md                    2 KB   Devs    │
│                                                                      │
│  ▶ VISION & STRATEGY                                                 │
│                    PLAN_AND_MODEL.md                  54 KB   Execs   │
│                    PITCH_DECK.md                      16 KB   Investors│
│                    FINANCIAL_MODEL.md                 12 KB   Execs   │
│                    COMPETITIVE_ANALYSIS.md            17 KB   Strategy│
│                    GTM_STRATEGY.md                    38 KB   Marketing│
│                    OPPORTUNITY_INTELLIGENCE_PLATFORM  65 KB   Everyone│
│                                                                      │
│  ▶ PROBLEM & PRODUCT                                                 │
│                    PROBLEM_DEFINITION.md              40 KB   Product │
│                    PROBLEM_FEATURE_MAP.md             24 KB   Product │
│                    GOALS_AND_PRIORITIES.md            25 KB   Product │
│                    USE_CASES.md                       37 KB   Product │
│                    HOW_IT_WORKS.md                    46 KB   Users   │
│                                                                      │
│  ▶ PLANNING                                                          │
│                    BUILD_PLAN.md                      48 KB   Devs    │
│                    WORK_PLAN.md                       58 KB   Devs    │
│                    MVP_PLAN.md                        38 KB   Devs    │
│                    TECHNICAL_ROADMAP.md               14 KB   Devs    │
│                    ROADMAP.md                         13 KB   Everyone│
│                                                                      │
│  ▶ ARCHITECTURE & DESIGN                                             │
│                    DESIGN_BEFORE_CODING.md            77 KB   Devs    │
│                    SOLUTION_DESIGN.md                108 KB   Devs    │
│                    REALTIME_ARCHITECTURE.md           61 KB   Devs    │
│                    ARCHITECTURE_PLAN.md               35 KB   Devs    │
│                                                                      │
│  ▶ DEVELOPMENT                                                       │
│                    CODING_STANDARDS.md                47 KB   Devs    │
│                    AGENT_DEVELOPMENT_GUIDE.md         33 KB   Devs    │
│                    VERSION_CONTROL.md                 42 KB   Devs    │
│                    DOCUMENT_DECISIONS.md              86 KB   Devs    │
│                                                                      │
│  ▶ SECURITY & QUALITY                                                │
│                    SECURITY_FROM_DAY_ONE.md           71 KB   Devs    │
│                    TESTING_STRATEGY.md                74 KB   Devs    │
│                    RISK_MANAGEMENT.md                 76 KB   Devs    │
│                                                                      │
│  ▶ OPERATIONS                                                        │
│                    MONITOR_PRODUCTION.md              60 KB   Devs    │
│                    DEPLOYMENT_GUIDE.md                17 KB   DevOps  │
│                    MAINTENANCE_PLAN.md                80 KB   DevOps  │
│                    PROGRESS_MONITORING_TOOLS.md       69 KB   PMs     │
│                                                                      │
│  ▶ API                                                               │
│                    API_DOCUMENTATION.md               24 KB   Devs    │
│                    API_CHANGELOG.md (NEW)              —     Devs    │
│                                                                      │
│  ▶ FEEDBACK                                                          │
│                    FEEDBACK_STRATEGY.md               74 KB   Product │
│                                                                      │
│  ▶ TROUBLESHOOTING                                                   │
│                    TROUBLESHOOTING.md (NEW)             —     DevOps  │
│                    DEPLOYMENT_CHECKLIST.md (NEW)        —     DevOps  │
│                                                                      │
│  TOTAL: 37+ documents, ~930 KB+                                      │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Summary

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  4 AREAS                    WHAT WE BUILT / DEFINED                  │
│  ─────────                  ─────────────────────                    │
│                                                                      │
│  ARCHITECTURE DECISIONS     11 existing ADRs (ADR-001 to ADR-011)  │
│                              ADR template for future decisions       │
│                              9 more ADRs to write (ADR-012 to 020) │
│                              ADR workflow: Proposed → Accepted →    │
│                              Deprecated → Superseded                │
│                                                                      │
│  API SPECIFICATIONS          Enhanced FastAPI auto-docs (Swagger/   │
│                              ReDoc), API_CHANGELOG.md (Keep a       │
│                              Changelog format), endpoint template    │
│                              with request/response/error schemas    │
│                                                                      │
│  DEPLOYMENT PROCESS          Deployment checklist (pre/during/post), │
│                              first production runbook (12 steps),   │
│                              environment matrix (local/stage/prod), │
│                              rollback procedure                     │
│                                                                      │
│  TROUBLESHOOTING STEPS       7 common issues with diagnosis + fix:  │
│                              T-001 Database down                     │
│                              T-002 Ollama timeout                    │
│                              T-003 Collectors not running            │
│                              T-004 High memory / OOM                │
│                              T-005 Disk full                         │
│                              T-006 WebSocket disconnects            │
│                              T-007 Tests failing                    │
│                              + Post-mortem template                  │
│                                                                      │
│  MAINTENANCE                 Weekly doc review schedule,             │
│                              automated freshness check script,      │
│                              document template with metadata,       │
│                              master documentation index (37+ files) │
│                                                                      │
│  NEW FILES TO CREATE:                                                │
│  • API_CHANGELOG.md          — Track every API change                │
│  • TROUBLESHOOTING.md        — Common issues + fixes                 │
│  • DEPLOYMENT_CHECKLIST.md   — Pre/during/post deploy checklist     │
│  • POST_MORTEM_*.md          — One per incident                      │
│  • scripts/check_doc_freshness.py — Weekly freshness audit          │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

*Last updated: June 5, 2026*
*Cross-references: MONITOR_PRODUCTION.md, SECURITY_FROM_DAY_ONE.md, DESIGN_BEFORE_CODING.md, DEPLOYMENT_GUIDE.md, DOCUMENT_DECISIONS.md*
