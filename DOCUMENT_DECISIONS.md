# 📋 Document Decisions — Record of Requirements, Architecture, Setup, and Issues

> "The faintest ink is better than the best memory."
> "What isn't documented doesn't exist."

---

## Why This Document Exists

```
THIS IS THE SINGLE SOURCE OF TRUTH FOR EVERY DECISION MADE
IN THE OPPORTUNITY INTELLIGENCE PLATFORM.

Purpose:
  1. A new developer reads this and understands WHY everything is the way it is
  2. Six months from now, YOU read this and remember why you chose MySQL
  3. A contributor asks "why Bytewax?" and you point to ADR-005
  4. Someone debates changing FastAPI to Django — you show the decision record

Sections:
  Part 1: Requirements — what we're building and why
  Part 2: Architecture Decision Records (ADRs) — every major technology choice
  Part 3: Setup Instructions — how to get it running from zero
  Part 4: Known Issues — what's broken, what's deferred, what's accepted
  Part 5: Decision Log — chronological record of all decisions
```

---

## Part 1: Requirements

---

### 1.1 Product Requirements

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  PRODUCT VISION:                                                     │
│  An open-source, self-hosted, real-time, multi-agent alternative    │
│  to Crunchbase/PitchBook/Tracxn that scores startup opportunities   │
│  using AI and explains WHY with data.                                │
│                                                                      │
│  SOURCE: README.md, OPPORTUNITY_INTELLIGENCE_PLATFORM.md            │
│  DECIDED: May 25, 2026                                              │
│  DECIDER: Koduri Gokul                                               │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 1.2 Functional Requirements

| ID | Requirement | Source | Status | Priority |
|---|---|---|---|---|
| **FR-1** | Score any startup 0-100 with factor attribution | Core vision | ✅ Built | P0 |
| **FR-2** | AI chat answers questions about startup data | Core vision | ✅ Built | P0 |
| **FR-3** | Search startups by name, sector, geography | Core vision | ✅ Built | P0 |
| **FR-4** | Browse failure patterns by category | Core vision | ✅ Built | P0 |
| **FR-5** | Knowledge graph of entities and relationships | BUILD_PLAN.md | ✅ Built | P0 |
| **FR-6** | Collect data from 26 external sources | BUILD_PLAN.md | ✅ Built | P1 |
| **FR-7** | Real-time stream processing pipeline | ARCHITECTURE_PLAN.md | ✅ Built | P1 |
| **FR-8** | Risk scoring for each entity | BUILD_PLAN.md | ✅ Built | P1 |
| **FR-9** | Survival rate analysis (BLS data) | BUILD_PLAN.md | ✅ Built | P1 |
| **FR-10** | Competitive landscape analysis | BUILD_PLAN.md | ✅ Built | P2 |
| **FR-11** | Temporal knowledge graph (time-series) | BUILD_PLAN.md | ✅ Built | P2 |
| **FR-12** | Community detection in investment networks | BUILD_PLAN.md | ✅ Built | P2 |
| **FR-13** | Alert dispatch (Slack, Email) | BUILD_PLAN.md | 🔲 Planned | P1 |
| **FR-14** | Continuous collector scheduler (24/7) | BUILD_PLAN.md | 🔲 Planned | P1 |
| **FR-15** | WebSocket live score updates | BUILD_PLAN.md | 🔲 Planned | P1 |
| **FR-16** | Authentication (JWT + API keys) | BUILD_PLAN.md | 🔲 Planned | P2 |
| **FR-17** | Watchlists for tracked entities | BUILD_PLAN.md | 🔲 Planned | P2 |
| **FR-18** | PDF/CSV export | BUILD_PLAN.md | 🔲 Planned | P2 |
| **FR-19** | CRM integration (Salesforce) | BUILD_PLAN.md | 🔲 Planned | P3 |
| **FR-20** | HuggingFace MCP model selection | SOLUTION_DESIGN.md | 🔲 Planned | P3 |

### 1.3 Non-Functional Requirements

| ID | Requirement | Target | Current | Status |
|---|---|---|---|---|
| **NFR-1** | API response time (search) | p95 < 500ms | ~200ms | ✅ Met |
| **NFR-2** | API response time (score) | p95 < 2s | ~1s | ✅ Met |
| **NFR-3** | API response time (chat) | p95 < 30s | 5-15s (CPU) | ✅ Met |
| **NFR-4** | Test pass rate | 100% | 98.3% | ❌ 12 failing |
| **NFR-5** | Test count | 681+ | 699 | ✅ Met |
| **NFR-6** | Docker services up time | < 3 min | ~2 min | ✅ Met |
| **NFR-7** | Self-hosted (no cloud required) | 100% | 100% | ✅ Met |
| **NFR-8** | Open-source dependencies | 100% | 100% | ✅ Met |
| **NFR-9** | Score accuracy | ≥ 70% | Unknown ❌ | 🔲 Unmeasured |
| **NFR-10** | Concurrent users (MVP) | 10 | ~5 | ✅ Met |
| **NFR-11** | Data freshness | < 6 hours | ~12 hours | ⚠️ Partial |
| **NFR-12** | Security (no SQL injection) | 0 vulns | Unaudited | 🔲 Needs audit |

