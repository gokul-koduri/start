# 🏗️ The Build Plan — Requirements, Scope, Timeline & Risks

> The complete execution plan: what we're building, what we're not, when it ships, and what could go wrong

---

## Part 1: Requirements List

---

### 1.1 Functional Requirements

Every requirement maps to a problem from `PROBLEM_DEFINITION.md` and a user from `USE_CASES.md`.

#### FR-1: Data Collection (Solves: "information is fragmented")

| ID | Requirement | Priority | Status | Verification |
|---|---|---|---|---|
| FR-1.1 | System shall collect data from 24+ sources automatically | MUST | ✅ 24 collectors built | All collectors run without error |
| FR-1.2 | System shall collect continuously (not just on-demand) | MUST | 🔨 Scheduler needed | Collectors run 24/7 without manual trigger |
| FR-1.3 | System shall collect from at least 3 real-time streaming sources | MUST | ✅ Twitter, Reddit, HN | Signals appear within 60 seconds of real-world event |
| FR-1.4 | System shall collect from news RSS feeds every 15 minutes | MUST | ✅ Google News, TechCrunch | Collection_runs table shows runs every 15 min |
| FR-1.5 | System shall collect from SEC EDGAR every 4 hours | MUST | ✅ Built | Collection_runs table shows runs every 4 hours |
| FR-1.6 | System shall collect patent filings daily | MUST | ✅ Built | Daily collection of USPTO data |
| FR-1.7 | System shall collect GitHub repo activity hourly | MUST | ✅ Built | Star count, commit velocity updated hourly |
| FR-1.8 | System shall deduplicate all collected signals | MUST | ✅ Built | No duplicate entries in raw_signals table |
| FR-1.9 | System shall publish all signals to Kafka for real-time processing | MUST | ✅ Built | Kafka topic raw.signals receives messages |
| FR-1.10 | System shall write all signals to MySQL for durable storage | MUST | ✅ Built | MySQL tables populated after each collection |
| FR-1.11 | System shall track collection run history (success/failure/counts) | MUST | ✅ Built | collection_runs table audit trail |
| FR-1.12 | System shall retry failed collections automatically | SHOULD | 🔨 Not built | Failed collector retries within 1 hour |
| FR-1.13 | System shall collect from non-English sources (future: Hindi, Portuguese) | NICE | ❌ Not built | Sources in 3+ languages |

#### FR-2: Signal Processing (Solves: "nobody connects the dots")

| ID | Requirement | Priority | Status | Verification |
|---|---|---|---|---|
| FR-2.1 | System shall normalize all signals into a standard SignalEnvelope format | MUST | ✅ Built | All 24 collectors produce same format |
| FR-2.2 | System shall process signals through a 5-stage stream pipeline | MUST | ✅ Built | Bytewax pipeline processes all stages |
| FR-2.3 | System shall aggregate signals per entity in 5-minute tumbling windows | MUST | ✅ Built | Window aggregation in stream/pipeline.py |
| FR-2.4 | System shall detect complex event patterns (scaling, distress, pivot) | MUST | ✅ Built | Pattern detection in stream operators |
| FR-2.5 | System shall detect anomalies using Z-score analysis | MUST | ✅ Built | Z-score > 2.0 flagged as anomaly |
| FR-2.6 | System shall process at least 10 signals per minute | MUST | ✅ Built | Throughput tracked in PipelineMetrics |
| FR-2.7 | System shall process signals with < 5-minute median latency | MUST | ✅ Built | Latency tracked in Redis metrics |
| FR-2.8 | System shall handle malformed signals without crashing (dead letter queue) | MUST | ✅ Built | DLQ topic receives bad messages |
| FR-2.9 | System shall enrich signals with keyword-based sentiment in the fast path | MUST | ✅ Built | stream_sentiment in metadata |
| FR-2.10 | System shall enrich signals with spaCy NER in an async worker | SHOULD | 🔨 Not built | Entities extracted within 60 seconds |
| FR-2.11 | System shall generate embeddings for semantic search | SHOULD | 🔨 Not built | Qdrant receives vectors for each signal |
| FR-2.12 | System shall generate LLM summaries via Ollama | SHOULD | 🔨 Not built | Summary stored in enrichment.complete topic |

#### FR-3: Scoring & Prediction (Solves: "can't predict outcomes")

| ID | Requirement | Priority | Status | Verification |
|---|---|---|---|---|
| FR-3.1 | System shall calculate a composite opportunity score (0-100) for every entity | MUST | ✅ Built | CompositeScorer produces scores |
| FR-3.2 | System shall calculate a risk score (0.0-1.0) for every entity | MUST | ✅ Built | RiskScorerAgent produces risk scores |
| FR-3.3 | System shall provide feature attribution for every score | MUST | ✅ Built | Attribution breakdown in score output |
| FR-3.4 | System shall apply time decay to signal weights | MUST | ✅ Built | Exponential decay with configurable λ |
| FR-3.5 | System shall use weighted signal sources (funding 25%, SEC 20%, etc.) | MUST | ✅ Built | Weights in CompositeScorer |
| FR-3.6 | System shall track score trend (rising, stable, declining) | MUST | ✅ Built | trend_direction in score output |
| FR-3.7 | System shall predict startup failure with >75% accuracy at 12 months | MUST | ⚠️ Needs validation | Backtesting against actual outcomes |
| FR-3.8 | System shall maintain false positive rate below 20% | MUST | ⚠️ Needs validation | "Said high-risk but survived" / total |
| FR-3.9 | System shall train ML models on historical failure data | SHOULD | ✅ Built | MLPredictorAgent with training pipeline |
| FR-3.10 | System shall self-improve scoring weights based on prediction accuracy | NICE | ❌ Not built | Weights auto-adjust quarterly |

