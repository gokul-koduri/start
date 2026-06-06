# 🎯 Opportunity Intelligence Platform — Architecture & Implementation Plan

## Context

**Why this change:** The existing Startup Research Report platform is a powerful AI-powered market intelligence system with 24+ agents, 41 MySQL tables, 5 data collectors, FastAPI + WebSocket, and Streamlit dashboards. However, it operates as a **batch-based, single-domain** system focused on failed startups and manufacturing revival. This plan evolves it into a **real-time, multi-signal Opportunity Intelligence Platform** — an open-source, self-hosted alternative to closed SaaS platforms like Crunchbase, PitchBook, and Tracxn.

**Market gap:** No mature open-source opportunity intelligence platform exists. The closest (Subsignal, 25★) handles only 1-2 signal types. No open-source project combines multi-signal ingestion, NLP enrichment, knowledge graph, composite scoring, and real-time dashboards. This is a rare "blue ocean" opportunity in 2026.

**Intended outcome:** A production-ready platform that continuously monitors 8+ signal sources (SEC filings, job postings, GitHub trends, funding events, patents, social media, website changes, regulatory filings), enriches them with NLP, scores opportunities with explainable composite scoring, maps relationships in a knowledge graph, and surfaces intelligence via real-time dashboards and APIs.

---

## Architecture Overview

The system evolves from **cron-based batch → event-driven Kappa architecture** (single stream processing pipeline). This is the industry-standard replacement for Lambda architecture.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        📊 DASHBOARD LAYER                                   │
│    Streamlit (internal tools)  │  Next.js + SSE (production dashboard)     │
├─────────────────────────────────────────────────────────────────────────────┤
│                        🔌 API & REAL-TIME LAYER                             │
│    FastAPI REST  │  GraphQL (Hasura)  │  WebSocket  │  SSE  │  gRPC          │
├─────────────────────────────────────────────────────────────────────────────┤
│                        ⚙️ ORCHESTRATION LAYER                                │
│    Dagster (asset-centric pipeline) — replaces cron + file locks            │
├─────────────────────────────────────────────────────────────────────────────┤
│                        🧠 INTELLIGENCE LAYER                                 │
│    NLP Pipeline (spaCy + SentenceTransformers)  │  Composite Scoring Engine │
│    Knowledge Graph (Apache Age / Neo4j)          │  Anomaly Detection (Z-score)│
│    Ollama LLM (local inference) ✅ existing      │  Feature Attribution       │
├─────────────────────────────────────────────────────────────────────────────┤
│                        ⚡ STREAM PROCESSING LAYER                            │
│    Bytewax (Python-native)  │  Event Correlation  │  Pattern Detection        │
│    Kafka Topics as central event bus                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                        📡 SIGNAL INGESTION LAYER                             │
│    SEC EDGAR │ Job Boards │ GitHub API │ Funding Events │ Patent (USPTO)    │
│    Social Media │ Website Monitors │ News RSS ✅ │ Regulatory Filings        │
├─────────────────────────────────────────────────────────────────────────────┤
│                        💾 STORAGE LAYER                                      │
│    MySQL 8.0 ✅ (operational)  │  ClickHouse (OLAP analytics)               │
│    TimescaleDB (time-series)    │  Qdrant (vector/semantic search)           │
│    Elasticsearch (full-text)    │  Apache Age (graph queries)                │
│    Redis (cache + pub/sub)      │                                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

