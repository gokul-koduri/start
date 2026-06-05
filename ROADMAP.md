# Opportunity Intelligence Platform — Master Roadmap

> Open-source, real-time, multi-agent alternative to Crunchbase / PitchBook / Tracxn
> Self-hosted. 50+ agents. 24 data sources. 7 storage engines.

---

## Phase Completion Status

| Phase | Status | Sessions | Files | Tests | Key Deliverables |
|-------|--------|----------|-------|-------|-----------------|
| Phase 1: Foundation | **COMPLETE** | 8/8 | 20 new | 86 | Scoring engine, 4 collectors, API server, Streamlit, seed data |
| Phase 2: Intelligence | **COMPLETE** | 10/10 | 16 new | 36 | NLP, entity resolution, semantic search, KG, patents |
| Phase 3: Scale | **COMPLETE** | 12/12 | 30 new | 36 | Stream processing, Next.js dashboard, Redis, 6 Docker services |
| Phase 4: Deep Collection | NOT STARTED | 0/15 | ~14 new | ~30 | 12 new collectors, schema migration |
| Phase 5: Advanced Intelligence | NOT STARTED | 0/18 | ~18 new | ~36 | 16 new agents, graph queries, topic modeling |
| Phase 6: Operations | NOT STARTED | 0/16 | ~25 new | ~30 | Auth, API v2, webhooks, Dagster, monitoring stack |

**Overall: 30/79 sessions complete (38%)**

---

## Session Recap: Phases 1-3

### Phase 1 (b09d812): Foundation
- Composite scoring engine with time-decay, anomaly detection, feature attribution
- 4 collectors: SEC EDGAR, job postings, GitHub trends, funding events
- Signal normalization (SignalEnvelope), Kafka producer
- FastAPI server with 15 endpoints, WebSocket live dashboard
- Streamlit interactive dashboard (11 pages)
- Seed data: 35 failed startups, manufacturing failures, revival industries

### Phase 2 (2cf5eeb): Intelligence
- NLP pipeline: spaCy NER, entity extraction, embeddings, classification, summarization
- Entity resolver: Jaro-Winkler fuzzy matching with alias table
- Semantic search: Qdrant + Elasticsearch hybrid search
- Knowledge graph: 12 entity types, 20 relationship types
- 2 new collectors: Patent filings (USPTO), Social media (Reddit + HN)
- Elasticsearch full-text index, Qdrant vector store

### Phase 3 (d7bb6c2): Scale
- Bytewax 5-stage stream processing: Ingest → Enrich → Aggregate → Score → Output
- Dual-write collector pattern: MySQL (durable) + Kafka (real-time)
- Next.js dashboard: 8 pages (overview, radar, signals, graph, opportunities, sectors, search)
- Redis caching layer for API responses
- 6 Docker services: Redis, Redpanda, Qdrant, Elasticsearch, ClickHouse, TimescaleDB
- PipelineMetrics flushed to Redis every 30s

### Current State
| Metric | Count |
|--------|-------|
| Python files | 111 |
| Agents | 35 |
| Collectors | 12 |
| API endpoints | 23 |
| DB tables | 52 |
| Tests | 228 (all passing) |
| Frontend pages | 8 |
| Docker services | 12 |

---

## Architecture

```
Collectors (24) → Kafka Event Bus → Bytewax Stream → Enrich → Score → Alert
       │                                    │              │         │
       ▼                                    ▼              ▼         ▼
    MySQL          ClickHouse          Qdrant + ES    opportunity_scores
    (operational)  (OLAP analytics)    (search)        → dashboard + webhooks
                    TimescaleDB
                    (time-series)
```

---

## Phase 4: Deep Collection (Sessions 4.1 - 4.15)

**Goal**: Add 12 new data collectors, expand signal coverage to 24+ sources.

Sessions 4.1-4.11 are independent and can be done in any order.
Session 4.12 depends on 4.2 + 4.3.
Sessions 4.13-4.15 are sequential cleanup (schema migration, integration tests, commit).

