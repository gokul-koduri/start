# 🛣️ Opportunity Intelligence Platform — Technical Roadmap

> Detailed implementation plan with session-level granularity
> 79 sessions | 6 phases | ~127 new files | ~42 modified files

---

## Progress Summary

| Phase | Status | Sessions | Key Deliverable |
|-------|--------|----------|-----------------|
| Phase 1: Foundation | ✅ COMPLETE | 8/8 | Scoring engine, collectors, API, Streamlit |
| Phase 2: Intelligence | ✅ COMPLETE | 10/10 | NLP, entity resolution, semantic search, KG |
| Phase 3: Scale | ✅ COMPLETE | 12/12 | Stream processing, Next.js, Redis, Docker |
| Phase 4: Deep Collection | ⏳ 60% DONE | 9/15 | 12 new collectors |
| Phase 5: Advanced Intelligence | 🔲 PLANNED | 0/18 | 16 new agents |
| Phase 6: Operations | 🔲 PLANNED | 0/16 | Auth, multi-tenant, monitoring |

**Overall: 30/79 sessions (38%) | 467 tests passing**

---

## Phase 4: Deep Collection (Sessions 4.1 - 4.15)

### Remaining Sessions (6 of 15)

#### 4.10 — NPM/PyPI Trends ⏳
```
NEW FILES:
  collectors/npm_pypi_collector.py
  tests/test_npm_pypi.py

MODIFIES:
  agents/collection.py         → Register NPMPyPICollector
  config/settings.yaml         → Add npm_pypi: config block
  db/schema.py                 → Add package_downloads table

DATA COLLECTED:
  - NPM package download counts (daily)
  - PyPI package download counts (daily)
  - Trend detection (7-day, 30-day velocity)
  - New package emergence signals

TESTS:
  - test_npm_pypi_collector.py
  - Mock HTTP responses from registry APIs
  - Verify dedup and rate limiting
```

#### 4.11 — Regulatory Filings ⏳
```
NEW FILES:
  collectors/regulatory_collector.py
  tests/test_regulatory.py

MODIFIES:
  agents/collection.py         → Register RegulatoryCollector
  config/settings.yaml         → Add regulatory: config block
  db/schema.py                 → Add regulatory_filings table

DATA COLLECTED:
  - Federal Register API (US)
  - EU regulatory filings
  - Sector-specific regulation changes
  - Compliance risk signals

TESTS:
  - test_regulatory.py
```

#### 4.12 — Newsletter Aggregation ⏳ (depends on 4.2, 4.3)
```
NEW FILES:
  collectors/newsletter_collector.py
  tests/test_newsletter.py

MODIFIES:
  agents/collection.py         → Register NewsletterCollector
  config/settings.yaml         → Add newsletter: config block
  db/schema.py                 → Add newsletter_items table

DATA COLLECTED:
  - Curated startup/tech newsletters
  - RSS-to-email aggregation
  - Key insight extraction
  - Topic tagging

DEPENDENCIES: Reddit Stream (4.2), HN Live (4.3) for source URLs
```

#### 4.13 — Schema Migration v14 ⏳ (depends on 4.1-4.12)
```
MODIFIES:
  db/schema.py                 → Bump _SCHEMA_VERSION to 14
  requirements.txt             → Add new dependencies
  agents/collection.py         → Finalize collector registry

NEW TABLES:
  - company_profiles
  - arxiv_papers
  - product_launches
  - website_snapshots
  - so_tag_stats
  - package_downloads
  - regulatory_filings
  - newsletter_items

VALIDATION:
  - All Phase 4 collectors registered
  - All new tables created
  - Migration is idempotent
```

#### 4.14 — Phase 4 Integration Tests ⏳
```
NEW FILES:
  tests/test_phase4_integration.py

TESTS:
  - Each collector produces valid signals
  - Signals flow through Kafka topics
  - Dual-write (MySQL + Kafka) verified
  - Deduplication works across collectors
  - Schema v14 migration runs cleanly
  - Full collection pipeline end-to-end
```

