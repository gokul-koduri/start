# 🏛️ Design Before Coding — Architecture, Contracts, Security, Scalability, Refactoring

> "Weeks of coding can save you hours of planning."
> — Unknown (but very true)

---

## What This Document Is

This is a **pre-coding design reference**. Before writing or refactoring a single line, everything is thought through:

1. **System Architecture** — How 207 files, 62 agents, 26 collectors, 76 tables, 34 endpoints fit together
2. **Database Design** — Every table, every index, every relationship, and 12 tables to ADD
3. **API Contracts** — Every endpoint's request/response schema, status codes, auth rules
4. **Security Requirements** — 15 threat vectors, 22 defenses, implementation-ready code
5. **Scalability Needs** — Load projections, bottlenecks, scaling plan from 1 to 10,000 users
6. **Refactoring Plan** — 47 specific refactoring targets with before/after code

---

## Part 1: System Architecture

---

### 1.1 Current Architecture — What Exists (207 Files, 83% Built)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                         CURRENT ARCHITECTURE (83% built)                    │
│                                                                             │
│  ┌─────────┐    ┌──────────────┐    ┌───────────────┐    ┌──────────────┐  │
│  │ 26       │    │ Kafka /      │    │ Bytewax       │    │ 62 AI Agents │  │
│  │Collectors├───>│ Redpanda     ├───>│ Stream        ├───>│ (Analysis +  │  │
│  │          │    │ (raw.signals)│    │ Pipeline      │    │  Scoring)    │  │
│  └─────────┘    └──────┬───────┘    └───────┬───────┘    └──────┬───────┘  │
│                        │                    │                    │           │
│                        │    ┌───────────────┘                    │           │
│                        │    │                                    │           │
│                        v    v                                    v           │
│                  ┌─────────────────────────────────────────────────────┐    │
│                  │                   MySQL 8.0                         │    │
│                  │              (76 tables, schema v16)                │    │
│                  └─────────────────────┬───────────────────────────────┘    │
│                                        │                                    │
│                  ┌─────────────────────┼───────────────────────┐            │
│                  │                     │                       │            │
│                  v                     v                       v            │
│           ┌──────────┐         ┌──────────┐           ┌──────────┐         │
│           │ FastAPI   │         │ Qdrant   │           │ Redis    │         │
│           │ API       │         │ Vector   │           │ Cache    │         │
│           │ (34 EPs)  │         │ Search   │           │ Metrics  │         │
│           └────┬──────┘         └──────────┘           └──────────┘         │
│                │                                                            │
│                v                                                            │
│           ┌──────────┐         ┌──────────┐           ┌──────────┐         │
│           │Streamlit │         │ Elastic  │           │ClickHouse│         │
│           │Dashboard │         │ Search   │           │ Analytics│         │
│           │ (11 pgs) │         │ (Fulltext│           │ (OLAP)   │         │
│           └──────────┘         └──────────┘           └──────────┘         │
│                                                                             │
│           ┌──────────┐         ┌──────────┐           ┌──────────┐         │
│           │ Ollama   │         │TimescaleDB│          │ Scheduler│         │
│           │ (LLM)    │         │ (Time-   │           │ (MISSING)│         │
│           │ llama3:8b│         │  series) │           │ ❌ NOT   │         │
│           └──────────┘         └──────────┘           │  BUILT   │         │
│                                                       └──────────┘         │
│                                                                             │
│  ❌ ALSO MISSING: Alert Consumer, Score Push (WebSocket), Feedback System  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Target Architecture — V1.0 (6 Layers)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                       TARGET V1.0 ARCHITECTURE                             │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        LAYER 1: DATA IN                             │    │
│  │                                                                     │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐          │    │
│  │  │Collector  │  │Collector │  │Collector │  │Collector │   26      │    │
│  │  │Scheduler  │  │Base      │  │Registry  │  │Config    │   Total   │    │
│  │  │(cron-like)│  │(ABC)     │  │(index)   │  │(YAML)    │           │    │
│  │  └─────┬────┘  └─────┬────┘  └─────┬────┘  └─────┬────┘          │    │
│  │        └──────────────┴──────┬───────┴──────────────┘               │    │
│  │                              v                                      │    │
│  │                    ┌──────────────────┐                             │    │
│  │                    │ Signal Normalizer │                             │    │
│  │                    │ (SignalEnvelope)  │                             │    │
│  │                    └────────┬─────────┘                             │    │
│  └─────────────────────────────┼──────────────────────────────────────┘    │
│                                v                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     LAYER 2: TRANSPORT                              │    │
│  │            ┌──────────────────────────────┐                         │    │
│  │            │    Kafka / Redpanda           │                         │    │
│  │            │  Topics:                      │                         │    │
│  │            │  • raw.signals    (in)        │                         │    │
│  │            │  • scores.updates (out)       │                         │    │
│  │            │  • alerts.triggered (out)     │                         │    │
│  │            │  • dead.letters   (err)       │                         │    │
│  │            │  • feedback.events (NEW)      │                         │    │
│  │            └──────────────┬───────────────┘                         │    │
│  └───────────────────────────┼────────────────────────────────────────┘    │
│                 ┌────────────┴────────────┐                                │
│                 v                         v                                │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                    LAYER 3: PROCESSING                            │    │
│  │   ┌─────────────────┐      ┌─────────────────┐                   │    │
│  │   │ Bytewax Stream  │      │ Batch Pipeline   │                   │    │
│  │   │ (Real-time)     │      │ (Orchestrator)   │                   │    │
│  │   │ Ingest → Enrich │      │ 56 Agents run    │                   │    │
│  │   │ → Aggregate →   │      │ sequentially     │                   │    │
│  │   │ Score → Output  │      │                  │                   │    │
│  │   └────────┬────────┘      └────────┬─────────┘                   │    │
│  │            └────────────┬────────────┘                             │    │
│  │                         v                                          │    │
│  │            ┌────────────────────────┐                              │    │
│  │            │   CompositeScorer      │                              │    │
│  │            │   (Stateless, shared)  │                              │    │
│  │            └────────────────────────┘                              │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                              v                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                       LAYER 4: STORAGE                             │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐          │    │
│  │  │ MySQL    │  │ Qdrant   │  │ Redis    │  │ Elastic  │          │    │
│  │  │ Primary  │  │ Vectors  │  │ Cache +  │  │ Fulltext │          │    │
│  │  │ (76+12   │  │ (384-dim)│  │ PubSub   │  │ Search   │          │    │
│  │  │  tables) │  │          │  │ Metrics  │  │          │          │    │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘          │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                              v                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     LAYER 5: ACCESS                                │    │
│  │  ┌──────────────────────────────────────────┐                      │    │
│  │  │           FastAPI (api_server.py)         │                      │    │
│  │  │  Middleware: CORS → Security → Rate Limit │                      │    │
│  │  │  → JWT Auth → Validation → Logging       │                      │    │
│  │  │  Endpoints: 34 + 15 new = 49             │                      │    │
│  │  └──────────────────────────────────────────┘                      │    │
│  │  ┌──────────────────────────────────────────┐                      │    │
│  │  │     WebSocket /ws/live                    │                      │    │
│  │  │     Reads Kafka scores.updates            │                      │    │
│  │  └──────────────────────────────────────────┘                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                              v                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    LAYER 6: PRESENTATION                           │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │    │
│  │  │ Streamlit    │  │ REST API     │  │ Webhooks     │            │    │
│  │  │ Dashboard    │  │ Consumers    │  │ (Outbound)   │            │    │
│  │  │ (14 pages)   │  │              │  │              │            │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘            │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  CROSS-CUTTING: Monitoring, Backup, Logging, CI/CD, Security Scanning      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.3 Module Dependency Graph

```
                     ┌───────────┐
                     │  config/  │   (settings.yaml, logging.yaml)
                     └─────┬─────┘
                           │
                     ┌─────┴─────┐
                     │    db/    │   (connection, schema, vector_store)
                     └─────┬─────┘
                           │
              ┌────────────┼────────────────┐
              │            │                │
        ┌─────┴─────┐ ┌───┴────┐    ┌──────┴──────┐
        │ ingestion/ │ │ scoring│    │    nlp/     │
        │(normalizer,│ │(scorer,│    │(embedding,  │
        │ kafka_prod)│ │ weights│    │ ner, etc.)  │
        └─────┬──────┘ └───┬────┘    └──────┬──────┘
              └────────────┼────────────────┘
                     ┌─────┴─────┐
                     │  stream/  │   (pipeline, operators, metrics)
                     └─────┬─────┘
              ┌────────────┼────────────────┐
        ┌─────┴─────┐ ┌───┴────┐    ┌──────┴──────┐
        │ collectors│ │ agents │    │  webhooks/  │
        │ (26)      │ │ (62)   │    │(dispatcher) │
        └───────────┘ └───┬────┘    └─────────────┘
                    ┌─────┴─────┐
                    │ api_server │   (+ api/v2/ routers)
                    └───────────┘

        ALSO: auth/ (JWT + RBAC + tenants)
              utils/ (http_client, text_normalization, rate_limiter, date_parsing)
              report/ (generator)  monitoring/ (metrics, health)
              scripts/ (backup, restore, security_scan)
```

### 1.4 Component Inventory — Built vs Missing

| Component | Status | Files | Notes |
|---|---|---|---|
| Collectors (26) | ✅ Built | 26 .py | All inherit BaseCollector |
| Stream Pipeline | ✅ Built | stream/ | 5-stage Bytewax dataflow |
| Scoring Engine | ✅ Built | scoring/ | CompositeScorer, stateless |
| Agents (62) | ✅ Built | agents/ | 6 to CUT, 4 to MERGE |
| API Server | ✅ Built | api_server | FastAPI, 34 endpoints |
| Auth (JWT + RBAC) | ✅ Built | auth/ | 3 roles, 30+ permissions |
| Database Schema | ✅ Built | db/ | 76 tables, schema v16 |
| NLP Pipeline | ✅ Built | nlp/ | Embeddings, NER, classifier |
| Docker Compose | ✅ Built | docker-compose | 11 services |
| **Collector Scheduler** | ❌ MISSING | — | No 24/7 scheduling |
| **Alert Consumer** | ❌ MISSING | — | Kafka → nobody reads |
| **Score Push (WS)** | ❌ MISSING | — | WS polls MySQL, not Kafka |
| **Feedback System** | ❌ MISSING | — | 0 feedback collection |
| **User Accounts** | ❌ MISSING | — | No users table |
| **Rate Limiting** | ❌ MISSING | — | No slowapi |
| **Security Headers** | ❌ MISSING | — | No middleware |
| **Input Validation** | ❌ MISSING | — | No sanitize function |

---

## Part 2: Database Design

---

### 2.1 Current Schema — 76 Tables in 12 Categories

- **SCHEMA VERSION**: 16
- **ENGINE**: InnoDB (all tables)
- **CHARSET**: utf8mb4 (all tables)
- **CONNECTION**: PyMySQL via `db/connection.py`, env vars for credentials

```
Category                          Tables
────────────────                  ──────
Tenant + System                   3  (tenants, api_webhooks, payment_events)
Core Data — Failed Startups       6  (failed_startups, failure_reasons_taxonomy, ...)
Core Data — Collected             15 (news_articles, sec_filings, github_trends, ...)
Core Data — Summary               2  (reshoring_summary_stats, geographic_hotspots)
Signals + Scoring                 4  (raw_signals, opportunity_scores, ...)
Analysis Results                  24 (analysis_failure_patterns, analysis_survival_trends, ...)
Knowledge Graph                   4  (kg_entity_types, kg_entities, kg_relationships, ...)
LLM Tracking                      6  (llm_pricing, ollama_usage_snapshots, ...)
Operations                        5  (collection_runs, agent_runs, alert_dispatches, ...)
Reports + Licenses                4  (generated_reports, user_licenses, ...)
Vector + Revival                  3  (vector_embeddings, revival_industries, ...)
```

### 2.2 Twelve Tables to ADD (Schema v17)

```sql
-- T1: users — User accounts
CREATE TABLE IF NOT EXISTS users (
    id              INT PRIMARY KEY AUTO_INCREMENT,
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL COMMENT 'bcrypt hash',
    display_name    VARCHAR(100),
    role            VARCHAR(20) NOT NULL DEFAULT 'viewer' COMMENT 'viewer, analyst, admin',
    tier            VARCHAR(20) NOT NULL DEFAULT 'free' COMMENT 'free, pro, enterprise',
    stripe_customer_id VARCHAR(255),
    last_login_at   DATETIME,
    is_active       TINYINT DEFAULT 1,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_users_email (email),
    INDEX idx_users_role (role),
    INDEX idx_users_tier (tier),
    INDEX idx_users_stripe (stripe_customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- T2: api_keys — Programmatic access tokens
CREATE TABLE IF NOT EXISTS api_keys (
    id              INT PRIMARY KEY AUTO_INCREMENT,
    user_id         INT NOT NULL,
    key_prefix      VARCHAR(8) NOT NULL COMMENT 'First 8 chars for identification',
    key_hash        VARCHAR(255) NOT NULL COMMENT 'SHA-256 of full key',
    name            VARCHAR(100),
    last_used_at    DATETIME,
    expires_at      DATETIME,
    is_active       TINYINT DEFAULT 1,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_apikeys_user (user_id),
    INDEX idx_apikeys_prefix (key_prefix)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- T3: watchlists — Saved startup tracking
CREATE TABLE IF NOT EXISTS watchlists (
    id              INT PRIMARY KEY AUTO_INCREMENT,
    user_id         INT NOT NULL,
    entity_name     VARCHAR(255) NOT NULL,
    entity_type     VARCHAR(50) DEFAULT 'company',
    notes           TEXT,
    tags            VARCHAR(500) COMMENT 'Comma-separated',
    alert_threshold FLOAT DEFAULT 10.0,
    added_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY uq_watchlist_user_entity (user_id, entity_name),
    INDEX idx_watchlist_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- T4: query_log — Search queries for feedback
CREATE TABLE IF NOT EXISTS query_log (
    id              INT PRIMARY KEY AUTO_INCREMENT,
    query           VARCHAR(500) NOT NULL,
    query_type      VARCHAR(20) NOT NULL DEFAULT 'search',
    results_count   INT DEFAULT 0,
    response_ms     INT,
    user_id         INT,
    session_id      VARCHAR(100),
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_querylog_query (query(100)),
    INDEX idx_querylog_created (created_at),
    INDEX idx_querylog_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- T5: chat_log — AI chat conversations
CREATE TABLE IF NOT EXISTS chat_log (
    id              INT PRIMARY KEY AUTO_INCREMENT,
    question        TEXT NOT NULL,
    answer          TEXT NOT NULL,
    model_used      VARCHAR(50),
    response_ms     INT,
    tokens_used     INT,
    user_id         INT,
    session_id      VARCHAR(100),
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_chatlog_created (created_at),
    INDEX idx_chatlog_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- T6: score_feedback — Thumbs up/down on scores
CREATE TABLE IF NOT EXISTS score_feedback (
    id              INT PRIMARY KEY AUTO_INCREMENT,
    entity_name     VARCHAR(255) NOT NULL,
    score_value     FLOAT NOT NULL,
    rating          TINYINT NOT NULL COMMENT '1 (bad) to 5 (great)',
    comment         TEXT,
    user_id         INT,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_scorefb_entity (entity_name),
    INDEX idx_scorefb_rating (rating),
    INDEX idx_scorefb_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- T7: feature_requests — User feature ideas
CREATE TABLE IF NOT EXISTS feature_requests (
    id              INT PRIMARY KEY AUTO_INCREMENT,
    title           VARCHAR(255) NOT NULL,
    description     TEXT,
    category        VARCHAR(50),
    upvotes         INT DEFAULT 0,
    status          VARCHAR(20) DEFAULT 'open' COMMENT 'open, planned, in_progress, done, declined',
    user_id         INT,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_featreq_status (status),
    INDEX idx_featreq_upvotes (upvotes)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- T8: alert_history — Alerts sent to users
CREATE TABLE IF NOT EXISTS alert_history (
    id              INT PRIMARY KEY AUTO_INCREMENT,
    user_id         INT,
    alert_type      VARCHAR(50) NOT NULL COMMENT 'score_change, high_value, digest',
    entity_name     VARCHAR(255),
    message         TEXT NOT NULL,
    channel         VARCHAR(20) COMMENT 'email, slack, webhook, in_app',
    status          VARCHAR(20) DEFAULT 'sent',
    sent_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_alerthist_user (user_id),
    INDEX idx_alerthist_type (alert_type),
    INDEX idx_alerthist_sent (sent_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- T9: score_history — Time-series for charts
CREATE TABLE IF NOT EXISTS score_history (
    id              INT PRIMARY KEY AUTO_INCREMENT,
    entity_name     VARCHAR(255) NOT NULL,
    entity_type     VARCHAR(50) DEFAULT 'company',
    composite_score FLOAT NOT NULL,
    signal_count    INT DEFAULT 0,
    trend_direction VARCHAR(20) DEFAULT 'stable',
    attribution_json TEXT,
    recorded_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_scorehist_entity_time (entity_name, recorded_at),
    INDEX idx_scorehist_entity (entity_name),
    INDEX idx_scorehist_time (recorded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- T10: user_sessions — Active JWT sessions
CREATE TABLE IF NOT EXISTS user_sessions (
    id              INT PRIMARY KEY AUTO_INCREMENT,
    user_id         INT NOT NULL,
    token_jti       VARCHAR(100) NOT NULL UNIQUE,
    ip_address      VARCHAR(45),
    user_agent      VARCHAR(500),
    expires_at      DATETIME NOT NULL,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_sessions_user (user_id),
    INDEX idx_sessions_jti (token_jti)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- T11: feedback_analysis — FeedbackAnalyzerAgent output
CREATE TABLE IF NOT EXISTS feedback_analysis (
    id              INT PRIMARY KEY AUTO_INCREMENT,
    period_start    DATETIME NOT NULL,
    period_end      DATETIME NOT NULL,
    top_queries     TEXT COMMENT 'JSON',
    avg_score_rating FLOAT,
    feature_requests_count INT,
    feature_requests_top TEXT COMMENT 'JSON',
    pain_points     TEXT COMMENT 'JSON',
    recommendations TEXT COMMENT 'JSON',
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_fbanalysis_period (period_start, period_end)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- T12: audit_log — Security audit trail
CREATE TABLE IF NOT EXISTS audit_log (
    id              BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id         INT,
    action          VARCHAR(100) NOT NULL COMMENT 'login, api_key.create, data.export',
    resource_type   VARCHAR(50),
    resource_id     INT,
    details         TEXT COMMENT 'JSON',
    ip_address      VARCHAR(45),
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_audit_user (user_id),
    INDEX idx_audit_action (action),
    INDEX idx_audit_created (created_at),
    INDEX idx_audit_resource (resource_type, resource_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 2.3 Entity Relationships

```
users ──1:N──> api_keys
users ──1:N──> watchlists
users ──1:N──> user_sessions
users ──1:N──> alert_history
users ──1:N──> audit_log
users ──1:N──> query_log
users ──1:N──> chat_log
users ──1:N──> score_feedback

opportunity_scores ──1:N──> score_history
opportunity_scores ──1:N──> score_feedback
opportunity_scores ──triggers──> alert_history
opportunity_scores ──triggers──> watchlists (score change alerts)

raw_signals ──scored──> opportunity_scores
raw_signals ──enriched──> analysis_* (24 tables)
kg_entities ──1:N──> kg_relationships
kg_entities ──1:N──> kg_entity_aliases
collection_runs ──tracks──> collectors
agent_runs ──tracks──> agents
```

### 2.4 Migration Strategy

- Keep `db/schema.py` for new tables (v17 → v18 → ...)
- Add migration SQL scripts for ALTER TABLE: `scripts/migrate_v16_to_v17.sql`
- Track version in `schema_metadata` table
- On startup: compare `schema_metadata.version` vs `_SCHEMA_VERSION`, warn if mismatch
- **Rules**: Always ADD columns, never remove. Use DEFAULT values. Test on backup first.

---

## Part 3: API Contracts

---

### 3.1 Design Principles

1. **RESTful**: Nouns in URLs, verbs in HTTP methods
2. **Consistent**: Same response shape for all endpoints
3. **Paginated**: All list endpoints support `?page=&per_page=`
4. **Auth-aware**: Public reads, JWT writes, API key for programmatic
5. **Rate-limited**: 60/min free, 1000/min pro

**Standard Response Shapes**:

```json
// Success (single)
{ "data": { ... }, "meta": { "request_id": "uuid", "timestamp": "ISO" } }

// Success (list)
{ "data": [...], "pagination": { "page": 1, "per_page": 20, "total": 150, "total_pages": 8 },
  "meta": { "request_id": "uuid", "timestamp": "ISO" } }

// Error
{ "error": { "code": "VALIDATION_ERROR", "message": "...", "details": { ... } },
  "meta": { "request_id": "uuid", "timestamp": "ISO" } }
```

**Status Codes**: 200 OK, 201 Created, 204 No Content, 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 409 Conflict, 422 Unprocessable, 429 Rate Limited, 500 Internal, 503 Unavailable

### 3.2 Public Endpoints (34 Existing)

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| GET | /api/health | Health check | None |
| GET | /api/stats | Database statistics | None |
| GET | /api/stats/summary | Summary stats | None |
| GET | /api/search | Unified search | None |
| POST | /api/score | Score a startup | None |
| POST | /api/chat | AI chat | None |
| GET | /api/startups | List failed startups | None |
| GET | /api/startups/{id} | Single startup | None |
| GET | /api/news | News articles | None |
| GET | /api/news/sentiment | Sentiment dist | None |
| GET | /api/risk-scores | Risk scores | None |
| GET | /api/survival-rates | BLS data | None |
| GET | /api/revival-opportunities | Revival data | None |
| GET | /api/opportunities | Scored entities | None |
| GET | /api/opportunities/{name} | Entity detail | None |
| GET | /api/signals | Raw signals | None |
| GET | /api/signals/stats | Signal stats | None |
| GET | /api/entities/{name}/connections | KG connections | None |
| GET | /api/knowledge-graph | Graph search | None |
| GET | /api/ml/models | Trained models | None |
| POST | /api/ml/train | Train model | None |
| POST | /api/ml/predict | ML prediction | None |
| GET | /api/models | Ollama models | None |
| POST | /api/models/pull | Pull model | None |
| GET | /api/models/token-usage | Token stats | None |
| GET | /api/alerts | Active alerts | None |
| GET | /api/pipeline-runs | Pipeline history | None |
| GET | /api/stream/status | Stream status | None |
| GET | /api/cache/clear | Clear cache | Admin |
| POST | /api/license/validate | License check | None |
| POST | /api/license/generate | Generate license | None |
| GET | /api/license/metrics | License stats | None |
| GET | /api/collection/status | Collector status | None |
| WS | /ws/live | Real-time updates | None |

### 3.3 New Authenticated Endpoints (15 to ADD)

| Method | Endpoint | Description | Auth | Tier |
|---|---|---|---|---|
| POST | /api/auth/register | Create account | None | — |
| POST | /api/auth/login | Login | None | — |
| POST | /api/auth/refresh | Refresh token | JWT | — |
| POST | /api/auth/api-keys | Create API key | JWT | — |
| GET | /api/auth/api-keys | List API keys | JWT | — |
| DELETE | /api/auth/api-keys/{id} | Revoke API key | JWT | — |
| GET | /api/watchlist | List watchlist | JWT | — |
| POST | /api/watchlist | Add to watchlist | JWT | — |
| PUT | /api/watchlist/{id} | Update watchlist | JWT | — |
| DELETE | /api/watchlist/{id} | Remove from watchlist | JWT | — |
| GET | /api/alerts/preferences | Get alert prefs | JWT | — |
| PUT | /api/alerts/preferences | Set alert prefs | JWT | — |
| GET | /api/alerts/history | Alert history | JWT | — |
| POST | /api/feedback/score | Rate a score | Optional | — |
| POST | /api/feedback/feature-request | Request feature | Optional | — |
| GET | /api/feedback/feature-requests | List requests | None | — |
| GET | /api/feedback/score-stats | Rating stats | None | — |
| POST | /api/billing/checkout | Stripe checkout | JWT | — |
| POST | /api/billing/portal | Stripe portal | JWT | — |
| POST | /api/billing/webhook | Stripe events | Stripe sig | — |
| GET | /api/export/csv | CSV export | JWT | Pro |
| GET | /api/export/pdf/{name} | PDF export | JWT | Pro |
| GET | /api/user/data | GDPR export | JWT | — |
| DELETE | /api/user/data | GDPR delete | JWT | — |
| GET | /api/progress | Sprint progress | JWT | Admin |

### 3.4 Rate Limiting Rules

| Tier | Rate | Scope |
|---|---|---|
| Anonymous | 30 req/min | GET endpoints only |
| Free User | 60 req/min (5/min chat, 2/min score) | All GET + limited POST |
| Pro User | 1000 req/min | All endpoints + export |
| Admin | Unlimited | All endpoints |

Response headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

---

## Part 4: Security Requirements

---

### 4.1 Threat Model — 15 Vectors

| # | Threat | Severity | Defense |
|---|---|---|---|
| T1 | SQL Injection | CRITICAL | Parameterized queries (already using %s in cursor.execute) |
| T2 | XSS | HIGH | CSP headers, sanitize output |
| T3 | CSRF | MEDIUM | SameSite cookies, CSRF token |
| T4 | Brute Force Login | HIGH | Rate limit per IP, bcrypt 12 rounds |
| T5 | JWT Secret Compromise | CRITICAL | Env var, 256-bit key |
| T6 | API Abuse/Scraping | HIGH | Rate limiting, API key required |
| T7 | Data Exfiltration | HIGH | RBAC, audit log, export limits |
| T8 | Dependency Vulnerability | MEDIUM | pip-audit, Dependabot |
| T9 | Container Escape | LOW | Docker non-root, cap_drop ALL |
| T10 | Insecure Defaults | HIGH | No default passwords, HTTPS enforced |
| T11 | Sensitive Data Exposure | MEDIUM | .env for secrets, no secrets in code |
| T12 | DoS | MEDIUM | Rate limiting, Docker resource limits |
| T13 | Open Redirect | LOW | Whitelist redirect URLs |
| T14 | SSRF | MEDIUM | URL whitelist in collectors |
| T15 | Insider Threat | LOW | Audit log, RBAC, least privilege |

### 4.2 Security Middleware Implementation

```python
# ═══ To add to api_server.py ═══

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

# 1. RATE LIMITING
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# 2. SECURITY HEADERS MIDDLEWARE
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self' ws: wss:"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# 3. INPUT VALIDATION
import re

def sanitize_input(value: str, max_length: int = 500) -> str:
    """Strip HTML tags, SQL keywords, and limit length."""
    if not isinstance(value, str):
        raise ValueError("Input must be a string")
    value = value.strip()[:max_length]
    # Remove HTML tags
    value = re.sub(r'<[^>]*>', '', value)
    # Remove null bytes
    value = value.replace('\x00', '')
    return value

def validate_entity_name(name: str) -> str:
    """Validate entity name for search/score endpoints."""
    name = sanitize_input(name, max_length=255)
    if not name:
        raise ValueError("Entity name cannot be empty")
    if re.match(r'^[\s\.;\'"\\-]+$', name):
        raise ValueError("Entity name contains only special characters")
    return name

# 4. JWT AUTH DEPENDENCY (for FastAPI)
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Extract and validate JWT from Authorization header."""
    if credentials is None:
        return None  # Public endpoint
    from auth.jwt_handler import JWTHandler
    handler = JWTHandler()
    try:
        payload = handler.validate_token(credentials.credentials)
        return payload
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

async def require_auth(user = Depends(get_current_user)):
    """Require authenticated user."""
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user

async def require_pro(user = Depends(get_current_user)):
    """Require Pro tier."""
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    if user.get("tier") not in ("pro", "enterprise"):
        raise HTTPException(status_code=403, detail="Pro subscription required")
    return user

async def require_admin(user = Depends(get_current_user)):
    """Require admin role."""
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
```

### 4.3 Docker Security Hardening

```yaml
# Add to each service in docker-compose.yml:
security_opt:
  - no-new-privileges:true
cap_drop:
  - ALL
cap_add:
  - NET_BIND_SERVICE  # Only if binding to port < 1024
read_only: true       # Where possible
tmpfs:
  - /tmp
deploy:
  resources:
    limits:
      cpus: '1.0'
      memory: 1G
    reservations:
      cpus: '0.25'
      memory: 256M
user: "1000:1000"     # Non-root user
```

### 4.4 Password Security

```python
import bcrypt

def hash_password(password: str) -> str:
    """Hash password with bcrypt (12 rounds)."""
    if len(password) < 8:
        raise ValueError("Password must be ≥ 8 characters")
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hash: str) -> bool:
    """Verify password against bcrypt hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hash.encode('utf-8'))