| Session | Title | New Files | Modified Files | Dependencies |
|---------|-------|-----------|-----------------|--------------|
| 4.1 | GitHub Deep Collector | `collectors/github_deep_collector.py`, `tests/test_github_deep.py` | `agents/collection.py`, `config/settings.yaml` | None |
| 4.2 | Reddit Stream Collector | `collectors/reddit_stream_collector.py`, `tests/test_reddit_stream.py` | `agents/collection.py`, `config/settings.yaml` | None |
| 4.3 | HN Live Collector | `collectors/hn_live_collector.py`, `tests/test_hn_live.py` | `agents/collection.py`, `config/settings.yaml` | None |
| 4.4 | OpenCorporates Collector | `collectors/opencorporates_collector.py`, `tests/test_opencorporates.py` | `agents/collection.py`, `config/settings.yaml`, `db/schema.py` | None |
| 4.5 | arXiv Paper Signals | `collectors/arxiv_collector.py`, `tests/test_arxiv.py` | `agents/collection.py`, `config/settings.yaml`, `db/schema.py` | None |
| 4.6 | Product Hunt Launches | `collectors/producthunt_collector.py`, `tests/test_producthunt.py` | `agents/collection.py`, `config/settings.yaml`, `db/schema.py` | None |
| 4.7 | Website Monitor Collector | `collectors/website_monitor_collector.py`, `tests/test_website_monitor.py` | `agents/collection.py`, `config/settings.yaml`, `db/schema.py` | None |
| 4.8 | Twitter/X Signals | `collectors/twitter_collector.py`, `tests/test_twitter.py` | `agents/collection.py`, `config/settings.yaml` | None |
| 4.9 | Stack Overflow Adoption | `collectors/stackoverflow_collector.py`, `tests/test_stackoverflow.py` | `agents/collection.py`, `config/settings.yaml`, `db/schema.py` | None |
| 4.10 | NPM/PyPI Trends | `collectors/npm_pypi_collector.py`, `tests/test_npm_pypi.py` | `agents/collection.py`, `config/settings.yaml`, `db/schema.py` | None |
| 4.11 | Regulatory Filings | `collectors/regulatory_collector.py`, `tests/test_regulatory.py` | `agents/collection.py`, `config/settings.yaml`, `db/schema.py` | None |
| 4.12 | Newsletter Aggregation | `collectors/newsletter_collector.py`, `tests/test_newsletter.py` | `agents/collection.py`, `config/settings.yaml`, `db/schema.py` | 4.2, 4.3 |
| 4.13 | Schema Migration v14 | None | `db/schema.py`, `requirements.txt`, `agents/collection.py` | 4.1-4.12 |
| 4.14 | Phase 4 Integration Tests | `tests/test_phase4_integration.py` | None | 4.13 |
| 4.15 | Phase 4 Commit + Validation | None | `PROGRESS.yaml`, `ROADMAP.md` | 4.14 |

**Collector pattern**: Each extends `BaseCollector`, implements `name` + `collect(conn)`, dual-writes MySQL + Kafka via `self.publish_signal()`.

**New DB tables** (added in session 4.13): company_profiles, arxiv_papers, product_launches, website_snapshots, so_tag_stats, package_downloads, regulatory_filings, newsletter_items.

---

## Phase 5: Advanced Intelligence (Sessions 5.1 - 5.18)

**Goal**: Add 16 new analysis agents covering market sizing, competitive landscape, founder analysis, graph algorithms, and topic modeling.