#### FR-4: Knowledge Graph (Solves: "20 hours of manual research per company")

| ID | Requirement | Priority | Status | Verification |
|---|---|---|---|---|
| FR-4.1 | System shall maintain a knowledge graph with 12+ entity types | MUST | ✅ Built | kg_entities table with type column |
| FR-4.2 | System shall maintain 20+ relationship types between entities | MUST | ✅ Built | kg_relationships table |
| FR-4.3 | System shall resolve entity aliases (same company, different names) | MUST | ✅ Built | kg_entity_aliases table |
| FR-4.4 | System shall support graph traversal queries (N-hop) | MUST | ✅ Built | GraphTraversalAgent |
| FR-4.5 | System shall detect communities/clusters in the graph | NICE | ✅ Built | CommunityDetectorAgent |
| FR-4.6 | System shall track graph changes over time | NICE | ✅ Built | TemporalGraphAgent |
| FR-4.7 | System shall expose graph connections via API | MUST | ✅ Built | /api/entities/{name}/connections |

#### FR-5: Alerting & Notifications (Solves: "I find out too late")

| ID | Requirement | Priority | Status | Verification |
|---|---|---|---|---|
| FR-5.1 | System shall trigger alerts when score exceeds configurable threshold | MUST | ✅ Built | emit_alert() in stream operators |
| FR-5.2 | System shall deliver alerts to Slack via webhook | MUST | 🔨 Not built | Alert arrives in Slack channel |
| FR-5.3 | System shall deliver alerts via email (SMTP) | SHOULD | 🔨 Not built | Email received within 5 minutes |
| FR-5.4 | System shall deliver alerts to Discord via webhook | SHOULD | 🔨 Not built | Alert arrives in Discord channel |
| FR-5.5 | System shall deliver alerts to custom webhooks | SHOULD | 🔨 Not built | HTTP POST received by webhook URL |
| FR-5.6 | System shall push score updates to dashboard via WebSocket | MUST | ⚠️ 70% done | Dashboard updates in real-time |
| FR-5.7 | System shall provide SSE endpoint for non-WebSocket clients | SHOULD | 🔨 Not built | SSE stream delivers updates |
| FR-5.8 | System shall support per-user alert preferences | NICE | ❌ Not built | User configures which entities/alerts |
| FR-5.9 | System shall send daily digest emails | NICE | ❌ Not built | Email sent at 8 AM daily |
| FR-5.10 | System shall generate weekly automated reports | MUST | ✅ Built | ReportGeneratorAgent |

#### FR-6: Search & Access (Solves: "tools are expensive and stupid")

| ID | Requirement | Priority | Status | Verification |
|---|---|---|---|---|
| FR-6.1 | System shall provide full-text search via Elasticsearch | MUST | ✅ Built | /api/search with type=fulltext |
| FR-6.2 | System shall provide semantic search via Qdrant | MUST | ✅ Built | /api/search with type=semantic |
| FR-6.3 | System shall provide hybrid search (fulltext + semantic) | MUST | ✅ Built | /api/search with type=hybrid |
| FR-6.4 | System shall provide a natural language AI chat interface | MUST | ✅ Built | POST /api/chat |
| FR-6.5 | System shall expose all data via REST API | MUST | ✅ Built | 34 endpoints documented |
| FR-6.6 | System shall provide a web dashboard | MUST | ✅ Built | site/index.html (2903 lines) |
| FR-6.7 | System shall be self-hostable via Docker Compose | MUST | ✅ Built | `docker compose up` starts everything |
| FR-6.8 | System shall be installable locally without Docker | SHOULD | ✅ Built | pip install + python run |
| FR-6.9 | System shall export data as CSV and JSON | MUST | ✅ Built | API export endpoints |
| FR-6.10 | System shall export reports as PDF | SHOULD | 🔨 Not built | PDF download available |
| FR-6.11 | System shall be free and open-source (core) | MUST | ✅ Built | Full source code available |
| FR-6.12 | System shall provide API key authentication for Pro users | SHOULD | 🔨 Not built | API returns 401 without valid key |

#### FR-7: Failure Intelligence (Solves: "nobody learns from failure")

| ID | Requirement | Priority | Status | Verification |
|---|---|---|---|---|
| FR-7.1 | System shall maintain a database of failed startups with failure reasons | MUST | ✅ Built | 50+ entries in failed_startups table |
| FR-7.2 | System shall categorize failures into a taxonomy (6+ categories) | MUST | ✅ Built | failure_reasons_taxonomy table |
| FR-7.3 | System shall analyze failure patterns by sector, geography, funding | MUST | ✅ Built | FailurePatternAgent |
| FR-7.4 | System shall calculate survival probabilities by sector and geography | MUST | ✅ Built | SurvivalAnalysisAgent |
| FR-7.5 | System shall identify manufacturing-specific failure categories | MUST | ✅ Built | manufacturing_failure_categories table |
| FR-7.6 | System shall identify revival opportunities from failed startups | MUST | ✅ Built | RevivalOpportunityAgent |
| FR-7.7 | System shall track failure trends over time (year-over-year) | SHOULD | ✅ Built | CohortAnalysisAgent |
| FR-7.8 | System shall provide BLS survival rate data for comparison | MUST | ✅ Built | BLSSurvivalRateCollector |

---

### 1.2 Non-Functional Requirements