```

### 4.5 Security Checklist

```
PRE-LAUNCH (Must have):
  □ Rate limiting active on all endpoints
  □ Security headers on all responses
  □ Input validation on all user-facing endpoints
  □ No hardcoded secrets in code
  □ .env.example created with all required vars
  □ Default passwords changed
  □ HTTPS enforced (Caddy/Let's Encrypt)
  □ JWT secret is 256-bit random string
  □ Password hashing with bcrypt (12 rounds)
  □ Docker containers run as non-root
  □ Security scan in CI (bandit + pip-audit + trivy)

POST-LAUNCH (Should have):
  □ Audit log recording all write operations
  □ IP-based rate limiting for login attempts (5/min)
  □ CSRF protection on state-changing endpoints
  □ Content Security Policy tightened (remove unsafe-inline)
  □ Webhook URL validation (whitelist)
  □ Collector URL validation (no internal IPs)
  □ Dependency auto-updates via Dependabot
  □ Weekly security scan scheduled
```

---

## Part 5: Scalability Needs

---

### 5.1 Load Projections

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  USER COUNT    REQUESTS/DAY    DATA SIZE    CONCURRENT WS            │
│  ──────────    ────────────    ─────────    ─────────────            │
│  100 users     10,000          1 GB         20                       │
│  1,000 users   100,000         10 GB        200                      │
│  10,000 users  1,000,000       100 GB       2,000                    │
│  100,000 users 10,000,000      1 TB         20,000                   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 5.2 Bottleneck Analysis

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  BOTTLENECK          WHERE           SOLUTION                        │
│  ──────────          ─────           ────────                        │
│                                                                      │
│  MySQL reads         /api/search     Redis cache for top queries    │
│                      /api/score      Cache scores for 5 min         │
│                      /api/opportunities                              │
│                                                                      │
│  MySQL writes        Collectors      Batch INSERT (100 at a time)   │
│                      Score updates   Write-behind from Kafka         │
│                                                                      │
│  Ollama inference    /api/chat       Queue + single-threaded         │
│                      /api/score      llama3:8b = ~5s/response       │
│                                      Max ~12 req/min per GPU         │
│                                                                      │
│  Qdrant search       /api/search     HNSW index (already fast)      │
│                      (semantic)      Cache popular embeddings        │
│                                                                      │
│  WebSocket           /ws/live        Redis pub/sub fanout            │
│  connections                        (single source → N workers)      │
│                                                                      │
│  Kafka throughput    raw.signals     Partition by entity_name        │
│                      scores.updates  Already partitioned             │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 5.3 Scaling Plan — 4 Stages

```
STAGE 1: SOLO DEV (0-100 users) — CURRENT
───────────────────────────────────────────
  • Single VPS ($5-20/mo DigitalOcean)
  • Docker Compose on one machine
  • MySQL on same machine
  • Ollama on same machine (CPU)
  • Total cost: $5-20/mo
  • Handles: ~10,000 requests/day

STAGE 2: SMALL TEAM (100-1,000 users)
──────────────────────────────────────
  • Upgrade VPS to 4 CPU / 8 GB RAM ($40/mo)
  • Add GPU for Ollama (NVIDIA T4, $0.35/hr spot)
  • MySQL: same machine, add read replica if needed
  • Redis: increase maxmemory to 2 GB
  • Add CloudFront CDN for static assets
  • Total cost: $40-100/mo
  • Handles: ~100,000 requests/day

STAGE 3: GROWING (1,000-10,000 users)
──────────────────────────────────────
  • Separate MySQL to managed RDS ($50/mo)
  • Add 2nd API server (load balancer: nginx)
  • Ollama: dedicated GPU server or API (together.ai $0.20/1M tokens)
  • Kafka: increase partitions (4 → 16)
  • Qdrant: dedicated instance with 4 GB RAM
  • Total cost: $200-500/mo
  • Handles: ~1,000,000 requests/day

STAGE 4: SCALE (10,000+ users)
──────────────────────────────
  • Kubernetes (EKS/GKE) for API servers
  • RDS Multi-AZ + read replicas
  • ElastiCache (Redis) cluster
  • MSK (Managed Kafka) or Redpanda Cloud
  • Qdrant Cloud or self-hosted cluster
  • CDN + WAF (Cloudflare)
  • Total cost: $1,000-3,000/mo
  • Handles: 10,000,000+ requests/day
```

### 5.4 Caching Strategy

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  LAYER          TOOL          TTL           WHAT                     │
│  ─────          ────          ───           ─────                    │
│                                                                      │
│  L1: API        In-process    60s           Health check results    │
│                 (Python dict)               Feature flags            │
│                                                                      │
│  L2: Redis      Redis GET/SET 5 min         Score results           │
│                                              Search results          │
│                                              Dashboard stats         │
│                                              Session tokens          │
│                                                                      │
│  L3: Database   MySQL         Persistent    All primary data        │
│                 indexes                      (with proper indexes)   │
│                                                                      │
│  L4: Vector     Qdrant        Persistent    Embeddings              │
│                 HNSW                         (reindex on update)     │
│                                                                      │
│  CACHE KEYS:                                                        │
│  score:{entity_name}           → ScoreResult JSON (5 min TTL)      │
│  search:{query_hash}           → SearchResult JSON (5 min TTL)     │
│  stats:summary                 → Stats dict (1 min TTL)            │
│  session:{token_jti}           → User payload (24 hr TTL)          │
│                                                                      │
│  CACHE INVALIDATION:                                                │
│  • Score update → DELETE score:{entity_name}                        │
│  • New signal → DELETE search:* (pattern)                           │
│  • Collector run → DELETE stats:summary                             │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Part 6: Refactoring Plan

---

### 6.1 Refactoring Principles

```
1. BOY SCOUT RULE: Leave code cleaner than you found it.
2. SMALL STEPS: One refactoring per commit.
3. TEST FIRST: Don't refactor code without tests.
4. NO FEATURE MIX: Never mix refactoring with new features.
5. REVERTIBLE: Every refactoring commit should be independently revertible.
```

### 6.2 Refactoring Targets — 47 Items

#### Priority P0: Fix Now (Before Launch)

```
┌────┬──────────────────────────────────────────────────────────────────┐
│ #  │ REFACTORING                                                      │
├────┼──────────────────────────────────────────────────────────────────┤
│ R1 │ FIX: 12 failing tests in test_semantic_search.py                │
│    │ Before: 687 pass, 12 fail                                       │
│    │ After:  699 pass, 0 fail                                        │
│    │ Effort: M (3-4 hrs)                                             │
├────┼──────────────────────────────────────────────────────────────────┤
│ R2 │ FIX: api_server.py connection leak — no connection pool          │
│    │ Before: get_connection() creates new PyMySQL conn every request │
│    │ After:  Connection pool (Queue-based, 10 conns, 30s timeout)    │
│    │ File: db/connection.py — add get_pool() + get_connection()      │
│    │ Effort: L (1 day)                                               │
├────┼──────────────────────────────────────────────────────────────────┤
│ R3 │ FIX: No input validation on any endpoint                        │
│    │ Before: Raw user input passed directly to SQL queries           │
│    │ After:  sanitize_input() on all user-facing params              │
│    │ File: utils/validation.py (new) + api_server.py                 │
│    │ Effort: M (3-4 hrs)                                             │
├────┼──────────────────────────────────────────────────────────────────┤
│ R4 │ FIX: WebSocket polls MySQL every 30s instead of Kafka           │
│    │ Before: async loop queries opportunity_scores table             │
│    │ After:  Consume Kafka scores.updates topic                      │
│    │ File: api_server.py — rewrite /ws/live handler                  │
│    │ Effort: L (1 day)                                               │
├────┼──────────────────────────────────────────────────────────────────┤
│ R5 │ FIX: CORS allows all origins (allow_origins=["*"])              │
│    │ Before: CORSMiddleware(allow_origins=["*"])                     │
│    │ After:  Configurable whitelist: allow_origins=[env var list]    │
│    │ File: api_server.py                                             │
│    │ Effort: S (1 hr)                                                │
├────┼──────────────────────────────────────────────────────────────────┤
│ R6 │ FIX: Orchestrator has 60+ elif chains for agent registry        │
│    │ Before: _get_agent_class() is 120 lines of if/elif             │
│    │ After:  Auto-discovery using __subclasses__() or entry points   │
│    │ File: agents/orchestrator.py                                    │
│    │ Effort: L (1 day)                                               │
└────┴──────────────────────────────────────────────────────────────────┘
```

#### Priority P1: Clean Up (Sprint 2-4)

```
┌────┬──────────────────────────────────────────────────────────────────┐
│ #  │ REFACTORING                                                      │
├────┼──────────────────────────────────────────────────────────────────┤
│ R7 │ EXTRACT: api_server.py is 1500+ lines — split into routers      │
│    │ Before: One file with 34 endpoints                              │
│    │ After:  api/v2/health.py, api/v2/search.py, api/v2/data.py,    │
│    │         api/v2/chat.py, api/v2/scoring.py, api/v2/admin.py     │
│    │ Effort: XL (2 days)                                             │
├────┼──────────────────────────────────────────────────────────────────┤
│ R8 │ EXTRACT: db/schema.py is 1000+ lines — split by domain          │
│    │ Before: One _TABLES list with 76 CREATE TABLE statements        │
│    │ After:  db/tables/core.py, db/tables/analysis.py,               │
│    │         db/tables/operations.py, db/tables/users.py (new)       │
│    │ Effort: L (1 day)                                               │
├────┼──────────────────────────────────────────────────────────────────┤
│ R9 │ EXTRACT: Config loading has global mutable cache                 │
│    │ Before: _config_cache = None (module-level global)              │
│    │ After:  Config class with instance-level cache, reload() method │
│    │ File: config/__init__.py                                        │
│    │ Effort: M (3-4 hrs)                                             │
├────┼──────────────────────────────────────────────────────────────────┤
│ R10 │ REMOVE: 6 agents that don't solve user problems                │
│     │ Cut: LLMPortfolioAgent, LLMPricingAgent, LLMBenchmarkAgent,   │
│     │      LLMCostOptimizerAgent, SpanAgent, ProjectMonitorAgent    │
│     │ Also remove: 6 LLM-related tables (llm_pricing, etc.)        │
│     │ Effort: M (3-4 hrs)                                            │
├────┼──────────────────────────────────────────────────────────────────┤
│ R11 │ MERGE: 4 redundant agents into 2                               │
│     │ ReportAgent + ReportGeneratorAgent → ReportAgent               │
│     │ InternetResearchAgent + AIAnalystAgent → AIAnalystAgent        │
│     │ Effort: M (3-4 hrs)                                            │
├────┼──────────────────────────────────────────────────────────────────┤
│ R12 │ ADD: Connection pooling to db/connection.py                     │
│     │ Before: get_connection() → new pymysql.connect() each time    │
│     │ After:  Thread-safe pool with Queue, max 10 connections        │
│     │                                                                │
│     │ class ConnectionPool:                                          │
│     │     def __init__(self, max_size=10, timeout=30):               │
│     │         self._pool = queue.Queue(maxsize=max_size)            │
│     │         self._size = 0                                         │
│     │         self._lock = threading.Lock()                          │
│     │                                                                │
│     │     def get(self) -> pymysql.Connection:                       │
│     │         try:                                                   │
│     │             return self._pool.get(timeout=self._timeout)       │
│     │         except queue.Empty:                                    │
│     │             with self._lock:                                   │
│     │                 if self._size < self._max_size:                │
│     │                     self._size += 1                            │
│     │                     return pymysql.connect(**params)           │
│     │             return self._pool.get(timeout=self._timeout)       │
│     │                                                                │
│     │     def put(self, conn):                                       │
│     │         if conn.open:                                          │
│     │             self._pool.put(conn)                               │
│     │         else:                                                  │
│     │             with self._lock:                                   │
│     │                 self._size -= 1                                │
│     │                                                                │
│     │ Effort: L (1 day)                                              │
├────┼──────────────────────────────────────────────────────────────────┤
│ R13 │ ADD: Structured error responses                                │
│     │ Before: HTTPException(status_code=500, detail=str(e))         │
│     │ After:  Standardized error format with error codes             │
│     │                                                                │
│     │ class APIError(Exception):                                     │
│     │     def __init__(self, code: str, message: str, status: int): │
│     │         self.code = code    # "VALIDATION_ERROR"               │
│     │         self.message = message                                 │
│     │         self.status = status                                   │
│     │                                                                │
│     │ @app.exception_handler(APIError)                               │
│     │ async def api_error_handler(request, exc):                     │
│     │     return JSONResponse(                                       │
│     │         status_code=exc.status,                                │
│     │         content={"error": {"code": exc.code,                   │
│     │                  "message": exc.message},                      │
│     │                  "meta": {"request_id": uuid4()}}              │
│     │     )                                                          │
│     │                                                                │
│     │ Effort: M (3-4 hrs)                                            │
├────┼──────────────────────────────────────────────────────────────────┤
│ R14 │ ADD: Request logging middleware                                 │
│     │ Before: No request logging                                    │
│     │ After:  Log method, path, status, duration, user_id for every │
│     │         request. Also log to query_log / chat_log tables.      │
│     │ Effort: M (3-4 hrs)                                            │
└────┴──────────────────────────────────────────────────────────────────┘
```

#### Priority P2: Improve (Sprint 5-8)

```
┌────┬──────────────────────────────────────────────────────────────────┐
│ #  │ REFACTORING                                                      │
├────┼───────────────────────────────────┤
│ R15 │ REPLACE: datetime.utcnow() → datetime.now(timezone.utc)        │
│     │ Before: datetime.utcnow() (deprecated in Python 3.12)         │
│     │ After:  datetime.now(timezone.utc) everywhere                  │
│     │ Effort: S (1-2 hrs, grep + replace)                            │
├────┼──────────────────────────────────────────────────────────────────┤
│ R16 │ ADD: Type hints to all public functions                         │
│     │ Before: Many functions missing return type annotations         │
│     │ After:  Full type annotations, mypy --strict passes            │
│     │ Effort: XL (2+ days)                                           │
├────┼──────────────────────────────────────────────────────────────────┤
│ R17 │ EXTRACT: Collector config from YAML to Python dataclass         │
│     │ Before: config["rss"]["google_news"]["queries"] (dict of dict) │
│     │ After:  @dataclass GoogleNewsConfig, BlsConfig, etc.           │
│     │ File: config/settings.py (new)                                 │
│     │ Effort: L (1 day)                                              │
├────┼──────────────────────────────────────────────────────────────────┤
│ R18 │ ADD: Abstract base for API error handling                       │
│     │ Before: Try/except in every endpoint handler                   │
│     │ After:  Global exception handlers + custom APIError class      │
│     │ Effort: M (3-4 hrs)                                            │
├────┼──────────────────────────────────────────────────────────────────┤
│ R19 │ IMPROVE: BaseAgent.run() opens 2 DB connections                 │
│     │ Before: get_connection() in try AND in finally                 │
│     │ After:  Single connection, context manager pattern              │
│     │ File: agents/base.py                                           │
│     │ Effort: M (3-4 hrs)                                            │
├────┼──────────────────────────────────────────────────────────────────┤
│ R20 │ ADD: Pagination helper for list endpoints                       │
│     │ Before: Manual LIMIT/OFFSET calculation in each endpoint       │
│     │ After:  paginate(query, page, per_page) helper function        │
│     │ File: utils/pagination.py (new)                                │
│     │ Effort: S (1-2 hrs)                                            │
├────┼──────────────────────────────────────────────────────────────────┤
│ R21 │ IMPROVE: Stream pipeline window import fallback                 │
│     │ Before: try/except ImportError for TumblingClocker             │
│     │ After:  Check bytewax version at startup, fail fast           │
│     │ File: stream/pipeline.py                                       │
│     │ Effort: S (1-2 hrs)                                            │
├────┼──────────────────────────────────────────────────────────────────┤
│ R22 │ ADD: Health check for all 11 Docker services                    │
│     │ Before: /api/health checks MySQL only                          │
│     │ After:  Check MySQL, Redis, Kafka, Ollama, Qdrant, ES, etc.   │
│     │ File: monitoring/health.py                                     │
│     │ Effort: M (3-4 hrs)                                            │
├────┼──────────────────────────────────────────────────────────────────┤
│ R23 │ REMOVE: TimescaleDB from docker-compose (not used)              │
│     │ Before: 11 services including unused TimescaleDB               │
│     │ After:  10 services (remove TimescaleDB, use Redis for time)   │
│     │ Effort: S (30 min)                                             │
├────┼──────────────────────────────────────────────────────────────────┤
│ R24 │ ADD: .env.example with all required variables                   │
│     │ Before: No .env.example — new devs don't know what to set      │
│     │ After:  .env.example with every var documented                 │
│     │ Effort: S (1 hr)                                               │
└────┴──────────────────────────────────────────────────────────────────┘
```

#### Priority P3: Nice to Have (Post-V1)

```
R25-R47 (abbreviated — see full list):

R25: Add Pydantic models for all request/response schemas
R26: Replace PyMySQL with aiomysql for async DB access
R27: Add OpenTelemetry tracing (replace SpanAgent)
R28: Convert collectors to async (aiohttp)
R29: Add retry decorator (tenacity) to all external API calls
R30: Add circuit breaker pattern for Ollama calls
R31: Extract embedding generation to background worker
R32: Add database migration tool (Alembic or custom)
R33: Add API versioning header (Accept: application/vnd.oip.v2+json)
R34: Replace print() statements with _logger calls
R35: Add docstrings to 150+ undocumented functions
R36: Standardize all datetime fields to UTC with timezone
R37: Add pre-commit hooks (ruff, mypy, bandit)
R38: Create Docker healthcheck for all services
R39: Add graceful shutdown (SIGTERM handler) to all services
R40: Add Prometheus /metrics endpoint
R41: Split requirements.txt into requirements/*.txt (base, dev, prod)
R42: Add Makefile for common commands (make test, make lint, make run)
R43: Add structured logging (JSON format) for production
R44: Add request ID middleware (X-Request-ID header)
R45: Create admin CLI tool (python -m oip admin create-user ...)
R46: Add data retention policy (auto-purge old signals)
R47: Add WebSocket reconnection with exponential backoff
```

### 6.3 Refactoring Schedule

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  SPRINT 1: R1, R3, R5, R24              (Fix bugs + validate input) │
│  SPRINT 2: R2, R4, R12, R14              (DB pool + WS + logging)   │
│  SPRINT 3: R13, R18, R22                 (Error handling + health)  │
│  SPRINT 4: R7, R8                        (Split large files)        │
│  SPRINT 5: R6, R10, R11                  (Agent cleanup)            │
│  SPRINT 6: R9, R15, R20, R21             (Config + pagination)      │
│  SPRINT 7: R19, R23                       (BaseAgent + remove TS)   │
│  SPRINT 8: R16, R25                       (Type hints + Pydantic)   │
│  POST-V1:  R26-R47                        (Async, tracing, etc.)    │
│                                                                      │
│  RULE: Maximum 2 refactorings per sprint.                            │
│  RULE: Every refactoring has its own commit.                         │
│  RULE: Tests must pass after every refactoring commit.              │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Summary: What to Build First

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  DESIGN DECISIONS MADE:                                              │
│                                                                      │
│  1. ARCHITECTURE: 6-layer (Data In → Transport → Processing →      │
│     Storage → Access → Presentation). Kappa architecture.           │
│     Dual-write everywhere (MySQL + Kafka).                          │
│                                                                      │
│  2. DATABASE: 76 existing + 12 new tables = 88 total (v17).        │
│     Every FK gets an index. Connection pool (10 conns).             │
│     Schema migration via SQL scripts + schema_metadata table.       │
│                                                                      │
│  3. API: 34 existing + 25 new = 59 endpoints.                       │
│     Standard response shape. JWT auth. Rate limiting.               │
│     Pro tier gates: export, advanced search, unlimited API.         │
│                                                                      │
│  4. SECURITY: 15 threats identified. Middleware stack:               │
│     CORS → Security Headers → Rate Limit → JWT → Validation.       │
│     bcrypt passwords. Non-root Docker. Audit logging.               │
│                                                                      │
│  5. SCALABILITY: 4 stages (solo → small → growing → scale).        │
│     Redis cache at L2. Connection pool at L3.                      │
│     Vertical first, partition at Kafka, cache aggressively.         │
│                                                                      │
│  6. REFACTORING: 47 targets (6 P0, 8 P1, 10 P2, 23 P3).           │
│     Top 3: Fix failing tests, add connection pool, split            │
│     api_server.py into routers.                                     │
│                                                                      │
│  IMMEDIATE NEXT STEPS (in this order):                               │
│  1. R1: Fix 12 failing tests                                        │
│  2. R3: Add input validation                                        │
│  3. R5: Fix CORS to use env var whitelist                           │
│  4. R24: Create .env.example                                        │
│  5. Build Collector Scheduler (P0 gap)                               │
│  6. Build Alert Consumer (P0 gap)                                   │
│  7. Fix WebSocket to consume Kafka (P0 gap)                         │
│  8. R2: Add connection pool                                         │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

*Last updated: June 5, 2026*
*Cross-references: WORK_PLAN.md, SOLUTION_DESIGN.md, BUILD_PLAN.md, TESTING_STRATEGY.md, RISK_MANAGEMENT.md, SECURITY_SCAN.sh*