| Session | Title | New Files | Modified Files | Dependencies |
|---------|-------|-----------|-----------------|--------------|
| 5.1 | Market Sizing Agent | `agents/market_sizing_agent.py`, `tests/test_market_sizing.py` | `agents/orchestrator.py`, `config/settings.yaml`, `db/schema.py` | None |
| 5.2 | Competitive Landscape | `agents/competitive_landscape_agent.py`, `tests/test_competitive_landscape.py` | `agents/orchestrator.py`, `db/schema.py` | 5.1 |
| 5.3 | Founder Background | `agents/founder_background_agent.py`, `tests/test_founder_background.py` | `agents/orchestrator.py`, `db/schema.py` | 4.4 |
| 5.4 | Technology Stack | `agents/technology_stack_agent.py`, `tests/test_tech_stack.py` | `agents/orchestrator.py` | 4.1, 4.9 |
| 5.5 | Moat Analyzer | `agents/moat_analyzer_agent.py`, `tests/test_moat_analyzer.py` | `agents/orchestrator.py` | 5.2, 5.4 |
| 5.6 | Timing Agent | `agents/timing_agent.py`, `tests/test_timing.py` | `agents/orchestrator.py` | 5.1 |
| 5.7 | Graph Traversal | `agents/graph_traversal_agent.py`, `tests/test_graph_traversal.py`, `db/graph_queries.py` | `agents/orchestrator.py` | None |
| 5.8 | Community Detector | `agents/community_detector_agent.py`, `tests/test_community_detector.py` | `agents/orchestrator.py` | 5.7 |
| 5.9 | Influence Propagation | `agents/influence_propagation_agent.py`, `tests/test_influence_propagation.py` | `agents/orchestrator.py` | 5.7, 5.8 |
| 5.10 | Temporal Graph | `agents/temporal_graph_agent.py`, `tests/test_temporal_graph.py` | `agents/orchestrator.py` | 5.7 |
| 5.11 | Topic Modeling | `agents/topic_modeling_agent.py`, `tests/test_topic_modeling.py` | `agents/orchestrator.py` | None |
| 5.12 | Relationship Extractor | `agents/relationship_extractor.py`, `tests/test_relationship_extractor.py` | `agents/orchestrator.py` | 5.11 |
| 5.13 | Trend Detector | `agents/trend_detector_agent.py`, `tests/test_trend_detector.py` | `agents/orchestrator.py` | 5.6 |
| 5.14 | Intent Classifier | `agents/intent_classifier_agent.py`, `tests/test_intent_classifier.py` | `agents/orchestrator.py` | 5.11 |
| 5.15 | Sector Rotation | `agents/sector_rotation_agent.py`, `tests/test_sector_rotation.py` | `agents/orchestrator.py` | 5.1, 5.6 |
| 5.16 | Cohort Analysis | `agents/cohort_analysis_agent.py`, `tests/test_cohort_analysis.py` | `agents/orchestrator.py` | 5.15 |
| 5.17 | Schema + Integration | `tests/test_phase5_integration.py` | `db/schema.py` (v15), `agents/orchestrator.py` | 5.1-5.16 |
| 5.18 | Commit + Validation | None | `PROGRESS.yaml`, `ROADMAP.md` | 5.17 |

---

## Phase 6: Operations (Sessions 6.1 - 6.16)

**Goal**: Add multi-tenancy, API versioning, webhooks, monitoring stack, and Dagster orchestration.

**Critical path**: 6.1 → 6.2 → 6.3 → 6.4 → 6.5 → 6.15 → 6.16