| ID | Requirement | Target | Status |
|---|---|---|---|
| NFR-1 | **Performance**: API response time < 500ms for all endpoints | p95 < 500ms | ⚠️ Not measured |
| NFR-2 | **Performance**: Stream pipeline throughput > 10 signals/min | > 10/min | ✅ Tracked in metrics |
| NFR-3 | **Performance**: Score calculation < 100ms per entity | < 100ms | ✅ CompositeScorer is fast |
| NFR-4 | **Availability**: System uptime > 99.5% | > 99.5% | ⚠️ No monitoring yet |
| NFR-5 | **Scalability**: Support 100 concurrent API users | 100 users | ✅ FastAPI handles this |
| NFR-6 | **Scalability**: Support 10,000 entities in knowledge graph | 10K entities | ✅ MySQL handles millions |
| NFR-7 | **Security**: All API endpoints require authentication (Pro/Enterprise) | Auth required | 🔨 Phase 6.1 |
| NFR-8 | **Security**: Data encrypted at rest (MySQL TLS) | TLS enabled | 🔨 Not configured |
| NFR-9 | **Security**: Self-hosted — no data leaves user's infrastructure | Zero external data | ✅ Architecture ensures this |
| NFR-10 | **Maintainability**: Test coverage > 500 tests | > 500 | ✅ 681 tests |
| NFR-11 | **Maintainability**: All components deployable via Docker Compose | One command | ✅ docker-compose.yml |
| NFR-12 | **Observability**: Pipeline metrics available via API | /api/stream/status | ✅ Built |
| NFR-13 | **Observability**: Prometheus metrics exported | /metrics endpoint | 🔨 Phase 6.11 |
| NFR-14 | **Cost**: Total infrastructure cost < $200/month (self-hosted) | < $200/mo | ✅ All open-source |

---

## Part 2: Scope Definition

---

### 2.1 What IS In Scope (We Are Building This)

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  IN SCOPE: The Opportunity Intelligence Platform                     │
│                                                                      │
│  1. DATA COLLECTION ENGINE                                           │
│     24 collectors monitoring public data sources continuously        │
│     Dual-write to MySQL (durable) + Kafka (real-time)                │
│     Automated scheduling with retry logic                            │
│                                                                      │
│  2. STREAM PROCESSING ENGINE                                         │
│     Bytewax 5-stage pipeline: ingest → enrich → aggregate →         │
│     score → output                                                   │
│     Complex event pattern detection                                  │
│     Anomaly detection via Z-score                                    │
│                                                                      │
│  3. SCORING ENGINE                                                   │
│     Composite opportunity score (0-100) with attribution             │
│     Risk score (0.0-1.0) with per-factor breakdown                   │
│     Survival probability by sector/geography                         │
│     ML-based failure prediction                                      │
│                                                                      │
│  4. KNOWLEDGE GRAPH                                                  │
│     12+ entity types, 20+ relationship types                         │
│     Entity resolution (alias matching)                               │
│     Graph traversal for relationship queries                         │
│                                                                      │
│  5. ALERTING SYSTEM                                                  │
│     Configurable threshold-based alerts                              │
│     Delivery via Slack, Email, Discord, Webhook                      │
│     Real-time push to dashboard via WebSocket/SSE                    │
│                                                                      │
│  6. SEARCH & ACCESS                                                  │
│     Full-text search (Elasticsearch)                                 │
│     Semantic search (Qdrant)                                         │
│     Hybrid search                                                    │
│     Natural language AI chat                                         │
│     REST API with 34+ endpoints                                      │
│     Web dashboard                                                    │
│                                                                      │
│  7. INTELLIGENCE AGENTS                                              │
│     26 core agents solving documented problems:                      │
│     Failure patterns, risk scoring, geographic strategy,             │
│     survival analysis, revival opportunities, whale investor,        │
│     news intelligence, competitive landscape, etc.                   │
│                                                                      │
│  8. DEPLOYMENT                                                       │
│     Docker Compose (one-command deploy)                              │
│     Free and open-source (MIT or Apache 2.0 license)                │
│     Self-hostable — all data stays on user's infrastructure          │
│                                                                      │
│  9. MONETIZATION (Phase 2+)                                          │
│     Pro tier ($99/mo): alerts, API access, reports                   │
│     Enterprise tier: SSO, custom agents, SLA                         │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 What Is NOT In Scope (We Are NOT Building This)

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  NOT IN SCOPE — These are deliberate exclusions                      │
│                                                                      │
│  ❌ MOBILE APPLICATION                                               │
│     Why not: Web dashboard is responsive; mobile app is Year 2+      │
│     Alternative: PWA (progressive web app) in Phase 5                │
│                                                                      │
│  ❌ BROWSER EXTENSION                                                │
│     Why not: Nice-to-have, doesn't solve core problem                │
│     Alternative: Year 2 if users request it                          │
│                                                                      │
│  ❌ CHATGPT PLUGIN                                                   │
│     Why not: Depends on OpenAI's platform; not core                  │
│     Alternative: Year 2 when API stabilizes                          │
│                                                                      │
│  ❌ PROPRIETARY DATA ACQUISITION                                     │
│     Why not: We only use public data sources                         │
│     We don't buy data, scrape behind paywalls, or store PII          │
│                                                                      │
│  ❌ USER-GENERATED CONTENT / SOCIAL FEATURES                         │
│     Why not: This is an intelligence tool, not a social network      │
│     No comments, forums, or user profiles (Discord serves this)      │
│                                                                      │
│  ❌ PORTFOLIO MANAGEMENT                                             │
│     Why not: Out of scope — use existing tools (AngelList, Carta)    │
│     We provide INTELLIGENCE, not portfolio tracking                  │
│                                                                      │
│  ❌ FINANCIAL MODELING / VALUATION                                   │
│     Why not: Requires financial data we don't collect                │
│     We score OPPORTUNITY, not stock price                            │
│                                                                      │
│  ❌ CRM SYSTEM                                                       │
│     Why not: We INTEGRATE with CRMs, we don't REPLACE them           │
│     Salesforce/HubSpot integration is in scope; building a CRM isn't │
│                                                                      │
│  ❌ MULTI-TENANT SAAS HOSTING                                        │
│     Why not: Self-hosted first. SaaS hosting is Year 3+              │
│     Users deploy on their own infrastructure                         │
│                                                                      │
│  ❌ REAL-TIME TRADING / INVESTMENT EXECUTION                         │
│     Why not: We provide intelligence, not financial services         │
│     No trading integration, no investment execution                  │
│                                                                      │
│  ❌ LLM FINE-TUNING / MODEL TRAINING PLATFORM                        │
│     Why not: We USE models (Ollama), we don't TRAIN them             │
│     LLM optimization is internal, not a product feature              │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.3 Scope Boundaries by Phase