```
                          SIGNAL SOURCES
                ┌──────────┬──────────┬──────────┬──────────┐
          ┌─────┴───┐ ┌────┴────┐ ┌───┴────┐ ┌──┴──────┐ ┌────────┐
          │SEC EDGAR│ │Job Boards│ │GitHub  │ │News RSS │ │Funding │
          │10-K/8-K │ │LinkedIn  │ │Trending│ │TechCrunch│ │Crunch- │
          └────┬────┘ └────┬────┘ └───┬────┘ └──┬──────┘ │base    │
               │            │          │         │         └───┬────┘
          ┌────┴───┐ ┌─────┴───┐ ┌────┴───┐          │             │
          │Patents │ │Social   │ │Website │          │             │
          │USPTO   │ │Reddit/HN│ │Monitor │          │             │
          └────┬───┘ └────┬────┘ └────┬───┘          │             │
               │          │          │               │             │
    ───────────┴──────────┴──────────┴───────────────┴─────────────
                     KAFKA EVENT BUS (Redpanda)
    ───────────┬──────────┬──────────┬───────────────┬─────────────
               │          │          │               │
         ┌─────┴──┐  ┌───┴────┐ ┌──┴───┐  ┌───────┴──────┐
         │raw.    │  │raw.    │ │raw.  │  │raw.           │
         │signals │  │news    │ │filing│  │funding        │
         │(generic│  │(typed) │ │(typed│  │(typed)        │
         └─────┬──┘  └───┬────┘ └──┬───┘  └───────┬──────┘
               │          │          │               │
    ───────────┴──────────┴──────────┴───────────────┴─────────────
                BYTewax STREAM PROCESSING
               │                                  │
      ┌────────┴─────────┐          ┌─────────────┴──────┐
      │  Enrichment Pipe  │          │  Pattern Detection  │
      │  ─ spaCy NER      │          │  ─ Funding→Hiring   │
      │  ─ Deduplication  │          │  ─ Competitor entry │
      │  ─ Classification │          │  ─ Innovation sig   │
      │  ─ Embedding gen  │          │  ─ Distress signal  │
      └────────┬─────────┘          └─────────────┬──────┘
               │                                  │
    ───────────┴──────────────────────────────────┴─────────────
                 KAFKA (processed topics)
    ───────────┬──────────┬──────────┬───────────────┬─────────────
               │          │          │               │
         ┌─────┴──┐  ┌───┴────┐ ┌──┴───┐  ┌───────┴──────┐
         │enriched│  │scores. │ │graph.│  │alerts.       │
         │signals │  │updates │ │events│  │triggered     │
         └─────┬──┘  └───┬────┘ └──┬───┘  └───────┬──────┘
               │          │         │               │
    ───────────┴──────────┴─────────┴───────────────┴─────────────
               STORAGE LAYER (Multi-Engine)
         ┌─────┴──┐  ┌───┴────┐ ┌──┴───┐  ┌──────┴──────┐
         │ClickHse│  │MySQL   │ │Qdrant│  │Elasticsearch│
         │(OLAP)  │  │(OPS) ✅│ │(Vect)│  │(Search)     │
         └────────┘  └────────┘ └──────┘  └─────────────┘
         ┌─────┴──┐  ┌───┴────┐
         │Timescale│ │Apache  │
         │(TS)    │ │Age(GR) │
         └────────┘ └────────┘
               │
    ───────────┴──────────────────────────────────────────────────
               API + REAL-TIME
         ┌─────┴────┐  ┌────────┐  ┌───────┐
         │FastAPI   │  │GraphQL │  │WS/SSE │
         │REST ✅   │  │Hasura  │  │Live   │
         └─────┬────┘  └────────┘  └───────┘
               │
    ───────────┴──────────────────────────────────────────────────
               DASHBOARDS
         ┌─────┴────────────────┐
         │Streamlit ✅ (internal)│  Next.js (production)
         └──────────────────────┘
```

---

## Docker Compose Service Map