| Session | Title | New Files | Modified Files | Dependencies |
|---------|-------|-----------|-----------------|--------------|
| 6.1 | Auth Package (JWT + RBAC) | `auth/__init__.py`, `auth/jwt_handler.py`, `auth/rbac.py`, `tests/test_auth.py` | `requirements.txt` | None |
| 6.2 | Tenant Manager | `auth/tenant_manager.py`, `tests/test_tenant_manager.py` | `db/schema.py` (v16) | 6.1 |
| 6.3 | API v2 Router | `api/v2/__init__.py`, `api/v2/opportunities.py`, `api/v2/signals.py`, `tests/test_api_v2.py` | `api_server.py` | 6.1 |
| 6.4 | API v2 Webhooks + Export | `api/v2/webhooks.py`, `api/v2/export.py` | `api_server.py` | 6.3 |
| 6.5 | Webhook Dispatcher | `webhooks/__init__.py`, `webhooks/dispatcher.py`, `webhooks/templates.py`, `tests/test_webhooks.py` | `config/settings.yaml` | 6.4 |
| 6.6 | Collaboration Features | `collaboration/__init__.py`, `collaboration/annotations.py`, `collaboration/watchlists.py` | `db/schema.py`, `api_server.py` | 6.2 |
| 6.7 | Slack Integration Agent | `agents/slack_integration_agent.py`, `tests/test_slack_integration.py` | `agents/orchestrator.py` | 6.5 |
| 6.8 | Email Digest Agent | `agents/email_digest_agent.py`, `tests/test_email_digest.py` | `agents/orchestrator.py` | 6.5 |
| 6.9 | Export Agent | `agents/export_agent.py`, `tests/test_export_agent.py` | `agents/orchestrator.py` | 6.4 |
| 6.10 | Feed Generator Agent | `agents/feed_generator_agent.py`, `tests/test_feed_generator.py` | `agents/orchestrator.py` | 6.4 |
| 6.11 | Prometheus Metrics | `monitoring/__init__.py`, `monitoring/metrics.py`, `monitoring/health.py` | `api_server.py` | None |
| 6.12 | Data Quality Agent | `agents/data_quality_agent.py`, `tests/test_data_quality.py` | `agents/orchestrator.py` | None |
| 6.13 | Pipeline Health Agent | `agents/pipeline_health_agent.py`, `tests/test_pipeline_health.py` | `agents/orchestrator.py` | 6.11 |
| 6.14 | Cost Tracking Agent | `agents/cost_tracking_agent.py`, `tests/test_cost_tracking.py` | `agents/orchestrator.py` | 6.11 |
| 6.15 | Dagster Orchestration | `dagster/__init__.py`, `dagster/repository.py`, `dagster/ops/`, `dagster/schedules.py`, `tests/test_dagster_repo.py` | `docker-compose.yml`, `requirements.txt` | 6.13 |
| 6.16 | Final Commit + Deploy | None | `docker-compose.yml`, `PROGRESS.yaml`, `ROADMAP.md` | 6.1-6.15 |

---

## Dependency Graph

```
Phase 4:  4.1-4.11 (parallel) → 4.13 → 4.14 → 4.15
           4.12 (deps: 4.2, 4.3) ↗

Phase 5:  5.1 → 5.2 ────────────→ 5.5 (deps: 5.2, 5.4)
          5.1 → 5.6 → 5.13 → 5.15 → 5.16
          5.1, 5.6 → 5.15
          5.7 → 5.8 → 5.9
          5.7 → 5.10
          5.11 → 5.12, 5.14
          5.3 (deps: 4.4), 5.4 (deps: 4.1, 4.9)
          All → 5.17 → 5.18

Phase 6:  6.1 → 6.2 → 6.3 → 6.4 → 6.5 → {6.7, 6.8, 6.9, 6.10}
          6.2 → 6.6
          6.11 → {6.13, 6.14}
          6.12 (independent)
          All → 6.15 → 6.16
```

---

## Deviation Protocol

When a session needs to be changed:

| Type | When to Use | Command |
|------|-------------|---------|
| Skipped | Session no longer needed | `python -m agents.project_monitor --deviate 4.3 "Reason"` |
| Split | Session too large | `python -m agents.project_monitor --deviate 6.3 "Split" --replace 6.3a` |
| Merged | Two sessions combined | Log deviation for both, mark only one as complete |
| Reprioritized | Order changed | Log deviation, update dependencies |
| Added | New unplanned session | `python -m agents.project_monitor --plan-add --id "X.Y" --title "..."` |

---

## Target End State

| Metric | Current (Phase 3) | Target (Phase 6) |
|--------|-------------------|-----------------|
| Data sources | 12 | 24+ |
| Agents | 35 | 50+ |
| Collectors | 12 | 24 |
| API endpoints | 23 | 40+ |
| DB tables | 52 | 65+ |
| Docker services | 12 | 18 |
| Tests | 228 | 400+ |
| Storage engines | 5 | 7 |
| Orchestration | Cron + file locks | Dagster |
| Dashboard | Next.js + Streamlit | Production Next.js |
