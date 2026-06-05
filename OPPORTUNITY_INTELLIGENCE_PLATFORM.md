# Opportunity Intelligence Platform — Full Architecture Blueprint

> **Open-source, real-time, multi-agent alternative to Crunchbase / PitchBook / Tracxn**

---

## Table of Contents

1. [Current State Audit](#1-current-state-audit)
2. [Target Vision](#2-target-vision)
3. [System Architecture](#3-system-architecture)
4. [Data Sources & Real-Time APIs](#4-data-sources--real-time-apis)
5. [Tech Stack](#5-tech-stack)
6. [Agent Taxonomy (50+ Agents)](#6-agent-taxonomy)
7. [Data Flow Diagram](#7-data-flow-diagram)
8. [Storage Topology](#8-storage-topology)
9. [Agent Interaction Map](#9-agent-interaction-map)
10. [Docker Compose Service Map](#10-docker-compose-service-map)
11. [Phased Rollout](#11-phased-rollout)
12. [What Is the Outcome](#12-what-is-the-outcome)

---

## 1. Current State Audit

### What Exists Today

| Component | Count | Details |
|---|---|---|
| **Agents** | 35 | NER, sentiment, ML predictor/trainer, knowledge graph, risk scorer, opportunity scorer, entity resolver, report generator, alert dispatcher, dashboard, orchestrator, LLM portfolio/pricing/benchmark/cost optimizer, whale investor, geographic strategy, survival analysis, failure patterns, revival opportunity, global market viability, correlation, news intelligence, NLP enrichment, semantic search |
| **Collectors** | 12 | SEC EDGAR, GitHub trends, job postings, funding events, patent filings, social media (Reddit + HN), Crunchbase, Failory scraper, BLS survival rates, TechCrunch RSS, Google News RSS, reshoring PDF |
| **DB Tables** | 52 | failed_startups, news_articles, raw_signals, sec_filings, job_postings, github_trends, funding_events, patent_filings, social_posts, vector_embeddings, kg_entities, kg_relationships, kg_entity_aliases, ml_models, opportunity_scores, signal_events, + 37 more |
| **NLP Modules** | 6 | ner_pipeline, entity_extractor, embedding_generator, text_classifier, summarizer, sentiment_agent |
| **Search** | 2 | VectorStore (Qdrant), SearchIndex (Elasticsearch) |
| **Tests** | 192 | All passing across 14 test files |
| **API Endpoints** | 20+ | FastAPI REST + WebSocket live dashboard |
| **Dashboard** | 2 | Streamlit (internal), HTML/JS (live) |

### Architecture Gaps

```
CURRENT (Batch)                    TARGET (Real-Time)
─────────────────                  ─────────────────
cron → collect → MySQL → report    stream → ingest → Kafka → enrich → score → alert → dashboard
     ↑                                      ↑
  single-pass                         continuous, event-driven
  no streaming                        Bytewax stream processing
  MySQL only                         7 storage engines
  12 collectors                      20+ collectors
  35 agents                          50+ agents
```

---

## 2. Target Vision

### One-Sentence Pitch

A self-hosted, open-source platform that continuously monitors 20+ data sources across GitHub, Reddit, Hacker News, SEC filings, patents, job boards, and news — enriches signals with NLP, scores opportunities with explainable ML, maps relationships in a knowledge graph — and surfaces real-time intelligence via dashboards, APIs, and webhooks.

### What Makes This Unique

- **No open-source competitor exists** — Crunchbase ($$$), PitchBook ($$$), Tracxn ($$$) are all closed SaaS
- **Multi-agent architecture** — 50+ specialized agents vs. monolithic scrapers
- **Real-time Kappa architecture** — single stream processing pipeline (not batch Lambda)
- **Fully self-hosted** — all data stays on your infrastructure
- **Explainable scoring** — every opportunity score has feature attribution

---

## 3. System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        📊 DASHBOARD LAYER                                 │
│  Streamlit (internal tools)  │  Next.js + SSE (production)                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                        🔌 API & REAL-TIME LAYER                             │
│  FastAPI REST  │  GraphQL (Hasura)  │  WebSocket  │  SSE  │  Webhooks       │
├─────────────────────────────────────────────────────────────────────────────┤
│                        ⚙️ ORCHESTRATION LAYER                                │
│  Dagster (asset-centric pipeline) — replaces cron + file locks              │
├─────────────────────────────────────────────────────────────────────────────┤
│                        🧠 INTELLIGENCE LAYER                                │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐      │
│  │ NLP Pipeline  │ │ Composite     │ │ Knowledge    │ │ Anomaly &    │      │
│  │ spaCy NER     │ │ Scoring Engine│ │ Graph (12    │ │ Pattern      │      │
│  │ Embeddings    │ │ ML + Heuristic│ │ entity types,│ │ Detection    │      │
│  │ Classification│ │ Feature Attr │ │ 20 relations)│ │ Z-score      │      │
│  │ Summarization │ │ Explainable  │ │ Entity Res.  │ │ Correlation  │      │
│  │ Sentiment     │ │ Time Decay   │ │ Alias Mgmt   │ │ Survival     │      │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐      │
│  │ Ollama LLM   │ │ LLM Portfolio │ │ Whale        │ │ Global Market│      │
│  │ Local Infer. │ │ Pricing/Bench │ │ Investor     │ │ Viability    │      │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘      │
├─────────────────────────────────────────────────────────────────────────────┤
│                        ⚡ STREAM PROCESSING LAYER                           │
│  Bytewax (Python-native, Rust engine)                                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐      │
│  │ Signal        │ │ Event         │ │ Temporal      │ │ Cross-Source │      │
│  │ Normalization │ │ Correlation   │ │ Windowing     │ │ Pattern Det. │      │
│  │ Deduplication │ │ Funding→Hire  │ │ Session Agg.  │ │ Competitor   │      │
│  │ Routing       │ │ GitHub→News   │ │ Trend Calc.   │ │ Distress Sig.│      │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘      │
│  Kafka Topics as central event bus                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                        📡 SIGNAL INGESTION LAYER                            │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐       │
│  │ GitHub │ │ Reddit │ │Hacker  │ │  SEC   │ │ Patents│ │  Jobs  │       │
│  │ API    │ │ PRAW   │ │ News   │ │ EDGAR  │ │ USPTO  │ │ Boards │       │
│  │ Trending│ │ 15+ sub│ │ Algolia│ │Form C  │ │ Search │ │LinkedIn│       │
│  │ GraphQL│ │realtime│ │ stream │ │ 10-K   │ │ Citations│ │Indeed │       │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘ └────────┘       │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐       │
│  │ News   │ │Funding │ │ Crunch-│ │ Open-  │ │Website │ │ arXiv  │       │
│  │ RSS    │ │ Events│ │ base   │ │ Corps  │ │ Mon.   │ │ Papers │       │
│  │TC+GN   │ │AngelLst│ │ API   │ │ 220M+  │ │Changes │ │ ML/AI  │       │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘ └────────┘       │
├─────────────────────────────────────────────────────────────────────────────┤
│                        💾 STORAGE LAYER                                      │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐      │
│  │ MySQL  │ │ClickHse│ │Timescale│ │ Qdrant │ │ Elastic │ │ Redis  │      │
│  │ (OPS)  │ │ (OLAP) │ │ (TS)   │ │ (Vector)│ │ (Search)│ │(Cache) │      │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘ └────────┘      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Data Sources & Real-Time APIs

### Tier 1: Core Sources (Implement First)

| Source | API | Data Collected | Latency | Library |
|---|---|---|---|---|
| **GitHub** | REST + GraphQL | Trending repos, star velocity, commit frequency, fork graphs, language distribution, topic tags, release activity | Near real-time | `PyGithub`, `github-graphql` |
| **Reddit** | PRAW (Python Reddit API) | Posts/comments from r/startups, r/technology, r/SaaS, r/machinelearning, r/programming, r/Entrepreneur | Real-time (streaming) | `praw>=7.7.0` |
| **Hacker News** | Algolia Search API | Stories, comments, points, upvote velocity, "Show HN" launches, Ask HN discussions | Near real-time | `requests` (HTTP) |
| **SEC EDGAR** | Full-text API + EdgarTools | Form C (crowdfunding), 10-K, 8-K, S-1, insider trades, ownership changes | 15-min delay | `edgartools`, `sec-api.io` |
| **Job Postings** | LinkedIn/Indeed/Wellfound | Job titles, skills required, company, salary range, posting velocity (hiring signals) | Daily | Custom scrapers |
| **News** | TechCrunch + Google News RSS | Funding announcements, M&A, IPO, product launches, layoffs | Near real-time | `feedparser` |
| **Patents** | USPTO Patent Public Search | Patent filings, assignees, classifications, citations, abstracts | Daily | Custom scraper |
| **Funding Events** | OpenCorporates + AngelList | Funding rounds, investors, company profiles, incorporation data | Daily | `opencorporates-sdk` |

### Tier 2: Expansion Sources (Phase 3-4)

| Source | API | Data Collected | Library |
|---|---|---|---|
| **arXiv Papers** | arXiv API (Atom feed) | ML/AI research papers, author institutions, citations | `arxiv` |
| **Product Hunt** | Product Hunt API | Product launches, upvotes, comments, maker profiles | GraphQL API |
| **Crunchbase** | Crunchbase API ($49/mo) | Company profiles, funding rounds, acquisitions, IPOs | `crunchbase` |
| **OpenCorporates** | OpenCorporates API | 220M+ company profiles, directors, filings across 140+ jurisdictions | REST API |
| **Website Monitor** | Custom (diff detection) | Pricing changes, feature launches, team page changes, blog posts | `playwright` / `diffbot` |
| **Twitter/X** | Academic API | Founder/CEO tweets, company announcements, sentiment | `tweepy` |
| **Stack Overflow** | Stack Exchange API | Technology adoption signals, trending tags, job postings | REST API |
| **NPM/PyPI** | Registry APIs | Package download trends, new releases, dependency graphs | HTTP scraping |

### Reddit Deep Dive — Real-Time Intelligence

```
MONITORED SUBREDDITS (15+)
├── r/startups          — Founder discussions, launch announcements
├── r/SaaS              — SaaS metrics, churn discussions, pricing
├── r/Entrepreneur      — Business building, market validation
├── r/smallbusiness     — Local market signals
├── r/technology        — Broad tech trends
├── r/machinelearning   — AI/ML adoption signals
├── r/artificial        — AI product launches, GPT wrappers
├── r/programming       — Developer tool adoption
├── r/webdev            — Framework trends (React, Next.js, etc.)
├── r/python            — Python ecosystem growth
├── r/cybersecurity     — Security startup signals
├── r/Bitcoin           — Crypto/blockchain startup activity
├── r/DevOps            — Infrastructure tool adoption
├── r/dataengineering   — Data stack trends
└── r/Robotics          — Hardware/robotics startup signals

SIGNALS EXTRACTED PER POST:
├── Entity mentions (startup names, products, technologies)
├── Sentiment score (VADER + Ollama deep mode)
├── Engagement metrics (score, comments, upvote velocity)
├── Topic classification (funding, product_launch, hiring, pivot, shutdown)
├── Timestamp for trend analysis
└── Author credibility score (karma, account age, history)
```

### GitHub Deep Dive — Repository Intelligence

```
GITHUB API ENDPOINTS USED:
├── GET /search/repositories — Advanced search (stars:>100, pushed:>2025-01-01)
├── GET /repositories/{owner}/{repo} — Full repo metadata
├── GET /repos/{owner}/{repo}/languages — Language breakdown
├── GET /repos/{owner}/{repo}/topics — Topic tags
├── GET /repos/{owner}/{repo}/stargazers — Star history
├── GET /repos/{owner}/{repo}/forks — Fork graph
├── GET /repos/{owner}/{repo}/releases — Release cadence
├── GET /repos/{owner}/{repo}/commits — Commit velocity
├── GET /search/issues — Issue tracker signals
└── GraphQL: STAR_GROWTH_HISTORY — Star growth over time

INTELLIGENCE EXTRACTED:
├── Star velocity (stars gained per day/week → trend detection)
├── Language popularity shifts → technology adoption signals
├── Fork activity → developer interest in a project/startup
├── Release frequency → project health and activity
├── "Show HN" pattern → product launch detection
├── Topic co-occurrence → market segment clustering
├── Contributor count → team size estimation
└── Issue sentiment → user satisfaction / pain points
```

---

## 5. Tech Stack

### Why These Choices (Research-Backed)

```
┌─────────────────────────────────────────────────────────────────┐
│                    TECH STACK DECISION MATRIX                     │
├─────────────┬──────────────────┬────────────────────────────────┤
│  Layer      │  Choice          │  Why (Research-Backed)         │
├─────────────┼──────────────────┼────────────────────────────────┤
│  Streaming  │  Redpanda         │  Kafka-compatible, no ZooKeeper│
│             │  (over Kafka)     │  C++ = 10x lower latency,     │
│             │                   │  single binary deploy         │
├─────────────┼──────────────────┼────────────────────────────────┤
│  Stream Proc│  Bytewax         │  Python-native (not JVM),      │
│             │                   │  Rust engine under hood,       │
│             │                   │  M12 (Microsoft) backed,       │
│             │                   │  Flink-like semantics           │
├─────────────┼──────────────────┼────────────────────────────────┤
│  OLAP       │  ClickHouse      │  Petabyte-scale, best single-  │
│             │                   │  table query speed, 10x         │
│             │                   │  compression, vectorized exec  │
├─────────────┼──────────────────┼────────────────────────────────┤
│  Time-Series│  TimescaleDB     │  PostgreSQL extension,         │
│             │                   │  hypertables, continuous agg,  │
│             │                   │  full Postgres ecosystem       │
├─────────────┼──────────────────┼────────────────────────────────┤
│  Graph      │  Apache Age       │  PostgreSQL extension (no new │
│             │                   │  DB), Cypher queries, ACID     │
├─────────────┼──────────────────┼────────────────────────────────┤
│  Vector     │  Qdrant           │  HNSW index, cosine distance,  │
│             │                   │  filtering, batch upsert       │
├─────────────┼──────────────────┼────────────────────────────────┤
│  Full-Text  │  Elasticsearch   │  BM25 search, hybrid with      │
│             │                   │  vector, highlights            │
├─────────────┼──────────────────┼────────────────────────────────┤
│  Cache/PubSub│  Redis           │  Session cache, pub/sub for    │
│             │                   │  real-time events              │
├─────────────┼──────────────────┼────────────────────────────────┤
│  NLP        │  spaCy +         │  en_core_web_trf for NER       │
│  Embeddings │  Sentence-Transf. │  all-MiniLM-L6-v2 (384-dim)   │
├─────────────┼──────────────────┼────────────────────────────────┤
│  Orchestration│ Dagster        │  Asset-centric, native Python, │
│             │                   │  replaces cron + file locks    │
├─────────────┼──────────────────┼────────────────────────────────┤
│  Dashboard  │  Streamlit +     │  Streamlit for internal tools,  │
│             │  Next.js          │  Next.js+SSE for production    │
├─────────────┼──────────────────┼────────────────────────────────┤
│  LLM        │  Ollama           │  Local inference, privacy,     │
│             │                   │  no API costs, existing infra   │
└─────────────┴──────────────────┴────────────────────────────────┘
```

### Storage Engine Routing Rules

```
SIGNAL → STORAGE ROUTING:
─────────────────────────
  raw_signals           → MySQL (operational, CRUD)
  time-series metrics   → TimescaleDB (signal_events, trend data)
  analytics/aggregation → ClickHouse (dashboards, OLAP queries)
  embeddings            → Qdrant (semantic search)
  full-text            → Elasticsearch (BM25 search)
  graph relationships  → Apache Age (traversal, Cypher queries)
  cache/sessions       → Redis (pub/sub, hot data)
```

---

## 6. Agent Taxonomy

### Complete Agent Map (50+ Agents by Layer)

```
═══════════════════════════════════════════════════════════════
LAYER 1: SIGNAL INGESTION (20+ Collectors)
═══════════════════════════════════════════════════════════════
  ✅ github_trends_collector      — GitHub trending repos, star velocity
  ✅ social_media_collector       — Reddit (15 subreddits) + Hacker News
  ✅ sec_edgar_collector          — SEC filings (10-K, 8-K, S-1, Form C)
  ✅ patent_collector             — USPTO patent filings + citations
  ✅ job_postings_collector       — LinkedIn/Indeed/Wellfound job signals
  ✅ funding_events_collector     — AngelList/OpenCorporates funding rounds
  ✅ techcrunch_rss               — TechCrunch funding/M&A news
  ✅ google_news_rss              — Google News aggregated signals
  ✅ crunchbase_collector         — Crunchbase company/funding data
  ✅ failory_scraper              — Failed startup post-mortems
  ✅ bls_survival_rates           — BLS business survival statistics
  ✅ reshoring_pdf                — Manufacturing reshoring data

  🔜 github_deep_collector        — GitHub GraphQL: commit velocity, fork graphs,
                                      contributor networks, release cadence
  🔜 reddit_stream_collector      — Real-time Reddit comment stream (PRAW streaming)
  🔜 hn_live_collector            — HN live story stream via Firebase API
  🔜 opencorporates_collector     — OpenCorporates 220M+ company profiles
  🔜 arxiv_collector              — arXiv ML/AI paper signals
  🔜 producthunt_collector        — Product Hunt launches + upvotes
  🔜 website_monitor_collector    — Website change detection (pricing, features)
  🔜 twitter_collector             — Founder/CEO tweet signals
  🔜 stackoverflow_collector      — Technology adoption via Stack Overflow
  🔜 npm_pypi_collector           — Package download trend signals
  🔜 regulatory_collector         — Government regulations (FDA, FTC, EU)
  🔜 podcast_collector            — Startup/VC podcast transcript mining
  🔜 newsletter_collector        — curated newsletter aggregation (Morning Brew, etc)

═══════════════════════════════════════════════════════════════
LAYER 2: STREAM PROCESSING (Bytewax Pipelines)
═══════════════════════════════════════════════════════════════
  ✅ signal_normalizer            — Unified SignalEnvelope for all sources
  ✅ kafka_producer               — Route signals to Kafka topics

  🔜 dedup_stream                — Real-time deduplication (fingerprint + Jaccard)
  🔜 event_correlator            — Cross-source event correlation
                                      Funding → Hiring → GitHub spike
  🔜 temporal_window_stream       — Session aggregation, trend windows
  🔜 anomaly_stream               — Z-score anomaly detection on streams
  🔜 routing_stream               — Dynamic routing to storage engines

═══════════════════════════════════════════════════════════════
LAYER 3: NLP ENRICHMENT
═══════════════════════════════════════════════════════════════
  ✅ nlp_enrichment_agent        — Extract entities, classify, embed, index
  ✅ ner_pipeline                 — spaCy en_core_web_trf + EntityRuler
  ✅ entity_extractor             — Unified: spaCy primary, Ollama fallback
  ✅ embedding_generator          — all-MiniLM-L6-v2 (384-dim)
  ✅ text_classifier              — Signal type + sentiment classification
  ✅ summarizer                   — Ollama abstractive summarization
  ✅ sentiment_agent              — VADER + keyword fallback

  🔜 topic_modeling_agent         — BERTopic clustering for market segments
  🔜 relationship_extractor       — NLP-based relationship extraction
                                      ("Company A acquired Company B")
  🔜 trend_detector_agent         — Time-series trend detection (Mann-Kendall)
  🔜 intent_classifier_agent      — Classify startup intent (B2B, B2C, D2C)

═══════════════════════════════════════════════════════════════
LAYER 4: INTELLIGENCE & SCORING
═══════════════════════════════════════════════════════════════
  ✅ opportunity_scorer           — Composite scoring (ML + heuristic blend)
  ✅ risk_scorer                   — Sector-based risk scoring
  ✅ composite_scorer              — Multi-signal weighted scoring engine
  ✅ feature_attribution           — Explainable scoring (SHAP-like)
  ✅ ml_trainer                    — XGBoost + Random Forest ensemble
  ✅ ml_predictor                 — ML-based failure risk prediction
  ✅ survival_analysis_agent      — Cox proportional hazards model
  ✅ failure_pattern_agent         — Pattern mining from failed startups
  ✅ anomaly_detector              — Z-score anomaly on signal metrics
  ✅ time_decay                    — Exponential decay with signal half-lives
  🔜 market_sizing_agent           — TAM/SAM/SOM estimation from signals
  🔜 competitive_landscape_agent  — Market positioning analysis
  🔜 founder_background_agent     — Founder pedigree scoring (LinkedIn, exits)
  🔜 technology_stack_agent        — Tech stack analysis from GitHub + job posts
  🔜 moat_analyzer_agent          — Competitive moat assessment
  🔜 timing_agent                 — Market timing score (too early / right time / late)

═══════════════════════════════════════════════════════════════
LAYER 5: KNOWLEDGE GRAPH
═══════════════════════════════════════════════════════════════
  ✅ knowledge_graph_agent        — 12 entity types, 20 relationship types
  ✅ entity_resolver               — Jaro-Winkler + blocking strategy
  ✅ semantic_search_agent         — Qdrant + ES sync agent

  🔜 graph_traversal_agent         — Multi-hop reasoning queries
  🔜 community_detector_agent     — Louvain/Leiden community detection
  🔜 influence_propagation_agent  — PageRank-style entity influence scoring
  🔜 temporal_graph_agent         — Time-stamped relationship tracking

═══════════════════════════════════════════════════════════════
LAYER 6: ANALYSIS & INSIGHTS
═══════════════════════════════════════════════════════════════
  ✅ news_intelligence_agent       — News analysis and trend extraction
  ✅ internet_research            — Deep web research via Ollama
  ✅ ai_analyst_agent             — AI-powered market analysis
  ✅ correlation_agent            — Cross-signal correlation analysis
  ✅ revival_opportunity_agent    — Dead startup → market revival detection
  ✅ geographic_strategy_agent    — Regional opportunity mapping
  ✅ global_market_viability_agent — International expansion scoring
  ✅ whale_investor_agent         — Whale investor pattern tracking
  🔜 sector_rotation_agent        — Sector momentum and rotation signals
  🔜 cohort_analysis_agent        — Startup cohort comparison (by year, sector, region)

═══════════════════════════════════════════════════════════════
LAYER 7: OUTPUT & DISTRIBUTION
═══════════════════════════════════════════════════════════════
  ✅ report_generator_agent        — PDF/HTML report generation
  ✅ alert_dispatcher_agent        — Email/Slack/webhook alert dispatch
  ✅ dashboard_agent               — Streamlit dashboard rendering
  ✅ orchestrator                  — Agent pipeline orchestration
  ✅ api_server                    — FastAPI REST + WebSocket endpoints

  🔜 webhook_agent                 — Outbound webhook notifications
  🔜 slack_integration_agent       — Slack bot for real-time alerts
  🔜 email_digest_agent            — Daily/weekly email digests
  🔜 export_agent                 — CSV/JSON/Parquet data export
  🔜 api_v2_agent                 — Versioned API with auth, rate limiting
  🔜 feed_generator_agent          — RSS/Atom feed generation for external consumption

═══════════════════════════════════════════════════════════════
LAYER 8: OPERATIONS & META
═══════════════════════════════════════════════════════════════
  ✅ model_manager                 — Ollama model registry + token tracking
  ✅ llm_portfolio_agent           — LLM model portfolio management
  ✅ llm_pricing_agent             — LLM API pricing comparison
  ✅ llm_benchmark_agent           — LLM performance benchmarking
  ✅ llm_cost_optimizer_agent      — LLM cost optimization
  ✅ ollama_usage_tracker          — Token usage monitoring
  ✅ license_agent                 — Stripe billing + license management
  🔜 data_quality_agent            — Signal quality scoring + dedup validation
  🔜 pipeline_health_agent         — Pipeline failure detection + auto-restart
  🔜 cost_tracking_agent           — Per-signal processing cost attribution

LEGEND: ✅ = Implemented  🔜 = Planned  🔴 = Not started
```

### Agent Dependency Graph (Who Feeds Whom)

```
COLLECTORS ──→ raw_signals table ──→ NLP ENRICHMENT
                                     │
                                     ├──→ vector_embeddings → Qdrant
                                     ├──→ processed signals  → ClickHouse
                                     └──→ KG entities/rels   → Apache Age
                                            │
                                     SCORING ←─────────────┘
                                     │
                                     ├──→ opportunity_scores
                                     ├──→ startup_risk_scores
                                     └──→ signal_events → TimescaleDB
                                            │
                                     ANALYSIS ←─────────────┘
                                     │
                                     ├──→ analysis tables
                                     └──→ alert_rules → ALERTS → Slack/Email/Webhook
```

---

## 7. Data Flow Diagram

```
                        ┌──────────────────────────────────┐
                        │         EXTERNAL WORLD           │
                        │  GitHub │ Reddit │ HN │ SEC │ ...  │
                        └──────────────┬───────────────────┘
                                       │
                              ┌────────▼────────┐
                              │   COLLECTORS    │
                              │   (20+ agents)  │
                              │   Python scripts│
                              └────────┬────────┘
                                       │
                        ┌──────────────▼───────────────────┐
                        │       KAFKA EVENT BUS            │
                        │  (Redpanda — Kafka-compatible)    │
                        │                                   │
                        │  Topics:                          │
                        │  ├─ raw.signals                   │
                        │  ├─ raw.news                      │
                        │  ├─ raw.filing                    │
                        │  ├─ raw.funding                   │
                        │  ├─ raw.social                    │
                        │  ├─ raw.github                    │
                        │  ├─ enriched.signals              │
                        │  ├─ scores.updates                │
                        │  ├─ graph.events                  │
                        │  └─ alerts.triggered              │
                        └──┬──────────┬──────────┬─────────┘
                           │          │          │
              ┌────────────▼──┐  ┌───▼─────────▼──┐
              │  BYTEWAX       │  │  BYTEWAX        │
              │  Enrichment    │  │  Pattern        │
              │  Pipeline      │  │  Detection      │
              │                │  │                  │
              │  • spaCy NER   │  │  • Funding→Hire│
              │  • Classify    │  │  • GitHub→News  │
              │  • Embed       │  │  • Anomaly      │
              │  • Dedup       │  │  • Correlation  │
              │  • Route       │  │  • Distress     │
              └────────┬───────┘  └───────┬────────┘
                       │                  │
        ┌──────────────┼──────────────────┼──────────────┐
        │              │                  │              │
   ┌────▼────┐   ┌────▼────┐    ┌────────▼────┐  ┌────▼────┐
   │  MySQL  │   │ClickHse │    │   Qdrant     │  │ Elastic │
   │ (OPS)   │   │ (OLAP)  │    │  (Vector)    │  │ (Search)│
   └─────────┘   └─────────┘    └─────────────┘  └─────────┘
   ┌────▼────┐   ┌─────────┐    ┌─────────────┐  ┌─────────┐
   │Timescale│   │Apache   │    │    Redis     │  │ Apache  │
   │  (TS)   │   │  Age    │    │   (Cache)    │  │  Age    │
   └─────────┘   │ (Graph) │    └─────────────┘  └─────────┘
                 └─────────┘
                       │
        ┌──────────────┼──────────────────────────────────────┐
        │              │                                      │
   ┌────▼──────────────▼──────────────────────────────────┐  │
   │                   API LAYER                           │  │
   │  FastAPI REST │ GraphQL │ WebSocket │ SSE │ Webhooks  │  │
   └──────────────────────┬───────────────────────────────┘  │
                           │                                  │
   ┌───────────────────────▼────────────────────────────────▼┐
   │                   DASHBOARD LAYER                        │
   │  Streamlit (internal)    Next.js + SSE (production)     │
   │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
   │  │Opportunity│ │ Knowledge│ │ Real-time│ │  Signal  │  │
   │  │ Dashboard │ │ Graph    │ │ Feed     │ │ Heatmap  │  │
   │  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
   └────────────────────────────────────────────────────────┘
```

---

## 8. Storage Topology

```
┌─────────────────────────────────────────────────────────────────────┐
│                    STORAGE ENGINE MAP                                │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  MySQL 8.0 — Operational Data (CRUD)                        │    │
│  │  Tables: failed_startups, collection_runs, agent_runs,      │    │
│  │          user_licenses, subscription_metrics, alert_rules,  │    │
│  │          ml_models, raw_signals, opportunity_scores          │    │
│  │  Role: Primary data store, agent orchestration state          │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  ClickHouse — OLAP Analytics                                  │    │
│  │  Tables: signal_events (time-series), aggregate_scores,       │    │
│  │          trend_metrics, cohort_analysis                        │    │
│  │  Role: Fast dashboard queries, aggregation, rollups           │    │
│  │  Ingestion: Kafka → ClickHouse (native connector)             │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  TimescaleDB — Time-Series + Continuous Aggregates            │    │
│  │  Tables: signal_metrics (hypertable), anomaly_scores,         │    │
│  │          engagement_trends, velocity_metrics                    │    │
│  │  Role: Time-based queries, retention policies, real-time agg  │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  Qdrant — Vector Search (384-dim, Cosine)                     │    │
│  │  Collections: startup_signals, entity_embeddings                │    │
│  │  Role: Semantic search, similarity ranking, clustering         │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  Elasticsearch — Full-Text Search (BM25)                       │    │
│  │  Index: startup_research (title, body_text, entity_name)        │    │
│  │  Role: Keyword search, fuzzy matching, highlights              │    │
│  │  Hybrid: script_score blending BM25 + cosine similarity        │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  Apache Age — Knowledge Graph (Cypher over PostgreSQL)          │    │
│  │  Nodes: startup(12 types), investor, technology, market          │    │
│  │  Edges: funded_by, acquired_by, competes_with, uses_tech       │    │
│  │  Role: Multi-hop traversal, community detection, PageRank        │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  Redis — Cache + Pub/Sub                                        │    │
│  │  Keys: session:*, cache:search:*, live:stats:*                  │    │
│  │  Pub/Sub: alerts.triggered, scores.updated, graph.changed        │    │
│  │  Role: Real-time events, hot data cache, WebSocket backbone     │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 9. Agent Interaction Map

```
                         ┌───────────────┐
                         │   ORCHESTRATOR │
                         │  (Central Hub) │
                         └───────┬───────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
    ┌─────▼─────┐          ┌─────▼─────┐          ┌─────▼─────┐
    │ COLLECTORS│          │ANALYSIS   │          │ OUTPUT     │
    │ (20+ src) │          │PIPELINE   │          │ PIPELINE   │
    └─────┬─────┘          └─────┬─────┘          └─────┬─────┘
          │                      │                      │
    ┌─────▼─────┐    ┌────────────┼────────────┐    ┌─────▼─────┐
    │           │    │            │            │    │           │
    │ GitHub    │    │  NLP       │ Intelligence│   │ Reports   │
    │ Reddit    │    │ Enrichment │ Scoring    │   │ Dashboard │
    │ HN        │    │            │            │   │ API       │
    │ SEC       │───▶│ spaCy NER  │ Composite  │──▶│ Webhook   │
    │ Patents   │    │ Classify   │ Scoring    │   │ Slack     │
    │ Jobs      │    │ Embed      │ Anomaly    │   │ Email     │
    │ News      │    │ Sentiment  │ Survival   │   │ RSS Feed  │
    │ arXiv     │    │ Summarize  │ Patterns   │   │ Export    │
    │ OpenCorp. │    │            │ Market     │   │           │
    │ ProductHnt│    └─────┬──────┴────────────┘    └───────────┘
    │ Twitter   │          │
    │ NPM/PyPI  │    ┌─────▼──────┐
    │ Website   │    │ Knowledge  │
    │ Newsletter│──▶│ Graph       │
    │ Podcast   │    │ 12 entities│
    │ Regulatory│    │ 20 rels     │
    │ Crunchbase│    │ Entity Res. │
    └───────────┘    │ Semantic    │
                     │ Search      │
                     └────────────┘

DATA FLOW: Collectors → raw_signals → NLP Enrich → Score → Graph → Alert → Output
```

---

## 10. Docker Compose Service Map

```
┌─────────────────────────────────────────────────────────────────┐
│  docker-compose.yml — 18 Services                                 │
│                                                                  │
│  ┌─ EXISTING (7) ────────────────────────────────────────────┐  │
│  │  mysql:8.0           (port 3306)     — Operational DB      │  │
│  │  redis:7             (port 6379)     — Cache + Pub/Sub    │  │
│  │  kafka + zookeeper    (port 9092)     — Event bus          │  │
│  │  qdrant              (port 6333/6334)— Vector search       │  │
│  │  elasticsearch:8.12  (port 9200)     — Full-text search    │  │
│  │  api_server          (port 8000)     — FastAPI            │  │
│  │  streamlit           (port 8501)     — Internal dashboard │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌─ NEW — PHASE 3 (5) ────────────────────────────────────────┐  │
│  │  redpanda             (port 9093)     — Kafka replacement  │  │
│  │  clickhouse           (port 8123)     — OLAP analytics     │  │
│  │  timescaledb          (port 5432 ext)  — Time-series        │  │
│  │  dagster-webserver    (port 3000)     — Pipeline UI        │  │
│  │  dagster-daemon       (background)    — Pipeline executor  │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌─ NEW — PHASE 4 (6) ────────────────────────────────────────┐  │
│  │  nextjs-dashboard     (port 3001)     — Production UI      │  │
│  │  apache-age          (port 5432 ext)  — Graph queries      │  │
│  │  hasura               (port 8080)     — GraphQL engine      │  │
│  │  prometheus           (port 9090)     — Metrics collection  │  │
│  │  grafana              (port 3002)     — Metrics dashboard   │  │
│  │  vector              (port 6880)     — Log aggregator     │  │
│  └────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 11. Phased Rollout

### Phase 3: Real-Time Stream Processing

**What changes:** Add Bytewax stream processing, replace batch cron with Dagster, add Redpanda, ClickHouse, TimescaleDB.

```
New Files:
  stream/__init__.py
  stream/kafka_consumer.py          — Consume from Kafka topics
  stream/enrichment_pipeline.py     — Bytewax NLP enrichment flow
  stream/pattern_detection.py       — Cross-source correlation
  stream/temporal_windows.py       — Session aggregation
  stream/sink_router.py             — Route to storage engines
  dagster_repository.py             — Dagster asset definitions
  dagster/__init__.py

Modified Files:
  docker-compose.yml                 — +redpanda, +clickhouse, +timescaledb, +dagster
  config/settings.yaml               — +stream, +bytewax, +dagster sections
  requirements.txt                   — +bytewax, +redpanda, +clickhouse-driver
  db/schema.py                       — +timescaledb hypertable DDL
  agents/orchestrator.py             — Dagster integration
```

**Verification:**
- `docker compose up -d` — 12 services start
- `dagit` shows pipeline DAG
- Reddit stream flows through: Collector → Kafka → Bytewax → NLP → ClickHouse
- Dashboard queries ClickHouse in <100ms

---

### Phase 4: Deep Collection + Production Dashboard

**What changes:** Add 12 new collectors (GitHub deep, Reddit stream, OpenCorporates, arXiv, Product Hunt, etc.), Next.js production dashboard, Hasura GraphQL, monitoring stack.

```
New Files:
  collectors/github_deep_collector.py
  collectors/reddit_stream_collector.py
  collectors/hn_live_collector.py
  collectors/opencorporates_collector.py
  collectors/arxiv_collector.py
  collectors/producthunt_collector.py
  collectors/website_monitor_collector.py
  collectors/twitter_collector.py
  collectors/stackoverflow_collector.py
  collectors/npm_pypi_collector.py
  collectors/regulatory_collector.py
  collectors/podcast_collector.py

  dashboard/nextjs/                  — Next.js production dashboard
    package.json
    pages/
    components/
    app/api/

Modified Files:
  agents/collection.py               — Register 12 new collectors
  docker-compose.yml                 — +nextjs, +hasura, +prometheus, +grafana
```

**Verification:**
- `python run_agent.py --pipeline collection` — 24 collectors run
- `curl http://localhost:3001` — Next.js dashboard loads
- `curl http://localhost:8080/v1/graphql` — Hasura GraphQL works

---

### Phase 5: Advanced Intelligence

**What changes:** Add 15 new analysis agents (market sizing, competitive landscape, founder background, timing, community detection, etc.), Apache Age graph queries.

```
New Files:
  agents/market_sizing_agent.py
  agents/competitive_landscape_agent.py
  agents/founder_background_agent.py
  agents/technology_stack_agent.py
  agents/moat_analyzer_agent.py
  agents/timing_agent.py
  agents/graph_traversal_agent.py
  agents/community_detector_agent.py
  agents/influence_propagation_agent.py
  agents/temporal_graph_agent.py
  agents/topic_modeling_agent.py
  agents/relationship_extractor.py
  agents/trend_detector_agent.py
  agents/intent_classifier_agent.py
  agents/sector_rotation_agent.py
  agents/cohort_analysis_agent.py

Modified Files:
  agents/orchestrator.py             — Register 16 new agents
  db/schema.py                       — Apache Age graph schema
  api_server.py                      — New analysis endpoints
```

---

### Phase 6: Multi-Tenancy + API v2

```
New Files:
  api/v2/
    router.py
    auth.py
    rate_limiter.py
    webhooks.py
  agents/webhook_agent.py
  agents/slack_integration_agent.py
  agents/email_digest_agent.py
  agents/export_agent.py
  agents/feed_generator_agent.py
  agents/data_quality_agent.py
  agents/pipeline_health_agent.py
  agents/cost_tracking_agent.py
```

---

## 12. What Is the Outcome

### At the End of Full Implementation

```
┌──────────────────────────────────────────────────────────────────┐
│              WHAT YOU GET                                        │
│                                                                  │
│  50+ AGENTS running autonomously                                  │
│  ├── 24 collectors monitoring real-time data streams             │
│  ├── 8 NLP/enrichment agents processing signals                  │
│  ├── 12 intelligence/scoring agents analyzing opportunities       │
│  ├── 5 knowledge graph agents mapping 12 entity types            │
│  ├── 10 analysis agents producing insights                       │
│  └── 6 output agents distributing intelligence                  │
│                                                                  │
│  20+ DATA SOURCES continuously monitored                         │
│  ├── GitHub (star velocity, trending, commits)                   │
│  ├── Reddit (15 subreddits, real-time comments)                  │
│  ├── Hacker News (live stories, "Show HN" launches)              │
│  ├── SEC EDGAR (filings, insider trades, Form C)                  │
│  ├── Patents (USPTO filings, citations, assignees)                │
│  ├── Job boards (hiring signals, skill demand)                   │
│  ├── News (TechCrunch, Google News, RSS feeds)                   │
│  ├── arXiv (ML/AI research papers)                               │
│  ├── Product Hunt (product launches)                             │
│  └── 12+ more sources                                            │
│                                                                  │
│  7 STORAGE ENGINES with intelligent routing                       │
│  ├── MySQL (operational data)                                    │
│  ├── ClickHouse (OLAP dashboards, sub-100ms queries)             │
│  ├── TimescaleDB (time-series, continuous aggregates)             │
│  ├── Qdrant (semantic search, 384-dim embeddings)                 │
│  ├── Elasticsearch (BM25 full-text, hybrid search)               │
│  ├── Apache Age (knowledge graph, Cypher queries)                │
│  └── Redis (real-time pub/sub, caching)                          │
│                                                                  │
│  REAL-TIME PIPELINE                                              │
│  ├── Event-driven (Kafka/Redpanda)                               │
│  ├── Stream processed (Bytewax, Python-native)                   │
│  ├── Orchestrated (Dagster asset-centric)                        │
│  └── Monitored (Prometheus + Grafana)                            │
│                                                                  │
│  PRODUCTION DASHBOARDS                                            │
│  ├── Opportunity Radar (live signal feed + scoring)              │
│  ├── Knowledge Graph Explorer (D3.js interactive)                │
│  ├── Real-time Signal Heatmap (geographic + sector)              │
│  ├── Competitive Landscape (market positioning)                   │
│  ├── Founder Intelligence (pedigree + track record)              │
│  └── Custom Alert Rules (threshold + anomaly + composite)         │
│                                                                  │
│  API ENDPOINTS                                                   │
│  ├── GET /api/search (semantic/fulltext/hybrid)                  │
│  ├── GET /api/entities/{name}/connections (graph traversal)       │
│  ├── GET /api/opportunities (scored, ranked, filtered)            │
│  ├── GET /api/signals/live (real-time SSE stream)                │
│  ├── POST /api/webhooks (outbound notifications)                 │
│  └── GraphQL endpoint (Hasura)                                   │
│                                                                  │
│  CONCRETE CAPABILITIES                                           │
│  ✅ Detect a startup's funding round within 15 minutes           │
│  ✅ Score opportunity quality with explainable ML features       │
│  ✅ Map competitive relationships across 12 entity types         │
│  ✅ Track GitHub star velocity as a leading indicator            │
│  ✅ Monitor Reddit sentiment for market signals                   │
│  ✅ Correlate hiring spikes with product launches                │
│  ✅ Alert on anomaly patterns (distress signals, market shifts)  │
│  ✅ Generate PDF reports with knowledge graph visualizations       │
│  ✅ Self-hosted — all data stays on your infrastructure          │
└──────────────────────────────────────────────────────────────────┘
```

### Key Metrics

| Metric | Current | Target |
|---|---|---|
| Data sources monitored | 12 | 24+ |
| Agents | 35 | 50+ |
| Collection frequency | Batch (daily) | Real-time (continuous) |
| Query latency (dashboard) | ~2s (MySQL) | <100ms (ClickHouse) |
| Search modes | 2 (vector + fulltext) | 3 (semantic + fulltext + hybrid) |
| Entity types in KG | 12 | 16+ |
| Relationship types | 20 | 30+ |
| Storage engines | 3 (MySQL, Qdrant, ES) | 7 (+ ClickHouse, TimescaleDB, Age, Redis) |
| Docker services | 7 | 18 |
| Test coverage | 192 tests | 400+ tests |

---

## Research Sources

This architecture was informed by research across these real tools and APIs:

- [Trendshift.io](https://trendshift.io/) — Real-time GitHub trending detection
- [OSSInsight](https://ossinsight.io/trending) — 10B+ data points of GitHub analytics
- [PRAW (Python Reddit API)](https://painonsocial.com/blog/reddit-api-tools-2) — Reddit data collection
- [Reddit Streaming Pipeline](https://github.com/nama1arpit/reddit-streaming-pipeline) — Real-time Reddit + Spark pipeline
- [Hacker News Algolia API](https://hn.algolia.com/api) — HN search/streaming
- [python-hacker-news](https://github.com/santiagobasulto/python-hacker-news) — Python HN library
- [EdgarTools](https://github.com/dgunning/edgartools) — Python SEC EDGAR parser
- [SEC-API.io](https://sec-api.io/) — Real-time SEC filing streaming
- [OpenCorporates](https://opencorporates.com/) — 220M+ company profiles, open API
- [Crunchbase Alternatives 2026](https://dev.to/agenthustler/crunchbase-api-in-2026-free-tier-gone-what-startup-data-hunters-do-now-1177) — Free data source comparison
- [Bytewax](https://bytewax.io/) — Python-native stream processing (M12 backed)
- [ClickHouse vs Apache Doris](https://tacnode.io/post/apache-doris-vs-clickhouse) — OLAP comparison
- [Apache Doris Official Comparison](https://doris.apache.org/docs/2.1/gettingStarted/alternatives/alternative-to-clickhouse/) — Benchmark data
- [Redpanda vs Kafka](https://www.kai-waehner.de/blog/2022/11/16/when-to-choose-redpanda-instead-of-apache-kafka/) — Streaming comparison
- [Multi-Agent Architecture Papers](https://github.com/kyegomez/awesome-multi-agent-papers) — Research compilation
- [Top 5 Open-Source Multi-Agent Frameworks](https://generativeai.pub/top-5-open-source-frameworks-to-build-multi-agent-ai-systems-in-2025-fc92b0fb62af) — Framework comparison