| Phase | Scope | NOT In Scope |
|---|---|---|
| **Phase 6 (Current)** | Auth, API v2, webhooks, monitoring, orchestration | Mobile, i18n, SaaS |
| **Launch (Month 1-2)** | Real-time pipeline, alert delivery, public demo, Pro tier | Enterprise features |
| **Growth (Month 3-6)** | Watchlist, CRM integration, PDF export, accuracy tuning | Browser extension, PWA |
| **Scale (Month 7-12)** | Community features, contributor tools, university program | Mobile app, SaaS hosting |
| **Year 2** | Multi-language, mobile PWA, browser extension | Trading, financial modeling |

---

## Part 3: Timeline & Milestones

---

### 3.1 Overall Timeline (18 Months to Market Standard)

```
2026                                                    2027
JUN  JUL  AUG  SEP  OCT  NOV  DEC  JAN  FEB  MAR  APR  MAY  JUN
 │    │    │    │    │    │    │    │    │    │    │    │    │
 │    │    │    │    │    │    │    │    │    │    │    │    │
 ├────┼────┤    │    │    │    │    │    │    │    │    │    │
 │ PHASE 6│    │    │    │    │    │    │    │    │    │    │
 │ Sessions│   │    │    │    │    │    │    │    │    │    │
 │ 6.1-16  │   │    │    │    │    │    │    │    │    │    │
 ├────┼────┼────┤    │    │    │    │    │    │    │    │    │
 │    REAL-TIME   │    │    │    │    │    │    │    │    │
 │    + LAUNCH    │    │    │    │    │    │    │    │    │
 ├────┼────┼────┼────┼────┤    │    │    │    │    │    │
 │    │    │    │  SHOULD-HAVE  │    │    │    │    │    │
 │    │    │    │  FEATURES     │    │    │    │    │    │
 ├────┼────┼────┼────┼────┼────┼────┼────┼────┤    │    │
 │    │    │    │    │    │    │    COMMUNITY +    │    │
 │    │    │    │    │    │    │    GROWTH         │    │
 ├────┼────┼────┼────┼────┼────┼────┼────┼────┼────┼────┤
 │    │    │    │    │    │    │    │    │    │  INDUSTRY  │
 │    │    │    │    │    │    │    │    │    │  STANDARD  │
 └────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┘
```

### 3.2 Detailed Milestones

---

#### MILESTONE 1: Complete Phase 6 (Operations)

```
START:     June 2026 (NOW)
DURATION:  3-4 weeks
DEPENDENCY: None (Phase 5 complete)

SESSIONS:  6.1 → 6.16 (16 sessions)

DELIVERABLES:
  ┌─────────────────────────────────────────────────────────────┐
  │  Session 6.1-6.2: Authentication                             │
  │    • JWT token generation and validation                     │
  │    • RBAC with 4 roles: viewer, analyst, admin, superadmin  │
  │    • Multi-tenant support (tenant_id on all queries)         │
  │    • Tests: 20+ for auth flows                               │
  │                                                              │
  │  Session 6.3-6.5: API v2 + Webhooks                          │
  │    • Versioned API router (/api/v2/)                         │
  │    • Webhook registration and delivery                       │
  │    • Webhook templates for common events                     │
  │    • Tests: 15+ for webhook flows                            │
  │                                                              │
  │  Session 6.6-6.10: Collaboration + Integration Agents        │
  │    • Watchlists (per-user entity tracking)                   │
  │    • Annotations (user notes on entities)                    │
  │    • Slack integration agent                                 │
  │    • Email digest agent                                      │
  │    • Export agent (CSV, JSON, PDF)                           │
  │    • Feed generator (ranked opportunity feed)                │
  │                                                              │
  │  Session 6.11-6.14: Monitoring + Quality                     │
  │    • Prometheus metrics export                               │
  │    • Data quality agent (detect stale/missing data)          │
  │    • Pipeline health agent (detect failures)                 │
  │    • Cost tracking agent (API usage monitoring)              │
  │                                                              │
  │  Session 6.15-6.16: Orchestration + Final Deploy             │
  │    • Dagster pipeline orchestration                          │
  │    • Schedules for all collectors                            │
  │    • Final Docker Compose with all services                  │
  │    • PROGRESS.yaml updated                                   │
  └─────────────────────────────────────────────────────────────┘

EXIT CRITERIA:
  ☐ All 16 sessions complete
  ☐ 681+ tests passing (add ~80 new tests)
  ☐ Docker Compose starts all services
  ☐ API v2 endpoints return authenticated responses
  ☐ Webhooks deliver to external URLs
  ☐ Watchlists persist across sessions
```