```
┌─────────────────────────────────────────────────────────────────────┐
│  docker-compose.yml (Target — 15+ services)                         │
│                                                                     │
│  EXISTING (4 services):                                             │
│    mysql        MySQL 8.0 (operational DB)                          │
│    ollama       Local LLM inference                                 │
│    api          FastAPI server                                      │
│    streamlit    Internal dashboard                                  │
│                                                                     │
│  PHASE 1 ADDITIONS (2):                                             │
│    kafka        Redpanda (Kafka-compatible, simpler to deploy)      │
│    redis        Cache + pub/sub for WebSocket/SSE                   │
│                                                                     │
│  PHASE 2 ADDITIONS (2):                                             │
│    qdrant       Vector similarity search                             │
│    elasticsearch Full-text search                                    │
│                                                                     │
│  PHASE 3 ADDITIONS (4):                                             │
│    clickhouse   OLAP analytics engine                                │
│    timescaledb  Time-series database (Postgres extension)           │
│    dagster      Pipeline orchestration (replaces cron)               │
│    nlp-worker   spaCy + SentenceTransformers microservice           │
│                                                                     │
│  PHASE 4 ADDITIONS (3):                                             │
│    hasura       GraphQL engine over MySQL                           │
│    prometheus   Metrics collection                                  │
│    grafana      Monitoring dashboards                                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## New Signal Sources

Each collector inherits from existing `BaseCollector` (`collectors/base.py`) and registers in `agents/collection.py`.

| # | Signal Source | Library | Latency | Phase | Why It Matters |
|---|---|---|---|---|---|
| 1 | **SEC EDGAR Filings** | `sec-edgar-downloader` | Hours | P1 | 10-K/8-K filings reveal financial health, M&A, strategy |
| 2 | **Job Postings** | LinkedIn RSS, Indeed API | Hours-Days | P1 | Hiring spikes = company growth signals |
| 3 | **GitHub Trending** | PyGithub API | Real-time | P1 | Tech adoption signals, open-source momentum |
| 4 | **Funding Events** | Crunchbase/AngelList | Hours | P1 | Direct investment signal |
| 5 | **Patent Filings (USPTO)** | `uspatent` / OPS API | Days | P2 | Innovation trajectory, IP strategy |
| 6 | **Social Media** | PRAW (Reddit), HN API | Minutes | P2 | Sentiment, buzz, community signals |
| 7 | **Website Changes** | ChangeTower/Diffbot API | Hours | P3 | Product launches, pricing changes, pivot signals |
| 8 | **Regulatory Filings** | Federal Register API | Days | P3 | Compliance risk, market regulation shifts |

### New Collector Files

```
collectors/
  base.py                     ✅ existing
  google_news_rss.py          ✅ existing
  techcrunch_rss.py           ✅ existing
  failory_scraper.py          ✅ existing
  bls_survival_rates.py       ✅ existing
  reshoring_pdf.py            ✅ existing
  sec_edgar_collector.py      🆕 Phase 1
  job_postings_collector.py   🆕 Phase 1
  github_trends_collector.py  🆕 Phase 1
  funding_events_collector.py 🆕 Phase 1
  patent_collector.py         🆕 Phase 2
  social_media_collector.py   🆕 Phase 2
  website_monitor_collector.py🆕 Phase 3
  regulatory_collector.py     🆕 Phase 3
```

---

## Opportunity Scoring Engine

Replaces the simple additive scoring in `agents/opportunity_pipeline_agent.py` with a proper composite scoring system.

### Composite Score Formula

```
Composite_Score(entity, t) =
    Σ( w_i × signal_score_i(entity) × decay(t - t_i) ) / Σ( w_i × decay(t - t_i) )
    × anomaly_multiplier(entity)
    × confidence_factor(entity)