### 1.4 Scope Decisions

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  IN SCOPE (what we're building):                                     │
│                                                                      │
│  ✅ Startup scoring with AI explanations                             │
│  ✅ AI chat for startup intelligence                                 │
│  ✅ Failure pattern analysis                                         │
│  ✅ Knowledge graph of startup ecosystems                            │
│  ✅ Real-time data collection from public sources                    │
│  ✅ Self-hosted deployment (Docker)                                  │
│  ✅ Open-source (MIT license, planned)                              │
│  ✅ Multi-agent architecture                                         │
│  ✅ Semantic search (vector + keyword)                               │
│  ✅ Risk assessment per entity                                       │
│                                                                      │
│  SOURCE: BUILD_PLAN.md, MVP_PLAN.md                                 │
│  DECIDED: Ongoing since May 25, 2026                                │
│                                                                      │
│  OUT OF SCOPE (what we're NOT building):                             │
│                                                                      │
│  ❌ Mobile app (PWA possible in future)                              │
│  ❌ Multi-language support (English only for MVP)                    │
│  ❌ Real-time stock/crypto prices                                    │
│  ❌ Personal financial advice                                        │
│  ❌ Social network features                                          │
│  ❌ User-generated content / forums                                  │
│  ❌ White-label version (yet)                                        │
│  ❌ Desktop application                                              │
│  ❌ Browser extension                                                │
│  ❌ Native CRM replacement                                           │
│                                                                      │
│  SOURCE: BUILD_PLAN.md, PROBLEM_DEFINITION.md                       │
│  DECIDED: June 5, 2026                                              │
│  RATIONALE: Focus on core value prop (score + chat + patterns).     │
│             Everything else is distraction until validated.          │
│                                                                      │
│  AGENTS CUT (solving no user problem):                               │
│                                                                      │
│  ❌ LLMPortfolioAgent — no user needs LLM portfolio tracking        │
│  ❌ LLMPricingAgent — no user needs LLM price comparison            │
│  ❌ LLMBenchmarkAgent — no user needs LLM benchmarking              │
│  ❌ LLMCostOptimizerAgent — no user needs LLM cost optimization     │
│  ❌ SpanAgent — traces add no user-visible value                     │
│  ❌ ProjectMonitorAgent — internal health, not user-facing           │
│                                                                      │
│  SOURCE: PROBLEM_FEATURE_MAP.md                                     │
│  DECIDED: June 5, 2026                                              │
│  RATIONALE: 6 agents identified as solving no validated user         │
│             problem. Cutting reduces complexity and maintenance.     │
│                                                                      │
│  AGENTS MERGED:                                                      │
│                                                                      │
│  🔀 ReportAgent + ReportGeneratorAgent → single ReportAgent          │
│  🔀 InternetResearchAgent + AIAnalystAgent → single AIAnalystAgent   │
│  🔀 IntentClassifierAgent → replaced with keyword matching           │
│                                                                      │
│  SOURCE: PROBLEM_FEATURE_MAP.md                                     │
│  DECIDED: June 5, 2026                                              │
│  RATIONALE: Redundant functionality. Merging reduces agent count     │
│             from 60 to ~50 without losing capability.                │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Part 2: Architecture Decision Records (ADRs)

---

### ADR-001: Python 3.12 as Primary Language

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  DECISION:  Use Python 3.12+ as the sole programming language       │
│  DATE:      May 25, 2026                                            │
│  STATUS:    Accepted                                                 │
│  DECIDER:   Koduri Gokul                                            │
│                                                                      │
│  CONTEXT:                                                             │
│  The platform needs a language that supports:                        │
│  - AI/ML libraries (transformers, spacy, scikit-learn)              │
│  - Web framework (API server)                                        │
│  - Stream processing (Bytewax)                                       │
│  - Data processing (pandas, numpy)                                   │
│  - Rapid prototyping                                                 │
│                                                                      │
│  ALTERNATIVES CONSIDERED:                                            │
│  1. Python 3.12 ← CHOSEN                                            │
│     ✅ Best ML/AI ecosystem                                          │
│     ✅ str | None syntax (cleaner type hints)                        │
│     ✅ Performance improvements over 3.10/3.11                       │
│     ❌ Slower than Go/Rust for hot paths                             │
│                                                                      │
│  2. Go                                                                │
│     ✅ Fast, great for APIs                                          │
│     ✅ Small binaries, efficient                                     │
│     ❌ Weak ML/AI ecosystem                                          │
│     ❌ Would need Python bridge for ML anyway                        │
│                                                                      │
│  3. TypeScript/Node.js                                               │
│     ✅ Good for APIs                                                 │
│     ❌ Weak ML/AI ecosystem                                          │
│     ❌ Not ideal for data processing                                 │
│                                                                      │
│  CONSEQUENCES:                                                        │
│  + Single language across all components (API, agents, ML, stream)  │
│  + Largest ecosystem for AI/ML libraries                             │
│  + Easy to find contributors (Python is widely known)               │
│  - Performance ceiling lower than Go/Rust for CPU-bound work        │
│  - GIL limits true parallelism (mitigated by multiprocessing)       │
│                                                                      │
│  REVISIT: Not planned. Python is the right choice for this domain.  │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

### ADR-002: MySQL 8.0 as Primary Database

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  DECISION:  Use MySQL 8.0 as the primary relational database        │
│  DATE:      May 25, 2026                                            │
│  STATUS:    Accepted                                                 │
│  DECIDER:   Koduri Gokul                                            │
│                                                                      │
│  CONTEXT:                                                             │
│  The platform needs a relational database to store:                  │
│  - 76 tables of startup data, scores, signals, entities              │
│  - Relationships between entities (knowledge graph)                  │
│  - Configuration and metadata                                        │
│                                                                      │
│  ALTERNATIVES CONSIDERED:                                            │
│  1. MySQL 8.0 ← CHOSEN                                              │
│     ✅ Used from the start (original research report used MySQL)     │
│     ✅ Wide ecosystem, well-understood                               │
│     ✅ Good enough for current scale (100-10K entities)              │
│     ✅ Docker image available, easy to run                           │
│     ❌ Less advanced JSON support than PostgreSQL                    │
│     ❌ No native vector search (need Qdrant separately)              │
│                                                                      │
│  2. PostgreSQL + pgvector                                            │
│     ✅ Better JSON support, extensions                               │
│     ✅ pgvector could replace Qdrant                                 │
│     ✅ More advanced query optimizer                                 │
│     ❌ Would require rewriting all SQL queries                       │
│     ❌ Migration cost > benefit at current scale                     │
│                                                                      │
│  3. SQLite                                                           │
│     ✅ Simple, no server needed                                      │
│     ❌ Can't handle concurrent writes                                │
│     ❌ No real full-text search                                      │
│     ❌ Not suitable for multi-service Docker setup                   │
│                                                                      │
│  CONSEQUENCES:                                                        │
│  + No migration needed (started with MySQL)                          │
│  + Well-supported by PyMySQL driver                                  │
│  - Need separate Qdrant for vector search                            │
│  - Need separate Elasticsearch for advanced full-text search         │
│  - MySQL-specific SQL may limit future portability                   │
│                                                                      │
│  REVISIT: If we need vector search in DB, consider PostgreSQL +     │
│           pgvector. But only if Qdrant becomes a bottleneck.        │
│           Not worth migrating 76 tables for marginal benefit.       │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

### ADR-003: FastAPI as Web Framework

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  DECISION:  Use FastAPI for the API server                           │
│  DATE:      May 25, 2026                                            │
│  STATUS:    Accepted                                                 │
│  DECIDER:   Koduri Gokul                                            │
│                                                                      │
│  CONTEXT:                                                             │
│  The platform needs an API server that serves:                       │
│  - 34 REST endpoints (search, score, chat, data)                     │
│  - WebSocket connections (real-time score push)                      │
│  - Static files (dashboard HTML/CSS/JS)                              │
│  - AI chat (long-running streaming responses)                        │
│                                                                      │
│  ALTERNATIVES CONSIDERED:                                            │
│  1. FastAPI ← CHOSEN                                                 │
│     ✅ Async/await native (fast for I/O-bound work)                  │
│     ✅ Auto-generated OpenAPI/Swagger docs                           │
│     ✅ Type hints built-in (Pydantic validation)                     │
│     ✅ WebSocket support built-in                                    │
│     ✅ High performance (comparable to Node.js/Go)                   │
│     ❌ Younger ecosystem than Flask/Django                           │
│                                                                      │
│  2. Flask                                                            │
│     ✅ Mature, huge ecosystem                                        │
│     ❌ No native async (needs Flask 2.0+ with async)                 │
│     ❌ No auto-generated docs                                        │
│     ❌ WebSocket requires extensions                                 │
│                                                                      │
│  3. Django                                                           │
│     ✅ Batteries-included (ORM, admin, auth)                         │
│     ❌ Too heavy for an API-only service                             │
│     ❌ ORM would conflict with raw SQL used in agents                │
│     ❌ Overkill for our needs                                        │
│                                                                      │
│  CONSEQUENCES:                                                        │
│  + Fast, async API with < 200ms response times                      │
│  + Auto-generated API docs at /docs                                  │
│  + WebSocket support for real-time features                          │
│  + Type-safe request/response with Pydantic                          │
│  - Requires Python 3.8+ (not a problem — we use 3.12)              │
│                                                                      │
│  REVISIT: No. FastAPI is the right choice.                           │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

### ADR-004: Ollama for Local LLM Inference

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  DECISION:  Use Ollama for local LLM inference (not OpenAI API)     │
│  DATE:      May 25, 2026                                            │
│  STATUS:    Accepted (with planned HuggingFace MCP fallback)         │
│  DECIDER:   Koduri Gokul                                            │
│                                                                      │
│  CONTEXT:                                                             │
│  The platform needs LLM inference for:                               │
│  - AI chat ("Why did X fail?")                                       │
│  - Summarization of news/signals                                     │
│  - Knowledge graph enrichment                                        │
│  - Report generation                                                 │
│                                                                      │
│  ALTERNATIVES CONSIDERED:                                            │
│  1. Ollama (local llama3:8b) ← CHOSEN                               │
│     ✅ Free (zero API cost)                                          │
│     ✅ Private (no data leaves the machine)                          │
│     ✅ Self-hosted (no vendor dependency)                            │
│     ✅ Simple Docker deployment                                      │
│     ✅ Works offline                                                 │
│     ❌ CPU-only is slow (5-15s per response)                         │
│     ❌ Quality lower than GPT-4                                      │
│     ❌ No cloud fallback if local model fails                        │
│                                                                      │
│  2. OpenAI API (GPT-4/3.5)                                          │
│     ✅ Best quality                                                  │
│     ✅ Fast API responses                                            │
│     ❌ Costs $0.03-0.06 per 1K tokens                               │
│     ❌ Data sent to third party                                      │
│     ❌ Requires internet connection                                  │
│     ❌ Vendor dependency                                             │
│     ❌ Rate limits (3 RPM on free tier)                              │
│                                                                      │
│  3. HuggingFace Inference API (planned fallback)                    │
│     ✅ Free tier (1,000 requests/hour)                               │
│     ✅ Access to 500K+ models                                        │
│     ❌ Requires internet                                             │
│     ❌ Rate limited                                                  │
│                                                                      │
│  CONSEQUENCES:                                                        │
│  + Zero API cost (important for open-source, free product)           │
│  + Full privacy (self-hosted = data never leaves)                    │
│  + Works offline                                                     │
│  - Slow on CPU (5-15s per chat response)                            │
│  - Lower quality than GPT-4                                          │
│  - No fallback when Ollama crashes (FIX: add graceful degradation)  │
│                                                                      │
│  REVISIT: HuggingFace MCP integration planned (SOLUTION_DESIGN.md   │
│           Part 6) for cloud fallback + dynamic model selection.     │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

### ADR-005: Bytewax for Stream Processing

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  DECISION:  Use Bytewax for real-time stream processing              │
│  DATE:      June 1, 2026 (Phase 3)                                  │
│  STATUS:    Accepted                                                 │
│  DECIDER:   Koduri Gokul                                            │
│                                                                      │
│  CONTEXT:                                                             │
│  The platform needs stream processing for:                           │
│  - Real-time signal enrichment (NER, sentiment, classification)     │
│  - Score computation on new signals                                  │
│  - Alert triggering on score changes                                 │
│  - Metric aggregation                                                │
│                                                                      │
│  ALTERNATIVES CONSIDERED:                                            │
│  1. Bytewax ← CHOSEN                                                 │
│     ✅ Python-native (same language as all other code)               │
│     ✅ Simpler than Flink/Spark (fewer concepts to learn)            │
│     ✅ Good Kafka integration                                        │
│     ✅ Stateful processing with recovery                             │
│     ❌ Smaller community than Flink/Spark                            │
│     ❌ Less battle-tested at massive scale                           │
│                                                                      │
│  2. Apache Flink                                                     │
│     ✅ Industry standard for stream processing                       │
│     ✅ Massive scale proven                                          │
│     ❌ Java-based (would need Python bridge via PyFlink)             │
│     ❌ Complex setup and operations                                  │
│     ❌ Overkill for our current scale                                │
│                                                                      │
│  3. Apache Spark Structured Streaming                                │
│     ✅ Good for batch + streaming combined                           │
│     ❌ Heavier infrastructure requirements                           │
│     ❌ Higher latency than Bytewax for real-time                     │
│     ❌ JVM-based (same Python bridge problem)                        │
│                                                                      │
│  CONSEQUENCES:                                                        │
│  + Single language (Python) for stream + API + agents                │
│  + Simpler operations (one less JVM service to manage)               │
│  + Good enough for our scale (< 100K messages/second)               │
│  - Smaller community = fewer StackOverflow answers                   │
│  - If we outgrow Bytewax, migration to Flink would be significant   │
│                                                                      │
│  REVISIT: Only if Bytewax can't handle > 100K msg/sec.              │
│           Current throughput is < 1K msg/sec — not a concern.       │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

### ADR-006: Kappa Architecture (not Lambda)

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  DECISION:  Use Kappa architecture (single stream pipeline)          │
│             instead of Lambda architecture (separate batch + stream) │
│  DATE:      June 1, 2026 (Phase 3 design)                           │
│  STATUS:    Accepted                                                 │
│  DECIDER:   Koduri Gokul                                            │
│  SOURCE:    ARCHITECTURE_PLAN.md, SOLUTION_DESIGN.md                 │
│                                                                      │
│  CONTEXT:                                                             │
│  The platform processes both:                                        │
│  - Real-time signals (news, social media, job postings)              │
│  - Batch data (BLS survival rates, historical failures)              │
│                                                                      │
│  ALTERNATIVES CONSIDERED:                                            │
│  1. Kappa Architecture ← CHOSEN                                      │
│     ✅ One pipeline for both real-time and batch                     │
│     ✅ Simpler to maintain (one code path)                            │
│     ✅ Batch is just "replay the stream from the beginning"          │
│     ✅ Less infrastructure (no separate batch cluster)               │
│     ❌ Batch processing slower than dedicated batch system           │
│                                                                      │
│  2. Lambda Architecture                                              │
│     ✅ Separate optimization for batch and stream                    │
│     ✅ Batch layer handles historical data well                      │
│     ❌ Two code paths to maintain (batch + stream)                   │
│     ❌ Two infrastructure stacks                                     │
│     ❌ Complex to ensure consistency between layers                  │
│     ❌ More operational overhead for solo developer                  │
│                                                                      │
│  CONSEQUENCES:                                                        │
│  + Simpler codebase (stream/pipeline.py handles everything)          │
│  + Easier to debug (one pipeline to trace)                           │
│  + Less infrastructure cost                                          │
│  - Re-processing historical data means replaying the Kafka topic    │
│                                                                      │
│  REVISIT: No. Kappa is the right choice for our scale and team size. │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

### ADR-007: Redpanda (Kafka-compatible) for Event Streaming

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  DECISION:  Use Redpanda (Kafka-compatible) instead of Apache Kafka │
│  DATE:      June 1, 2026                                            │
│  STATUS:    Accepted                                                 │
│  DECIDER:   Koduri Gokul                                            │
│                                                                      │
│  CONTEXT:                                                             │
│  The platform needs event streaming for:                             │
│  - Decoupling collectors from processors                             │
│  - Replay capability (re-process signals)                            │
│  - Pub/sub for alert dispatching                                     │
│  - Score update propagation to WebSocket                             │
│                                                                      │
│  ALTERNATIVES CONSIDERED:                                            │
│  1. Redpanda (Kafka API compatible) ← CHOSEN                        │
│     ✅ Single binary (no JVM, no ZooKeeper)                          │
│     ✅ Kafka-compatible API (uses kafka-python-ng client)            │
│     ✅ Lower memory footprint                                        │
│     ✅ Faster startup time                                           │
│     ✅ Simpler Docker deployment                                     │
│     ❌ Less battle-tested than Apache Kafka                          │
│                                                                      │
│  2. Apache Kafka                                                     │
│     ✅ Industry standard                                            │
│     ✅ Massive scale proven                                          │
│     ❌ JVM-based (heavier resource usage)                            │
│     ❌ Requires ZooKeeper (or KRaft — complex setup)                │
│     ❌ Slower Docker startup                                         │
│                                                                      │
│  3. RabbitMQ                                                         │
│     ✅ Simpler than Kafka                                            │
│     ❌ No replay capability (messages deleted after ack)             │
│     ❌ Not designed for event streaming                              │
│     ❌ No partitioning for parallel processing                      │
│                                                                      │
│  CONSEQUENCES:                                                        │
│  + Lighter infrastructure (no JVM overhead)                          │
│  + Kafka-compatible (can switch to real Kafka if needed)             │
│  - Redpanda specific behavior may differ from Kafka edge cases      │
│                                                                      │
│  REVISIT: If Redpanda has issues, can swap to Apache Kafka with     │
│           zero code changes (same Kafka API).                        │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

### ADR-008: Qdrant for Vector Search

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  DECISION:  Use Qdrant for vector similarity search                  │
│  DATE:      June 1, 2026 (Phase 2)                                  │
│  STATUS:    Accepted                                                 │
│  DECIDER:   Koduri Gokul                                            │
│                                                                      │
│  CONTEXT:                                                             │
│  The platform needs vector search for:                               │
│  - Semantic search ("AI companies that failed in 2024")             │
│  - Entity resolution (is "Tesla" same as "Tesla Motors"?)           │
│  - Similarity search (find startups like "Fisker")                  │
│                                                                      │
│  ALTERNATIVES CONSIDERED:                                            │
│  1. Qdrant ← CHOSEN                                                  │
│     ✅ Open-source, self-hosted                                      │
│     ✅ Fast (Rust-based)                                             │
│     ✅ Good Python SDK (qdrant-client)                               │
│     ✅ Docker image available                                        │
│     ✅ Supports filtering + vector search combined                   │
│                                                                      │
│  2. Pinecone                                                         │
│     ✅ Managed (no ops)                                              │
│     ❌ Cloud-only (conflicts with self-hosted philosophy)            │
│     ❌ Paid for production use                                       │
│     ❌ Vendor lock-in                                                │
│                                                                      │
│  3. Weaviate                                                         │
│     ✅ Open-source, self-hosted                                      │
│     ❌ JVM-based (heavier resource usage)                            │
│     ❌ More complex setup                                            │
│     ❌ Slower than Qdrant in benchmarks                              │
│                                                                      │
│  4. PostgreSQL + pgvector                                            │
│     ✅ Would eliminate need for separate service                     │
│     ❌ Would require migrating from MySQL to PostgreSQL              │
│     ❌ pgvector less mature than Qdrant                              │
│                                                                      │
│  CONSEQUENCES:                                                        │
│  + Fast vector search with filtering                                 │
│  + Self-hosted, no vendor dependency                                 │
│  - One more Docker service to manage                                 │
│  - Vector dimensions fixed at index creation (384 for MiniLM)       │
│                                                                      │
│  REVISIT: If we migrate to PostgreSQL, could consolidate to          │
│           pgvector and remove Qdrant. Not planned.                   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

### ADR-009: sentence-transformers/all-MiniLM-L6-v2 for Embeddings

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  DECISION:  Use all-MiniLM-L6-v2 for text embeddings                │
│  DATE:      June 1, 2026 (Phase 2)                                  │
│  STATUS:    Accepted (with planned upgrade via HuggingFace MCP)     │
│  DECIDER:   Koduri Gokul                                            │
│                                                                      │
│  CONTEXT:                                                             │
│  The platform needs text embeddings for:                             │
│  - Semantic search (query → similar documents)                       │
│  - Entity resolution (name similarity)                               │
│  - Clustering (group similar startups)                               │
│                                                                      │
│  ALTERNATIVES CONSIDERED:                                            │
│  1. all-MiniLM-L6-v2 ← CHOSEN                                       │
│     ✅ Small (~80MB)                                                 │
│     ✅ Fast (384-dimensional, smaller index)                          │
│     ✅ Good quality for general English text                         │
│     ✅ Free, runs locally                                            │
│     ❌ Not the best quality (newer models are better)                │
│                                                                      │
│  2. OpenAI text-embedding-3-small                                    │
│     ✅ Better quality (1536-dimensional)                             │
│     ❌ Costs $0.02 per 1M tokens (adds up at scale)                 │
│     ❌ Requires internet                                             │
│     ❌ Vendor dependency                                             │
│     ❌ 1536-dim = larger Qdrant index (4x storage)                   │
│                                                                      │
│  3. BAAI/bge-small-en-v1.5                                           │
│     ✅ Better quality than MiniLM, same size (384-dim)              │
│     ✅ Free, runs locally                                            │
│     ❌ Not yet integrated (planned via HuggingFace MCP)              │
│                                                                      │
│  CONSEQUENCES:                                                        │
│  + Small model size (80MB) runs on any machine                       │
│  + 384-dim vectors are efficient to store and search                 │
│  - Quality ceiling lower than 768/1024-dim models                   │
│  - Upgrading requires re-embedding all documents                     │
│                                                                      │
│  REVISIT: HuggingFace MCP (SOLUTION_DESIGN.md Part 6) will allow   │
│           dynamic model selection. BAAI/bge-small-en-v1.5 is the    │
│           likely upgrade path (same dims, better quality).           │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

### ADR-010: spaCy for Named Entity Recognition

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  DECISION:  Use spaCy en_core_web_sm for NER                         │
│  DATE:      June 1, 2026 (Phase 2)                                  │
│  STATUS:    Accepted (with planned upgrade path to BERT-NER)        │
│  DECIDER:   Koduri Gokul                                            │
│                                                                      │
│  CONTEXT:                                                             │
│  The platform needs NER for:                                         │
│  - Extracting company names from news articles                       │
│  - Identifying people, products, locations in text                   │
│  - Building knowledge graph entities                                 │
│                                                                      │
│  ALTERNATIVES CONSIDERED:                                            │
│  1. spaCy en_core_web_sm ← CHOSEN                                   │
│     ✅ Very small (~12MB)                                            │
│     ✅ Very fast (< 10ms per document)                               │
│     ✅ Good enough for company/entity extraction                     │
│     ✅ Easy to extend with custom patterns                           │
│     ❌ F1 = 0.83 (not state-of-the-art)                              │
│                                                                      │
│  2. HuggingFace BERT-NER (dslim/bert-base-NER)                      │
│     ✅ Much better F1 = 0.92                                         │
│     ✅ Better at complex entity boundaries                           │
│     ❌ Large (~440MB)                                                │
│     ❌ Slow (~200ms per document on CPU)                             │
│     ❌ May need GPU for production use                               │
│                                                                      │
│  CONSEQUENCES:                                                        │
│  + Lightweight and fast                                              │
│  + Custom patterns added for PATENT, PRODUCT entities                │
│  - May miss some entity mentions (F1 = 0.83)                        │
│ - Users with GPU can upgrade to BERT-NER (planned via MCP)          │
│                                                                      │
│  REVISIT: HuggingFace MCP will allow dynamic NER model selection.   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

### ADR-011: Docker Compose for Deployment

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  DECISION:  Use Docker Compose for local and production deployment   │
│  DATE:      May 25, 2026                                            │
│  STATUS:    Accepted                                                 │
│  DECIDER:   Koduri Gokul                                            │
│                                                                      │
│  CONTEXT:                                                             │
│  The platform has 11+ services that need to run together:            │
│  MySQL, Ollama, FastAPI, Streamlit, Redis, Kafka/Redpanda,          │
│  Qdrant, Elasticsearch, ClickHouse, TimescaleDB, Pipeline            │
│                                                                      │
│  ALTERNATIVES CONSIDERED:                                            │
│  1. Docker Compose ← CHOSEN                                         │
│     ✅ Simple (one file defines everything)                          │
│     ✅ Reproducible (same config everywhere)                         │
│     ✅ Good for single-host deployment (MVP)                         │
│     ✅ Easy to understand and modify                                 │
│     ❌ Not designed for multi-host orchestration                     │
│     ❌ No auto-scaling                                               │
│                                                                      │
│  2. Kubernetes                                                       │
│     ✅ Production-grade orchestration                                │
│     ✅ Auto-scaling, self-healing                                    │
│     ❌ Massive overkill for MVP (10 concurrent users)               │
│     ❌ Steep learning curve                                          │
│     ❌ More complex CI/CD                                            │
│     ❌ Higher infrastructure cost                                    │
│                                                                      │
│  3. Manual installation                                              │
│     ❌ Not reproducible                                              │
│     ❌ Difficult to maintain                                         │
│     ❌ Different on every machine                                    │
│                                                                      │
│  CONSEQUENCES:                                                        │
│  + One command: docker compose up -d                                 │
│  + Works on any machine with Docker                                  │
│  + Easy to add/remove services                                       │
│  - Single-host limitation (mitigated by vertical scaling)            │
│  - No auto-scaling (not needed for MVP)                              │
│                                                                      │
│  REVISIT: Kubernetes for V3+ if we need multi-host, auto-scaling.   │
│           Docker Compose is fine for < 1,000 concurrent users.      │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Part 3: Setup Instructions

---

### 3.1 Prerequisites

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  REQUIREMENT         VERSION    HOW TO CHECK                        │
│  ────────────────────────────────────────────────────────────────    │
│  Python               3.12+     python3 --version                   │
│  Docker               24+       docker --version                    │
│  Docker Compose       2.20+     docker compose version              │
│  Git                  2.30+     git --version                        │
│  Disk space           10 GB+    df -h                                │
│  RAM                  8 GB+     (16 GB recommended for Ollama)      │
│  CPU                  4+ cores  (8+ recommended for Ollama)         │
│                                                                      │
│  SOURCE: README.md, DEPLOYMENT_GUIDE.md                             │
│  LAST VERIFIED: June 5, 2026                                        │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.2 Quick Start (5 Minutes)

```bash
# 1. Clone the repository
git clone https://github.com/gokul-koduri/start.git
cd start

# 2. Create environment file
cp .env.example .env
# Edit .env with your values (see .env section below)

# 3. Start all services
docker compose up -d

# 4. Wait for services to be healthy (~2-3 minutes)
docker compose ps  # All services should show "healthy"

# 5. Seed the database with initial data
docker compose exec api python seed_data.py

# 6. Open the platform
# API:          http://localhost:8000
# Dashboard:    http://localhost:8000/site/
# API docs:     http://localhost:8000/docs
# Streamlit:    http://localhost:8501

# 7. Run collectors to get live data
docker compose exec api python run_collectors.py --all

# 8. Run scoring pipeline
docker compose exec api python run_agent.py --pipeline analysis

# 9. Try it!
# Score a startup:
curl -X POST http://localhost:8000/api/score-a-startup \
  -H "Content-Type: application/json" \
  -d '{"company_name": "Fisker"}'

# Search:
curl http://localhost:8000/api/search?q=tesla

# AI Chat:
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Why did Juicero fail?"}'
```

### 3.3 Environment Variables

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  FILE: .env (required for Docker Compose)                           │
│                                                                      │
│  VARIABLE              REQUIRED   DEFAULT                DESCRIPTION │
│  ────────────────────────────────────────────────────────────────    │
│  MYSQL_HOST             Yes       localhost              DB host     │
│  MYSQL_PORT             Yes       3306                   DB port     │
│  MYSQL_USER             Yes       root                   DB user     │
│  MYSQL_PASSWORD         Yes       startup2024            DB password │
│  MYSQL_DATABASE         Yes       startup_research       DB name     │
│  BLS_API_KEY            No        (empty)                BLS data    │
│  GITHUB_TOKEN           No        (empty)                GitHub API  │
│  GITHUB_REPO            No        (empty)                For deploy  │
│  OLLAMA_URL             No        http://ollama:11434    LLM server  │
│  REDIS_URL              No        redis://redis:6379/0   Cache       │
│  KAFKA_BOOTSTRAP_SERVERS No       kafka:9092             Streaming   │
│  LOG_LEVEL              No        INFO                   Logging     │
│                                                                      │
│  SECURITY NOTE:                                                      │
│  ✅ .env is in .gitignore (never committed)                         │
│  ✅ Config uses ${VAR} references (not hardcoded secrets)            │
│  ❌ Default passwords in docker-compose.yml should be changed        │
│                                                                      │
│  SOURCE: .env, docker-compose.yml, config/settings.yaml             │
│  LAST UPDATED: June 5, 2026                                         │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.4 Port Allocations

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  SERVICE          PORT     URL                                    │
│  ────────────────────────────────────────────────────────────────    │
│  FastAPI API       8000     http://localhost:8000                   │
│  Streamlit         8501     http://localhost:8501                   │
│  MySQL             3306     mysql://localhost:3306                  │
│  Ollama            11434    http://localhost:11434                  │
│  Redis             6379     redis://localhost:6379                  │
│  Kafka/Redpanda    9092     kafka://localhost:9092                  │
│  Kafka Admin       9000     http://localhost:9000                   │
│  Qdrant HTTP       6333     http://localhost:6333                   │
│  Qdrant gRPC       6334     localhost:6334                          │
│  Elasticsearch     9200     http://localhost:9200                   │
│  ClickHouse        8123     http://localhost:8123                   │
│  TimescaleDB       5433     postgresql://localhost:5433              │
│                                                                      │
│  DECISION: These ports are chosen to avoid common conflicts.        │
│  TimescaleDB uses 5433 (not default 5432) to avoid PostgreSQL      │
│  conflicts on developer machines.                                   │
│                                                                      │
│  SOURCE: docker-compose.yml                                         │
│  LAST UPDATED: June 5, 2026                                         │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.5 Docker Services (11 total)

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  SERVICE            PURPOSE                    STATUS    REQUIRED    │
│  ────────────────────────────────────────────────────────────────    │
│  mysql              Primary database (76 tables)   ✅        YES     │
│  ollama             Local LLM inference           ✅        YES     │
│  api                FastAPI server (34 endpoints)  ✅        YES     │
│  redis              Caching + metrics              ✅        YES     │
│  streamlit          Interactive dashboard          ✅        NO      │
│  pipeline           Cron-based agent pipeline      ✅        NO      │
│  stream_processor   Bytewax real-time processing   ✅        NO      │
│  kafka (Redpanda)   Event streaming                ✅        NO      │
│  qdrant             Vector search                  ✅        NO      │
│  elasticsearch      Full-text search               ✅        NO      │
│  clickhouse         OLAP analytics                 ✅        NO      │
│  timescaledb        Time-series metrics            ✅        NO      │
│                                                                      │
│  DECISION: Only MySQL + Ollama + FastAPI + Redis are required       │
│  for MVP. Everything else is optional and gracefully degraded.      │
│                                                                      │
│  SOURCE: docker-compose.yml, DEPLOYMENT_GUIDE.md                    │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Part 4: Known Issues

---

### 4.1 Critical Issues (Fix Before Launch)

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  ISSUE #    DESCRIPTION                          SEVERITY   STATUS   │
│  ────────────────────────────────────────────────────────────────    │
│                                                                      │
│  KI-001     12 failing tests in                    HIGH      OPEN    │
│             test_semantic_search.py                                  │
│             CAUSE: Likely import/interface change after               │
│                    refactoring between phases                         │
│             IMPACT: Test suite is not clean, blocks CI               │
│             FIX: Update test expectations to match new               │
│                  VectorStore/SearchIndex interface                    │
│             EFFORT: 2-4 hours                                       │
│             SOURCE: Found during TESTING_STRATEGY.md audit           │
│             DATE: June 5, 2026                                      │
│                                                                      │
│  KI-002     No database backup system               CRITICAL  OPEN   │
│             CAUSE: Never implemented                                 │
│             IMPACT: Data loss if MySQL crashes or docker             │
│                    volumes are deleted                                │
│             FIX: Add scripts/backup_db.sh + cron + S3               │
│             EFFORT: 1 hour                                          │
│             SOURCE: RISK_MANAGEMENT.md R1                            │
│             DATE: June 5, 2026                                      │
│                                                                      │
│  KI-003     No LICENSE file                         HIGH      OPEN    │
│             CAUSE: Never created                                     │
│             IMPACT: Cannot accept contributions, legal ambiguity     │
│             FIX: Create LICENSE file (MIT)                           │
│             EFFORT: 15 minutes                                      │
│             SOURCE: RISK_MANAGEMENT.md                               │
│             DATE: June 5, 2026                                      │
│                                                                      │
│  KI-004     Score accuracy never measured          CRITICAL  OPEN    │
│             CAUSE: Built without validation                          │
│             IMPACT: Core product may be wrong                        │
│             FIX: Score 20 known startups, measure accuracy           │
│             EFFORT: 2-3 hours                                       │
│             SOURCE: RISK_MANAGEMENT.md R2                            │
│             DATE: June 5, 2026                                      │
│                                                                      │
│  KI-005     45 untracked files in Git              HIGH      OPEN    │
│             CAUSE: Files created by AI assistant never               │
│                    staged/committed                                   │
│             IMPACT: 600KB+ docs + 22 source files at risk of loss   │
│             FIX: git add -A && git commit && git push                │
│             EFFORT: 10 minutes                                      │
│             SOURCE: VERSION_CONTROL.md audit                         │
│             DATE: June 5, 2026                                      │
│                                                                      │
│  KI-006     No rate limiting on API endpoints      HIGH      OPEN    │
│             CAUSE: Not implemented for MVP simplicity                │
│             IMPACT: Anyone can DoS the API with 10K requests        │
│             FIX: Add slowapi or FastAPI RateLimiter middleware       │
│             EFFORT: 1 hour                                          │
│             SOURCE: RISK_MANAGEMENT.md R6                            │
│             DATE: June 5, 2026                                      │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 4.2 Medium Issues (Fix Before V1)

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  KI-007     35 hardcoded "localhost" references    MEDIUM    OPEN    │
│             CAUSE: Convenience during development                    │
│             IMPACT: Breaks when deployed to a server                 │
│             FIX: Replace with ${HOST} or config values               │
│             FILES: ingestion/kafka_producer.py, stream/metrics.py,  │
│                    stream/pipeline.py, streamlit_app.py, agents/*    │
│             EFFORT: 3-4 hours                                       │
│             DATE: June 5, 2026                                      │
│                                                                      │
│  KI-008     No Ollama cloud fallback               MEDIUM    OPEN    │
│             CAUSE: Only local Ollama configured                      │
│             IMPACT: Chat breaks when Ollama is down                  │
│             FIX: Add HuggingFace Inference API fallback              │
│             EFFORT: 4-6 hours (SOLUTION_DESIGN.md Part 6)          │
│             DATE: June 5, 2026                                      │
│                                                                      │
│  KI-009     52 agents without test files           MEDIUM    OPEN    │
│             CAUSE: Agents built faster than tests written            │
│             IMPACT: No regression protection for 86% of agents      │
│             FIX: Write tests (68 API + 15 scorer + 54 agents)       │
│             EFFORT: 28 hours (TESTING_STRATEGY.md)                  │
│             DATE: June 5, 2026                                      │
│                                                                      │
│  KI-010     api_server.py has 0 tests              MEDIUM    OPEN    │
│             CAUSE: Never written                                     │
│             IMPACT: API changes may break endpoints silently         │
│             FIX: Create tests/test_api_endpoints.py (68 tests)      │
│             EFFORT: 4-6 hours                                       │
│             DATE: June 5, 2026                                      │
│                                                                      │
│  KI-011     db/schema.py has 0 tests               MEDIUM    OPEN    │
│             CAUSE: Never written                                     │
│             IMPACT: Schema migrations may break silently             │
│             FIX: Create tests/test_schema.py (10 tests)             │
│             EFFORT: 2 hours                                         │
│             DATE: June 5, 2026                                      │
│                                                                      │
│  KI-012     CI runs pipeline but NOT tests         MEDIUM    OPEN    │
│             CAUSE: test.yml workflow doesn't exist                   │
│             IMPACT: Broken code can be pushed to main                │
│             FIX: Create .github/workflows/test.yml                   │
│             EFFORT: 1 hour                                          │
│             DATE: June 5, 2026                                      │
│                                                                      │
│  KI-013     No .env.example file                   MEDIUM    OPEN    │
│             CAUSE: Never created                                     │
│             IMPACT: New users don't know what env vars to set        │
│             FIX: Create .env.example with all variables listed       │
│             EFFORT: 15 minutes                                      │
│             DATE: June 5, 2026                                      │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 4.3 Low Issues (Accepted / Deferred)

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  KI-014     3 deprecation warnings                  LOW     ACCEPT   │
│             (datetime.utcnow in jwt_handler.py,                      │
│              signal_normalizer.py)                                    │
│             FIX: Replace with datetime.now(datetime.UTC)             │
│             EFFORT: 15 minutes                                      │
│             ACCEPTED: Not breaking, just warnings                    │
│                                                                      │
│  KI-015     6 agents should be CUT                  LOW    PLANNED   │
│             (LLMPortfolioAgent, LLMPricingAgent, etc.)               │
│             SOURCE: PROBLEM_FEATURE_MAP.md audit                     │
│             EFFORT: 2 hours to remove cleanly                       │
│             DEFERRED: Post-MVP cleanup                               │
│                                                                      │
│  KI-016     4 agents should be MERGED               LOW    PLANNED   │
│             (ReportAgent+ReportGeneratorAgent, etc.)                 │
│             SOURCE: PROBLEM_FEATURE_MAP.md audit                     │
│             EFFORT: 4 hours to merge and update tests               │
│             DEFERRED: Post-MVP cleanup                               │
│                                                                      │
│  KI-017     No API versioning                       LOW    ACCEPT    │
│             All endpoints at /api/* (no /v1/ prefix)                 │
│             FIX: Add /v1/ prefix to all routes                       │
│             ACCEPTED: Not needed until we have external API users   │
│                                                                      │
│  KI-018     No type checking (mypy)                 LOW    ACCEPT    │
│             FIX: Add mypy to CI pipeline                             │
│             ACCEPTED: Gradual typing in new code is sufficient      │
│                                                                      │
│  KI-019     Schema version mismatch                 LOW    TRACKING  │
│             PROGRESS.yaml says schema_version: 15                    │
│             db/schema.py says _SCHEMA_VERSION = 16                   │
│             FIX: Update PROGRESS.yaml to match schema.py            │
│             EFFORT: 5 minutes                                       │
│                                                                      │
│  KI-020     PROGRESS.yaml claims all phases         LOW    TRACKING  │
│             complete but Phase 6 sessions are                        │
│             listed as 16/16 — need verification                      │
│             FIX: Verify Phase 6 actually complete                    │
│                                                                      │
│  KI-021     Docker compose has no resource limits   LOW    ACCEPT    │
│             No mem_limit or CPU limits on any service                │
│             ACCEPTED: For dev/low-traffic use, not needed           │
│             FIX: Add resource limits for production deploy           │
│                                                                      │
│  KI-022     No CONTRIBUTING.md file                 LOW    PLANNED   │
│             FIX: Create contributing guide                           │
│             DEFERRED: Until repo goes public                         │
│                                                                      │
│  KI-023     No privacy policy                       LOW    PLANNED   │
│             FIX: Create PRIVACY.md before launch                    │
│             DEFERRED: Until public launch                            │
│                                                                      │
│  KI-024     No Code of Conduct                      LOW    PLANNED   │
│             FIX: Create CODE_OF_CONDUCT.md before community         │
│             DEFERRED: Until repo goes public                         │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Part 5: Decision Log (Chronological)

---

### 5.1 All Decisions, When They Were Made

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  #    DATE        DECISION                                          │
│  ────────────────────────────────────────────────────────────────    │
│                                                                      │
│  D01  2026-05-25  Project language: Python 3.12                     │
│  D02  2026-05-25  Database: MySQL 8.0                               │
│  D03  2026-05-25  Web framework: FastAPI                            │
│  D04  2026-05-25  LLM: Ollama (local, not OpenAI cloud)             │
│  D05  2026-05-25  Deployment: Docker Compose                        │
│  D06  2026-05-25  Repository: GitHub (gokul-koduri/start)           │
│  D07  2026-05-25  Agent architecture: Multi-agent pipeline          │
│  D08  2026-05-25  Scoring: Composite (0-100) with factor attribution│
│  D09  2026-05-25  Dashboard: Static HTML site (not React)           │
│  D10  2026-05-25  Secondary dashboard: Streamlit                    │
│  D11  2026-05-26  Report: Static site generated + GitHub Pages     │
│  D12  2026-05-27  Seed data: 50+ failed startups (manual curation) │
│  D13  2026-05-28  Embeddings: sentence-transformers/all-MiniLM-L6-v2│
│  D14  2026-05-28  NER: spaCy en_core_web_sm                         │
│  D15  2026-05-28  Vector search: Qdrant (not Pinecone/Weaviate)     │
│  D16  2026-05-29  Full-text search: Elasticsearch (optional)        │
│  D17  2026-06-01  Stream processing: Bytewax (not Flink/Spark)      │
│  D18  2026-06-01  Event streaming: Redpanda (Kafka-compatible)      │
│  D19  2026-06-01  Architecture: Kappa (not Lambda)                  │
│  D20  2026-06-01  Analytics: ClickHouse (optional, not needed MVP)  │
│  D21  2026-06-01  Time-series: TimescaleDB (optional, not MVP)      │
│  D22  2026-06-01  Caching: Redis                                    │
│  D23  2026-06-02  CI/CD: GitHub Actions                             │
│  D24  2026-06-02  Deployment: GitHub Pages (gh-pages branch)        │
│  D25  2026-06-03  Schema versioning: Incremental integer (v16 now)  │
│  D26  2026-06-04  Revenue model: Free (OSS) + Pro ($99) + Enterprise│
│  D27  2026-06-04  License: MIT (planned, not yet created)           │
│  D28  2026-06-04  Competitive position: Open-source, AI-first      │
│  D29  2026-06-05  Agent audit: Cut 6, merge 4 (PROBLEM_FEATURE_MAP)│
│  D30  2026-06-05  Feature priority: 3-axis scoring (Problem +      │
│                    Demand + Feasibility)                             │
│  D31  2026-06-05  MVP scope: 3 features (Score + Chat + Patterns)  │
│  D32  2026-06-05  MVP timeline: 2 weeks                             │
│  D33  2026-06-05  Version control: Conventional Commits + SemVer   │
│  D34  2026-06-05  Testing: 7-stage testing strategy                │
│  D35  2026-06-05  HuggingFace MCP: Planned for V3 (not MVP)       │
│  D36  2026-06-05  Branching: Trunk-based (solo dev)                │
│  D37  2026-06-05  Risk response: Mitigate critical before launch   │
│  D38  2026-06-05  Scoring accuracy: Must measure before launch      │
│  D39  2026-06-05  Scale: Vertical first, partition at Kafka         │
│  D40  2026-06-05  Security: Self-hosted = secure default, defense   │
│                    in depth, open-source = auditable                 │
│                                                                      │
│  TOTAL: 40 documented decisions                                     │
│  FORMAT: ADR-001 through ADR-011 (detailed), D01-D40 (chronological)│
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 5.2 Decisions Reversed

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  REVERSED DECISIONS:  0                                              │
│                                                                      │
│  No decisions have been reversed so far. All 40 decisions stand.    │
│                                                                      │
│  WHY THIS MATTERS:                                                   │
│  Reversed decisions are expensive — they mean rework.               │
│  Having zero reversals suggests either:                              │
│  1. Decisions were well-considered (good), or                       │
│  2. We haven't hit the scale/usage that forces reconsideration      │
│                                                                      │
│  DECISIONS MOST LIKELY TO BE REVERSED:                               │
│  1. MySQL → PostgreSQL (if we need pgvector or better JSON)         │
│  2. Bytewax → Flink (if we need > 100K msg/sec)                    │
│  3. Docker Compose → Kubernetes (if we need multi-host)             │
│  4. all-MiniLM-L6-v2 → bge-small-en-v1.5 (easy, planned via MCP)  │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Part 6: The One-Page Decision Record

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  DOCUMENT DECISIONS — ONE PAGE                                       │
│                                                                      │
│  REQUIREMENTS:                                                       │
│    20 functional requirements (FR-1 to FR-20)                        │
│    12 non-functional requirements (NFR-1 to NFR-12)                  │
│    10 in-scope, 10 out-of-scope items                                │
│    6 agents cut, 4 agents merged                                     │
│                                                                      │
│  ARCHITECTURE CHOICES (11 ADRs):                                     │
│    Python 3.12 + FastAPI + MySQL 8.0 + Ollama + Docker Compose     │
│    Bytewax (stream) + Redpanda/Kafka (events) + Qdrant (vectors)    │
│    Kappa architecture (not Lambda)                                    │
│    all-MiniLM-L6-v2 (embeddings) + spaCy (NER)                      │
│    Self-hosted first, open-source, MIT license (planned)             │
│                                                                      │
│  SETUP INSTRUCTIONS:                                                 │
│    Prerequisites: Python 3.12, Docker, 8GB RAM, 10GB disk           │
│    Start: git clone → docker compose up -d → seed → collect → score │
│    13 ports, 11 Docker services, 8 env vars                         │
│                                                                      │
│  KNOWN ISSUES (24 total):                                            │
│    6 CRITICAL/HIGH (fix before launch): tests, backup, license,     │
│      score accuracy, uncommitted files, rate limiting                │
│    7 MEDIUM (fix before V1): localhost refs, fallback, tests, CI    │
│    11 LOW (accepted/deferred): deprecation, cleanup, versioning     │
│                                                                      │
│  DECISION LOG: 40 decisions documented, 0 reversed                   │
│                                                                      │
│  DOCUMENTS IN THIS REPO:                                             │
│    33 markdown files, 600KB+ total                                   │
│    Every decision, requirement, and issue is traceable to a file     │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

*Last updated: June 5, 2026*