---

#### MILESTONE 2: Real-Time Pipeline Operational

```
START:     July 2026
DURATION:  2 weeks
DEPENDENCY: Milestone 1 complete

DELIVERABLES:
  ┌─────────────────────────────────────────────────────────────┐
  │  1. Collector Scheduler (scheduler.py)                       │
  │     • APScheduler with 24 collector jobs                    │
  │     • Continuous threads for Twitter, Reddit, HN            │
  │     • Cron schedules for all other collectors               │
  │     • Health monitoring and auto-restart                    │
  │                                                              │
  │  2. Alert Consumer (alerting/consumer.py)                    │
  │     • Kafka consumer for alerts.triggered topic             │
  │     • Slack webhook delivery                                │
  │     • Email delivery via SMTP                                │
  │     • Discord webhook delivery                              │
  │     • Custom webhook delivery                               │
  │                                                              │
  │  3. Score Push (enhanced api_server.py)                      │
  │     • Background task consuming scores.updates topic         │
  │     • WebSocket broadcast on score change                   │
  │     • SSE endpoint for non-WebSocket clients                │
  │                                                              │
  │  4. Kafka Topics (scripts/create-topics.sh)                  │
  │     • raw.signals (12 partitions)                           │
  │     • scores.updates (6 partitions)                         │
  │     • alerts.triggered (3 partitions)                       │
  │     • dead.letters (3 partitions)                           │
  └─────────────────────────────────────────────────────────────┘

EXIT CRITERIA:
  ☐ Collector scheduler runs 24/7 without manual intervention
  ☐ All 24 collectors complete at least one run
  ☐ Signal freshness < 15 minutes (median)
  ☐ Alert delivered to Slack within 15 minutes of event
  ☐ Dashboard shows score updates in real-time via WebSocket
  ☐ SSE endpoint delivers updates to non-WebSocket clients
```

---

#### MILESTONE 3: Public Launch

```
START:     July-August 2026
DURATION:  2 weeks
DEPENDENCY: Milestone 2 complete

DELIVERABLES:
  ┌─────────────────────────────────────────────────────────────┐
  │  1. Public Demo Instance                                     │
  │     • demo.opportunity-intel.org                             │
  │     • Pre-loaded with 1,000+ entities                        │
  │     • "Type a startup name → get full analysis" works       │
  │     • Professional UI with charts and tables                 │
  │                                                              │
  │  2. GitHub Repository Polish                                 │
  │     • README.md with badges, screenshots, demo GIF          │
  │     • CONTRIBUTING.md with agent/collector guide             │
  │     • Issue templates (bug, feature, agent proposal)         │
  │     • PR template with checklist                             │
  │                                                              │
  │  3. Launch Content                                           │
  │     • "Show HN" post with demo GIF                          │
  │     • Blog post: "Why 90% of Startups Fail"                 │
  │     • YouTube walkthrough (10 minutes)                       │
  │     • Discord server launched                                │
  └─────────────────────────────────────────────────────────────┘

EXIT CRITERIA:
  ☐ Demo instance accessible and responsive
  ☐ GitHub repository public with professional README
  ☐ Hacker News post submitted
  ☐ 500+ GitHub stars within 2 weeks
  ☐ 100+ daily active users within 1 month
```

---

#### MILESTONE 4: Should-Have Features Complete

```
START:     September 2026
DURATION:  8 weeks
DEPENDENCY: Milestone 3 complete

DELIVERABLES:
  ┌─────────────────────────────────────────────────────────────┐
  │  Month 2 (September):                                       │
  │    • Watchlist feature (add/remove entities, get alerts)     │
  │    • Opportunity Feed (ranked by score, filterable)          │
  │    • Score Delta View ("what changed since yesterday")       │
  │    • Pro Tier setup (Stripe + API key auth)                  │
  │    • API key authentication middleware                       │
  │                                                              │
  │  Month 3 (October):                                         │
  │    • Custom alert thresholds (per entity/sector)             │
  │    • PDF report export                                       │
  │    • Historical score charts (time-series)                   │
  │    • CRM integration (Salesforce webhook)                    │
  │    • Company comparison (side-by-side)                       │
  │    • SSE endpoint                                            │
  │    • NLP Worker (spaCy + embeddings async)                   │
  └─────────────────────────────────────────────────────────────┘

EXIT CRITERIA:
  ☐ Watchlist persists across sessions
  ☐ Opportunity Feed shows top 50 entities
  ☐ Score delta explains every change
  ☐ Pro tier accepting payments via Stripe
  ☐ PDF reports downloadable
  ☐ CRM integration delivers webhooks to Salesforce
  ☐ 200+ Pro subscribers
  ☐ $25K MRR
```

---

#### MILESTONE 5: Community & Growth

```
START:     November 2026
DURATION:  12 weeks (through January 2027)
DEPENDENCY: Milestone 4 complete

DELIVERABLES:
  ┌─────────────────────────────────────────────────────────────┐
  │  Community Building:                                        │
  │    • Ambassador program (20 ambassadors)                     │
  │    • University partnerships (5 universities)                │
  │    • Accelerator partnerships (2 accelerators)               │
  │    • Quarterly hackathon program                             │
  │                                                              │
  │  Content Marketing:                                         │
  │    • 4 blog posts per month                                  │
  │    • 1 YouTube video per week                                │
  │    • Monthly "OIP Startup Health Index" report              │
  │    • 3 conference talks submitted                            │
  │                                                              │
  │  Score Accuracy:                                            │
  │    • Backtesting against 100+ actual outcomes               │
  │    • Weight tuning based on prediction accuracy             │
  │    • New failure categories added                            │
  │    • Accuracy > 75% validated                               │
  │                                                              │
  │  Enterprise:                                                │
  │    • 5 enterprise customers                                  │
  │    • SSO/SAML integration                                    │
  │    • Custom agent development framework                      │
  │    • 99.9% SLA offered                                       │
  └─────────────────────────────────────────────────────────────┘

EXIT CRITERIA:
  ☐ 15,000 GitHub stars
  ☐ 3,000 daily active users
  ☐ 200 Pro subscribers
  ☐ 5 Enterprise customers
  ☐ 50+ community contributors
  ☐ Score accuracy > 75% (validated)
  ☐ $25K MRR
```