#### 4.15 — Phase 4 Commit + Validation ⏳
```
MODIFIES:
  PROGRESS.yaml                → Update phase_4 status
  ROADMAP.md                   → Mark Phase 4 complete

VALIDATION:
  - All tests passing (pytest)
  - No import errors
  - Schema version >= 14
  - Docker compose up -d succeeds
```

---

## Phase 5: Advanced Intelligence (Sessions 5.1 - 5.18)

### Market Analysis Track

#### 5.1 — Market Sizing Agent
```
NEW FILES:
  agents/market_sizing_agent.py
  tests/test_market_sizing.py

FUNCTION:
  - TAM/SAM/SOM estimation for any sector/geography
  - Uses existing startup data + BLS data + funding data
  - Formula-based + LLM-assisted estimation
  - Outputs: market_size, growth_rate, saturation, opportunity_gap

DEPENDENCIES: None (can start immediately)
```

#### 5.2 — Competitive Landscape
```
NEW FILES:
  agents/competitive_landscape_agent.py
  tests/test_competitive_landscape.py

FUNCTION:
  - Map competitors in any sector
  - Market share estimation from funding + news signals
  - Competitive positioning matrix
  - Threat assessment (new entrants, substitutes)

DEPENDENCIES: 5.1 (Market Sizing)
```

#### 5.6 — Timing Agent
```
NEW FILES:
  agents/timing_agent.py
  tests/test_timing.py

FUNCTION:
  - Market timing analysis (is now the right time?)
  - Technology adoption curves (S-curve fitting)
  - Funding cycle analysis (boom/bust detection)
  - Regulatory window identification
  - Score: timing_score (0-100)

DEPENDENCIES: 5.1 (Market Sizing)
```

#### 5.13 — Trend Detector
```
NEW FILES:
  agents/trend_detector_agent.py
  tests/test_trend_detector.py

FUNCTION:
  - Detect macro trends before they peak
  - Signal aggregation across all sources
  - Trend lifecycle stage (emerging, growing, peaking, declining)
  - Trend velocity and acceleration

DEPENDENCIES: 5.6 (Timing Agent)
```

#### 5.15 — Sector Rotation
```
NEW FILES:
  agents/sector_rotation_agent.py
  tests/test_sector_rotation.py

FUNCTION:
  - Track capital flow between sectors
  - Identify heating/cooling sectors
  - Rotation signals (funding shifts, hiring changes)
  - Predictive rotation model

DEPENDENCIES: 5.1, 5.6
```

#### 5.16 — Cohort Analysis
```
NEW FILES:
  agents/cohort_analysis_agent.py
  tests/test_cohort_analysis.py

FUNCTION:
  - Compare startup cohorts by year, sector, geography, stage
  - Survival curves per cohort
  - Success factor analysis per cohort
  - Temporal pattern detection

DEPENDENCIES: 5.15 (Sector Rotation)
```

### Founder & Technology Track

#### 5.3 — Founder Background
```
NEW FILES:
  agents/founder_background_agent.py
  tests/test_founder_background.py

FUNCTION:
  - Founder track record (exits, failures)
  - Network strength (connections in KG)
  - Experience relevance to current venture
  - Founder score (0-100)

DEPENDENCIES: 4.4 (OpenCorporates for company data)
```

#### 5.4 — Technology Stack
```
NEW FILES:
  agents/technology_stack_agent.py
  tests/test_tech_stack.py

FUNCTION:
  - Detect tech stack from GitHub repos
  - Modern stack = agility signal
  - Technology maturity assessment
  - Tech debt indicator

DEPENDENCIES: 4.1 (GitHub Deep), 4.9 (StackOverflow)
```

#### 5.5 — Moat Analyzer
```
NEW FILES:
  agents/moat_analyzer_agent.py
  tests/test_moat_analyzer.py

FUNCTION:
  - Competitive moat strength analysis
  - Network effects detection
  - Switching costs estimation
  - IP/patent moat
  - Brand moat from news/social signals
  - Moat score (0-100)

DEPENDENCIES: 5.2 (Competitive Landscape), 5.4 (Tech Stack)
```

### Graph & Network Track

