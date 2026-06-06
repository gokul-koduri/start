# 🏛️ Solution Design — Architecture, UX, Data Flow, Scalability & Security

> The complete technical blueprint: how every piece connects, what the user experiences, how data moves, how it scales, and how it stays safe

---

## Part 1: Architecture

---

### 1.1 Architecture Philosophy

```
THREE PRINCIPLES THAT DRIVE EVERY DECISION:

1. KAPPA, NOT LAMBDA
   One stream processing pipeline handles both real-time and batch.
   No separate batch layer. Bytewax processes everything.
   Simpler = fewer bugs = faster shipping.

2. DUAL-WRITE EVERYWHERE
   Every signal writes to MySQL (durable) AND Kafka (real-time).
   If Kafka dies, MySQL keeps everything. If MySQL dies, Kafka replays.
   No data loss. Ever.

3. SELF-HOSTED FIRST
   Every component runs on the user's machine via Docker Compose.
   No cloud dependencies. No vendor lock-in. No data leaves.
   Open-source stack: MySQL, Kafka, Redis, Qdrant, Elasticsearch, ClickHouse.
```

---

### 1.2 Layer Architecture (7 Layers)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  LAYER 7: PRESENTATION                                                       │
│  ┌─────────────────────┐  ┌──────────────────────┐  ┌────────────────────┐  │
│  │  Web Dashboard       │  │  API Consumers        │  │  Chat Interface    │  │
│  │  (site/index.html    │  │  (curl, SDKs,         │  │  (POST /api/chat   │  │
│  │   2,903 lines,       │  │   integrations)       │  │   via Ollama)      │  │
│  │   Canvas charts,     │  │                       │  │                    │  │
│  │   WebSocket live)    │  │                       │  │                    │  │
│  └──────────┬──────────┘  └──────────┬───────────┘  └─────────┬──────────┘  │
│             │                         │                        │             │
│  LAYER 6: API GATEWAY                                                       │
│  ┌──────────┴─────────────────────────┴────────────────────────┴──────────┐  │
│  │  FastAPI Server (api_server.py)                                        │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐   │  │
│  │  │  34 REST endpoints  │  WebSocket /ws/live  │  Auth middleware   │   │  │
│  │  │  Redis cache        │  License validation │  CORS handling     │   │  │
│  │  └─────────────────────────────────────────────────────────────────┘   │  │
│  └──────────────────────────────┬───────────────────────────────────────┘   │
│                                  │                                           │
│  LAYER 5: INTELLIGENCE                                                     │
│  ┌──────────────────────────────┴───────────────────────────────────────┐   │
│  │  26 Core Agents (agents/*.py)                                         │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐  │   │
│  │  │ Opportunity  │ │ Risk         │ │ Failure      │ │ Knowledge  │  │   │
│  │  │ Scorer       │ │ Scorer       │ │ Patterns     │ │ Graph      │  │   │
│  │  │ (composite   │ │ (0.0-1.0)    │ │ (6 category  │ │ (12 entity │  │   │
│  │  │  0-100)      │ │              │ │  taxonomy)   │ │  types)    │  │   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └────────────┘  │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐  │   │
│  │  │ Geographic   │ │ Whale        │ │ Survival     │ │ Revival    │  │   │
│  │  │ Strategy     │ │ Investors    │ │ Analysis     │ │ Opportun.  │  │   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └────────────┘  │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐  │   │
│  │  │ Competitive  │ │ Founder      │ │ News Intel   │ │ Alert      │  │   │
│  │  │ Landscape    │ │ Background   │ │              │ │ Dispatcher │  │   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └────────────┘  │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐  │   │
│  │  │ ML Predictor │ │ Report Gen   │ │ Semantic     │ │ Trend      │  │   │
│  │  │              │ │              │ │ Search       │ │ Detector   │  │   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └────────────┘  │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                  │   │
│  │  │ Cohort       │ │ Sector       │ │ Intent       │                  │   │
│  │  │ Analysis     │ │ Rotation     │ │ Classifier   │                  │   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘                  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                  │                                           │
│  LAYER 4: STREAM PROCESSING                                                │
│  ┌──────────────────────────────┴───────────────────────────────────────┐   │
│  │  Bytewax 5-Stage Dataflow (stream/pipeline.py)                        │   │
│  │                                                                       │   │
│  │  ┌─────────┐   ┌─────────┐   ┌──────────┐   ┌─────────┐   ┌───────┐ │   │
│  │  │ 1.INGEST│──▶│ 2.ENRICH│──▶│3.AGGREGATE│──▶│ 4.SCORE │──▶│5.OUTPUT│ │   │
│  │  │ Parse   │   │ Fast    │   │ Tumbling  │   │ Composit│   │ MySQL  │ │   │
│  │  │ Kafka   │   │ sentim. │   │ 5-min     │   │ + Risk  │   │ Kafka  │ │   │
│  │  │ msg     │   │ + meta  │   │ windows   │   │ + Attr  │   │ Alerts │ │   │
│  │  └─────────┘   └─────────┘   └──────────┘   └─────────┘   └───────┘ │   │
│  │                                                                       │   │
│  │  Operators: parse_signal_envelope, detect_complex_events,            │   │
│  │  compute_zscore, emit_alert, stateful_entity_tracker                 │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                  │                                           │
│  LAYER 3: MESSAGE BUS                                                      │
│  ┌──────────────────────────────┴───────────────────────────────────────┐   │
│  │  Kafka / Redpanda                                                     │   │
│  │  ┌────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐  │   │
│  │  │raw.signals │ │scores.updates│ │alerts.       │ │dead.letters  │  │   │
│  │  │(12 parts)  │ │(6 parts)     │ │triggered     │ │(3 parts)     │  │   │
│  │  │            │ │              │ │(3 parts)     │ │              │  │   │
│  │  └────────────┘ └──────────────┘ └──────────────┘ └──────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                  │                                           │
│  LAYER 2: DATA COLLECTION                                                  │
│  ┌──────────────────────────────┴───────────────────────────────────────┐   │
│  │  26 Collectors (collectors/*.py)                                       │   │
│  │                                                                       │   │
│  │  REAL-TIME (continuous):          SCHEDULED (periodic):              │   │
│  │  ┌────────────┐                  ┌────────────┐ ┌───────────────┐   │   │
│  │  │ Twitter    │                  │ SEC EDGAR  │ │ News RSS      │   │   │
│  │  │ (streaming)│                  │ (4 hours)  │ │ (15 min)      │   │   │
│  │  └────────────┘                  └────────────┘ └───────────────┘   │   │
│  │  ┌────────────┐                  ┌────────────┐ ┌───────────────┐   │   │
│  │  │ Reddit     │                  │ Patents    │ │ Job Postings  │   │   │
│  │  │ Stream     │                  │ (daily)    │ │ (6 hours)     │   │   │
│  │  └────────────┘                  └────────────┘ └───────────────┘   │   │
│  │  ┌────────────┐                  ┌────────────┐ ┌───────────────┐   │   │
│  │  │ HN Live    │                  │ GitHub     │ │ ProductHunt   │   │   │
│  │  │ (WebSocket)│                  │ (hourly)   │ │ (daily)       │   │   │
│  │  └────────────┘                  └────────────┘ └───────────────┘   │   │
│  │                                   + Crunchbase, arXiv, StackOverflow │   │
│  │                                   + Website Monitor, Regulatory      │   │
│  │                                   + Newsletter, NPM/PyPI, BLS, etc. │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                  │                                           │
│  LAYER 1: STORAGE                                                          │
│  ┌──────────────────────────────┴───────────────────────────────────────┐   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────────────┐  │   │
│  │  │ MySQL 8.0  │ │ Redis      │ │ Qdrant     │ │ Elasticsearch    │  │   │
│  │  │ (76 tables │ │ (cache +   │ │ (vector    │ │ (full-text       │  │   │
│  │  │  operational│   metrics)  │ │  search)   │ │  search)         │  │   │
│  │  │  store)    │ │            │ │            │ │                  │  │   │
│  │  └────────────┘ └────────────┘ └────────────┘ └──────────────────┘  │   │
│  │  ┌────────────┐ ┌────────────┐                                       │   │
│  │  │ ClickHouse │ │ TimescaleDB│                                       │   │
│  │  │ (OLAP      │ │ (time-     │                                       │   │
│  │  │  analytics)│ │  series)   │                                       │   │
│  │  └────────────┘ └────────────┘                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

### 1.3 Component Inventory

| Component | File(s) | Technology | Purpose | Status |
|---|---|---|---|---|
| **API Server** | `api_server.py` | FastAPI | REST + WebSocket gateway | ✅ 34 endpoints |
| **Web Dashboard** | `site/index.html` | HTML/JS/Canvas | Visual dashboard | ✅ 2,903 lines |
| **Chat Widget** | `site/chat-widget.js` | JavaScript | AI chat interface | ✅ |
| **Risk Widget** | `site/risk-widget.js` | JavaScript | Risk score visualization | ✅ |
| **KG Widget** | `site/knowledge-graph-widget.js` | JavaScript | Knowledge graph vis | ✅ |
| **Stream Pipeline** | `stream/pipeline.py` | Bytewax | 5-stage dataflow | ✅ |
| **Stream Operators** | `stream/operators.py` | Bytewax | Enrichment + detection | ✅ |
| **Stream State** | `stream/state.py` | Bytewax | Entity state tracking | ✅ |
| **Stream Metrics** | `stream/metrics.py` | Redis | Pipeline monitoring | ✅ |
| **Kafka Producer** | `ingestion/kafka_producer.py` | kafka-python-ng | Signal publishing | ✅ |
| **Signal Normalizer** | `ingestion/signal_normalizer.py` | Python | SignalEnvelope format | ✅ |
| **Orchestrator** | `agents/orchestrator.py` | Python | Agent execution engine | ✅ |
| **Collector Base** | `collectors/base.py` | Python | Dual-write pattern | ✅ |
| **Scoring Engine** | `agents/opportunity_scorer.py` | Python | Composite score (0-100) | ✅ |
| **Risk Engine** | `agents/risk_scorer.py` | Python | Risk score (0.0-1.0) | ✅ |
| **ML Pipeline** | `agents/ml_trainer.py`, `ml_predictor.py` | scikit-learn | ML prediction | ✅ |
| **Knowledge Graph** | `agents/knowledge_graph_agent.py` | MySQL | 12 entity types | ✅ |
| **NLP Pipeline** | `agents/nlp_enrichment_agent.py` | spaCy | NER + embeddings | ✅ |
| **LLM Interface** | `agents/model_manager.py` | Ollama | Local LLM inference | ✅ |
| **Auth System** | `auth/` (Phase 6.1) | JWT + RBAC | Authentication | 🔨 Not built |
| **Alert Consumer** | `alerting/consumer.py` (needed) | Python | Kafka → Slack/Email | 🔨 Not built |
| **Collector Scheduler** | `scheduler.py` (needed) | APScheduler | 24/7 collection | 🔨 Not built |

---

### 1.4 Service Map (Docker Compose)

```
┌──────────────────────────────────────────────────────────────┐
│  Docker Compose Network: oip-network                         │
│                                                              │
│  APPLICATION SERVICES                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │ api      │  │ streamlit│  │ pipeline │  │ stream_    │  │
│  │ :8000    │  │ :8501    │  │ (worker) │  │ processor  │  │
│  │ FastAPI  │  │ Dashboard│  │ Bytewax  │  │ Bytewax    │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └─────┬──────┘  │
│       │              │             │               │          │
│  DATA SERVICES                                               │
│  ┌────┴─────┐  ┌─────┴────┐  ┌───┴─────┐  ┌─────┴──────┐  │
│  │ mysql    │  │ redis    │  │ kafka   │  │ ollama     │  │
│  │ :3306    │  │ :6379    │  │ :9092   │  │ :11434     │  │
│  │ 76 tables│  │ cache    │  │ topics  │  │ llama3:8b  │  │
│  └──────────┘  └──────────┘  └─────────┘  └────────────┘  │
│                                                              │
│  SEARCH & ANALYTICS SERVICES                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ qdrant   │  │ elastic  │  │ click-   │  │ timescale│   │
│  │ :6333    │  │ :9200    │  │ house    │  │ db       │   │
│  │ vectors  │  │ full-text│  │ OLAP     │  │ time-    │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│                                                              │
│  PERSISTENCE VOLUMES                                        │
│  mysql_data │ redis_data │ kafka_data │ ollama_data         │
│  qdrant_data │ elasticsearch_data │ clickhouse_data         │
│  timescaledb_data                                           │
└──────────────────────────────────────────────────────────────┘

Total: 11 services + 8 volumes = 19 Docker Compose entries
```

---

## Part 2: User Experience (UX)

---

### 2.1 UX Philosophy

```
THREE RULES:

1. ZERO-CLICK VALUE
   The user gets intelligence before they click anything.
   Dashboard loads with live data, top opportunities, and recent alerts.
   Not an empty screen demanding input.

2. TYPE-AND-GET
   Every interaction should be: user types something → gets intelligence.
   Search box: type company name → get full analysis.
   Chat box: type question → get answer with citations.
   No multi-step wizards. No mandatory onboarding.

3. SPEED > COMPLETENESS
   Show partial results in 2 seconds rather than complete results in 30.
   "Found 23 signals for Tesla. Loading scores..." (progressive loading)
   "Score: 72 (preliminary — final score in 10 seconds)"
```

---

### 2.2 The 5 User Journeys

---

#### Journey 1: First-Time Visitor (30 seconds → "wow")

```
TIME: 0s                    TIME: 2s                  TIME: 10s
  │                           │                          │
  ▼                           ▼                          ▼
┌─────────────────────┐  ┌──────────────────┐  ┌──────────────────────┐
│ User opens          │  │ Dashboard loads  │  │ User sees:           │
│ demo.opportunity-   │  │ with:            │  │                      │
│ intel.org           │  │                  │  │  • Top 10 scored     │
│                     │  │  • Live signal   │  │    opportunities     │
│ NO SIGNUP           │  │    count (503)   │  │  • Failure pattern   │
│ NO LOGIN            │  │  • Risk chart    │  │    chart             │
│ NO INSTALL          │  │  • Recent alerts │  │  • "Why did these    │
│                     │  │  • Search box    │  │    startups fail?"   │
│ Just a URL          │  │  (blinking cursor│  │    breakdown         │
└─────────────────────┘  └──────────────────┘  └──────────────────────┘
                                                      │
                                                      ▼
                                              ┌──────────────────────┐
                                              │ TIME: 15s            │
                                              │                      │
                                              │ User types "Rivian"  │
                                              │ in search box        │
                                              │                      │
                                              │ INSTANTLY sees:      │
                                              │  • Score: 61         │
                                              │  • Risk: 0.42        │
                                              │  • "Why 61: Funding  │
                                              │    +18, Jobs +12,    │
                                              │    Patent +5..."     │
                                              │  • Failure pattern:  │
                                              │    "Similar to       │
                                              │    Better Place"     │
                                              │  • Connections:      │
                                              │    Amazon, Ford,     │
                                              │    US DOE            │
                                              │                      │
                                              │ USER THINKS: "Wow"   │
                                              └──────────────────────┘
```

#### Journey 2: Investor Gets Alert (15 minutes from event to action)

```
T=0 (Real-world event)     T=2min (Collection)       T=5min (Processing)
│                            │                          │
│ Startup X announces        │ Twitter collector        │ Pipeline detects
│ Series B funding           │ picks up tweet           │ "funding_event"
│ on Twitter                 │ → publishes to           │ → enriches with NER
│                            │   raw.signals topic      │ → aggregates with
│                            │   + writes to MySQL      │   other signals
│                            │                          │   for Startup X
│                            │                          │
│                            │                          ▼
│                            │                    T=7min (Scoring)
│                            │                    │
│                            │                    │ CompositeScorer runs
│                            │                    │ Score: 78 → 85 (+7)
│                            │                    │ Risk: 0.35 → 0.28
│                            │                    │ Attribution: "Funding
│                            │                    │   event +19, Jobs +8"
│                            │                    │
│                            │                    │ Score exceeds threshold
│                            │                    │ → emit_alert() called
│                            │                    │ → alerts.triggered topic
│                            │                    │
│                            │                    ▼
│                            │              T=8min (Alert Dispatch)
│                            │              │
│                            │              │ Alert Consumer reads topic
│                            │              │ Sends to:
│                            │              │  → Slack: "Startup X
│                            │              │    scored 85 (+7). Funding
│                            │              │    Series B — $40M."
│                            │              │  → Email: Full report
│                            │              │  → WebSocket: Dashboard
│                            │              │    updates live
│                            │              │
│                            │              ▼
│                            │        T=10min (Investor sees alert)
│                            │        │
│                            │        │ Investor opens Slack
│                            │        │ Sees alert with score + link
│                            │        │ Clicks link → opens dashboard
│                            │        │ Sees full analysis:
│                            │        │  • Score breakdown
│                            │        │  • Why it went up
│                            │        │  • Similar companies
│                            │        │  • Risk factors
│                            │        │
│                            │        │ INVESTOR DECIDES TO ACT
│                            │        └────────────────────────────────

TOTAL END-TO-END: 5-15 minutes (real-world event → user action)
```

#### Journey 3: Founder Avoids a Mistake

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  FOUNDER: "I want to start an EV battery company"          │
│                                                             │
│  Step 1: Searches "EV battery" in OIP                      │
│          → Sees 12 failed EV battery startups               │
│          → Average funding before failure: $48M             │
│          → Top failure reason: "Unit economics" (67%)       │
│                                                             │
│  Step 2: Clicks "Geographic Strategy"                       │
│          → Sees: "Michigan: 73% viability, 4% tax incentive"│
│          → Sees: "California: 58% viability, high talent"   │
│          → Sees: "Germany: 81% viability, EU subsidy"       │
│                                                             │
│  Step 3: Asks AI chat:                                     │
│          "Why did QuantumScape's stock drop?"               │
│          → OIP answers with data from SEC filings, news,    │
│            and failure patterns                             │
│                                                             │
│  Step 4: Views survival probability                         │
│          → "EV battery startups: 23% survive 5 years"       │
│          → "Manufacturing startups: 45% survive 5 years"    │
│                                                             │
│  DECISION: Founder pivots to solid-state battery            │
│  licensing (not manufacturing), sets up in Michigan         │
│  with German partnership.                                   │
│                                                             │
│  VALUE: Avoided a $10M mistake.                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### Journey 4: Researcher Gets Data for Paper

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  RESEARCHER: "I need failure data for my MBA thesis"       │
│                                                             │
│  Step 1: GET /api/startups?sector=manufacturing             │
│          → 500+ failed startups with structured data        │
│                                                             │
│  Step 2: GET /api/survival-rates?sector=tech                │
│          → BLS survival rates by sector                     │
│          → Cohort analysis by founding year                 │
│                                                             │
│  Step 3: GET /api/risk-scores?min_score=70                  │
│          → All currently high-scoring entities               │
│          → With risk breakdowns and attribution             │
│                                                             │
│  Step 4: POST /api/chat                                     │
│          "Correlation between funding and failure            │
│           in hardware startups?"                             │
│          → AI analysis with citations to OIP data           │
│                                                             │
│  Step 5: Export to CSV via /api/export                      │
│          → Downloads clean CSV for statistical analysis     │
│                                                             │
│  VALUE: 3 months of research compressed to 30 minutes.     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### Journey 5: Enterprise Analyst Integrates via API

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  ANALYST: "I need OIP data in our internal dashboard"      │
│                                                             │
│  Step 1: Self-host OIP via Docker Compose                   │
│          → docker compose up -d                             │
│          → All 11 services running                          │
│          → Data stays on company servers                    │
│                                                             │
│  Step 2: Generate API key                                   │
│          → POST /api/license/generate (admin only)          │
│          → Receives: oip_pro_xxxx_xxxx_xxxx                 │
│                                                             │
│  Step 3: Build integration                                  │
│          → Python SDK: from oip import OIPClient            │
│          → client = OIPClient(api_key="...", base_url="...")│
│          → scores = client.get_scores(min_score=80)         │
│          → Alerts pushed to internal Slack via webhook      │
│                                                             │
│  Step 4: Set up watchlist                                   │
│          → POST /api/watchlist (add 50 target companies)    │
│          → Webhook fires on any score change                │
│          → Internal dashboard shows real-time scores        │
│                                                             │
│  VALUE: Custom intelligence pipeline in 2 hours,           │
│  not 2 months. No data leaves the company.                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

### 2.3 Dashboard Layout (site/index.html)

```
┌──────────────────────────────────────────────────────────────────────────┐
│  🔍 Search: [type company name or question...]          FREE │ 🌙 │ WS ● │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐      │
│  │ SIGNALS: 503     │  │ SCORED: 47       │  │ ALERTS: 3        │      │
│  │ ▲ 12 today       │  │ ▲ 5 today        │  │ Latest: 2 min ago│      │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘      │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  FAILURE PATTERNS           │  FAILURES BY YEAR                  │    │
│  │  ■ No Market Need  (42%)    │  ▓▓▓▓▓▓▓▓░░░░ 2020: 34           │    │
│  │  ■ Ran Out of Cash (29%)    │  ▓▓▓▓▓▓▓▓▓▓▓░ 2021: 51           │    │
│  │  ■ Team Issues      (14%)   │  ▓▓▓▓▓▓▓▓▓▓▓▓ 2022: 67           │    │
│  │  ■ Competition      (8%)    │  ▓▓▓▓▓▓▓▓▓▓▓▓▓ 2023: 78           │    │
│  │  ■ Legal            (4%)    │  ▓▓▓▓▓▓▓▓▓▓▓░ 2024: 62           │    │
│  │  ■ Other            (3%)    │  ▓▓▓▓▓▓░░░░░░ 2025: 33           │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  TOP OPPORTUNITIES                                              │    │
│  │  1. Company A   Score: 92  ▲+8  "Series C, 200 jobs posted"    │    │
│  │  2. Company B   Score: 88  ▲+3  "Patent granted, SEC filing+"  │    │
│  │  3. Company C   Score: 85  ▲+12 "Funding + key hire"           │    │
│  │  4. Company D   Score: 83  ────  "Stable, monitoring"          │    │
│  │  5. Company E   Score: 81  ▼-5  "CTO departed, 50 layoffs"     │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  💬 Ask anything: "Why did Juicero fail?"                       │   │
│  │                                                                  │   │
│  │  AI: Juicero (2016-2017) raised $118M and failed because...     │   │
│  │  1. No Market Need: $400 juicer squeezed bags that hands could  │   │
│  │  2. Unit Economics: $400 device with $15M+ manufacturing cost   │   │
│  │  3. Overengineering: 400 custom parts, WiFi-connected press     │   │
│  │                                                                  │   │
│  │  Similar patterns: GoPro Karma, Peloton Tread, Jawbone UP      │   │
│  │  Pattern match confidence: 94%                                   │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  BLS SURVIVAL RATES (Manufacturing) │  FAILURES BY REGION       │    │
│  │  Year 1: 79.3%                      │  🟢 Midwest: 12          │    │
│  │  Year 3: 55.8%                      │  🔴 California: 23       │    │
│  │  Year 5: 45.4%                      │  🟡 Northeast: 18        │    │
│  │  Year 7: 38.2%                      │  🔵 Europe: 14           │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  GLOBAL MARKET VIABILITY                                        │    │
│  │  Germany: ████████░░ 81%  │  US-Michigan: ███████░░░ 73%       │    │
│  │  Japan:   ███████░░░ 72%  │  India:       ██████░░░░ 64%       │    │
│  │  China:   ██████░░░░ 61%  │  Brazil:      █████░░░░░ 48%       │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  [Dark mode toggle] [WebSocket status: ● Connected] [Last update: 2m]  │
└──────────────────────────────────────────────────────────────────────────┘
```

**Current dashboard features** (already built in site/index.html):
- ✅ Canvas-based charts (failure categories, year trends, survival rates, regions)
- ✅ WebSocket live connection with status indicator
- ✅ Dark mode toggle
- ✅ Search input
- ✅ Tier badge (FREE/PRO/ENTERPRISE)
- ✅ Responsive sidebar with hamburger menu
- ✅ Global Market Viability analysis section
- ✅ Revenue charts
- ✅ Research report content (failed startups, revival industries)

**Missing (to build):**
- 🔨 Score cards with delta arrows
- 🔨 Top opportunities ranked list
- 🔨 AI chat inline panel
- 🔨 Alert feed (recent alerts)
- 🔨 Watchlist management

---

### 2.4 API Response Design

Every API response follows the same envelope:

```json
{
  "status": "success",
  "data": { ... },
  "meta": {
    "total": 523,
    "page": 1,
    "per_page": 20,
    "cached": true,
    "cache_ttl_seconds": 300,
    "processing_time_ms": 42
  },
  "links": {
    "self": "/api/startups?page=1",
    "next": "/api/startups?page=2",
    "prev": null
  }
}
```

**Error responses** are consistent:

```json
{
  "status": "error",
  "error": {
    "code": "ENTITY_NOT_FOUND",
    "message": "No entity found with name 'nonexistent-corp'",
    "suggestion": "Try /api/search?q=nonexistent+corp for fuzzy matching"
  }
}
```

---

### 2.5 Accessibility & Responsiveness

| Requirement | Implementation | Status |
|---|---|---|
| Keyboard navigation | Tab through search, charts, links | ✅ Native HTML |
| Screen reader labels | aria-label on buttons, roles on regions | ✅ Partial |
| Dark mode | Toggle button, CSS variables | ✅ Built |
| Mobile responsive | Hamburger menu, flex layouts | ✅ Built |
| High contrast | CSS variable theme system | ✅ Built |
| WCAG 2.1 AA | Target for full compliance | ⚠️ Partial |

---

## Part 3: Data Flow

---

### 3.1 Signal Lifecycle (From Real-World Event to User Decision)

```
REAL WORLD          COLLECTION          INGESTION           PROCESSING
EVENT               (0-60 sec)          (1-2 sec)           (1-5 min)
    │                   │                   │                   │
    │  "Startup X      │  Collector        │  Signal normal-   │  Bytewax pipeline:
    │   raises $40M    │  detects event    │  izer creates     │  1. Parse signal
    │   Series B"      │  via API/stream   │  SignalEnvelope   │  2. Enrich (sentiment)
    │                   │                   │  with:            │  3. Aggregate (window)
    │                   │  BaseCollector    │  • entity_name    │  4. Score (composite)
    │                   │  .run() method:   │  • signal_type    │  5. Output (MySQL+Kafka)
    │                   │  1. Collect raw   │  • source         │
    │                   │  2. Normalize     │  • confidence     │  If score > threshold:
    │                   │  3. Write MySQL   │  • timestamp      │  → emit_alert()
    │                   │  4. Publish Kafka │  • dedup_hash     │  → alerts.triggered
    │                   │                   │                   │
    ▼                   ▼                   ▼                   ▼
                                                            ┌──────────┐
                                                            │ STORAGE  │
                                                            │ MySQL:   │
                                                            │ raw_sig- │
                                                            │ nals     │
                                                            │ Kafka:   │
                                                            │ raw.sig- │
                                                            │ nals     │
                                                            └──────────┘
                                                                  │
                                                                  ▼
SCORING             STORAGE             DELIVERY            USER
(1-3 sec)           (instant)           (1-5 sec)           (action)
    │                   │                   │                   │
    │  CompositeScorer  │  MySQL:           │  Alert Consumer   │  Investor
    │  calculates:      │  opportunity_     │  reads Kafka      │  sees Slack
    │  • Score: 78→85   │  scores table     │  alerts.triggered │  notification
    │  • Risk: 0.35→0.28│                   │                   │
    │  • Attribution:   │  Redis:           │  Dispatches to:   │  Clicks link
    │    "Funding +19,  │  cached score     │  • Slack webhook  │  → sees full
    │     Jobs +8,      │  for fast API     │  • Email (SMTP)   │    analysis
    │     Patent +3"    │  reads            │  • WebSocket push │
    │                   │                   │  • Custom webhook │  Makes
    │  Writes to:       │  Qdrant:          │                   │  decision
    │  • scores.updates │  vector for       │  Score Push       │  in minutes,
    │    (Kafka)        │  semantic search  │  reads Kafka      │  not days
    │  • MySQL          │                   │  scores.updates   │
    │  • Redis cache    │                   │  → WebSocket      │
    ▼                   ▼                   ▼                   ▼
```

---

### 3.2 Data Flow: Dual-Write Pattern (Critical)

```
                    COLLECTOR
                   ┌──────────┐
                   │ collect()│
                   └────┬─────┘
                        │
                        ▼
                ┌───────────────┐
                │  SignalEnvelope│
                │  (normalized)  │
                └───────┬───────┘
                        │
              ┌─────────┴─────────┐
              │                   │
    ┌─────────▼──────┐  ┌────────▼────────┐
    │  MySQL WRITE   │  │  KAFKA PUBLISH  │
    │  (durable)     │  │  (real-time)    │
    │                │  │                 │
    │  INSERT INTO   │  │  producer.send()│
    │  raw_signals   │  │  → raw.signals  │
    │                │  │  topic          │
    │  GUARANTEE:    │  │                 │
    │  Never lost    │  │  GUARANTEE:     │
    │  ACID          │  │  Eventually     │
    │  transaction   │  │  consistent     │
    └────────────────┘  └─────────────────┘
              │                   │
              │                   ▼
              │          ┌─────────────────┐
              │          │  Bytewax         │
              │          │  Stream Pipeline │
              │          │  (5 stages)      │
              │          └────────┬────────┘
              │                   │
              │                   ▼
              │          ┌─────────────────┐
              │          │  PROCESSED DATA  │
              │          │  MySQL: scores,  │
              │          │  alerts, events  │
              │          │  Kafka: scores.  │
              │          │  updates, alerts │
              │          │  Redis: cached   │
              │          │  scores, metrics │
              │          └──────────────────┘
              │                   │
              └───────┬───────────┘
                      │
                      ▼
              ┌───────────────┐
              │  API READS    │
              │  1. Check     │
              │     Redis     │
              │     (cache)   │
              │  2. If miss:  │
              │     Read      │
              │     MySQL     │
              │     + cache   │
              │  Response:    │
              │  <50ms cached │
              │  <500ms fresh │
              └───────────────┘
```

---

### 3.3 Kafka Topic Topology

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  INGESTION TOPICS (written by collectors)                              │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  raw.signals          ← ALL signals (12 partitions by entity)   │ │
│  │  raw.signals.sec      ← SEC filing signals (typed)              │ │
│  │  raw.signals.funding  ← Funding event signals (typed)            │ │
│  │  raw.signals.job      ← Job posting signals (typed)              │ │
│  │  raw.signals.github   ← GitHub activity signals (typed)          │ │
│  │  raw.signals.patent   ← Patent filing signals (typed)            │ │
│  │  raw.signals.social   ← Social media signals (typed)             │ │
│  │  raw.signals.news     ← News RSS signals (typed)                 │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  PROCESSING TOPICS (written by Bytewax pipeline)                       │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  scores.updates       ← Score changes (6 partitions)             │ │
│  │  alerts.triggered     ← High-priority alerts (3 partitions)     │ │
│  │  enrichment.complete  ← NLP-enriched signals (future)            │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ERROR TOPICS                                                           │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  dead.letters         ← Malformed signals (3 partitions, 7 days) │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  CONSUMER GROUPS                                                        │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  signal-processor     ← Bytewax pipeline (main consumer)         │ │
│  │  alert-dispatcher     ← Alert Consumer (→ Slack/Email)           │ │
│  │  score-pusher         ← Score Push (→ WebSocket clients)          │ │
│  │  enrichment-worker    ← NLP Worker (future)                       │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### 3.4 Data Storage Map

| Data Type | Primary Store | Secondary Store | Why Both |
|---|---|---|---|
| **Raw signals** | MySQL `raw_signals` | Kafka `raw.signals` | MySQL = query, Kafka = process |
| **Opportunity scores** | MySQL `opportunity_scores` | Redis cache | MySQL = history, Redis = speed |
| **Risk scores** | MySQL `startup_risk_scores` | Redis cache | MySQL = audit, Redis = API speed |
| **Knowledge graph** | MySQL `kg_entities`, `kg_relationships` | — | Graph queries via SQL JOINs |
| **News articles** | MySQL `news_articles` | Elasticsearch | MySQL = storage, ES = search |
| **Failed startups** | MySQL `failed_startups` | Elasticsearch | MySQL = analysis, ES = search |
| **Vector embeddings** | Qdrant | — | Semantic search only |
| **Time-series metrics** | Redis `stream:metrics` | TimescaleDB (future) | Redis = real-time, TSDB = history |
| **OLAP analytics** | ClickHouse | — | Fast aggregations across millions |
| **Collection history** | MySQL `collection_runs` | — | Operational audit trail |
| **Alerts** | MySQL `alert_dispatches` | Kafka `alerts.triggered` | MySQL = audit, Kafka = dispatch |
| **Webhooks** | MySQL `api_webhooks` | — | Configuration storage |
| **User licenses** | MySQL `user_licenses` | — | Auth + billing |
| **Tenants** | MySQL `tenants` | — | Multi-tenancy config |

---

### 3.5 Data Volume Estimates

| Metric | Current | Month 6 | Year 1 | Year 2 |
|---|---|---|---|---|
| **Signals / day** | ~100 (seed) | 5,000 | 50,000 | 200,000 |
| **Signals / month** | ~3,000 | 150,000 | 1.5M | 6M |
| **Scored entities** | ~50 | 500 | 5,000 | 20,000 |
| **Knowledge graph nodes** | ~200 | 2,000 | 20,000 | 100,000 |
| **Knowledge graph edges** | ~500 | 5,000 | 50,000 | 250,000 |
| **MySQL size** | ~50 MB | 500 MB | 5 GB | 25 GB |
| **Kafka throughput** | ~10 msg/min | 100 msg/min | 1,000 msg/min | 5,000 msg/min |
| **Redis cache size** | ~10 MB | 50 MB | 200 MB | 1 GB |
| **Qdrant vectors** | ~1,000 | 10,000 | 100,000 | 500,000 |

---

## Part 4: Scalability

---

### 4.1 Scalability Philosophy

```
THREE PRINCIPLES:

1. SCALE VERTICALLY FIRST
   A single server with 32GB RAM and 8 cores handles 50,000 signals/day.
   Don't prematurely distribute. Keep it simple.

2. PARTITION AT KAFKA
   Kafka topics are partitioned by entity_name.
   Add partitions → add workers → linear throughput scaling.
   No code changes needed.

3. CACHE AGGRESSIVELY
   Redis caches every API response for 5 minutes.
   90%+ of reads hit cache, not MySQL.
   Scale reads without scaling MySQL.
```

---

### 4.2 Scalability Tiers

```
TIER 1: SINGLE MACHINE (0-1,000 users)
┌─────────────────────────────────────────────────────┐
│  Hardware: 8 cores, 32GB RAM, 500GB SSD             │
│  Cost: ~$100/month (any cloud VM or local machine)  │
│                                                     │
│  All 11 Docker services on one machine              │
│  Handles: 50K signals/day, 1K API req/min           │
│  THIS IS WHERE WE ARE NOW.                          │
└─────────────────────────────────────────────────────┘

TIER 2: SMALL CLUSTER (1,000-10,000 users)
┌─────────────────────────────────────────────────────┐
│  Hardware: 3 machines (API, Data, Processing)       │
│  Cost: ~$300/month                                   │
│                                                     │
│  Machine 1 (API): FastAPI (4w) + Redis + Ollama    │
│  Machine 2 (Data): MySQL + ES + Qdrant + CH + TSDB │
│  Machine 3 (Processing): Kafka (3br) + Bytewax (4w)│
│                                                     │
│  Handles: 500K signals/day, 5K API req/min          │
│  THIS IS WHERE WE ARE AT MONTH 6.                   │
└─────────────────────────────────────────────────────┘

TIER 3: PRODUCTION CLUSTER (10,000+ users)
┌─────────────────────────────────────────────────────┐
│  Hardware: Kubernetes cluster, 8+ nodes              │
│  Cost: ~$1,000/month                                 │
│                                                     │
│  • API: 8 replicas    • MySQL: 1 primary + 2 repl   │
│  • Kafka: 5 brokers   • Redis: 3-node sentinel      │
│  • ES: 3 nodes        • Qdrant: 3 nodes             │
│  • Bytewax: 8 workers  • Ollama: 2 GPU nodes        │
│                                                     │
│  Handles: 5M signals/day, 50K API req/min            │
│  THIS IS WHERE WE ARE AT YEAR 2.                     │
└─────────────────────────────────────────────────────┘
```

---

### 4.3 Scalability Bottlenecks & Solutions

| Bottleneck | Where | Limit | Solution |
|---|---|---|---|
| **API throughput** | FastAPI workers | ~1K req/sec/worker | Add workers (horizontal) |
| **Kafka throughput** | Broker I/O | ~100K msg/sec/broker | Add partitions + brokers |
| **MySQL reads** | API queries | ~5K queries/sec | Redis cache (built) + read replicas |
| **MySQL writes** | Signal inserts | ~10K inserts/sec | Batch inserts + ClickHouse |
| **Bytewax processing** | Window aggregation | ~1K signals/min/worker | Add workers (partition scaling) |
| **Ollama inference** | LLM chat | ~10 req/sec (CPU) | Add GPU or lighter model |
| **Qdrant search** | Vector similarity | ~10K queries/sec | Cluster mode |
| **Elasticsearch** | Full-text search | ~5K queries/sec | Add shards + nodes |

---

### 4.4 Horizontal Scaling Paths

```
SCALE PATH 1: API LAYER
  1 FastAPI worker → 4 workers → 8 workers → Kubernetes autoscaling
  Trigger: p95 latency > 500ms
  Action: Add workers (no code change)

SCALE PATH 2: STREAM PROCESSING
  1 Bytewax worker → 2 → 4 → 8
  Trigger: Processing lag > 5 minutes
  Action: Increase Kafka partitions + Bytewax workers
  Command: python -m stream.pipeline --workers 4

SCALE PATH 3: DATABASE READS
  1 MySQL primary → +1 read replica → +2 read replicas
  Trigger: MySQL CPU > 70%
  Action: Route API reads to replicas via ProxySQL
  (Redis cache already handles 90%+ of reads)

SCALE PATH 4: SEARCH
  1 Qdrant node → 3-node cluster
  1 ES node → 3-node cluster
  Trigger: Search latency > 200ms
  Action: Add nodes, increase shards

SCALE PATH 5: KAFKA
  1 broker → 3 brokers → 5 brokers
  12 partitions → 24 partitions → 48 partitions
  Trigger: Consumer lag increasing
  Action: Add brokers + partitions
```

---

### 4.5 Performance Targets by Tier

| Metric | Tier 1 (Now) | Tier 2 (Month 6) | Tier 3 (Year 2) |
|---|---|---|---|
| **API p50 latency** | < 100ms | < 100ms | < 100ms |
| **API p95 latency** | < 500ms | < 300ms | < 200ms |
| **API p99 latency** | < 1000ms | < 500ms | < 300ms |
| **Signal throughput** | 100/min | 1,000/min | 5,000/min |
| **Search latency** | < 200ms | < 150ms | < 100ms |
| **Chat response time** | < 10s | < 5s | < 3s |
| **Alert delivery** | < 15 min | < 10 min | < 5 min |
| **Concurrent users** | 100 | 1,000 | 10,000 |
| **Uptime** | 99.5% | 99.9% | 99.95% |
| **Daily signals** | 5,000 | 50,000 | 200,000 |

---

## Part 5: Security

---

### 5.1 Security Philosophy

```
THREE PRINCIPLES:

1. SELF-HOSTED = SECURE BY DEFAULT
   All data stays on the user's infrastructure.
   No cloud dependencies. No third-party data sharing.
   The biggest security feature is: we don't have your data.

2. DEFENSE IN DEPTH
   Every layer has its own security:
   Network → API → Application → Data → Access
   A breach at one layer doesn't compromise everything.

3. OPEN SOURCE = AUDITABLE
   Every line of code is public.
   Security through transparency, not obscurity.
   Community reviews code for vulnerabilities.
```

---

### 5.2 Threat Model

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  🔴 HIGH PRIORITY                                                   │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ T1: API abuse — unauthenticated user scrapes all data          │  │
│  │     Mitigation: Rate limiting + API key auth + query limits    │  │
│  │     Status: 🔨 Rate limiting not built, auth is Phase 6.1     │  │
│  │                                                                │  │
│  │ T2: SQL injection — malicious input in search/chat queries     │  │
│  │     Mitigation: Parameterized queries (cursor.execute params)  │  │
│  │     Status: ✅ Already using parameterized queries             │  │
│  │                                                                │  │
│  │ T3: Kafka unauthorized access — rogue producer/consumer        │  │
│  │     Mitigation: Kafka SASL + network isolation (Docker net)    │  │
│  │     Status: ⚠️ Kafka is open within Docker network            │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  🟡 MEDIUM PRIORITY                                                  │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ T4: Data source ToS violation — scraping rate-limited APIs     │  │
│  │     Mitigation: Rate limiting per collector + exponential       │  │
│  │     backoff + respect robots.txt                               │  │
│  │     Status: ✅ Rate limiting in config/settings.yaml           │  │
│  │                                                                │  │
│  │ T5: LLM prompt injection — malicious chat input                │  │
│  │     Mitigation: Input sanitization + output filtering          │  │
│  │     Status: ⚠️ Partial — Ollama is local (limited impact)     │  │
│  │                                                                │  │
│  │ T6: Credential exposure — API keys in logs or config           │  │
│  │     Mitigation: Environment variables + .env file + .gitignore │  │
│  │     Status: ✅ Config uses ${VAR} env var substitution         │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  🟢 LOW PRIORITY (but handled)                                       │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ T7: XSS — in dashboard or API       → CSP headers             │  │
│  │ T8: CORS exploitation               → Strict CORS policy      │  │
│  │ T9: DDoS — overwhelming API         → Rate limiting + nginx   │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

### 5.3 Security Architecture by Layer

#### Network Security

```
Docker Network Isolation:

  oip-internal network (no external access)
    ├── mysql:3306       ← only API + collectors connect
    ├── kafka:9092       ← only collectors + pipeline connect
    ├── redis:6379       ← only API + pipeline connect
    ├── qdrant:6333      ← only API + enrichment connect
    ├── elasticsearch    ← only API + enrichment connect
    ├── clickhouse       ← only pipeline + analytics connect
    └── timescaledb      ← only pipeline + metrics connect

  Exposed to host (external):
    ├── api:8000         ← users connect here
    ├── streamlit:8501   ← internal dashboard
    └── ollama:11434     ← LLM inference (local only)

  Production additions:
    • nginx reverse proxy with TLS termination
    • Firewall rules: only ports 80/443 exposed
    • VPN for admin access
```

#### API Security

```
Authentication (Phase 6.1):

  Tier        Auth Required    Rate Limit     Access
  ─────       ─────────────    ──────────     ──────
  Free        None             60 req/min     Read-only
  Pro         API key          300 req/min    Read + alerts
  Enterprise  API key + SSO    1000 req/min   Full access
  Admin       JWT token        Unlimited      System management

API Key Flow:
  1. POST /api/license/generate → returns oip_pro_xxxx_xxxx
  2. Client sends: Authorization: Bearer oip_pro_xxxx_xxxx
  3. Middleware validates key against user_licenses table
  4. Checks tier + expiry + rate limit
  5. If valid → proceeds. If invalid → 401 Unauthorized

JWT Flow (admin):
  1. POST /auth/login → returns JWT token (HS256, 24h expiry)
  2. Client sends: Authorization: Bearer <jwt>
  3. Middleware validates signature + expiry + role
  4. Role determines access (viewer/analyst/admin/superadmin)
```

#### Application Security

```
Input Validation:
  • All API inputs validated via Pydantic models
  • Search queries sanitized (no special characters)
  • Chat input length limited (max 1000 characters)
  • File uploads rejected (no upload endpoints)

SQL Injection Prevention:
  • ALL queries use parameterized cursor.execute(sql, params)
  • No string formatting in SQL queries
  • Pydantic validation before any database interaction
  • Status: ✅ Verified in api_server.py + agents

LLM Security:
  • Ollama runs locally (no external API calls)
  • Chat responses don't include system prompts
  • Input length limited to prevent resource exhaustion
  • No PII in chat logs (only company/investor data)
```

#### Data Security

```
What We Store                  What We DON'T Store
┌────────────────────────┐     ┌─────────────────────────┐
│ ✅ Company names       │     │ ❌ Personal emails      │
│ ✅ Funding amounts     │     │ ❌ Phone numbers        │
│ ✅ SEC filing data     │     │ ❌ Home addresses       │
│ ✅ Public news         │     │ ❌ Social security #    │
│ ✅ Job posting data    │     │ ❌ Credit card numbers  │
│ ✅ Patent data         │     │ ❌ Password hashes      │
│ ✅ GitHub public repos │     │ ❌ Health records       │
│ ✅ BLS statistics      │     │ ❌ Any PII              │
└────────────────────────┘     └─────────────────────────┘

Data Classification: PUBLIC ONLY
  Every data point in OIP comes from public sources.
  We never collect, store, or process personal information.
  This dramatically simplifies GDPR/CCPA compliance.

Encryption:
  • At rest: MySQL TLS (configurable)
  • In transit: HTTPS (nginx TLS termination)
  • In Kafka: TLS between brokers (production)
  • API keys: Bcrypt-hashed in user_licenses table
```

#### Access Control (RBAC — Phase 6.1)

```
Resource           Viewer  Analyst  Admin  SuperAdmin  Public
─────────────      ──────  ───────  ─────  ──────────  ──────
Read scores         ✅      ✅       ✅      ✅         ✅
Read signals        ✅      ✅       ✅      ✅         ✅
Read alerts         ✅      ✅       ✅      ✅         ❌
Create watchlist    ❌      ✅       ✅      ✅         ❌
Export data         ❌      ✅       ✅      ✅         ❌
Manage webhooks     ❌      ❌       ✅      ✅         ❌
Manage users        ❌      ❌       ✅      ✅         ❌
Configure agents    ❌      ❌       ❌      ✅         ❌
System settings     ❌      ❌       ❌      ✅         ❌
Delete data         ❌      ❌       ❌      ✅         ❌
```

---

### 5.4 GDPR / CCPA Compliance (Simplified by Design)

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  WHY COMPLIANCE IS EASY:                                             │
│                                                                      │
│  1. NO PII = NO GDPR PROBLEM                                        │
│     We don't collect personal data. We collect company data.        │
│     Company names, funding, SEC filings = public data.              │
│     GDPR applies to PERSONAL data, not company intelligence.        │
│                                                                      │
│  2. SELF-HOSTED = USER IS THE CONTROLLER                            │
│     The user runs OIP on their own infrastructure.                  │
│     They are the data controller, not us.                           │
│     We don't process, store, or have access to their data.          │
│                                                                      │
│  3. OPEN SOURCE = TRANSPARENT PROCESSING                            │
│     Every data processing step is visible in source code.           │
│     No black boxes. No hidden data collection.                      │
│     Article 30 (records of processing) = the source code.           │
│                                                                      │
│  4. NO COOKIES = NO CONSENT NEEDED                                  │
│     The dashboard uses WebSocket, not cookies.                      │
│     No tracking. No analytics. No advertising.                      │
│                                                                      │
│  STILL NEED TO DO:                                                   │
│  • Privacy policy template for self-hosters                         │
│  • Data retention configuration (auto-delete signals after N days)  │
│  • Right-to-delete endpoint (DELETE /api/entities/{name})           │
│  • Audit log of all data access (Phase 6.1 auth logs)              │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

### 5.5 Security Checklist (What's Done vs. Needed)

| Security Control | Status | Phase |
|---|---|---|
| Parameterized SQL queries | ✅ Done | Always |
| Docker network isolation | ✅ Done | Always |
| CORS handling | ✅ Done | Always |
| Environment variable configs | ✅ Done | Always |
| .gitignore for secrets | ✅ Done | Always |
| Graceful Kafka fallback | ✅ Done | Always |
| Dead letter queue | ✅ Done | Always |
| API rate limiting | 🔨 Not built | Phase 6.1 |
| JWT authentication | 🔨 Not built | Phase 6.1 |
| RBAC authorization | 🔨 Not built | Phase 6.1 |
| API key validation | ✅ Built (license endpoint) | Phase 5 |
| CSP headers | 🔨 Not built | Phase 6.1 |
| HTTPS (nginx TLS) | 🔨 Not built | Launch |
| Kafka SASL authentication | 🔨 Not built | Production |
| MySQL TLS | 🔨 Not built | Production |
| Input length limits | ⚠️ Partial | Phase 6.1 |
| Output sanitization | ⚠️ Partial | Phase 6.1 |
| Audit logging | 🔨 Not built | Phase 6.1 |
| Data retention policy | 🔨 Not built | Phase 6.2 |
| Prometheus alerting | 🔨 Not built | Phase 6.11 |

---

## Part 6: HuggingFace MCP Integration

---

### 6.1 What Is HuggingFace MCP?

```
MCP = Model Context Protocol

An open protocol that lets AI assistants (like Claude, GPT, etc.)
connect to external tools and data sources through a standardized interface.

HuggingFace MCP Server provides:
  • Access to 500,000+ models on HuggingFace Hub
  • Model search and discovery
  • Model performance benchmarks
  • Model download and deployment
  • Inference endpoint management

WHY THIS MATTERS FOR OIP:
  OIP currently uses sentence-transformers (all-MiniLM-L6-v2) for
  embeddings and Ollama for LLM inference. HuggingFace MCP gives us
  a standardized way to:
  1. Discover better models without code changes
  2. Swap embedding models dynamically
  3. Access HuggingFace Inference API for heavy lifting
  4. Let users choose their own models via MCP config
```

---

### 6.2 Current HuggingFace Usage (Without MCP)

```
CURRENT STATE:

┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  EMBEDDINGS (Hardcoded)                                              │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │  File: nlp/embedding_generator.py                               ││
│  │  Model: sentence-transformers/all-MiniLM-L6-v2                  ││
│  │  Dimensions: 384                                                 ││
│  │  Size: ~80MB                                                     ││
│  │  Purpose: Semantic search (Qdrant), entity resolution            ││
│  │                                                                  ││
│  │  Problem: Model is hardcoded. To swap models, edit source code. ││
│  │  Problem: No way to benchmark alternatives.                     ││
│  │  Problem: No way to use HuggingFace Inference API.              ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  LLM INFERENCE (Ollama — Local)                                     │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │  File: agents/model_manager.py                                  ││
│  │  Model: llama3:8b (via Ollama)                                   ││
│  │  Purpose: AI chat, summarization, report generation             ││
│  │                                                                  ││
│  │  Problem: CPU-only, slow (5-10s per response).                  ││
│  │  Problem: No fallback to cloud inference.                       ││
│  │  Problem: No way to try new models without manual pull.         ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  NLP PIPELINE                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │  File: agents/nlp_enrichment_agent.py                           ││
│  │  Tools: spaCy NER + custom classifiers                          ││
│  │  Purpose: Named entity recognition, relationship extraction     ││
│  │                                                                  ││
│  │  Problem: spaCy is good but limited. No access to HF models    ││
│  │  like BERT-NER, RoBERTa-NER, etc.                              ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  STATUS: Works, but rigid. No model flexibility. No MCP.            │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

### 6.3 Proposed HuggingFace MCP Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  WITHOUT MCP (Current):                     WITH MCP (Proposed):    │
│                                                                      │
│  ┌──────────────┐                           ┌──────────────┐        │
│  │ OIP Code     │                           │ OIP Code     │        │
│  │              │                           │              │        │
│  │ import       │                           │ MCP Client   │        │
│  │ SentenceTr...│                           │ (standardized│        │
│  │ model =      │                           │  interface)  │        │
│  │ SentenceTr...│                           │              │        │
│  │ ("all-MiniLM")                           │      │       │        │
│  │              │                           │      │ MCP   │        │
│  │ HARDCODED    │                           │      │ Proto │        │
│  │ NO SWAPPING  │                           │      │ col   │        │
│  │ NO DISCOVERY │                           │      ▼       │        │
│  └──────────────┘                           │ ┌──────────┐ │        │
│                                             │ │HF MCP    │ │        │
│                                             │ │Server    │ │        │
│                                             │ │          │ │        │
│                                             │ │ • Search │ │        │
│                                             │ │ • Download│ │        │
│                                             │ │ • Infer  │ │        │
│                                             │ │ • Bench  │ │        │
│                                             │ │          │ │        │
│                                             │ │ ┌──────┐ │ │        │
│                                             │ │ │ HF   │ │ │        │
│                                             │ │ │ Hub  │ │ │        │
│                                             │ │ │ 500K+│ │ │        │
│                                             │ │ │models│ │ │        │
│                                             │ │ └──────┘ │ │        │
│                                             │ └──────────┘ │        │
│                                             └──────────────┘        │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

### 6.4 How HuggingFace MCP Integrates with OIP

#### Integration Point 1: Dynamic Embedding Model Selection

```
CURRENT:
  EmbeddingGenerator("all-MiniLM-L6-v2")  <- hardcoded in nlp/embedding_generator.py

WITH MCP:
  MCP Client -> HF MCP Server -> search("best embedding model for startup names")
  -> Returns: [all-MiniLM-L6-v2, bge-small-en-v1.5, e5-base-v2, ...]
  -> User selects model -> MCP downloads + configures
  -> EmbeddingGenerator uses selected model

CONFIG (config/settings.yaml):
  models:
    embedding:
      provider: "huggingface_mcp"          # or "local" (current)
      model: "BAAI/bge-small-en-v1.5"      # MCP-discovered
      dimensions: 384
      fallback: "all-MiniLM-L6-v2"         # if MCP unavailable
    llm:
      provider: "ollama"                    # or "huggingface_mcp"
      model: "llama3:8b"
      fallback: "keyword_based"
```

#### Integration Point 2: HuggingFace Inference API (Cloud Fallback)

```
USE CASE: Self-hosted user doesn't have GPU for embeddings.

WITHOUT MCP:
  User must install sentence-transformers + download 80MB model.
  If their machine is slow, embeddings take 5-10 seconds each.

WITH MCP:
  OIP -> MCP Client -> HF Inference API -> returns embeddings in 100ms.
  No local model download. No GPU needed.
  Free tier: 1,000 requests/hour (enough for most users).

CODE FLOW:
  embed_text("Tesla Inc")
    -> MCP Client calls hf_inference/embeddings
    -> Returns: [0.12, -0.34, 0.56, ...] (384-dim vector)
    -> Same interface as local model
    -> User doesn't know or care if it's local or cloud
```

#### Integration Point 3: Model Benchmarking for NER

```
USE CASE: Which NER model is best for startup entity extraction?

CURRENT:
  We use spaCy en_core_web_sm. Good but not state-of-the-art.
  No way to compare alternatives.

WITH MCP:
  MCP Client -> HF MCP Server -> search("named entity recognition english")
  -> Returns models with benchmarks:
     - dslim/bert-base-NER:     F1 = 0.92 (440MB)
     - Jean-Baptiste/camembert-ner: F1 = 0.91 (1.1GB)
     - spaCy transformer:        F1 = 0.89 (400MB)
     - Current spaCy sm:          F1 = 0.83 (12MB)
  -> User picks based on accuracy vs. size tradeoff
  -> MCP downloads and configures selected model

BENEFIT: Users with GPU can use BERT-NER for better accuracy.
         Users without GPU stick with spaCy small.
         MCP makes this a config choice, not a code change.
```

#### Integration Point 4: LLM Model Discovery

```
USE CASE: Ollama doesn't have the model a user wants.

CURRENT:
  User must manually: ollama pull mistral
  Then edit config to point to mistral.

WITH MCP:
  MCP Client -> HF MCP Server -> search("open source LLM chat")
  -> Returns: [llama3, mistral, phi3, gemma, qwen, ...]
  -> Shows: size, quality benchmarks, quantization options
  -> User picks -> MCP configures Ollama or HF Inference API

BENEFIT: Model selection becomes a UI choice, not a CLI command.
```

---

### 6.5 HuggingFace MCP in the Architecture

```
                    ┌──────────────────────────────┐
                    │      OIP Application          │
                    │                              │
                    │  ┌────────────────────────┐  │
                    │  │   MCP Client Layer      │  │
                    │  │                          │  │
                    │  │  ┌──────────────────┐   │  │
                    │  │  │ Model Registry   │   │  │
                    │  │  │ (config-driven)  │   │  │
                    │  │  │                   │   │  │
                    │  │  │ embedding: bge-   │   │  │
                    │  │  │   small-en-v1.5   │   │  │
                    │  │  │ ner: bert-base-   │   │  │
                    │  │  │   NER             │   │  │
                    │  │  │ llm: llama3:8b    │   │  │
                    │  │  │ classifier: dist- │   │  │
                    │  │  │   ilbert-base     │   │  │
                    │  │  └──────────────────┘   │  │
                    │  │            │              │  │
                    │  │            ▼              │  │
                    │  │  ┌──────────────────┐   │  │
                    │  │  │ MCP Router       │   │  │
                    │  │  │                   │   │  │
                    │  │  │ Local? -> Ollama  │   │  │
                    │  │  │         spaCy     │   │  │
                    │  │  │         SentenceTr│   │  │
                    │  │  │                   │   │  │
                    │  │  │ Cloud? -> HF MCP  │   │  │
                    │  │  │         Server    │   │  │
                    │  │  └──────────────────┘   │  │
                    │  └────────────────────────┘  │
                    │                │               │
                    └────────────────┼───────────────┘
                                     │
                          ┌──────────┴──────────┐
                          │                      │
                   ┌──────▼───────┐      ┌───────▼───────┐
                   │   LOCAL      │      │   HUGGINGFACE  │
                   │   MODELS     │      │   MCP SERVER   │
                   │              │      │               │
                   │ * Ollama     │      │ * Model search │
                   │ * spaCy      │      │ * Inference API│
                   │ * SentenceTr │      │ * Benchmarks   │
                   │ * scikit-learn│     │ * Downloads    │
                   │              │      │ * 500K+ models │
                   │ FAST         │      │ UNLIMITED      │
                   │ OFFLINE      │      │ REQUIRES NET   │
                   │ FREE         │      │ FREE TIER      │
                   └──────────────┘      └───────────────┘
```

---

### 6.6 HuggingFace MCP Configuration Design

```yaml
# config/settings.yaml -- MCP section (NEW)

mcp:
  enabled: true                          # Enable MCP integration
  provider: "huggingface"                # MCP server provider
  server_url: "https://huggingface.co"   # HuggingFace Hub URL
  api_token: "${HF_API_TOKEN}"           # Optional: HF API token
  inference_fallback: true               # Use HF Inference if local fails
  cache_models: true                     # Cache downloaded models locally
  cache_dir: "./models/"                 # Local model cache directory

  # Model selection strategy
  strategy: "auto"                       # auto | local-first | cloud-first | manual
  # auto:       Use local if available, fallback to HF Inference API
  # local-first: Always prefer local, fail if unavailable
  # cloud-first: Always prefer HF Inference API
  # manual:      Use exactly what's specified in models section

  models:
    embedding:
      primary: "BAAI/bge-small-en-v1.5"       # Better than MiniLM
      fallback: "all-MiniLM-L6-v2"            # Current default
      dimensions: 384
      provider: "auto"                         # auto | local | huggingface
      max_batch_size: 64

    ner:
      primary: "dslim/bert-base-NER"          # Better than spaCy
      fallback: "spacy:en_core_web_sm"         # Current default
      provider: "local"                        # NER should be local (speed)
      confidence_threshold: 0.7

    llm:
      primary: "llama3:8b"                    # Via Ollama
      fallback: "keyword_based"               # If all models fail
      provider: "ollama"                       # ollama | huggingface
      max_tokens: 2048
      temperature: 0.3

    classifier:
      primary: "distilbert-base-uncased"       # Signal classification
      fallback: "keyword"                      # Keyword-based fallback
      provider: "auto"
      labels: ["funding", "failure", "hiring", "product", "regulatory", "other"]

    summarization:
      primary: "facebook/bart-large-cnn"       # For report summarization
      fallback: "ollama:llama3:8b"              # Use LLM if BART unavailable
      provider: "huggingface"                   # Cloud inference for heavy tasks
      max_length: 150
```

---

### 6.7 HuggingFace MCP Data Flow

```
USER QUERY: "Tell me about Rivian"

WITHOUT MCP:
+----------+    +----------+    +----------+    +----------+
| API      |--->| Keyword  |--->| MySQL    |--->| Return   |
| /search  |    | search   |    | raw SQL  |    | results  |
+----------+    +----------+    +----------+    +----------+
                                        |
                                        v
                                 (If semantic search)
                               +----------+
                               | Local    |
                               | SentenceTr|
                               | (80MB)   |
                               +----------+

WITH MCP:
+----------+    +----------+    +----------+    +----------+
| API      |--->| MCP      |--->| Model    |--->| Return   |
| /search  |    | Router   |    | Registry |    | results  |
+----------+    +-----+----+    +----------+    +----------+
                      |
               +------+------+
               |             |
         +-----v-----+ +----v--------+
         | LOCAL     | | HF MCP      |
         | SentenceTr| | Inference   |
         | (cached)  | | API         |
         |           | |             |
         | FAST      | | UNLIMITED   |
         | OFFLINE   | | MODELS      |
         +-----------+ +-------------+

BENEFITS:
  1. User can pick any embedding model from 500K+ on HuggingFace
  2. Local-first with cloud fallback = always works
  3. Model swap = config change, not code change
  4. New models available immediately (no code update needed)
```

---

### 6.8 HuggingFace MCP for the AI Chat Feature

```
CURRENT AI CHAT FLOW:
  User types question -> Ollama llama3:8b -> response (5-10 sec on CPU)

WITH MCP:
  User types question
     |
     v
  MCP Router checks config:
     |
     +-- strategy=local-first -> Ollama llama3:8b (5-10 sec, free)
     |                         |
     |                         +-- (if Ollama down)
     |                             -> HF Inference API (1-2 sec, free tier)
     |
     +-- strategy=cloud-first -> HF Inference API (1-2 sec)
     |                         -> mistral-7b or llama3-70b (better quality)
     |
     +-- strategy=auto      -> Local first, cloud fallback

ADDED CAPABILITIES WITH MCP:

  1. Model Hot-Swap
     "Switch to mistral for this query" -> MCP loads mistral
     "Switch back to llama3" -> MCP loads llama3
     No restart. No manual pull.

  2. Query-Routed Models
     Simple factual -> HF Inference API (fast, cheap)
     Complex analysis -> Local Ollama llama3 (offline, private)
     Classification -> HF hosted BERT (specialized)

  3. Model Benchmarking
     "Which model is best for startup failure analysis?"
     MCP -> searches HF Hub -> returns benchmarks -> user picks

  4. Fine-Tuned Models (Future)
     "Upload my startup analysis model to HuggingFace"
     MCP -> uploads model -> available to all OIP users
     Community-built models for specific domains
```

---

### 6.9 HuggingFace MCP for Embedding Pipeline Enhancement

```
CURRENT EMBEDDING FLOW:

  Signal text -> all-MiniLM-L6-v2 -> 384-dim vector -> Qdrant
                 (fixed model)
                 (local only)
                 (80MB)

WITH MCP:

  Signal text -> MCP Router -> Best available model -> Vector -> Qdrant
                    |
                    +-- Option A: BAAI/bge-small-en-v1.5
                    |   Better quality, same size (384-dim)
                    |
                    +-- Option B: BAAI/bge-large-en-v1.5
                    |   Best quality, larger (1024-dim)
                    |   Requires Qdrant collection rebuild
                    |
                    +-- Option C: intfloat/e5-base-v2
                    |   Good for long documents
                    |
                    +-- Option D: thenlper/gte-base
                    |   Good for technical content
                    |
                    +-- Option E: HF Inference API
                        No local model needed
                        1,000 req/hour free

MIGRATION PATH (safe, no downtime):

  Phase 1: Add MCP client alongside current EmbeddingGenerator
           -> Both generate embeddings -> compare quality
           -> No production impact

  Phase 2: MCP client becomes primary, current becomes fallback
           -> New signals use better model
           -> Old signals still searchable (old vectors)

  Phase 3: Background re-embedding job
           -> Re-embed all old signals with new model
           -> Qdrant collection rebuilt
           -> Full quality upgrade

  Phase 4: Remove hardcoded model dependency
           -> All model selection via MCP config
           -> User-driven model choices
```

---

### 6.10 Implementation Plan for HuggingFace MCP

```
+----------------------------------------------------------------------+
|                                                                      |
|  PHASE 1: MCP Client + Router (Week 1)                              |
|  ------------------------------                                      |
|  Files to create:                                                    |
|    * mcp/__init__.py              <- MCP client package              |
|    * mcp/client.py                <- HuggingFace MCP client          |
|    * mcp/router.py                <- Local vs. cloud router          |
|    * mcp/model_registry.py        <- Model config + caching          |
|    * config/mcp_settings.yaml     <- MCP configuration              |
|    * tests/test_mcp_client.py     <- Unit tests                      |
|                                                                      |
|  DELIVERABLE: MCP client connects to HuggingFace Hub                |
|              Can search models, get info, run inference              |
|                                                                      |
|  PHASE 2: Integrate with EmbeddingGenerator (Week 2)                |
|  -----------------------------------------------                    |
|  Modify:                                                             |
|    * nlp/embedding_generator.py  <- Add MCP router                  |
|    * config/settings.yaml        <- Add models.embedding section     |
|    * stream/pipeline.py          <- Use MCP-aware enrichment         |
|                                                                      |
|  DELIVERABLE: Embeddings can use any HF model via config            |
|              Falls back to current all-MiniLM-L6-v2 if offline       |
|                                                                      |
|  PHASE 3: Integrate with AI Chat (Week 3)                           |
|  ---------------------------------                                   |
|  Modify:                                                             |
|    * agents/model_manager.py     <- Add MCP inference option         |
|    * api_server.py               <- Chat endpoint uses MCP router   |
|    * config/settings.yaml        <- Add models.llm section           |
|                                                                      |
|  DELIVERABLE: Chat can use local Ollama OR HF Inference API        |
|              Auto-fallback if Ollama is down                        |
|                                                                      |
|  PHASE 4: NER Model Selection (Week 4)                              |
|  ------------------------------                                      |
|  Modify:                                                             |
|    * agents/nlp_enrichment_agent.py <- Add HF NER models            |
|    * mcp/ner_selector.py         <- NER model benchmarking          |
|                                                                      |
|  DELIVERABLE: Users can choose spaCy (fast) or BERT-NER (accurate) |
|              via config                                             |
|                                                                      |
|  PHASE 5: UI for Model Selection (Month 2)                          |
|  ------------------------------------                                |
|  New:                                                                |
|    * GET /api/models/search       <- Search HF Hub for models       |
|    * POST /api/models/select      <- Set active model               |
|    * GET /api/models/benchmarks   <- Get model comparison           |
|    * Dashboard section: "Model Settings"                            |
|                                                                      |
|  DELIVERABLE: Users change models from the dashboard               |
|              No code editing required                               |
|                                                                      |
+----------------------------------------------------------------------+
```

---

### 6.11 HuggingFace MCP Impact on Each Architecture Layer

| Layer | Current | With MCP | Change |
|---|---|---|---|
| **Presentation** | Fixed models | Model selector UI, benchmarks dashboard | New UI section |
| **API** | Ollama-only chat | Multi-provider chat (Ollama + HF API) | `/api/models/*` endpoints |
| **Intelligence** | Hardcoded NER/spaCy | Configurable NER (spaCy or BERT-NER) | Better accuracy |
| **Stream** | Fixed embedding model | MCP-routed embeddings | Better vectors |
| **Storage** | Qdrant with fixed dims | Qdrant with configurable dims | Migration needed |
| **Collection** | No change | No change | None |
| **Config** | Static settings.yaml | Dynamic model registry | New config section |

---

### 6.12 Risks of HuggingFace MCP Integration

| Risk | Severity | Mitigation |
|---|---|---|
| **HF API rate limiting** | Medium | Local-first with cloud fallback. Cache aggressively. Free tier = 1K req/hr. |
| **Vendor dependency** | Medium | MCP is an open protocol. Can swap HF for any MCP-compatible server. Local always works. |
| **Model size mismatch** | Medium | Validate dimension compatibility before swap. Re-embed if dimensions change. |
| **Latency increase** | Low-Medium | Local-first strategy. Cloud only used when local unavailable or for heavy tasks. |
| **API token exposure** | Medium | Token in environment variable, not config. Same pattern as BLS_API_KEY. |
| **Offline breakage** | Critical | ALWAYS have local fallback. MCP is additive, never required. |

---

## Part 7: The One-Page Solution Design

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  ARCHITECTURE: 7 layers, Kappa architecture, dual-write pattern      │
│  Presentation → API → Intelligence → Stream → MessageBus →          │
│  Collection → Storage                                               │
│                                                                      │
│  UX: 5 user journeys, zero-click value, type-and-get,               │
│  2,903-line dashboard with charts, WebSocket, dark mode              │
│                                                                      │
│  DATA FLOW: Event → Collect (60s) → Normalize (2s) →                │
│  Stream (5min) → Score (3s) → Alert (5s) → User (15min total)      │
│                                                                      │
│  STORAGE: MySQL (76 tables) + Redis + Kafka + Qdrant +              │
│  Elasticsearch + ClickHouse + TimescaleDB = 7 engines               │
│                                                                      │
│  SCALABILITY: Tier 1 single machine ($100/mo) →                     │
│  Tier 2 small cluster ($300/mo) → Tier 3 K8s ($1K/mo)              │
│  Scale via Kafka partitions + Redis cache + read replicas            │
│                                                                      │
│  SECURITY: Self-hosted = no data leaves. Public data only.          │
│  Defense in depth: Network → API → App → Data → Access              │
│  No PII = simplified GDPR. Open source = auditable.                 │
│                                                                      │
│  WHAT'S BUILT: 19/22 components (86%)                                │
│  WHAT'S MISSING: Auth, Alert Consumer, Collector Scheduler,          │
│                  HuggingFace MCP Integration                         │
│                                                                      │
│  TOTAL: 55 agents, 26 collectors, 76 tables, 681 tests,             │
│  34 API endpoints, 11 Docker services, 185 Python files              │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

*Last updated: June 5, 2026*