---

#### MILESTONE 6: Industry Standard (Year 2 Target)

```
START:     February 2027
DURATION:  12 months
DEPENDENCY: Milestone 5 complete

EXIT CRITERIA:
  ☐ 35,000 GitHub stars
  ☐ 12,000 daily active users
  ☐ $3M ARR
  ☐ 10+ academic papers citing OIP
  ☐ 50+ media mentions
  ☐ 15+ university adoptions
  ☐ 100+ tools built on OIP API
  ☐ Monthly "OIP Index" read by 100,000+
```

---

### 3.3 Critical Path

```
Phase 6 Sessions ──→ Real-Time Pipeline ──→ Public Launch ──→ Should-Haves ──→ Community
     │                     │                     │                │               │
     │  CRITICAL:          │  CRITICAL:          │  CRITICAL:     │               │
     │  Auth + Webhooks    │  Scheduler +        │  Demo +        │  Watchlist +  │
     │  must work before   │  Alerts must        │  GitHub        │  Pro tier +   │
     │  Pro tier launch    │  work before        │  polish must   │  PDF + CRM    │
     │                     │  launch             │  happen        │               │
     │                     │                     │                │               │
     ▼                     ▼                     ▼                ▼               ▼
  Jul 2026              Jul 2026             Aug 2026        Oct 2026        Jan 2027

BLOCKERS:
  • Phase 6 (6.1 Auth) blocks everything — no Pro tier without authentication
  • Collector Scheduler blocks real-time — no alerts without continuous collection
  • Alert Consumer blocks investor value — no Slack alerts = no reason to pay
  • Public Demo blocks growth — nobody tries a tool they can't see
```

---

## Part 4: Risk Assessment

---

### 4.1 Risk Matrix

```
IMPACT →
        │ CATASTROPHIC      │ SERIOUS           │ MODERATE          │ MINOR
────────┼───────────────────┼───────────────────┼───────────────────┼──────────────
  HIGH  │ R1: Score         │ R3: Nobody        │ R5: Kafka         │ R9: Feature
PROB    │ accuracy < 50%    │ adopts OIP        │ unavailable       │ creep
        │                   │                   │                   │
────────┼───────────────────┼───────────────────┼───────────────────┼──────────────
MEDIUM  │ R2: Crunchbase    │ R4: Real-time     │ R6: LLM costs     │ R10: Team
PROB    │ copies features   │ latency > 30 min  │ too high          │ burnout
        │                   │                   │                   │
────────┼───────────────────┼───────────────────┼───────────────────┼──────────────
  LOW   │ R7: Legal action  │ R8: Data quality  │ R11: Open-source  │ R12: Cost
PROB    │ from data source  │ issues            │ community forks   │ overrun
        │                   │                   │                   │
────────┼───────────────────┼───────────────────┼───────────────────┼──────────────
```

---

### 4.2 Detailed Risk Analysis

#### R1: Score Accuracy Is Too Low (Catastrophic × High = 🔴 Critical)

```
WHAT:     Our scores don't predict outcomes better than random guessing
WHY IT MATTERS: If users can't trust the score, they won't use the platform
             This is the #1 existential risk

PROBABILITY: MEDIUM-HIGH (we haven't validated accuracy yet)
IMPACT:     CATASTROPHIC (platform has no value without trusted scores)

MITIGATION:
  1. Backtest against 100+ known outcomes (successful + failed startups)
     → Compare our predictions with what actually happened
     → Target: >75% accuracy

  2. Publish accuracy transparently
     → "Our predictions were correct for X% of backtested startups"
     → Honesty builds trust even when accuracy is imperfect

  3. Focus on explainability over raw accuracy
     → "Scored 84 because funding +19, jobs +12, patent +6"
     → Even if score is wrong, user understands the reasoning
     → User can override with their own judgment

  4. Improve iteratively
     → Track every prediction vs. actual outcome
     → Adjust weights quarterly based on accuracy data
     → Add new signal types that improve prediction

EARLY WARNING:
  → Backtest results < 65% accuracy → pause launch, improve model
  → User surveys show < 50% trust in scores → redesign attribution

RESIDUAL RISK: LOW (after mitigation)
```

#### R2: Crunchbase Copies Our Features (Catastrophic × Medium = 🔴 High)

```
WHAT:     Crunchbase adds AI analysis, scoring, and real-time alerts
WHY IT MATTERS: They have 80M users and $100M+ revenue
             They could clone our differentiators in 6-12 months

PROBABILITY: MEDIUM (they're a database company, not AI-native)
IMPACT:     CATASTROPHIC (lose competitive advantage)

MITIGATION:
  1. Open-source moat: They can't clone community
     → 200+ contributors by Year 2
     → Community-built agents they don't have
     → Their code is closed-source; ours is transparent

  2. Speed: We ship faster
     → Community ships new agents weekly
     → Crunchbase ships quarterly (enterprise company speed)
     → We're always 2-3 features ahead

  3. Price: We're free
     → Even if they copy every feature, they still charge $490/mo
     → Free + equivalent features = we win
     → They can't go free (revenue targets from shareholders)

  4. Self-hosted: Enterprise prefers on-premise
     → Crunchbase can't offer self-hosted (their business IS hosted)
     → Enterprise data sovereignty requirement = our win

EARLY WARNING:
  → Crunchbase job postings mentioning "AI" or "scoring"
  → Crunchbase blog posts about "intelligence" features

RESIDUAL RISK: MEDIUM (open-source is hard to displace)
```