#### 5.7 — Graph Traversal
```
NEW FILES:
  agents/graph_traversal_agent.py
  tests/test_graph_traversal.py
  db/graph_queries.py

FUNCTION:
  - Shortest path between entities
  - Degree centrality (most connected entities)
  - PageRank (most influential entities)
  - k-hop neighborhood queries
  - Graph statistics (density, clustering coefficient)

DEPENDENCIES: None
```

#### 5.8 — Community Detector
```
NEW FILES:
  agents/community_detector_agent.py
  tests/test_community_detector.py

FUNCTION:
  - Detect clusters in investor-founder-startup network
  - Identify investment syndicates
  - Founder-school networks
  - Geographic clustering

DEPENDENCIES: 5.7 (Graph Traversal)
```

#### 5.9 — Influence Propagation
```
NEW FILES:
  agents/influence_propagation_agent.py
  tests/test_influence_propagation.py

FUNCTION:
  - How influence spreads through the network
  - Who moves markets? (identify key influencers)
  - Influence cascade modeling
  - Signal amplification detection

DEPENDENCIES: 5.7, 5.8
```

#### 5.10 — Temporal Graph
```
NEW FILES:
  agents/temporal_graph_agent.py
  tests/test_temporal_graph.py

FUNCTION:
  - How relationships evolve over time
  - Funding pattern evolution
  - Team composition changes
  - Strategic pivot detection in graph structure

DEPENDENCIES: 5.7 (Graph Traversal)
```

### NLP & Topic Track

#### 5.11 — Topic Modeling
```
NEW FILES:
  agents/topic_modeling_agent.py
  tests/test_topic_modeling.py

FUNCTION:
  - Discover emerging themes across all data sources
  - BERTopic / LDA-based topic extraction
  - Topic evolution over time
  - Cross-source topic correlation

DEPENDENCIES: None
```

#### 5.12 — Relationship Extractor
```
NEW FILES:
  agents/relationship_extractor.py
  tests/test_relationship_extractor.py

FUNCTION:
  - Extract new relationship types from unstructured text
  - "Company X partnered with Company Y"
  - "Founder left to start new venture"
  - Auto-populate knowledge graph

DEPENDENCIES: 5.11 (Topic Modeling)
```

#### 5.14 — Intent Classifier
```
NEW FILES:
  agents/intent_classifier_agent.py
  tests/test_intent_classifier.py

FUNCTION:
  - Classify user queries for agent routing
  - "Compare failure rates" → survival analysis agent
  - "Who invested in X?" → whale investor agent
  - "Should I start Y?" → market sizing + timing agents

DEPENDENCIES: 5.11 (Topic Modeling)
```

### Integration

#### 5.17 — Schema + Integration
```
NEW FILES:
  tests/test_phase5_integration.py

MODIFIES:
  db/schema.py                 → Bump to v15, add agent output tables
  agents/orchestrator.py       → Register all 16 new agents

VALIDATION:
  - All 16 agents produce valid outputs
  - Agent dependency chains execute correctly
  - No circular dependencies
  - Schema v15 migration clean
```

#### 5.18 — Commit + Validation
```
MODIFIES:
  PROGRESS.yaml                → Update phase_5 status
  ROADMAP.md                   → Mark Phase 5 complete
```

---

## Phase 6: Operations (Sessions 6.1 - 6.16)

### Auth Track

#### 6.1 — Auth Package (JWT + RBAC)
```
NEW FILES:
  auth/__init__.py
  auth/jwt_handler.py          → JWT token creation, validation, refresh
  auth/rbac.py                 → Role-based access control (admin, user, viewer)
  tests/test_auth.py

MODIFIES:
  requirements.txt             → Add PyJWT>=2.8.0
```

#### 6.2 — Tenant Manager
```
NEW FILES:
  auth/tenant_manager.py       → Multi-tenant data isolation
  tests/test_tenant_manager.py

MODIFIES:
  db/schema.py                 → Add tenants, tenant_members tables (v16)
```

### API v2 Track

#### 6.3 — API v2 Router
```
NEW FILES:
  api/v2/__init__.py
  api/v2/opportunities.py      → CRUD + filtering + pagination
  api/v2/signals.py            → Signal management
  tests/test_api_v2.py

MODIFIES:
  api_server.py                → Mount v2 router with auth middleware
```