```

Where:
- `w_i` = configurable weight per signal type
- `signal_score_i` = raw score (0-100) from signal source
- `decay(t - t_i)` = exponential decay: `e^(-λ × hours_since_event)`
- `anomaly_multiplier` = boost when Z-score anomaly detected (>1.0)
- `confidence_factor` = decreasing with missing signals

### Signal Weights (Configurable)

```python
SIGNAL_WEIGHTS = {
    "funding_round":     {"weight": 25.0, "decay_lambda": 0.003},  # ~1yr half-life
    "sec_filing":        {"weight": 20.0, "decay_lambda": 0.005},  # ~6mo half-life
    "job_posting_spike": {"weight": 15.0, "decay_lambda": 0.01},   # ~2mo half-life
    "patent_filed":      {"weight": 12.0, "decay_lambda": 0.002},  # ~1yr half-life
    "github_trend":      {"weight": 10.0, "decay_lambda": 0.02},   # ~1mo half-life
    "news_mention":      {"weight": 10.0, "decay_lambda": 0.01},   # ~2mo half-life
    "social_buzz":       {"weight": 5.0,  "decay_lambda": 0.03},   # ~2wk half-life
    "website_change":    {"weight": 3.0,  "decay_lambda": 0.05},   # ~1wk half-life
}
```

### Example Score Output (Explainable)

```json
{
  "entity_name": "Neuromorphic Labs",
  "composite_score": 78.5,
  "attribution": [
    {"signal": "funding_round", "contribution": 18.2, "weight": 25, "freshness": 0.85},
    {"signal": "sec_filing",    "contribution": 14.1, "weight": 20, "freshness": 0.94},
    {"signal": "job_posting",   "contribution": 8.9,  "weight": 15, "freshness": 0.85},
    {"signal": "github_trend",  "contribution": 6.2,  "weight": 10, "freshness": 0.95},
    {"signal": "news_mention",  "contribution": 5.8,  "weight": 10, "freshness": 0.97}
  ],
  "anomaly_detected": true,
  "anomaly_z_score": 3.2,
  "trend_direction": "rising",
  "confidence": 0.82
}
```

### Scoring Files

```
scoring/
  __init__.py
  composite_scorer.py      # Main composite scoring engine
  time_decay.py            # Exponential time-decay functions
  anomaly_detector.py      # Z-score spike detection
  signal_weights.py        # Configurable signal weight definitions
  feature_attribution.py   # Per-signal attribution for explainability