#### R3: Nobody Adopts OIP (Serious × High = 🟠 High)

```
WHAT:     We launch and nobody cares
WHY IT MATTERS: No users = no revenue = dead project

PROBABILITY: MEDIUM (open-source projects often struggle with adoption)
IMPACT:     SERIOUS (project survives but doesn't grow)

MITIGATION:
  1. Killer demo: "Type a startup name → get full analysis in 2 seconds"
     → This is what makes people say "wow" and share
     → Must be deployed before GitHub launch

  2. Solve a real pain point immediately
     → First-time user must get value within 5 minutes
     → No signup, no install — just type and get results

  3. Hacker News front page is critical
     → 10,000+ visitors in 24 hours if we hit front page
     → Demo GIF must be visually impressive
     → Title must be compelling: "Show HN: Open-source Crunchbase + AI"

  4. Content marketing flywheel
     → Weekly blog posts with data insights from OIP
     → "We analyzed 500 failed startups — here's what we found"
     → This drives organic traffic even if HN launch flops

  5. University adoption (long-term wedge)
     → Students learn with OIP → use at companies → enterprise deals
     → Even if consumer adoption is slow, academic adoption compounds

EARLY WARNING:
  → < 500 GitHub stars in first month → rethink positioning
  → < 100 daily active users after 3 months → pivot messaging

RESIDUAL RISK: MEDIUM
```

#### R4: Real-Time Pipeline Doesn't Meet Latency Target (Serious × Medium = 🟡 Medium)

```
WHAT:     Events take > 30 minutes to reach users instead of < 15 minutes
WHY IT MATTERS: Speed is our competitive advantage over Crunchbase

PROBABILITY: LOW-MEDIUM (pipeline is built, just needs operational tuning)
IMPACT:     SERIOUS (users revert to manual research)

MITIGATION:
  1. Measure latency end-to-end
     → Timestamp at collection → timestamp at alert delivery
     → Track in Redis metrics

  2. Tune Bytewax window size
     → Current: 5 minutes (tumbling)
     → Can reduce to 2 minutes if needed (trade-off: fewer signals per window)

  3. Add real-time path for Tier 1 sources
     → Twitter, Reddit, HN bypass windowing for instant alerts
     → Only Tier 2+ sources use windowed aggregation

EARLY WARNING:
  → Median latency > 10 minutes → reduce window size
  → P95 latency > 20 minutes → investigate bottleneck

RESIDUAL RISK: LOW
```

#### R5: Kafka Unavailable (Moderate × High = 🟡 Medium)

```
WHAT:     Redpanda (Kafka) crashes or becomes unavailable
WHY IT MATTERS: Real-time pipeline stops; alerts stop delivering

PROBABILITY: MEDIUM (Kafka is reliable but needs proper configuration)
IMPACT:     MODERATE (system degrades gracefully to batch mode)

MITIGATION:
  1. Graceful degradation (already built)
     → Collectors continue writing to MySQL
     → Stream processor exits with warning
     → No data loss, just delayed processing

  2. Auto-restart in Docker Compose
     → restart: unless-stopped in docker-compose.yml
     → Redpanda restarts automatically on crash

  3. Health monitoring
     → PipelineMetrics flushed to Redis every 30 seconds
     → /api/stream/status reports Kafka health
     → Alert if pipeline goes stale for > 5 minutes

EARLY WARNING:
  → Kafka consumer lag increasing → scale partitions or add workers
  → Docker logs show connection errors → check Redpanda health

RESIDUAL RISK: LOW
```

#### R6: LLM Costs Too High (Moderate × Medium = 🟡 Low-Medium)

```
WHAT:     Ollama LLM inference uses too much RAM/CPU
WHY IT MATTERS: Self-hosted users may not have GPU/server hardware

PROBABILITY: LOW (Ollama runs on CPU, models are small)
IMPACT:     MODERATE (AI chat becomes slow, not broken)

MITIGATION:
  1. Use Ollama with small models (llama3:8b)
     → Runs on 8GB RAM, no GPU needed
     → Response time: 2-10 seconds (acceptable)

  2. Make LLM optional
     → AI chat falls back to keyword-based answers without Ollama
     → Stream enrichment uses keyword sentiment (no LLM needed)
     → Only AI chat and report summaries require Ollama

  3. Cache LLM responses
     → Redis cache for common queries
     → Reduces LLM calls by 50%+

EARLY WARNING:
  → Ollama response time > 30 seconds → reduce model size
  → RAM usage > 16GB → switch to smaller model

RESIDUAL RISK: LOW
```

#### R7: Legal Action from Data Source (Catastrophic × Low = 🟡 Medium)