#### 6.4 — API v2 Webhooks + Export
```
NEW FILES:
  api/v2/webhooks.py           → Webhook CRUD
  api/v2/export.py             → CSV/JSON/PDF export endpoints
```

#### 6.5 — Webhook Dispatcher
```
NEW FILES:
  webhooks/__init__.py
  webhooks/dispatcher.py       → Outgoing webhook delivery with retry
  webhooks/templates.py        → Payload templates for Slack/Discord/Custom
  tests/test_webhooks.py
```

### Collaboration Track

#### 6.6 — Collaboration Features
```
NEW FILES:
  collaboration/__init__.py
  collaboration/annotations.py → User annotations on entities
  collaboration/watchlists.py  → Entity watchlists with alert rules

MODIFIES:
  db/schema.py                 → Add annotations, watchlists, shared_notes
  api_server.py                → Collaboration endpoints
```

### Integration Agents

#### 6.7 — Slack Integration Agent
#### 6.8 — Email Digest Agent
#### 6.9 — Export Agent
#### 6.10 — Feed Generator Agent
```
Each follows same pattern:
  agents/{name}.py
  tests/test_{name}.py
  Modified: agents/orchestrator.py
```

### Monitoring Track

#### 6.11 — Prometheus Metrics
```
NEW FILES:
  monitoring/__init__.py
  monitoring/metrics.py         → Counter, Gauge, Histogram for all ops
  monitoring/health.py          → Deep health checks
```

#### 6.12 — Data Quality Agent (independent)
#### 6.13 — Pipeline Health Agent (depends on 6.11)
#### 6.14 — Cost Tracking Agent (depends on 6.11)

### Orchestration

#### 6.15 — Dagster Orchestration
```
NEW FILES:
  dagster/__init__.py
  dagster/repository.py        → Dagster asset definitions
  dagster/ops/collect_ops.py   → Collector ops
  dagster/ops/score_ops.py     → Scoring ops
  dagster/ops/kg_ops.py        → KG ops
  dagster/schedules.py         → Schedules (replaces cron)
  tests/test_dagster_repo.py

MODIFIES:
  docker-compose.yml           → Add dagster service
  requirements.txt             → Add dagster
```

#### 6.16 — Final Commit + Deploy
```
MODIFIES:
  docker-compose.yml           → Finalize all 18 services
  PROGRESS.yaml                → Mark all phases complete
  ROADMAP.md                   → Final status update
```

---

## Critical Path

```
CRITICAL PATH TO LAUNCH:

4.10 → 4.11 → 4.13 → 4.14 → 4.15 (Phase 4 complete)
                                    ↓
5.1 → 5.2 → 5.5                     (Phase 5 starts)
5.1 → 5.6 → 5.13 → 5.15 → 5.16
5.7 → 5.8 → 5.9
5.11 → 5.12, 5.14
                    ↓
              5.17 → 5.18 (Phase 5 complete)
                          ↓
6.1 → 6.2 → 6.3 → 6.4 → 6.5 (API + Webhooks)
6.1 → 6.6 (Collaboration)
6.11 → 6.13, 6.14 (Monitoring)
                          ↓
              6.15 → 6.16 (Phase 6 complete → LAUNCH)
```

### Estimated Timeline

| Phase | Sessions Remaining | Est. Duration |
|-------|-------------------|---------------|
| Phase 4 | 6 sessions | 2-3 weeks |
| Phase 5 | 18 sessions | 6-8 weeks |
| Phase 6 | 16 sessions | 8-10 weeks |
| **Total to launch** | **40 sessions** | **16-21 weeks** |

---

## Testing Strategy Per Phase

| Phase | New Tests | Test Focus |
|-------|-----------|------------|
| Phase 4 | ~30 | Collector unit tests, mocked HTTP, dedup, dual-write |
| Phase 5 | ~36 | Agent logic, scoring formulas, graph algorithms, NLP accuracy |
| Phase 6 | ~30 | Auth flows, API v2 contracts, webhook delivery, monitoring |

---

*Last updated: June 5, 2026*
*Current: Session 4.9 complete, next: Session 4.10*