```

---

## Knowledge Graph Design

### Expanded Entity Types (7 existing → 12)

| Entity | Phase | Description |
|---|---|---|
| `startup` | ✅ existing | Companies (active or failed) |
| `industry` | ✅ existing | Industry sectors |
| `investor` | ✅ existing | VC firms, angels, PE |
| `region` | ✅ existing | Geographic areas |
| `sector` | ✅ existing | Business sectors |
| `failure_reason` | ✅ existing | Failure categories |
| `technology` | ✅ existing | Technologies |
| **`person`** | 🆕 P2 | Founders, CEOs, board members |
| **`product`** | 🆕 P2 | Products/services |
| **`market`** | 🆕 P2 | Target markets/segments |
| **`patent`** | 🆕 P2 | Patent documents |
| **`regulation`** | 🆕 P3 | Regulatory frameworks |

### New Relationship Types (7 existing → 20)

| Relationship | Source → Target | Description |
|---|---|---|
| `founded_by` | startup → person | Founder relationship |
| `funded_by` | startup → investor | Funding round |
| `acquired_by` | startup → startup | Acquisition |
| `competes_with` | startup → startup | Competition |
| `uses_tech` | startup → technology | Tech stack |
| `targets_market` | startup → market | Target market |
| `patent_held_by` | patent → startup | Patent ownership |
| `patent_cites` | patent → patent | Citation link |
| `person_is_investor` | person → investor | Person-fund link |
| `product_of` | product → startup | Product owner |
| `regulated_by` | industry → regulation | Regulatory link |
| `technology_used_by` | technology → startup | Reverse tech link |

### Entity Resolution Strategy

**Phase 1 (Quick Win):** Extend existing `_normalize_name()` in `agents/knowledge_graph_agent.py:39` with:
- Abbreviation expansion ("OpenAI" → "open artificial intelligence")
- Common alias mapping ("Meta" = "Facebook")
- Suffix stripping ("Acme Inc." = "acme")

**Phase 2 (Production):** Full entity resolution:
1. **Blocking**: LSH on name trigrams to generate candidate pairs
2. **Matching**: Jaro-Winkler similarity + context overlap
3. **Merging**: Entity clusters with canonical name selection

---

## Complex Event Patterns (Stream Processing)

The Bytewax pipeline detects multi-signal patterns in real-time:

| Pattern Name | Signals | Window | Score Boost |
|---|---|---|---|
| **Scaling Signal** | funding_round + hiring_spike (5+ jobs) | 30 days | +15 |
| **Innovation Signal** | patent + github_trend + 8-K filing | 90 days | +20 |
| **Distress Signal** | negative news + declining job postings | 14 days | -10 |
| **Market Entry** | new competitor funding + hiring | 60 days | +10 |
| **Pivot Signal** | tech_stack change + job role shift + website change | 45 days | +12 |

---

## Phased Implementation

### Phase 1: Foundation (4-6 weeks)
**Goal:** Real-time ingestion via Kafka, 4 new signal collectors, composite scoring engine

**New Files (20):**
| File | Purpose |
|---|---|
| `collectors/sec_edgar_collector.py` | SEC EDGAR filings |
| `collectors/job_postings_collector.py` | Job board aggregation |
| `collectors/github_trends_collector.py` | GitHub trending repos |
| `collectors/funding_events_collector.py` | Crunchbase/AngelList |
| `scoring/__init__.py` | Scoring package |
| `scoring/composite_scorer.py` | Composite scoring engine |
| `scoring/time_decay.py` | Exponential decay |
| `scoring/signal_weights.py` | Signal weight config |
| `scoring/anomaly_detector.py` | Z-score detection |
| `scoring/feature_attribution.py` | Explainability |
| `agents/opportunity_scorer.py` | Scoring agent |
| `ingestion/__init__.py` | Ingestion package |
| `ingestion/kafka_producer.py` | Kafka producer wrapper |
| `ingestion/signal_normalizer.py` | Signal normalization |
| `db/graph_queries.py` | Graph traversal helpers |
| `kafka_topics.py` | Topic definitions |
| `tests/test_composite_scorer.py` | Scoring tests |
| `tests/test_time_decay.py` | Decay tests |
| `tests/test_anomaly_detector.py` | Anomaly tests |
| `tests/test_sec_collector.py` | SEC collector tests |

**Modified Files (9):**
- `db/schema.py` — Add 7 new tables (`raw_signals`, `opportunity_scores`, `signal_events`, `sec_filings`, `job_postings`, `github_trends`, `funding_events`), bump `_SCHEMA_VERSION` to 12
- `db/dedup.py` — Add dedup functions for each new signal type
- `agents/collection.py` — Register 4 new collectors
- `agents/orchestrator.py` — Register `opportunity_scorer` in `AGENT_REGISTRY` and `_get_agent_class()`
- `config/settings.yaml` — Add SEC, jobs, GitHub, funding, scoring configs
- `api_server.py` — Add `GET /api/opportunities`, `GET /api/signals`
- `requirements.txt` — Add: `sec-edgar-downloader`, `PyGithub`, `kafka-python-ng`, `redis`
- `docker-compose.yml` — Add `kafka` (Redpanda) + `redis` services + volumes
- `run_agent.py` — Add `opportunity_scorer` to config merge

**New Dependencies:**
```
sec-edgar-downloader>=5.0.0
PyGithub>=2.1.0
kafka-python-ng>=2.2.0
redis>=5.0.0
```

**Verification:**
- [ ] Each collector: unit tests with mocked HTTP (pytest-httpx)
- [ ] Scoring: verify composite formula, time-decay, anomaly detection (z > 2.0)
- [ ] Integration: `python run_agent.py --pipeline analysis` → `opportunity_scores` populated
- [ ] Kafka smoke: produce → consume round-trip on `raw.signals`
- [ ] Docker: `docker compose up -d` starts cleanly with Kafka + Redis

---

### Phase 2: Intelligence (6-8 weeks)
**Goal:** NLP pipeline with spaCy, expanded knowledge graph (12 entity types), semantic search via Qdrant

**New Files (20):**
| File | Purpose |
|---|---|
| `nlp/__init__.py` | NLP package |
| `nlp/ner_pipeline.py` | spaCy NER with custom entities |
| `nlp/entity_extractor.py` | Unified extraction (spaCy + Ollama fallback) |
| `nlp/text_classifier.py` | Signal classification |
| `nlp/embedding_generator.py` | SentenceTransformer embeddings |
| `nlp/summarizer.py` | Ollama text summarization |
| `collectors/patent_collector.py` | USPTO patents |
| `collectors/social_media_collector.py` | Reddit/HN |
| `agents/entity_resolver.py` | Entity resolution agent |
| `agents/semantic_search_agent.py` | Vector search agent |
| `agents/nlp_enrichment_agent.py` | NLP pipeline agent |
| `db/vector_store.py` | Qdrant client wrapper |
| `db/search_index.py` | Elasticsearch client wrapper |
| `tests/test_ner_pipeline.py` | NER tests |
| `tests/test_entity_resolver.py` | Resolution tests |
| `tests/test_semantic_search.py` | Vector search tests |

**Modified Files (9):**
- `db/schema.py` — Add `patent_filings`, `social_posts`, `vector_embeddings`, `kg_entity_aliases` tables. Expand KG types. Bump to v13
- `agents/knowledge_graph_agent.py` — Replace Ollama NER with spaCy. Add 5 new entity types, 13 new relationship types. Add `_extract_relationships_from_funding()`, `_extract_relationships_from_jobs()`
- `agents/orchestrator.py` — Register `entity_resolver`, `semantic_search_agent`, `nlp_enrichment_agent`
- `agents/collection.py` — Register patent + social collectors
- `config/settings.yaml` — Add `nlp:`, `patents:`, `social_media:`, `qdrant:` configs
- `api_server.py` — Add `GET /api/search?mode=semantic`, `GET /api/entities/{name}/connections`
- `docker-compose.yml` — Add `qdrant`, `elasticsearch`
- `requirements.txt` — Add: `spacy>=3.7.0`, `sentence-transformers>=2.5.0`, `qdrant-client>=1.9.0`, `elasticsearch>=8.12.0`, `praw>=7.7.0`

**Verification:**
- [ ] NER benchmark: 100 labeled sentences, precision/recall vs. current Ollama approach
- [ ] Entity resolution: synthetic duplicates ("OpenAI", "Open AI", "OpenAI Inc.") → correct clustering
- [ ] Semantic search: 50 known opportunities, natural language queries, top-5 recall > 80%
- [ ] End-to-end: SEC filing → raw_signal → NLP enrichment → KG extraction → scoring

---

### Phase 3: Scale (6-8 weeks)
**Goal:** Bytewax stream processing, ClickHouse OLAP, Dagster orchestration, Next.js production dashboard, SSE real-time

**New Files (30):**
| File | Purpose |
|---|---|
| `stream/__init__.py` | Stream processing package |
| `stream/bytewax_pipeline.py` | Main dataflow definition |
| `stream/signal_enrichment.py` | NLP enrichment operator |
| `stream/pattern_detector.py` | Complex event patterns |
| `stream/score_calculator.py` | Real-time scoring |
| `stream/sink_dispatcher.py` | Multi-sink writer |
| `collectors/website_monitor_collector.py` | Website change detection |
| `collectors/regulatory_collector.py` | Regulatory filings |
| `dagster/__init__.py` | Orchestration package |
| `dagster/repository.py` | Dagster asset definitions |
| `dagster/ops/collect_ops.py` | Collector ops |
| `dagster/ops/score_ops.py` | Scoring ops |
| `dagster/ops/kg_ops.py` | KG ops |
| `dagster/schedules.py` | Schedules (replace cron) |
| `db/clickhouse.py` | ClickHouse client |
| `db/timescaledb.py` | TimescaleDB client |
| `frontend/nextjs/` | Next.js production dashboard |
| `frontend/nextjs/package.json` | Next.js deps |
| `frontend/nextjs/src/app/page.tsx` | Main dashboard |
| `frontend/nextjs/src/components/OpportunityTable.tsx` | Opportunity table |
| `frontend/nextjs/src/components/SignalGraph.tsx` | G6 network graph |
| `frontend/nextjs/src/components/AnomalyTimeline.tsx` | Anomaly viz |
| `frontend/nextjs/src/components/ScoreTrends.tsx` | Time-series charts |
| `frontend/nextjs/src/hooks/useSSE.ts` | SSE hook |
| `tests/test_bytewax_pipeline.py` | Stream processing tests |
| `tests/test_pattern_detector.py` | Pattern tests |
| `tests/test_dagster_repo.py` | Dagster tests |

**Modified Files (7):**
- `db/schema.py` — Add `regulatory_filings`, `website_changes`, `anomaly_alerts`. Bump to v14
- `agents/collection.py` — Register website + regulatory collectors
- `agents/orchestrator.py` — Register new agents
- `api_server.py` — Add SSE `GET /api/events/stream`, analytics endpoints
- `docker-compose.yml` — Add `clickhouse`, `timescaledb`, `dagster`, `nlp-worker`
- `Makefile` — Add targets: `make dagster`, `make stream`, `make frontend`
- `Dockerfile` — Split into multi-stage builds

**Verification:**
- [ ] Bytewax: inject signal sequences, verify pattern detection fires correctly
- [ ] ClickHouse: 10K synthetic signals, OLAP queries < 100ms
- [ ] SSE: test client receives events within 5s of signal ingestion
- [ ] Frontend: `npm run build` succeeds, dashboard renders with mock data
- [ ] Dagster: all assets registered, schedules trigger correctly

---

### Phase 4: Platform (8-10 weeks)
**Goal:** Multi-tenancy, API v2, webhooks, collaboration, monitoring, production hardening

**New Files (25):**
| File | Purpose |
|---|---|
| `auth/__init__.py` | Authentication package |
| `auth/jwt_handler.py` | JWT tokens |
| `auth/tenant_manager.py` | Multi-tenant isolation |
| `auth/rbac.py` | Role-based access |
| `api/v2/__init__.py` | API v2 |
| `api/v2/opportunities.py` | Opportunity CRUD |
| `api/v2/signals.py` | Signal management |
| `api/v2/webhooks.py` | Webhook management |
| `api/v2/export.py` | CSV/JSON/PDF export |
| `api/graphql_schema.py` | Custom GraphQL resolvers |
| `webhooks/dispatcher.py` | Outgoing webhooks |
| `webhooks/templates.py` | Payload templates |
| `collaboration/annotations.py` | User annotations |
| `collaboration/watchlists.py` | Entity watchlists |
| `collaboration/notes.py` | Shared notes |
| `monitoring/metrics.py` | Prometheus metrics |
| `monitoring/health.py` | Deep health checks |
| `monitoring/usage_tracking.py` | Per-tenant usage |
| `migrations/001_initial.sql` | Phase 1 tables |
| `migrations/002_intelligence.sql` | Phase 2 tables |
| `migrations/003_scale.sql` | Phase 3 tables |
| `migrations/004_platform.sql` | Phase 4 tables |
| `migrations/005_multi_tenant.sql` | Tenant isolation |
| `tests/test_auth.py` | Auth tests |
| `tests/test_api_v2.py` | API v2 tests |

**Modified Files (7):**
- `db/schema.py` — Add `tenants`, `tenant_members`, `annotations`, `watchlists`, `shared_notes`, `webhook_subscriptions`, `api_usage_logs`. Bump to v15
- `db/connection.py` — Add `get_tenant_connection(tenant_id)` with row-level security
- `api_server.py` — Add auth middleware, API v2 router, rate limiting, `/metrics`
- `config/settings.yaml` — Add `auth:`, `rbac:`, `multi_tenant:`, `webhooks:`, `monitoring:`
- `docker-compose.yml` — Add `hasura`, `prometheus`, `grafana`
- `requirements.txt` — Add: `PyJWT>=2.8.0`, `prometheus-client>=0.20.0`, `alembic>=1.13.0`

**Verification:**
- [ ] Auth: JWT issuance, validation, role-based access, tenant isolation
- [ ] API v2: contract tests with pytest-httpx, pagination, filtering
- [ ] Webhooks: test server, verify payload arrives with correct signature
- [ ] Load test: 100 concurrent users, p95 < 500ms reads, < 2s scoring
- [ ] Docker full stack: all 15+ services, Grafana dashboards showing metrics

---

## Effort Summary

| Phase | Duration | New Files | Modified Files | New Deps | Key Deliverable |
|---|---|---|---|---|---|
| **Phase 1** | 4-6 weeks | ~20 | ~9 | 4 | Real-time ingestion + scoring + 4 collectors |
| **Phase 2** | 6-8 weeks | ~20 | ~9 | 5 | NLP pipeline + KG expansion + semantic search |
| **Phase 3** | 6-8 weeks | ~30 | ~7 | 5+ | Stream processing + OLAP + production dashboard |
| **Phase 4** | 8-10 weeks | ~25 | ~7 | 4 | Multi-tenant + API v2 + monitoring |
| **Total** | **24-32 weeks** | **~95** | **~32** | **~18** | **Full platform** |

---

## Key Open-Source Tools Referenced

### Data Collection
| Repo | Stars | Use |
|---|---|---|
| `newspaper3k` | 16k★ | News article extraction |
| `trafilatura` | 5.5k★ | Web content extraction |
| `sherlock` | 52k★ | Social media account enumeration |
| `FreshRSS` | 11k★ | Self-hosted RSS aggregation |

### NLP & ML
| Repo | Stars | Use |
|---|---|---|
| `spaCy` | 30k★ | NER, text classification |
| `transformers` | 135k★ | Sentence embeddings, sentiment |
| `sentence-transformers` | 15k★ | Semantic embeddings for Qdrant |

### Real-Time Infrastructure
| Repo | Stars | Use |
|---|---|---|
| `Apache Kafka` | 28k★ | Event bus |
| `Bytewax` | 2.5k★ | Python-native stream processing |
| `Debezium` | 11k★ | Change data capture |

### Intelligence & OSINT
| Repo | Stars | Use |
|---|---|---|
| `SpiderFoot` | 5k★ | Automated OSINT (200+ sources) |
| `worldmonitor` | New | Real-time global intelligence dashboard |
| `subsignal` | 25★ | Deal flow monitoring (reference architecture) |

### Visualization
| Repo | Stars | Use |
|---|---|---|
| `G6` | 12k★ | Network graph visualization |
| `kepler.gl` | 10k★ | Geographic opportunity mapping |
| `Apache Superset` | 62k★ | Open-source Tableau alternative |

---

## Verification Strategy (Cross-Phase)

### Testing Pyramid
```
              /\
             /  \      E2E Tests (5%)
            /────\     - Full pipeline runs
           /  E2E \    - Docker compose smoke tests
          /────────\
         /Integr.  \   Integration Tests (20%)
        /  Tests    \  - DB + Kafka + API tests
       /────────────\
      /  Component   \  Component Tests (25%)
     /    Tests       \ - Collector tests with mocked HTTP
    /─────────────────\  - API endpoint tests
   /   Unit Tests (50%)
  /  - Scoring functions
 /   - Time decay math