```
WHAT:     A data source (Crunchbase, SEC, etc.) sends cease-and-desist
WHY IT MATTERS: Could force us to remove a critical collector

PROBABILITY: LOW (we use public APIs and fair use)
IMPACT:     CATASTROPHIC (if a critical source is removed)

MITIGATION:
  1. Only use public APIs and public data
     → SEC EDGAR: Public government data (no restriction)
     → USPTO: Public patent data (no restriction)
     → GitHub API: Public repos, rate-limited (ToS compliant)
     → Reddit API: PRAW with rate limiting (ToS compliant)
     → HN API: Public, no auth required

  2. Crunchbase: Only use free-tier API data
     → Don't scrape behind paywall
     → Don't republish their proprietary data
     → Use only what's available in free tier

  3. Don't store PII
     → No personal emails, phone numbers, addresses
     → Only public company and investor data

  4. Open-source license protects
     → We distribute code, not data
     → Users collect their own data using our code
     → We're a tool, not a data broker

EARLY WARNING:
  → API rate limiting increases → check ToS changes
  → Legal inquiry received → consult open-source legal counsel

RESIDUAL RISK: VERY LOW
```

#### R8: Data Quality Issues (Serious × Low = 🟡 Low-Medium)

```
WHAT:     Collected data is inaccurate, outdated, or incomplete
WHY IT MATTERS: Bad data → bad scores → user distrust

PROBABILITY: LOW-MEDIUM (deduplication exists, validation is partial)
IMPACT:     SERIOUS (cascade effect on all downstream analysis)

MITIGATION:
  1. Deduplication (already built)
     → Dedup hash on every signal prevents duplicates
     → ON DUPLICATE KEY UPDATE in MySQL

  2. Confidence scores on every signal
     → confidence field in SignalEnvelope
     → Low-confidence signals weighted lower in scoring

  3. Data quality agent (Phase 6.12)
     → Detects stale data (no updates in 30+ days)
     → Detects missing data (entity with no sector)
     → Flags for manual review

  4. Community correction mechanism
     → GitHub issues for data corrections
     → Pull requests for seed data updates

EARLY WARNING:
  → > 10% of entities have missing fields → add collectors
  → Score attribution shows "unknown" signals → improve entity extraction

RESIDUAL RISK: LOW
```

---

### 4.3 Risk Response Summary

| Risk | Severity | Probability | Response | Owner |
|---|---|---|---|---|
| **R1: Low score accuracy** | 🔴 Critical | Medium | Backtest + improve weights + publish transparency | ML lead |
| **R2: Crunchbase copies features** | 🔴 High | Medium | Open-source moat + speed + price advantage | Product |
| **R3: Nobody adopts** | 🟠 High | Medium | Killer demo + HN launch + content marketing | Growth |
| **R4: Latency too high** | 🟡 Medium | Low-Medium | Tune window size + real-time bypass | Engineering |
| **R5: Kafka unavailable** | 🟡 Medium | Medium | Graceful degradation + auto-restart | DevOps |
| **R6: LLM costs** | 🟡 Low-Medium | Low | Make optional + cache + small models | Engineering |
| **R7: Legal action** | 🟡 Medium | Low | Public data only + no PII + open-source license | Legal |
| **R8: Data quality** | 🟡 Low-Medium | Low-Medium | Dedup + confidence + quality agent | Data |

---

## Part 5: The One-Page Plan

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  REQUIREMENTS                                                        │
│  ───────────                                                         │
│  53 functional requirements (FR-1 to FR-7)                           │
│  14 non-functional requirements (NFR-1 to NFR-14)                    │
│  36 MUST / 15 SHOULD / 9 NICE                                       │
│  37 built (70%) / 16 to build (30%)                                  │
│                                                                      │
│  SCOPE                                                               │
│  ─────                                                               │
│  IN:  Collection, Processing, Scoring, Graph, Alerts, Search,       │
│       Agents, Deployment, Monetization                               │
│  OUT: Mobile app, browser extension, trading, CRM, SaaS hosting,    │
│       social features, financial modeling, LLM training platform     │
│                                                                      │
│  TIMELINE                                                            │
│  ─────────                                                           │
│  Jul 2026: Phase 6 complete (auth, webhooks, monitoring)            │
│  Jul 2026: Real-time pipeline operational (scheduler, alerts, push)  │
│  Aug 2026: Public launch (demo + GitHub + HN)                        │
│  Oct 2026: Should-have features (watchlist, feed, Pro tier)          │
│  Jan 2027: Community & growth (15K stars, 3K DAU, $25K MRR)         │
│  Jun 2027: Industry standard (35K stars, $3M ARR)                    │
│                                                                      │
│  MILESTONES                                                          │
│  ──────────                                                          │
│  M1: Phase 6 complete        → Jul 2026                             │
│  M2: Real-time operational   → Jul 2026                             │
│  M3: Public launch           → Aug 2026                             │
│  M4: Should-haves complete   → Oct 2026                             │
│  M5: Community & growth      → Jan 2027                             │
│  M6: Industry standard       → Jun 2027                             │
│                                                                      │
│  CRITICAL PATH                                                       │
│  ──────────────                                                      │
│  Auth (6.1) → Webhooks (6.5) → Scheduler → Alerts → Launch          │
│                                                                      │
│  TOP RISKS                                                           │
│  ──────────                                                          │
│  🔴 R1: Score accuracy < 50%     → Backtest before launch           │
│  🔴 R2: Crunchbase copies        → Open-source moat                │
│  🟠 R3: Nobody adopts            → Killer demo + HN launch          │
│                                                                      │
│  CURRENT STATUS                                                      │
│  ──────────────                                                      │
│  5 of 6 phases complete (83% of development)                        │
│  55 agents, 26 collectors, 76 tables, 681 tests, 34 API endpoints   │
│  Phase 6 (Operations): 0/16 sessions → START NEXT                   │
│                                                                      │
│  NEXT ACTION: Start Phase 6, Session 6.1 (Auth Package)             │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

*Last updated: June 5, 2026*
