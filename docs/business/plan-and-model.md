# 🏭 Opportunity Intelligence Platform — The Complete Plan & Business Model

> **Open-source, self-hosted, real-time, multi-agent alternative to Crunchbase / PitchBook / Tracxn**
> 50+ AI Agents | 24+ Data Sources | 7 Storage Engines | Fully Self-Hosted

---

## Table of Contents

1. [The Problem](#1-the-problem)
2. [The Solution](#2-the-solution)
3. [What Makes This Different](#3-what-makes-this-different)
4. [Who Is It For](#4-who-is-it-for)
5. [How It Works — System Architecture](#5-how-it-works--system-architecture)
6. [Data Sources](#6-data-sources)
7. [AI Agent Catalog (50+ Agents)](#7-ai-agent-catalog-50-agents)
8. [Scoring Engine — How Opportunities Are Ranked](#8-scoring-engine--how-opportunities-are-ranked)
9. [Knowledge Graph — How Everything Connects](#9-knowledge-graph--how-everything-connects)
10. [Stream Processing — Real-Time Intelligence](#10-stream-processing--real-time-intelligence)
11. [Tech Stack](#11-tech-stack)
12. [Storage Topology — 7 Engines](#12-storage-topology--7-engines)
13. [API Layer](#13-api-layer)
14. [Dashboard & User Interface](#14-dashboard--user-interface)
15. [Implementation Roadmap — 6 Phases](#15-implementation-roadmap--6-phases)
16. [Current Progress](#16-current-progress)
17. [Business Model](#17-business-model)
18. [Revenue Projections](#18-revenue-projections)
19. [Go-To-Market Strategy](#19-go-to-market-strategy)
20. [Competitive Landscape](#20-competitive-landscape)
21. [Risk Analysis & Mitigation](#21-risk-analysis--mitigation)
22. [10-Year Vision](#22-10-year-vision)
23. [Key Metrics & KPIs](#23-key-metrics--kpis)
24. [Appendix — Dependency Graphs, Docker Map, Testing Strategy](#24-appendix)

---

## 1. The Problem

### The World Has a Startup Intelligence Gap

| Problem | Impact |
|---|---|
| **90% of startups fail**, but the data on *why* is scattered, unstructured, and inaccessible | Founders repeat the same mistakes. Investors can't assess risk properly. |
| **Crunchbase costs $490/month**, PitchBook $1,000+/month, Tracxn $500+/month | Market intelligence is locked behind paywalls. Only wealthy firms can afford it. |
| **No open-source alternative exists** | You either pay or fly blind. There's no middle ground. |
| **Failure data is ignored** | Everyone studies success. Nobody systematically studies failure to learn from it. |
| **Manufacturing revival is a $1T+ opportunity** (reshoring, CHIPS Act, Make in India) | But there's no platform that connects failed manufacturing startups to revival opportunities. |
| **Market signals are fragmented** across 20+ sources (GitHub, Reddit, SEC, patents, job boards, news) | No single tool connects all these dots in real-time. |
| **Closed platforms own your data** | Your searches, watchlists, and strategies live on their servers. |

### The Cost of Not Having This

```
Founder launches a manufacturing startup in Ohio
  → Doesn't know 3 similar startups failed there in 2019-2023
  → Doesn't know Texas has 3x better survival rate for that sector
  → Doesn't know a whale investor just committed $200M to that sector in Mexico
  → Fails in 18 months
  → Could have been avoided with 30 seconds of data
```

---

## 2. The Solution

### One Sentence

A **self-hosted, open-source platform** that continuously monitors **24+ data sources** — enriches signals with NLP, scores opportunities with explainable ML, maps relationships in a knowledge graph — and surfaces real-time intelligence via dashboards, APIs, and webhooks.

### What It Does (Concrete)

| Capability | Detail |
|---|---|
| **Detect a startup's funding round within 15 minutes** | Real-time Kafka streaming from SEC, Crunchbase, AngelList |
| **Score opportunity quality with explainable ML features** | Every score has feature attribution — you know *why* it scored 78/100 |
| **Map competitive relationships across 12+ entity types** | Startups, founders, investors, patents, technologies — all connected |
| **Track GitHub star velocity as a leading indicator** | Open-source momentum → company growth signal |
| **Monitor Reddit/HN sentiment for market signals** | Community buzz before it hits mainstream news |
| **Correlate hiring spikes with product launches** | See what competitors are about to do before they announce it |
| **Alert on anomaly patterns** | Distress signals, market shifts, sudden funding changes |
| **Generate PDF reports with knowledge graph visualizations** | Weekly/monthly automated reports |
| **Answer natural language questions** | "Which manufacturing sectors have the best revival opportunities in Southeast Asia?" |
| **Self-hosted — all data stays on your infrastructure** | No third-party ever sees your queries or strategies |

### The Core Loop

```
COLLECT → ENRICH → SCORE → ALERT → REPORT → LEARN
   ↑                                        │
   └──────────── (continuous) ───────────────┘
   
24 sources    NLP/ML      Composite   Webhook/    Markdown    Self-tuning
              pipeline    scoring     Email/Slack  HTML/PDF    models
```

---

## 3. What Makes This Different

### No Open-Source Competitor Exists

| Feature | Crunchbase | PitchBook | Tracxn | **This Platform** |
|---|---|---|---|---|
| **Cost** | $490/mo | $1,000+/mo | $500+/mo | **Free (open-source)** |
| **Self-hosted** | ❌ | ❌ | ❌ | **✅ Your infrastructure** |
| **Data ownership** | Their servers | Their servers | Their servers | **100% yours** |
| **AI agents** | None | None | Basic | **50+ specialized agents** |
| **Failure analysis** | ❌ | Limited | ❌ | **Core feature** |
| **Manufacturing revival** | ❌ | ❌ | ❌ | **Unique focus** |
| **Knowledge graph** | ❌ | Limited | ❌ | **12 entity types, 20+ relations** |
| **Real-time streaming** | ❌ | ❌ | ❌ | **Kappa architecture** |
| **Explainable ML** | ❌ | ❌ | ❌ | **Feature attribution on every score** |
| **Customizable** | Fixed | Fixed | Fixed | **Open-source, fully extensible** |
| **NLP pipeline** | ❌ | ❌ | ❌ | **spaCy NER + embeddings + classification** |
| **Semantic search** | ❌ | Keyword only | ❌ | **Vector + fulltext + hybrid** |
| **Alert webhooks** | Limited | Limited | Limited | **Slack, Discord, Email, Custom** |

### Three Unique Angles

1. **We study failure, not just success** — The largest open database of *why startups fail* with pattern detection
2. **Manufacturing revival intelligence** — Connecting failed manufacturing ventures to reshoring/policy/funding opportunities
3. **Multi-agent AI architecture** — 50+ specialized agents vs. monolithic scrapers

---

## 4. Who Is It For

### Free Tier (Open Source)

| User | What They Do |
|---|---|
| **Entrepreneurs / Founders** | Study why startups fail in their sector/region. Find revival opportunities. Pick the right geography. |
| **Students & Researchers** | Academic research on startup failure patterns, survival rates, market correlations. |
| **Indie Developers** | Monitor GitHub trends, Reddit sentiment, HN discussions for product ideas. |
| **Journalists** | Track startup shutdowns, layoffs, bankruptcy news for reporting. |
| **Open-Source Community** | Self-host their own market intelligence instead of paying for Crunchbase. |

### Pro Tier (Paid)

| User | What They Do |
|---|---|
| **VC / Angel Investors** | Whale investor tracking. Real-time funding alerts. Risk scores with explainability. Portfolio monitoring. |
| **Startup Accelerators** | Batch company survival analysis. Competitive landscape mapping. Automated due diligence reports. |
| **Market Research Analysts** | Automated weekly/monthly reports. 420+ sector evaluations across 10 international markets. Knowledge graph exploration. |
| **Manufacturing Strategists** | Reshoring trend tracking. Manufacturing revival opportunities. BLS survival data analysis. |
| **Supply Chain Managers** | Identify distressed manufacturing assets. Track greenfield manufacturing deals. Monitor regulatory changes. |
| **Corporate Strategy / M&A Teams** | Competitive landscape mapping. Acquisition target discovery. Market entry analysis. |

### Enterprise Tier

| User | What They Do |
|---|---|
| **Governments / Economic Agencies** | Industrial policy decisions. Reshoring feasibility. Startup ecosystem health monitoring. |
| **Large VC Firms / PE** | Custom data source integration. White-label dashboards for LPs. On-premise deployment with SLA. |
| **Universities / Think Tanks** | Bulk data access. Research API. Custom agent development. |

---

## 5. How It Works — System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        📊 DASHBOARD LAYER                                  │
│  Streamlit (internal tools)  │  Next.js + SSE (production)                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                        🔌 API & REAL-TIME LAYER                             │
│  FastAPI REST  │  GraphQL (Hasura)  │  WebSocket  │  SSE  │  Webhooks     │
├─────────────────────────────────────────────────────────────────────────────┤
│                        🤖 INTELLIGENCE LAYER (50+ Agents)                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ Market   │ │Competitive│ │ Founder  │ │ Graph    │ │ Topic Modeling   │ │
│  │ Sizing   │ │Landscape │ │ Background│ │Traversal │ │ Trend Detection  │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────────────┘ │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ Moat     │ │ Timing   │ │ Community│ │ Influence│ │ Sector Rotation  │ │
│  │ Analyzer │ │ Agent    │ │ Detector │ │ Propag.  │ │ Cohort Analysis  │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────────────┘ │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ Failure  │ │ Survival │ │ Revival  │ │ Whale    │ │ Global Market    │ │
│  │ Patterns │ │ Analysis │ │ Opportunity│ │ Investor│ │ Viability       │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────────────┘ │
│  ┌─────────────────────┐ ┌──────────────────────┐ ┌────────────────────┐   │
│  │ NLP Pipeline        │ │ Entity Resolver      │ │ Risk Scorer        │   │
│  │ (NER, embed, classify)│ │ (Jaro-Winkler)     │ │ (Predictive 0-1)   │   │
│  └─────────────────────┘ └──────────────────────┘ └────────────────────┘   │
├─────────────────────────────────────────────────────────────────────────────┤
│                        ⚡ STREAM PROCESSING LAYER                           │
│  Kafka (Redpanda) → Bytewax 5-Stage Pipeline                               │
│  Ingest → Enrich → Aggregate → Score → Output                              │
│  Complex Event Patterns: Scaling / Innovation / Distress / Pivot / Entry   │
├─────────────────────────────────────────────────────────────────────────────┤
│                        📡 COLLECTION LAYER (24 Collectors)                  │
│  Tier 1 (Real-time): Reddit, HN, GitHub, News, Funding, SEC EDGAR         │
│  Tier 2 (Near real-time): Patents, Social, Product Hunt, Job Boards        │
│  Tier 3 (Daily): arXiv, StackOverflow, NPM/PyPI, Regulatory, Newsletters  │
│  Tier 4 (Weekly): OpenCorporates, Website Monitor, Twitter/X, Crunchbase   │
├─────────────────────────────────────────────────────────────────────────────┤
│                        💾 STORAGE LAYER (7 Engines)                         │
│  MySQL (operational) │ ClickHouse (OLAP) │ Qdrant (vectors)                │
│  Elasticsearch (search) │ TimescaleDB (time-series) │ Apache Age (graph)   │
│  Redis (cache + pub/sub)                                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                        🧠 LLM LAYER                                        │
│  Ollama (local llama3) │ LLM Pricing Tracker │ LLM Cost Optimizer          │
│  LLM Benchmark │ LLM Portfolio Allocation                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Data Sources

### Tier 1: Core Sources (Real-Time)

| # | Source | Library | Data | Frequency |
|---|---|---|---|---|
| 1 | **Reddit** | PRAW | Posts/comments from r/startups, r/technology, r/SaaS, r/Entrepreneur | Real-time streaming |
| 2 | **Hacker News** | HN Algolia API | Top stories, comments, Show HN launches | Real-time |
| 3 | **GitHub** | PyGithub + Deep Collector | Star velocity, repo trends, language adoption, contributor activity | Real-time |
| 4 | **SEC EDGAR** | sec-edgar-downloader | 10-K, 8-K, 10-Q filings — financial health, M&A, strategy | Hours |
| 5 | **Google News RSS** | feedparser | Startup failure, bankruptcy, shutdown news | Near real-time |
| 6 | **TechCrunch RSS** | feedparser | Startup and tech industry news, funding announcements | Near real-time |
| 7 | **Funding Events** | Crunchbase / AngelList API | Funding rounds, investors, valuations | Hours |

### Tier 2: Expansion Sources (Near Real-Time)

| # | Source | Library | Data | Frequency |
|---|---|---|---|---|
| 8 | **Patents (USPTO)** | python-uspto | Patent filings, citations, innovation trajectory | Days |
| 9 | **Job Postings** | LinkedIn RSS, Indeed API | Hiring spikes = growth signals, role shifts = pivot signals | Hours-Days |
| 10 | **Product Hunt** | GraphQL API | Product launches, upvotes, maker profiles | Daily |
| 11 | **BLS (Bureau of Labor Statistics)** | API + Downloads | Business survival rates by NAICS code | Monthly |
| 12 | **Failory** | Web Scrape | Failed startup profiles, failure reasons, metadata | Weekly |

### Tier 3: Deep Sources (Daily)

| # | Source | Library | Data | Frequency |
|---|---|---|---|---|
| 13 | **arXiv Papers** | arxiv API | Research papers — emerging technology signals | Daily |
| 14 | **Stack Overflow** | SO API | Tag adoption trends — technology momentum | Daily |
| 15 | **NPM / PyPI Trends** | Registry APIs | Package download trends — developer adoption | Daily |
| 16 | **Regulatory Filings** | Federal Register API | Compliance risk, market regulation shifts | Daily |
| 17 | **Newsletter Aggregation** | Custom parser | Curated intelligence from industry newsletters | Daily |

### Tier 4: Periodic Sources (Weekly)

| # | Source | Library | Data | Frequency |
|---|---|---|---|---|
| 18 | **OpenCorporates** | REST API | 220M+ company profiles, directors, filings across 140+ jurisdictions | Weekly |
| 19 | **Website Monitor** | Playwright / Diffbot | Pricing changes, feature launches, team page changes | Weekly |
| 20 | **Twitter / X** | API v2 | Real-time sentiment, executive announcements, market reactions | Weekly |
| 21 | **Crunchbase** | Crunchbase API | Company profiles, funding rounds, acquisitions, IPOs | Weekly |
| 22 | **Reshoring Initiative** | PyMuPDF | Manufacturing reshoring statistics and case studies | Monthly |

### Collector Pattern

Every collector:
1. Extends `BaseCollector` (abstract base class)
2. Implements `name` + `collect(conn)` method
3. Dual-writes to **MySQL** (durable) + **Kafka** (real-time) via `self.publish_signal()`
4. Follows rate limiting via `utils/rate_limiter.py`
5. Has dedup logic in `db/dedup.py`

---

## 7. AI Agent Catalog (50+ Agents)

### Foundation Agents (Built — Phase 1-3)

| Agent | Purpose |
|---|---|
| **Orchestrator** | Coordinates pipeline stages and agent execution order |
| **Collection** | Runs data collectors and ingests into MySQL |
| **Report** | Generates Markdown reports from database data |
| **Dashboard** | Builds interactive HTML dashboard with charts |
| **Git Publisher** | Commits and deploys to GitHub Pages |
| **AI Analyst** | Natural language Q&A over the research data |
| **Opportunity Scorer** | Composite scoring with time-decay + anomaly detection + feature attribution |
| **Opportunity Pipeline** | Scores and ranks revival opportunities |
| **Failure Pattern** | Detects common failure patterns across startups |
| **Survival Analysis** | Statistical analysis of startup survival rates |
| **Revival Opportunity** | Identifies opportunities to revive failed startups |
| **Geographic Strategy** | Location-based market analysis and recommendations |
| **News Intelligence** | Monitors and categorizes startup news |
| **Whale Investor** | Tracks mega-investments and greenfield manufacturing deals |
| **Correlation** | Market correlation analysis across sectors |
| **Global Market Viability** | 420+ sector evaluations across 10 international markets |
| **Knowledge Graph** | Maps entity relationships (12 entity types, 20+ relationships) |
| **Internet Research** | Discovers new data sources and research material |
| **Risk Scorer** | Predictive failure risk scoring (0.0–1.0) |
| **Report Generator** | Scheduled HTML/Markdown report generation + email delivery |
| **Alert Dispatcher** | Email, Slack, Discord, and custom webhook notifications |
| **Span Monitor** | Pipeline health monitoring with anomaly detection |
| **Ollama Usage Tracker** | Tracks local LLM inference usage and costs |
| **Entity Resolver** | Jaro-Winkler fuzzy matching with alias table |
| **NLP Enrichment** | spaCy NER + embeddings + classification pipeline |
| **Semantic Search** | Qdrant + Elasticsearch hybrid search |
| **Report Generator** | Scheduled HTML/Markdown reports with optional email delivery |
| **License Manager** | License key generation and validation |
| **Stripe Payments** | Polls Stripe API, auto-generates license keys on payment |

### LLM Infrastructure Agents (Built)

| Agent | Purpose |
|---|---|
| **LLM Pricing** | Tracks LLM API pricing across providers |
| **LLM Benchmark** | Compares LLM performance on analysis tasks |
| **LLM Portfolio** | Optimal LLM allocation strategy |
| **LLM Cost Optimizer** | Minimizes LLM infrastructure costs |

### Deep Collection Agents (Phase 4 — In Progress)

| # | Agent | Status | New Data |
|---|---|---|---|
| 1 | GitHub Deep Collector | ✅ Complete | Commit velocity, language breakdown, contributor graphs |
| 2 | Reddit Stream Collector | ✅ Complete | Real-time subreddit monitoring, sentiment flow |
| 3 | HN Live Collector | ✅ Complete | Live HN stories, Show HN launches, comment threads |
| 4 | OpenCorporates Collector | ✅ Complete | 220M+ company profiles, directors, cross-border filings |
| 5 | arXiv Paper Signals | ✅ Complete | Emerging technology research papers |
| 6 | Product Hunt Launches | ✅ Complete | Product launches, upvote velocity, maker profiles |
| 7 | Website Monitor Collector | ✅ Complete | Pricing changes, feature launches, team page changes |
| 8 | Twitter/X Signals | ✅ Complete | Real-time sentiment, executive announcements |
| 9 | Stack Overflow Adoption | ✅ Complete | Technology tag trends, developer adoption signals |
| 10 | NPM/PyPI Trends | ⏳ Pending | Package download trends |
| 11 | Regulatory Filings | ⏳ Pending | Compliance risk, market regulation |
| 12 | Newsletter Aggregation | ⏳ Pending | Curated industry intelligence |

### Advanced Intelligence Agents (Phase 5 — Planned)

| # | Agent | Purpose | Dependencies |
|---|---|---|---|
| 1 | **Market Sizing** | TAM/SAM/SOM estimation for sectors and geographies | None |
| 2 | **Competitive Landscape** | Maps competitors, market share, positioning | Market Sizing |
| 3 | **Founder Background** | Founder track record, previous exits/failures, network strength | OpenCorporates |
| 4 | **Technology Stack** | Tech choices as signals (modern stack = agility indicator) | GitHub + StackOverflow |
| 5 | **Moat Analyzer** | Competitive moat strength: network effects, switching costs, IP, brand | Competitive + Tech Stack |
| 6 | **Timing Agent** | Market timing analysis — is now the right time for this sector? | Market Sizing |
| 7 | **Graph Traversal** | Shortest path, degree centrality, PageRank on knowledge graph | None |
| 8 | **Community Detector** | Find clusters in the investor-founder-startup network | Graph Traversal |
| 9 | **Influence Propagation** | How influence spreads through the network (who moves markets?) | Graph + Community |
| 10 | **Temporal Graph** | How relationships evolve over time (funding patterns, team changes) | Graph Traversal |
| 11 | **Topic Modeling** | Discover emerging themes across all data sources | None |
| 12 | **Relationship Extractor** | Extract new relationship types from unstructured text | Topic Modeling |
| 13 | **Trend Detector** | Identify macro trends before they peak | Timing Agent |
| 14 | **Intent Classifier** | Classify user queries and route to appropriate agents | Topic Modeling |
| 15 | **Sector Rotation** | Track capital flow between sectors (which sectors are heating up/cooling down) | Market Sizing + Timing |
| 16 | **Cohort Analysis** | Compare startup cohorts by year, sector, geography, funding stage | Sector Rotation |

### Operations Agents (Phase 6 — Planned)

| # | Agent | Purpose |
|---|---|---|
| 1 | **Slack Integration** | Push alerts to Slack channels |
| 2 | **Email Digest** | Automated daily/weekly email reports |
| 3 | **Export Agent** | CSV/JSON/PDF data export |
| 4 | **Feed Generator** | RSS/Atom feed generation for custom watchlists |
| 5 | **Data Quality** | Detect stale data, missing fields, broken collectors |
| 6 | **Pipeline Health** | Anomaly detection for agent duration, failure rates, data drops |
| 7 | **Cost Tracking** | Infrastructure cost monitoring per tenant |

---

## 8. Scoring Engine — How Opportunities Are Ranked

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

### Signal Weights

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

### Example Output (Explainable)

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

### Scoring Module Files

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

## 9. Knowledge Graph — How Everything Connects

### Entity Types (12)

| Entity | Description |
|---|---|
| `startup` | Companies (active or failed) |
| `industry` | Industry sectors |
| `investor` | VC firms, angels, PE |
| `region` | Geographic areas |
| `sector` | Business sectors |
| `failure_reason` | Failure categories |
| `technology` | Technologies |
| `person` | Founders, CEOs, board members |
| `product` | Products/services |
| `market` | Target markets/segments |
| `patent` | Patent documents |
| `regulation` | Regulatory frameworks |

### Relationship Types (20+)

| Relationship | Source → Target |
|---|---|
| `founded_by` | startup → person |
| `funded_by` | startup → investor |
| `acquired_by` | startup → startup |
| `competes_with` | startup → startup |
| `uses_tech` | startup → technology |
| `targets_market` | startup → market |
| `patent_held_by` | patent → startup |
| `patent_cites` | patent → patent |
| `person_is_investor` | person → investor |
| `product_of` | product → startup |
| `regulated_by` | industry → regulation |
| `failed_because` | startup → failure_reason |
| `located_in` | startup → region |
| `operates_in` | startup → sector |

### Entity Resolution

1. **Blocking**: LSH on name trigrams → generate candidate pairs
2. **Matching**: Jaro-Winkler similarity + context overlap
3. **Merging**: Entity clusters with canonical name selection
4. **Alias table**: "Meta" = "Facebook", "OpenAI" = "Open Artificial Intelligence"

### Graph Algorithms (Phase 5)

| Algorithm | What It Finds |
|---|---|
| **PageRank** | Most influential entities in the network |
| **Community Detection** | Clusters of related founders/investors/startups |
| **Influence Propagation** | How signals spread through the network |
| **Shortest Path** | Connection between any two entities |
| **Temporal Analysis** | How relationships evolve over time |

---

## 10. Stream Processing — Real-Time Intelligence

### Bytewax 5-Stage Pipeline

```
Kafka Topics (raw signals)
    │
    ▼
┌─────────┐    ┌─────────┐    ┌───────────┐    ┌─────────┐    ┌──────────┐
│ INGEST  │───▶│ ENRICH  │───▶│ AGGREGATE │───▶│  SCORE  │───▶│  OUTPUT  │
│         │    │         │    │           │    │         │    │          │
│ Parse   │    │ NER     │    │ Window    │    │Composite│    │ ClickHse │
│ Validate│    │ Embed   │    │ Aggregate │    │ Score   │    │ MySQL    │
│ Normalize│   │ Classify│    │ Correlate │    │ Anomaly │    │ Alert    │
│ Dedup   │    │ Extract │    │ Pattern   │    │ Attrib. │    │ Webhook  │
└─────────┘    └─────────┘    └───────────┘    └─────────┘    └──────────┘
```

### Complex Event Patterns

| Pattern | Signals Required | Time Window | Score Impact |
|---|---|---|---|
| **Scaling Signal** | funding_round + hiring_spike (5+ jobs) | 30 days | +15 boost |
| **Innovation Signal** | patent + github_trend + 8-K filing | 90 days | +20 boost |
| **Distress Signal** | negative news + declining job postings | 14 days | -10 penalty |
| **Market Entry** | new competitor funding + hiring | 60 days | +10 boost |
| **Pivot Signal** | tech_stack change + job role shift + website change | 45 days | +12 boost |

---

## 11. Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Language** | Python 3.12 | Primary development language |
| **Database** | MySQL 8.0 | Operational data (PyMySQL) |
| **OLAP** | ClickHouse | Real-time analytics queries |
| **Time-Series** | TimescaleDB | Temporal data, trends, metrics |
| **Vectors** | Qdrant | Semantic similarity search |
| **Full-Text** | Elasticsearch | Full-text search across all content |
| **Graph** | Apache Age (PostgreSQL) | Knowledge graph queries |
| **Cache** | Redis | API caching, pub/sub, session store |
| **Streaming** | Redpanda (Kafka-compatible) | Event bus |
| **Stream Processing** | Bytewax | Python-native stream processing |
| **NLP** | spaCy 3.7+ | Named Entity Recognition, text classification |
| **Embeddings** | Sentence-Transformers | Semantic vector embeddings |
| **LLM** | Ollama (llama3) | Local LLM inference for analysis & chat |
| **API** | FastAPI | REST + WebSocket + SSE endpoints |
| **GraphQL** | Hasura | GraphQL engine over MySQL |
| **Orchestration** | Dagster | Pipeline scheduling (replaces cron) |
| **Frontend** | Next.js | Production dashboard with SSE |
| **Internal Tools** | Streamlit | Internal dashboard (11 pages) |
| **Scraping** | BeautifulSoup4, lxml, feedparser | Web scraping & RSS |
| **PDF** | PyMuPDF | PDF parsing |
| **Payments** | Stripe | Pro/Enterprise billing |
| **Auth** | JWT + RBAC | Authentication & authorization |
| **Monitoring** | Prometheus + Grafana | Infrastructure & pipeline monitoring |
| **CI/CD** | GitHub Actions | Auto-deploy to GitHub Pages |
| **Containerization** | Docker Compose | 18-service orchestration |

---

## 12. Storage Topology — 7 Engines

```
┌─────────────────────────────────────────────────────────────┐
│                     STORAGE LAYER                            │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  MySQL   │  │ClickHouse│  │  Qdrant  │  │Elastic   │   │
│  │(OPS DB)  │  │ (OLAP)   │  │(Vectors) │  │(Search)  │   │
│  │          │  │          │  │          │  │          │   │
│  │52+ tables│  │Aggregates│  │Embeddings│  │Full-text │   │
│  │Startups  │  │Scores    │  │Semantic  │  │Search    │   │
│  │Signals   │  │Trends    │  │Similarity│  │Fuzzy     │   │
│  │KG        │  │Analytics │  │Clustering│  │Indexing  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │TimescaleDB│ │Apache Age│  │  Redis   │                  │
│  │(Time-    │  │(Graph)   │  │(Cache +  │                  │
│  │ Series)  │  │          │  │ Pub/Sub) │                  │
│  │          │  │          │  │          │                  │
│  │Metrics   │  │Traversal │  │Sessions  │                  │
│  │Trends    │  │PageRank  │  │API cache │                  │
│  │Alerts    │  │Community │  │WebSocket │                  │
│  │Health    │  │Influence │  │Rate limit│                  │
│  └──────────┘  └──────────┘  └──────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

### What Goes Where

| Data Type | Engine | Why |
|---|---|---|
| Startup profiles, signals, KG entities | MySQL | Relational, transactional, 52+ tables |
| Score aggregates, OLAP analytics | ClickHouse | Columnar, <100ms analytics queries |
| Text embeddings, similarity search | Qdrant | Vector similarity, hybrid search |
| Full-text search, fuzzy matching | Elasticsearch | Inverted index, relevance ranking |
| Time-series metrics, trends, alerts | TimescaleDB | Time-optimized, continuous aggregates |
| Graph traversal, PageRank, community | Apache Age | Graph queries on PostgreSQL |
| API cache, sessions, pub/sub | Redis | In-memory, sub-millisecond latency |

---

## 13. API Layer

### REST API (FastAPI) — 40+ Endpoints

```
# Core
GET  /api/health                    → Health check
GET  /api/stats                     → Database statistics
GET  /api/startups                  → List startups (filter by sector, country, region)
GET  /api/startups/{id}             → Single startup details
GET  /api/news                      → Recent news articles
GET  /api/survival-rates            → BLS survival rate data
GET  /api/revival-opportunities     → Revival industry data
GET  /api/alerts                    → Active alerts
GET  /api/pipeline-runs             → Pipeline execution history
GET  /api/risk-scores               → Startup failure risk scores

# Scoring & Opportunities
POST /api/score                     → On-demand risk scoring
GET  /api/opportunities             → Scored, ranked, filtered opportunities
GET  /api/signals                   → Raw signal data with filters

# Knowledge Graph
GET  /api/knowledge-graph           → Entities + relationships
GET  /api/entities/{name}/connections → Graph traversal

# Search (3 modes)
GET  /api/search?mode=semantic      → Vector similarity search
GET  /api/search?mode=fulltext      → Elasticsearch full-text
GET  /api/search?mode=hybrid        → Combined vector + fulltext

# Real-Time
GET  /api/signals/live              → SSE real-time stream
GET  /api/events/stream             → WebSocket live events

# AI Chat
POST /api/chat                      → Natural language Q&A

# Webhooks
POST /api/webhooks                  → Outbound webhook management

# License & Billing
POST /api/license/validate          → Validate license key
POST /api/license/generate          → Generate license key (admin)
GET  /api/license/metrics           → Subscription metrics

# Monitoring
GET  /metrics                       → Prometheus metrics
```

### GraphQL (Hasura)
- Real-time subscriptions on opportunities, signals, knowledge graph
- Complex nested queries across entity types
- Auto-generated CRUD for all tables

---

## 14. Dashboard & User Interface

### Production Dashboard (Next.js)

| Page | Content |
|---|---|
| **Overview** | Key metrics, summary cards, score distribution |
| **Radar** | Real-time signal feed, anomaly alerts, live events |
| **Opportunities** | Scored + ranked opportunities, filters, explainable scores |
| **Signals** | Raw signals from all sources, timeline, correlation |
| **Knowledge Graph** | Interactive force-directed graph, search, filter, traversal |
| **Sectors** | 420+ sector evaluations across 10 markets |
| **Search** | Semantic + fulltext + hybrid search |
| **Settings** | API keys, webhooks, watchlists, alert preferences |

### Interactive Widgets

| Widget | Technology | Description |
|---|---|---|
| 💬 **AI Chat** | Custom JS | Floating chat bubble for natural language queries |
| ⚠️ **Risk Scores** | Chart.js | Risk distribution chart + top 10 riskiest startups |
| 🔗 **Knowledge Graph** | G6 (AntV) | Interactive force-directed graph with search & filter |

### Internal Dashboard (Streamlit)
- 11 pages for development and debugging
- Direct database queries
- Agent management
- Pipeline monitoring

---

## 15. Implementation Roadmap — 6 Phases

### Phase 1: Foundation ✅ COMPLETE
**Duration:** 4-6 weeks | **Sessions:** 8/8 | **Commit:** b09d812

| Deliverable | Detail |
|---|---|
| Composite scoring engine | Time-decay, anomaly detection, feature attribution |
| 4 new collectors | SEC EDGAR, job postings, GitHub trends, funding events |
| Signal normalization | SignalEnvelope, Kafka producer |
| FastAPI server | 15 endpoints, WebSocket live dashboard |
| Streamlit dashboard | 11 pages |
| Seed data | 35 failed startups, manufacturing failures, revival industries |

**Files:** 20 new | **Tests:** 86

---

### Phase 2: Intelligence ✅ COMPLETE
**Duration:** 6-8 weeks | **Sessions:** 10/10 | **Commit:** 2cf5eeb

| Deliverable | Detail |
|---|---|
| NLP pipeline | spaCy NER, entity extraction, embeddings, classification, summarization |
| Entity resolver | Jaro-Winkler fuzzy matching with alias table |
| Semantic search | Qdrant + Elasticsearch hybrid search |
| Knowledge graph | 12 entity types, 20 relationship types |
| 2 new collectors | Patent filings (USPTO), Social media (Reddit + HN) |

**Files:** 16 new | **Tests:** 36

---

### Phase 3: Scale ✅ COMPLETE
**Duration:** 6-8 weeks | **Sessions:** 12/12 | **Commit:** d7bb6c2

| Deliverable | Detail |
|---|---|
| Bytewax stream processing | 5-stage pipeline: Ingest → Enrich → Aggregate → Score → Output |
| Dual-write collectors | MySQL (durable) + Kafka (real-time) |
| Next.js dashboard | 8 pages with SSE real-time updates |
| Redis caching | API response caching + pub/sub |
| 6 Docker services | Redis, Redpanda, Qdrant, Elasticsearch, ClickHouse, TimescaleDB |

**Files:** 30 new | **Tests:** 36

---

### Phase 4: Deep Collection ⏳ IN PROGRESS (9/15 sessions complete)
**Duration:** 4-6 weeks | **Sessions:** 15 total

| Session | Title | Status |
|---------|-------|--------|
| 4.1 | GitHub Deep Collector | ✅ |
| 4.2 | Reddit Stream Collector | ✅ |
| 4.3 | HN Live Collector | ✅ |
| 4.4 | OpenCorporates Collector | ✅ |
| 4.5 | arXiv Paper Signals | ✅ |
| 4.6 | Product Hunt Launches | ✅ |
| 4.7 | Website Monitor Collector | ✅ |
| 4.8 | Twitter/X Signals | ✅ |
| 4.9 | Stack Overflow Adoption | ✅ |
| 4.10 | NPM/PyPI Trends | ⏳ Pending |
| 4.11 | Regulatory Filings | ⏳ Pending |
| 4.12 | Newsletter Aggregation | ⏳ Pending |
| 4.13 | Schema Migration v14 | ⏳ Pending |
| 4.14 | Phase 4 Integration Tests | ⏳ Pending |
| 4.15 | Phase 4 Commit + Validation | ⏳ Pending |

**New DB tables:** company_profiles, arxiv_papers, product_launches, website_snapshots, so_tag_stats, package_downloads, regulatory_filings, newsletter_items

---

### Phase 5: Advanced Intelligence ⏳ NOT STARTED (0/18 sessions)
**Duration:** 6-8 weeks | **Sessions:** 18 total

16 new agents:
- Market Sizing → Competitive Landscape → Moat Analyzer
- Timing Agent → Trend Detector → Sector Rotation → Cohort Analysis
- Graph Traversal → Community Detector → Influence Propagation → Temporal Graph
- Topic Modeling → Relationship Extractor, Intent Classifier
- Founder Background, Technology Stack

---

### Phase 6: Operations ⏳ NOT STARTED (0/16 sessions)
**Duration:** 8-10 weeks | **Sessions:** 16 total

| Deliverable | Detail |
|---|---|
| Auth (JWT + RBAC) | Multi-tenant authentication and role-based access |
| Tenant Manager | Per-tenant data isolation |
| API v2 | Versioned API with webhooks, export, pagination |
| Webhook Dispatcher | Outgoing Slack, Discord, Email, custom webhooks |
| Collaboration | Annotations, watchlists, shared notes |
| Prometheus + Grafana | Infrastructure and pipeline monitoring |
| Dagster Orchestration | Replaces cron with proper pipeline orchestration |
| Data Quality Agent | Stale data detection, missing field alerts |
| Cost Tracking | Per-tenant infrastructure cost monitoring |

---

### Target End State

| Metric | Current (Phase 3) | Target (Phase 6) |
|--------|-------------------|-----------------|
| Data sources | 12 | 24+ |
| Agents | 35 | 50+ |
| Collectors | 12 | 24 |
| API endpoints | 23 | 40+ |
| DB tables | 52 | 65+ |
| Docker services | 12 | 18 |
| Tests | 467 | 400+ |
| Storage engines | 5 | 7 |
| Orchestration | Cron + file locks | Dagster |
| Dashboard | Next.js + Streamlit | Production Next.js |
| Schema version | 13 | 16+ |

### Dependency Graph

```
Phase 4:  4.1-4.9 ✅ (complete) → 4.10-4.11 (parallel) → 4.12 (deps: 4.2, 4.3) → 4.13 → 4.14 → 4.15
Phase 5:  5.1 → 5.2 → 5.5 (deps: 5.2, 5.4)
          5.1 → 5.6 → 5.13 → 5.15 → 5.16
          5.7 → 5.8 → 5.9; 5.7 → 5.10
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

## 16. Current Progress

**Overall: 30/79 sessions complete (38%)**

| Phase | Status | Progress |
|-------|--------|----------|
| Phase 1: Foundation | ✅ COMPLETE | 8/8 sessions |
| Phase 2: Intelligence | ✅ COMPLETE | 10/10 sessions |
| Phase 3: Scale | ✅ COMPLETE | 12/12 sessions |
| Phase 4: Deep Collection | ⏳ IN PROGRESS | 9/15 sessions |
| Phase 5: Advanced Intelligence | 🔲 NOT STARTED | 0/18 sessions |
| Phase 6: Operations | 🔲 NOT STARTED | 0/16 sessions |

### Current Stats

| Metric | Count |
|--------|-------|
| Python files | 111 |
| Agents | 35 |
| Collectors | 12 (built) + 9 (Phase 4, built) = 21 collectors |
| API endpoints | 23 |
| DB tables | 52 |
| Tests | 467 (all passing) |
| Frontend pages | 8 (Next.js) + 11 (Streamlit) |
| Docker services | 12 |
| Schema version | 13 |
| Last session worked | 4.9 (Stack Overflow Adoption) |

---

## 17. Business Model

### Revenue Streams

```
                    REVENUE MODEL
                    
  ┌─────────────────────────────────────────────┐
  │                                             │
  │   1. OPEN SOURCE (Free)                     │
  │      Self-hosted, MIT license               │
  │      Basic collectors + agents              │
  │      Community support                      │
  │      → Builds trust, adoption, brand        │
  │                                             │
  │   2. PRO TIER ($49-199/month)              │
  │      Managed hosting (SaaS)                 │
  │      Real-time alerts + webhooks            │
  │      Advanced ML scoring                    │
  │      Full API access                        │
  │      Priority collectors                    │
  │      → Primary revenue driver               │
  │                                             │
  │   3. ENTERPRISE TIER ($500-5,000/month)    │
  │      On-premise deployment                  │
  │      Custom data source integration         │
  │      White-label dashboards                 │
  │      SLA guarantees                         │
  │      Dedicated support                      │
  │      Multi-tenant with RBAC                 │
  │      → High-value contracts                 │
  │                                             │
  │   4. DATA API ($0.01-0.10/query)           │
  │      Power third-party applications         │
  │      Embedded in CRM / ERP tools            │
  │      Bulk data exports                      │
  │      → Passive revenue at scale             │
  │                                             │
  │   5. CONSULTING & CUSTOMIZATION             │
  │      Custom agent development               │
  │      Industry-specific intelligence         │
  │      Integration with existing systems      │
  │      → High-margin services                 │
  │                                             │
  └─────────────────────────────────────────────┘
```

### Tier Feature Matrix

| Feature | Free | Pro ($49-199/mo) | Enterprise ($500-5,000/mo) |
|---|---|---|---|
| Self-hosted | ✅ | ✅ | ✅ |
| Managed hosting | ❌ | ✅ | ✅ |
| Basic collectors (12) | ✅ | ✅ | ✅ |
| Advanced collectors (24+) | ❌ | ✅ | ✅ |
| Basic agents (35) | ✅ | ✅ | ✅ |
| Advanced agents (50+) | ❌ | ✅ | ✅ |
| AI Chat | ✅ | ✅ | ✅ |
| Dashboard | ✅ | ✅ | ✅ |
| Real-time alerts | ❌ | ✅ | ✅ |
| Webhooks (Slack/Discord) | ❌ | ✅ | ✅ |
| API access | Limited | Full | Full + GraphQL |
| ML scoring with attribution | ❌ | ✅ | ✅ |
| Knowledge graph | Basic | Full | Full + custom |
| Multi-tenancy | ❌ | ❌ | ✅ |
| RBAC | ❌ | ❌ | ✅ |
| White-label dashboard | ❌ | ❌ | ✅ |
| Custom data sources | ❌ | ❌ | ✅ |
| SLA | ❌ | 99.5% | 99.9% |
| Support | Community | Email | Dedicated |
| License key | None | Stripe auto-gen | Custom |

---

## 18. Revenue Projections

### Year 1 (Build + Launch)

| Stream | Users | Price | Monthly Rev | Annual Rev |
|---|---|---|---|---|
| Free tier | 500 installs | $0 | $0 | $0 |
| Pro tier | 50 subscribers | $99/mo avg | $4,950 | $59,400 |
| Enterprise | 2 contracts | $1,500/mo avg | $3,000 | $36,000 |
| Data API | — | — | — | $5,000 |
| **Total** | | | **$7,950/mo** | **$100,400** |

### Year 2 (Growth)

| Stream | Users | Price | Monthly Rev | Annual Rev |
|---|---|---|---|---|
| Free tier | 2,000 installs | $0 | $0 | $0 |
| Pro tier | 300 subscribers | $99/mo avg | $29,700 | $356,400 |
| Enterprise | 10 contracts | $2,000/mo avg | $20,000 | $240,000 |
| Data API | 50 integrators | $0.05/query avg | $5,000 | $60,000 |
| Consulting | 5 projects | — | — | $75,000 |
| **Total** | | | **$54,700/mo** | **$731,400** |

### Year 3 (Scale)

| Stream | Users | Price | Monthly Rev | Annual Rev |
|---|---|---|---|---|
| Free tier | 10,000 installs | $0 | $0 | $0 |
| Pro tier | 1,500 subscribers | $120/mo avg | $180,000 | $2,160,000 |
| Enterprise | 30 contracts | $2,500/mo avg | $75,000 | $900,000 |
| Data API | 200 integrators | $0.05/query avg | $25,000 | $300,000 |
| Consulting | 10 projects | — | — | $200,000 |
| **Total** | | | **$280,000/mo** | **$3,560,000** |

---

## 19. Go-To-Market Strategy

### Phase A: Open-Source Community (Months 1-6)

| Action | Detail |
|---|---|
| **GitHub launch** | Publish repo with full README, 35 agents, 12 collectors, 467 tests |
| **Product Hunt launch** | "The open-source Crunchbase alternative" — target #1 product of the day |
| **Hacker News** | Show HN post — "We built an open-source market intelligence platform" |
| **Reddit** | Posts on r/Entrepreneur, r/startups, r/SaaS, r/datascience, r/MachineLearning |
| **Dev.to / Medium** | Technical blog posts: "How we built 50 AI agents for startup intelligence" |
| **Twitter/X** | Daily insights from the platform — "Startup failure pattern of the week" |
| **YouTube** | Demo videos: 10-minute walkthroughs of dashboard, API, agents |
| **Conference talks** | PyCon, AI/ML conferences, startup events |

**Target:** 1,000 GitHub stars, 500 free installs, 50 Pro signups

### Phase B: Pro Tier Launch (Months 6-12)

| Action | Detail |
|---|---|
| **Stripe integration** | Auto license key generation on payment |
| **Landing page** | Managed hosting signup, pricing tiers, demo |
| **Email campaigns** | Convert free users to Pro via in-app prompts |
| **VC outreach** | Direct sales to VC firms with custom demos |
| **University partnerships** | Free Pro licenses for research — builds credibility |
| **Accelerator partnerships** | Y Combinator, Techstars — intelligence for their batches |

**Target:** 300 Pro subscribers, 10 Enterprise contracts

### Phase C: Enterprise & Scale (Year 2+)

| Action | Detail |
|---|---|
| **Sales team** | 2-3 enterprise sales reps |
| **White-label offering** | Branded dashboards for large firms |
| **Government contracts** | Economic development agencies, trade ministries |
| **Data API** | Developer portal, API marketplace listing |
| **Partner integrations** | Salesforce, HubSpot, Bloomberg terminal plugins |
| **International expansion** | Localized dashboards for EU, India, SE Asia markets |

---

## 20. Competitive Landscape

### Direct Competitors

| Competitor | Pricing | Weakness | Our Advantage |
|---|---|---|---|
| **Crunchbase** | $490/mo | Closed, expensive, no AI agents, no failure analysis | Free, 50+ AI agents, self-hosted |
| **PitchBook** | $1,000+/mo | Closed, enterprise-only, no real-time | Open, real-time, affordable |
| **Tracxn** | $500+/mo | Limited sources, no explainability | 24+ sources, explainable ML |
| **CB Insights** | Custom pricing | Black-box scoring | Open scoring, feature attribution |
| **Dealroom** | €399/mo | EU-focused, limited AI | Global, multi-agent architecture |

### Indirect Competitors

| Competitor | What They Do | Our Differentiation |
|---|---|---|
| **AngelList / Wellfound** | Startup jobs + funding | We analyze, they list. Complementary, not competitive. |
| **Product Hunt** | Product launches | We monitor PH as a data source, not compete with it. |
| **Glassdoor** | Company reviews | We use job posting data for growth signals. |
| **SEMrush / Similarweb** | Marketing intelligence | Different domain. Potential integration partner. |

### Why We Win

1. **Price:** Free vs. $500-1,000/month
2. **Data ownership:** Yours vs. theirs
3. **AI depth:** 50+ agents vs. none
4. **Failure intelligence:** Unique dataset nobody else has
5. **Manufacturing revival:** Completely untapped niche
6. **Open-source trust:** Auditable, customizable, community-driven

---

## 21. Risk Analysis & Mitigation

### Technical Risks

| Risk | Impact | Probability | Mitigation |
|---|---|---|---|
| API rate limits from data sources | Collectors stop working | High | Built-in rate limiter, rotating proxies, graceful degradation |
| Data quality issues | Bad scores, wrong insights | Medium | Data quality agent (Phase 6), deduplication, manual review |
| LLM hallucination in analysis | Incorrect conclusions | Medium | Confidence scoring, multi-agent cross-validation, human review |
| Infrastructure costs scale | Unprofitable at growth | Low | Cost tracking agent, Redis caching, ClickHouse for OLAP efficiency |
| Security vulnerability | Data breach | Low | JWT + RBAC (Phase 6), tenant isolation, regular security audits |

### Business Risks

| Risk | Impact | Probability | Mitigation |
|---|---|---|---|
| Crunchbase opens free tier | Commoditizes basic data | Low | Our value is AI analysis, not raw data |
| Low conversion from free to paid | Revenue below projections | Medium | Generous free tier builds trust; Pro features are genuinely valuable |
| Data source blocks scrapers | Reduced coverage | Medium | API-first approach, 24+ sources = redundancy |
| Open-source fork becomes competitor | Fragmented community | Low | Stay ahead with rapid development, community engagement, brand |
| Regulatory (GDPR, CCPA) | Compliance costs | Medium | Self-hosted = user controls their own compliance; clear docs |

---

## 22. 10-Year Vision

### Year 1-2: Foundation & Launch
- Complete Phases 4-6 (79 sessions total)
- Launch open-source on GitHub + Product Hunt
- First Pro and Enterprise customers
- **1,000 GitHub stars, $100K ARR**

### Year 3-4: Growth & Market Position
- Become the de facto open-source market intelligence platform
- Community contributors add new agents and collectors
- 10,000+ installs, 1,500 Pro subscribers
- **$3.5M ARR, 15-person team**

### Year 5-6: Platform Ecosystem
- Third-party developer marketplace (custom agents, collectors)
- API powers 200+ third-party applications
- Government and university partnerships
- Multi-language support (10+ languages)
- **$10M ARR, 40-person team**

### Year 7-8: Industry Standard
- Default tool taught in business schools
- Used by every major accelerator and VC firm
- Real-time global startup health index (like a "stock market for startups")
- Predictive models with 85%+ accuracy on startup outcomes
- **$25M ARR, 100-person team**

### Year 9-10: Global Intelligence Layer
- Largest open-source knowledge graph of business relationships
- Autonomous opportunity discovery (the platform finds opportunities before anyone)
- Cross-market arbitrage intelligence (failed here → succeeds there)
- Embedded in economic policy decisions
- **$50M+ ARR, self-sustaining open-source ecosystem**

---

## 23. Key Metrics & KPIs

### Development Metrics

| Metric | Current | Target (Phase 6) | Target (Year 3) |
|--------|---------|-------------------|-----------------|
| Agents | 35 | 50+ | 100+ |
| Collectors | 21 | 24 | 50+ |
| API endpoints | 23 | 40+ | 100+ |
| Tests | 467 | 500+ | 1,000+ |
| Schema version | 13 | 16+ | 20+ |
| Docker services | 12 | 18 | 25+ |

### Business Metrics

| Metric | Year 1 | Year 2 | Year 3 |
|--------|--------|--------|--------|
| GitHub stars | 1,000 | 5,000 | 15,000 |
| Free installs | 500 | 2,000 | 10,000 |
| Pro subscribers | 50 | 300 | 1,500 |
| Enterprise contracts | 2 | 10 | 30 |
| MRR | $7,950 | $54,700 | $280,000 |
| ARR | $100K | $731K | $3.56M |
| Data API calls/mo | 10K | 500K | 5M |

### Product Metrics

| Metric | Target |
|--------|--------|
| Signal freshness (time from event to alert) | < 15 minutes |
| API response time (p95) | < 500ms |
| Scoring latency | < 2 seconds |
| Dashboard load time | < 3 seconds |
| Search query latency | < 100ms (ClickHouse) |
| Knowledge graph traversal | < 200ms (3 hops) |
| Pipeline uptime | > 99.5% |
| Test coverage | > 85% |

---

## 24. Appendix

### A. Docker Compose Service Map (Target — 18 services)

```
EXISTING (4 services):
  mysql        MySQL 8.0 (operational DB)
  ollama       Local LLM inference
  api          FastAPI server
  streamlit    Internal dashboard

PHASE 1 ADDITIONS (2):
  kafka        Redpanda (Kafka-compatible)
  redis        Cache + pub/sub

PHASE 2 ADDITIONS (2):
  qdrant       Vector similarity search
  elasticsearch Full-text search

PHASE 3 ADDITIONS (4):
  clickhouse   OLAP analytics engine
  timescaledb  Time-series database
  nlp-worker   spaCy + SentenceTransformers microservice
  nextjs       Production dashboard

PHASE 4 ADDITIONS (3):
  dagster      Pipeline orchestration
  hasura       GraphQL engine
  prometheus   Metrics collection

PHASE 5 ADDITIONS (3):
  grafana      Monitoring dashboards
  age          Apache Age (graph DB on PostgreSQL)
  nginx        Reverse proxy + SSL termination
```

### B. Testing Strategy

```
Testing Pyramid:
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
```

### C. CI/CD Pipeline

```
GitHub Actions:
  1. Lint (ruff) + type-check (mypy)
  2. Unit tests (pytest)
  3. Integration tests (docker compose test-db)
  4. Build Docker images
  5. Push to container registry
  6. Deploy to staging → E2E smoke tests
  7. Manual approval → production deploy
```

### D. Key Open-Source Dependencies

| Library | Stars | Purpose |
|---|---|---|
| spaCy | 30k★ | NER, text classification |
| sentence-transformers | 15k★ | Semantic embeddings |
| FastAPI | 75k★ | REST API framework |
| Bytewax | 2.5k★ | Python stream processing |
| Qdrant | 20k★ | Vector similarity search |
| Apache Kafka | 28k★ | Event streaming |
| ClickHouse | 38k★ | OLAP analytics |
| Dagster | 12k★ | Pipeline orchestration |
| Next.js | 130k★ | Production dashboard |
| Grafana | 65k★ | Monitoring dashboards |

### E. Effort Summary

| Phase | Duration | New Files | Modified Files | New Deps |
|---|---|---|---|---|
| Phase 1: Foundation | 4-6 weeks | ~20 | ~9 | 4 |
| Phase 2: Intelligence | 6-8 weeks | ~20 | ~9 | 5 |
| Phase 3: Scale | 6-8 weeks | ~30 | ~7 | 5+ |
| Phase 4: Deep Collection | 4-6 weeks | ~14 | ~5 | 3 |
| Phase 5: Advanced Intelligence | 6-8 weeks | ~18 | ~5 | 4 |
| Phase 6: Operations | 8-10 weeks | ~25 | ~7 | 4 |
| **Total** | **38-56 weeks** | **~127** | **~42** | **~25** |

---

## License

This project is licensed under the **MIT License**.

---

*Last updated: June 5, 2026*
*Current progress: 38% complete (30/79 sessions)*
*Next session: 4.10 — NPM/PyPI Trends*