/    - NER extraction
/     - Entity resolution
/      - Pattern detection
/──────────────────────
```

### CI/CD Pipeline (Phase 3+)
```
GitHub Actions:
  1. lint (ruff) + type-check (mypy)
  2. Unit tests (pytest)
  3. Integration tests (docker compose test-db)
  4. Build Docker images
  5. Push to container registry
  6. Deploy to staging → E2E smoke tests
  7. Manual approval → production deploy
```

---

## Critical Existing Files to Extend

| File | Role | What Changes |
|---|---|---|
| `db/schema.py` | 41 tables, `_SCHEMA_VERSION=11` | Add ~15 new tables across phases, bump to v15 |
| `agents/orchestrator.py` | Agent registry + pipeline | Register 8+ new agents in `AGENT_REGISTRY` + `_get_agent_class()` |
| `collectors/base.py` | Abstract `BaseCollector` | No changes — all new collectors inherit as-is |
| `agents/knowledge_graph_agent.py` | NER + KG (7 entity types) | Expand to 12 types, 20 relationships, replace Ollama NER with spaCy |
| `api_server.py` | FastAPI + 17 endpoints + WS | Add ~15 new endpoints across phases + SSE + auth middleware |
| `docker-compose.yml` | 4 services | Expand to 15+ services |
| `requirements.txt` | 15 deps | Expand to ~33 deps |
