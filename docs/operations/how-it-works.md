# 🔄 Opportunity Intelligence Platform — How It Works: The Complete Process

> Step-by-step breakdown of how data flows from source to intelligence
> From raw signals to actionable decisions

---

## Table of Contents

1. [The Big Picture — End-to-End Flow](#1-the-big-picture--end-to-end-flow)
2. [Step 1: Data Collection (How We Gather Signals)](#2-step-1-data-collection)
3. [Step 2: Signal Normalization (Making Data Uniform)](#3-step-2-signal-normalization)
4. [Step 3: Stream Processing (Real-Time Pipeline)](#4-step-3-stream-processing)
5. [Step 4: NLP Enrichment (Understanding Text)](#5-step-4-nlp-enrichment)
6. [Step 5: Knowledge Graph (Connecting Everything)](#6-step-5-knowledge-graph)
7. [Step 6: Scoring Engine (Ranking Opportunities)](#7-step-6-scoring-engine)
8. [Step 7: Agent Analysis (Deep Intelligence)](#8-step-7-agent-analysis)
9. [Step 8: Alerting (Notifying Users)](#9-step-8-alerting)
10. [Step 9: Reporting (Automated Output)](#10-step-9-reporting)
11. [Step 10: User Access (Dashboard + API + Chat)](#11-step-10-user-access)
12. [The Full Loop — How It Self-Improves](#12-the-full-loop--how-it-self-improves)
13. [Timing — How Long Each Step Takes](#13-timing--how-long-each-step-takes)

---

## 1. The Big Picture — End-to-End Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  REAL WORLD EVENT                                                       │
│  "Startup X raises $5M Series A"                                        │
│                                                                         │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 1: COLLECTION                                                     │
│  Collector detects the event from Crunchbase API, TechCrunch RSS,       │
│  SEC EDGAR 8-K filing, or Twitter/X announcement                        │
│                                                                         │
│  Time: Minutes to hours after the event                                 │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 2: NORMALIZATION                                                  │
│  Raw data is converted to standard SignalEnvelope format:               │
│  { source, entity, signal_type, value, timestamp, confidence }          │
│                                                                         │
│  Dual-write: MySQL (durable) + Kafka (real-time)                        │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 3: STREAM PROCESSING (Bytewax 5-stage pipeline)                   │
│  Kafka topic → Ingest → Enrich → Aggregate → Score → Output            │
│                                                                         │
│  Detects complex patterns:                                              │
│  "Funding round + Hiring spike + Patent filed = Innovation Signal"      │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 4: NLP ENRICHMENT                                                 │
│  spaCy NER extracts: entities, relationships, categories                │
│  Sentence-Transformers generate embeddings for semantic search          │
│  LLM (Ollama) summarizes and classifies                                │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 5: KNOWLEDGE GRAPH                                                │
│  Entities linked: Startup X → funded_by → VC Fund Y                     │
│  Entity resolution: "Startup X Inc." = "StartupX" = "startup-x"        │
│  Graph grows with every new signal                                      │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 6: SCORING ENGINE                                                 │
│  Composite score calculated:                                            │
│  Funding (25%) + SEC filing (20%) + Jobs (15%) + Patents (12%)         │
│  + GitHub (10%) + News (10%) + Social (5%) + Website (3%)              │
│                                                                         │
│  Time decay: Recent signals weighted higher                             │
│  Anomaly detection: Z-score spike = boost                              │
│  Feature attribution: "Scored 78.5 because funding contributed 18.2"   │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 7: AGENT ANALYSIS (50+ specialized agents)                        │
│  Failure Pattern Agent: "3 similar startups failed due to supply chain" │
│  Risk Scorer: "Failure probability: 0.35 in 18 months"                 │
│  Revival Agent: "Manufacturing revival opportunity: 82/100"            │
│  Market Viability: "US market saturation: 45%, India: 22%"             │
│  Whale Investor: "VC Fund Y also invested in Competitor Z"             │
│  Geographic Strategy: "Texas has 3x survival rate vs Ohio"             │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 8: ALERTING                                                       │
│  If score > threshold OR anomaly detected:                              │
│  → Slack notification to #opportunities channel                         │
│  → Email digest to investor@vc.com                                      │
│  → Webhook to CRM system                                                │
│  → Dashboard red highlight                                              │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 9: REPORTING                                                      │
│  Daily: New signals, score changes, alerts triggered                    │
│  Weekly: Sector trends, new opportunities, risk updates                 │
│  Monthly: Deep-dive analysis, market shifts, portfolio review           │
│                                                                         │
│  Formats: Markdown, HTML, PDF, Email                                    │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 10: USER ACCESS                                                   │
│  Dashboard: Interactive charts, tables, knowledge graph visualization   │
│  API: REST + GraphQL + WebSocket + SSE for integrations                 │
│  AI Chat: "Why did Startup X fail?" → instant answer                    │
│  Search: Semantic + fulltext + hybrid across all data                   │
│                                                                         │
│  User sees: Score 78.5, Rising trend, 3 similar failures,              │
│  Revival opportunity 82%, Best geography: Texas                         │
│  DECISION MADE                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Step 1: Data Collection

### What Happens

24 collectors continuously monitor data sources. Each collector:
1. Checks the source at its configured frequency
2. Fetches new data (API call, RSS parse, web scrape)
3. Deduplicates against existing records
4. Normalizes into a standard format
5. Writes to MySQL (durable storage)
6. Publishes to Kafka (real-time stream)

### Example: A Funding Round Is Announced

```
9:00 AM  TechCrunch publishes: "Neuromorphic Labs raises $5M Series A"
          Google News RSS picks it up

9:02 AM  TechCrunch RSS collector runs
          → Fetches article: title, content, date, categories
          → Writes to MySQL: news_articles table
          → Publishes to Kafka: topic "raw.signals"

9:05 AM  Crunchbase API collector runs
          → Detects new funding round: Neuromorphic Labs, $5M, Series A
          → Writes to MySQL: funding_events table
          → Publishes to Kafka: topic "raw.signals"

9:15 AM  SEC EDGAR collector runs
          → Detects 8-K filing from Neuromorphic Labs
          → Writes to MySQL: sec_filings table
          → Publishes to Kafka: topic "raw.signals"

9:30 AM  Twitter/X collector runs
          → Detects tweets from founders, investors mentioning the round
          → Writes to MySQL: social_posts table
          → Publishes to Kafka: topic "raw.signals"
```

### All 24 Collectors and What They Capture

| # | Collector | What It Captures | How Often | Example Signal |
|---|---|---|---|---|
| 1 | Google News RSS | Startup news articles | Every 15 min | "Company X shuts down" |
| 2 | TechCrunch RSS | Tech/startup news | Every 15 min | "Startup raises $10M" |
| 3 | BLS Survival Rates | Business survival stats | Monthly | "Manufacturing 5yr survival: 42%" |
| 4 | Failory Scraper | Failed startup profiles | Weekly | "Startup X failed due to market fit" |
| 5 | Reshoring PDF | Manufacturing reshoring data | Monthly | "500 jobs reshored to Ohio" |
| 6 | CrunchBase | Funding rounds, company data | Daily | "Series B $20M raised" |
| 7 | SEC EDGAR | 10-K, 8-K, 10-Q filings | Every 4 hours | "8-K: Material event filed" |
| 8 | Job Postings | Hiring data from boards | Every 6 hours | "12 ML engineer jobs posted" |
| 9 | GitHub Trends | Repo stars, activity | Hourly | "Stars up 500% this week" |
| 10 | Funding Events | Crunchbase/AngelList funding | Every 4 hours | "Angel round $500K" |
| 11 | Patents (USPTO) | Patent filings and citations | Daily | "Patent filed: AI chip design" |
| 12 | Social Media | Reddit + Hacker News posts | Real-time stream | "r/startups: positive sentiment" |
| 13 | GitHub Deep | Commit velocity, languages, contributors | Hourly | "300 commits this month" |
| 14 | Reddit Stream | Real-time subreddit monitoring | Real-time | "Post trending in r/SaaS" |
| 15 | HN Live | Hacker News live stories | Real-time | "Show HN: New AI tool" |
| 16 | OpenCorporates | 220M+ company profiles | Weekly | "Company registered in Delaware" |
| 17 | arXiv Papers | Research paper signals | Daily | "New paper on solid-state batteries" |
| 18 | Product Hunt | Product launches, upvotes | Daily | "Product launched, 500 upvotes" |
| 19 | Website Monitor | Pricing/page changes | Daily | "Pricing page updated" |
| 20 | Twitter/X | Real-time tweets, sentiment | Real-time | "CEO tweets about pivot" |
| 21 | Stack Overflow | Tag trends, developer adoption | Daily | "React Native questions up 40%" |
| 22 | NPM/PyPI | Package download trends | Daily | "Library downloads up 200%" |
| 23 | Regulatory | Government regulatory filings | Daily | "New EPA regulation proposed" |
| 24 | Newsletter | Industry newsletter aggregation | Daily | "Curated startup intelligence" |

---

## 3. Step 2: Signal Normalization

### The Problem

Every collector produces data in a different format:
```
TechCrunch: {"headline": "...", "body": "...", "published": "2024-01-15"}
Crunchbase:  {"company_name": "...", "funding_round": "Series A", "amount_usd": 5000000}
SEC EDGAR:   {"filing_type": "8-K", "cik": "0001234567", "filed_date": "2024-01-15"}
GitHub:      {"repo": "...", "stargazers_count": 4500, "language": "Python"}
```

### The Solution: SignalEnvelope

Every signal is normalized into a standard format:

```python
{
    "signal_id": "sig_20240115_001",
    "source": "crunchbase",           # Which collector
    "signal_type": "funding_round",   # Type of signal
    "entity_name": "Neuromorphic Labs",
    "entity_type": "startup",
    "timestamp": "2024-01-15T09:05:00Z",
    "raw_data": { ... },              # Original data
    "normalized_data": {
        "amount": 5000000,
        "round": "Series A",
        "investors": ["VC Fund A", "Angel B"],
        "sector": "AI/ML",
        "country": "US"
    },
    "confidence": 0.95,
    "dedup_hash": "a1b2c3d4..."       # For deduplication
}
```

### Where Signals Go

```
SignalEnvelope
    │
    ├── MySQL (durable)          → raw_signals table
    │   Used for: Historical queries, reporting, audit trail
    │
    ├── Kafka (real-time)        → "raw.signals" topic
    │   Used for: Stream processing, real-time alerts
    │
    ├── Qdrant (vectors)         → Embeddings for semantic search
    │   Used for: "Find similar startups" queries
    │
    └── Elasticsearch (fulltext) → Search index
        Used for: Keyword search, fuzzy matching
```

---

## 4. Step 3: Stream Processing

### The Bytewax 5-Stage Pipeline

```
Kafka "raw.signals" topic
    │
    ▼
╔══════════════════════════════════════════════════════════════════════╗
║  STAGE 1: INGEST                                                     ║
║  • Parse SignalEnvelope                                              ║
║  • Validate required fields                                          ║
║  • Check dedup hash — skip if already processed                      ║
║  • Assign processing timestamp                                       ║
╚════════════════════════╦═════════════════════════════════════════════╝
                         │
                         ▼
╔══════════════════════════════════════════════════════════════════════╗
║  STAGE 2: ENRICH                                                     ║
║  • Run spaCy NER — extract entities (companies, people, products)    ║
║  • Generate embeddings — Sentence-Transformers → 384-dim vectors     ║
║  • Classify signal — funding, failure, hiring, product, regulatory   ║
║  • Extract relationships — "Company X raised from VC Y"              ║
║  • Sentiment analysis — positive (0.7), negative (-0.5), neutral     ║
╚════════════════════════╦═════════════════════════════════════════════╝
                         │
                         ▼
╔══════════════════════════════════════════════════════════════════════╗
║  STAGE 3: AGGREGATE                                                  ║
║  • Window signals by entity + time (30-day tumbling window)          ║
║  • Count signals per entity: "Neuromorphic Labs: 8 signals in 30d"   ║
║  • Detect complex event patterns (see below)                         ║
║  • Correlate across sources: funding + hiring + news = strong signal  ║
╚════════════════════════╦═════════════════════════════════════════════╝
                         │
                         ▼
╔══════════════════════════════════════════════════════════════════════╗
║  STAGE 4: SCORE                                                      ║
║  • Calculate composite score using weighted formula                   ║
║  • Apply time decay: recent signals matter more                      ║
║  • Detect anomalies: Z-score > 2.0 = unusual activity                ║
║  • Generate feature attribution: "Funding contributed 18.2 points"   ║
║  • Determine trend: rising, stable, declining                        ║
╚════════════════════════╦═════════════════════════════════════════════╝
                         │
                         ▼
╔══════════════════════════════════════════════════════════════════════╗
║  STAGE 5: OUTPUT                                                     ║
║  • Write score to MySQL (opportunity_scores table)                   ║
║  • Write aggregates to ClickHouse (OLAP analytics)                   ║
║  • Write time-series to TimescaleDB (trends over time)               ║
║  • If anomaly or threshold breached → trigger alert                  ║
║  • Publish to "enriched.signals" Kafka topic                         ║
║  • Push SSE event to connected dashboards                            ║
╚══════════════════════════════════════════════════════════════════════╝
```

### Complex Event Pattern Detection

The stream processor doesn't just score individual signals — it detects **combinations** of signals that mean something special:

```
PATTERN: "Scaling Signal"
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  IF: funding_round detected for Entity X                 │
│  AND: hiring_spike detected for Entity X (5+ jobs)       │
│  WITHIN: 30 days                                         │
│                                                          │
│  THEN: Score boost +15                                   │
│  ALERT: "Entity X is scaling — funding + hiring"         │
│                                                          │
│  EXAMPLE:                                                │
│  Jan 5: Neuromorphic Labs raises $5M Series A            │
│  Jan 12: Posts 8 ML engineer positions on LinkedIn       │
│  → PATTERN FIRED: Scaling Signal (+15 boost)             │
│                                                          │
└──────────────────────────────────────────────────────────┘

PATTERN: "Innovation Signal"
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  IF: patent_filed for Entity X                           │
│  AND: github_trend for Entity X (star velocity > 100/wk) │
│  AND: sec_filing (8-K) for Entity X                      │
│  WITHIN: 90 days                                         │
│                                                          │
│  THEN: Score boost +20                                   │
│  ALERT: "Entity X shows innovation signals"              │
│                                                          │
└──────────────────────────────────────────────────────────┘

PATTERN: "Distress Signal"
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  IF: negative_news for Entity X (sentiment < -0.5)       │
│  AND: declining_jobs for Entity X (posting rate down 30%)│
│  WITHIN: 14 days                                         │
│                                                          │
│  THEN: Score penalty -10                                 │
│  ALERT: "Entity X showing distress signals"              │
│  RISK: Failure probability increases                     │
│                                                          │
└──────────────────────────────────────────────────────────┘

PATTERN: "Pivot Signal"
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  IF: tech_stack_change detected                          │
│  AND: job_role_shift detected (different roles posting)  │
│  AND: website_change detected (messaging updated)        │
│  WITHIN: 45 days                                         │
│                                                          │
│  THEN: Score adjustment +12                              │
│  ALERT: "Entity X may be pivoting"                       │
│                                                          │
└──────────────────────────────────────────────────────────┘

PATTERN: "Market Entry"
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  IF: new_competitor_funding in same sector               │
│  AND: competitor_hiring_spike in same sector             │
│  WITHIN: 60 days                                         │
│                                                          │
│  THEN: Score adjustment +10                              │
│  ALERT: "New competitor entering [sector] space"         │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## 5. Step 4: NLP Enrichment

### What NLP Does to Raw Text

```
INPUT: Raw news article
"Neuromorphic Labs, an AI chip startup based in Austin, TX, announced today
that it has raised $5 million in Series A funding led by Horizon Ventures
with participation from angel investor Sarah Chen. The company plans to use
the funding to expand its engineering team and accelerate product development."

    │
    ▼
╔══════════════════════════════════════════════════════╗
║  NAMED ENTITY RECOGNITION (spaCy)                    ║
║                                                      ║
║  Companies:   [Neuromorphic Labs]                    ║
║  People:      [Sarah Chen]                           ║
║  Investors:   [Horizon Ventures]                     ║
║  Location:    [Austin, TX]                           ║
║  Money:       [$5 million]                           ║
║  Product:     [AI chip]                              ║
║  Event:       [Series A funding]                     ║
╚══════════════════╦═══════════════════════════════════╝
                   │
                   ▼
╔══════════════════════════════════════════════════════╗
║  RELATIONSHIP EXTRACTION                             ║
║                                                      ║
║  Neuromorphic Labs --funded_by--> Horizon Ventures   ║
║  Neuromorphic Labs --funded_by--> Sarah Chen         ║
║  Neuromorphic Labs --located_in--> Austin, TX        ║
║  Neuromorphic Labs --produces--> AI chip             ║
║  Neuromorphic Labs --funding_round--> Series A       ║
║  Sarah Chen --invests_in--> Neuromorphic Labs        ║
╚════════════════════╦═════════════════════════════════╝
                   │
                   ▼
╔══════════════════════════════════════════════════════╗
║  EMBEDDING GENERATION (Sentence-Transformers)        ║
║                                                      ║
║  Text → 384-dimensional vector                       ║
║  [0.023, -0.145, 0.678, ..., 0.034]                 ║
║                                                      ║
║  Purpose: Semantic similarity search                  ║
║  "Find articles similar to this one" → Qdrant        ║
╚════════════════════╦═════════════════════════════════╝
                   │
                   ▼
╔══════════════════════════════════════════════════════╗
║  CLASSIFICATION                                       ║
║                                                      ║
║  Category: funding                                    ║
║  Sub-category: series_a                              ║
║  Sector: AI/ML, Semiconductors                       ║
║  Sentiment: positive (0.75)                          ║
║  Urgency: medium                                     ║
╚════════════════════╦═════════════════════════════════╝
                   │
                   ▼
╔══════════════════════════════════════════════════════╗
║  SUMMARIZATION (Ollama LLM)                          ║
║                                                      ║
║  Summary: "Neuromorphic Labs raised $5M Series A     ║
║  from Horizon Ventures and Sarah Chen for team        ║
║  expansion and product development in AI chips."      ║
╚══════════════════════════════════════════════════════╝
```

---

## 6. Step 5: Knowledge Graph

### How the Graph Grows

```
BEFORE (No signals for Neuromorphic Labs):
┌──────────────────────┐
│  Graph has no entry  │
│  for this entity     │
└──────────────────────┘

AFTER STEP 1 (Funding round detected):
┌──────────────┐     funded_by     ┌──────────────────┐
│ Neuromorphic │ ───────────────── │ Horizon Ventures │
│    Labs      │ ───────────────── │ Sarah Chen       │
│  (startup)   │     funded_by     │   (investor)     │
└──────┬───────┘                   └──────────────────┘
       │
       │ located_in
       ▼
┌──────────────┐
│  Austin, TX  │
│  (region)    │
└──────────────┘

AFTER STEP 2 (Patent filed):
┌──────────────┐     funded_by     ┌──────────────────┐
│ Neuromorphic │ ───────────────── │ Horizon Ventures │
│    Labs      │     produces      │ Sarah Chen       │
│  (startup)   │ ──────────┐       └──────────────────┘
└──────┬───────┘           │
       │                   ▼
       │            ┌──────────────┐
       │ located_in │ US Patent    │
       ▼            │ #12,345,678  │
┌──────────────┐    │ (patent)     │
│  Austin, TX  │    └──────────────┘
└──────────────┘

AFTER STEP 3 (GitHub trending + Job postings):
┌──────────────┐  ──funded_by──→  ┌──────────────────┐
│ Neuromorphic │  ──produces───→  │ Horizon Ventures │
│    Labs      │  ──uses_tech──→  │ Sarah Chen       │
│  (startup)   │  ──hiring─────→  │ AI chip patent   │
└──────┬───────┘                  │ PyTorch          │
       │                          │ 12 job openings  │
       │ located_in               └──────────────────┘
       ▼
┌──────────────┐   competes_with   ┌──────────────┐
│  Austin, TX  │  ←──────────────  │ QuantumScape │
└──────────────┘                   │ (startup)    │
                                   └──────────────┘

LATER (Entity resolution discovers aliases):
"Neuromorphic Labs" = "Neuro Labs" = "neuromorphic-labs" = "NeuroLabs Inc."
→ All merged into single entity with alias table
```

### What the Graph Enables

```
QUERY: "Who else did Horizon Ventures invest in?"

Graph traversal (2 hops):
Neuromorphic Labs → funded_by → Horizon Ventures → funded → [Startup A, Startup B, Startup C]

RESULT: "Horizon Ventures also invested in:
  - Startup A (AI chip, failed 2022, supply chain issues)
  - Startup B (EV battery, active, raised Series B $20M)
  - Startup C (Solar manufacturing, failed 2021, regulatory issues)"

INSIGHT: "Horizon Ventures has pattern of investing in deep-tech manufacturing.
2 of 3 similar companies failed due to supply chain and regulatory issues.
Neuromorphic Labs should address these risks."
```

---

## 7. Step 6: Scoring Engine

### How a Score Is Calculated (Real Example)

```
ENTITY: Neuromorphic Labs
DATE: January 15, 2024

SIGNALS DETECTED (last 90 days):
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│  1. FUNDING ROUND (Jan 5, 2024)                                │
│     Weight: 25.0  │  Decay λ: 0.003  │  Age: 10 days          │
│     Freshness: e^(-0.003 × 240) = 0.487 → No, wait...         │
│     Freshness: e^(-0.003 × 10 × 24) = ...                     │
│     Simpler: freshness = 0.95 (very recent)                    │
│     Raw score: 80/100                                          │
│     Contribution: 25.0 × 0.80 × 0.95 = 19.0                   │
│                                                                │
│  2. SEC FILING (Jan 3, 2024)                                   │
│     Weight: 20.0  │  Freshness: 0.97                           │
│     Raw score: 75/100                                          │
│     Contribution: 20.0 × 0.75 × 0.97 = 14.55                  │
│                                                                │
│  3. JOB POSTING SPIKE (Jan 12, 2024)                           │
│     Weight: 15.0  │  Freshness: 0.90                           │
│     Raw score: 90/100 (12 jobs = strong spike)                 │
│     Contribution: 15.0 × 0.90 × 0.90 = 12.15                  │
│                                                                │
│  4. GITHUB TREND (Jan 10, 2024)                                │
│     Weight: 10.0  │  Freshness: 0.92                           │
│     Raw score: 70/100                                          │
│     Contribution: 10.0 × 0.70 × 0.92 = 6.44                   │
│                                                                │
│  5. NEWS MENTION (Jan 5, 2024)                                 │
│     Weight: 10.0  │  Freshness: 0.95                           │
│     Raw score: 85/100 (positive coverage)                      │
│     Contribution: 10.0 × 0.85 × 0.95 = 8.08                   │
│                                                                │
│  6. SOCIAL BUZZ (Jan 6-14, 2024)                               │
│     Weight: 5.0   │  Freshness: 0.88                           │
│     Raw score: 80/100 (Reddit + HN positive)                   │
│     Contribution: 5.0 × 0.80 × 0.88 = 3.52                    │
│                                                                │
│  MISSING SIGNALS:                                               │
│  - Patent filed: NO (penalty to confidence)                    │
│  - Website change: NO (minor)                                  │
│                                                                │
└────────────────────────────────────────────────────────────────┘

COMPOSITE SCORE CALCULATION:

  Numerator = 19.0 + 14.55 + 12.15 + 6.44 + 8.08 + 3.52 = 63.74
  Denominator = (25×0.95) + (20×0.97) + (15×0.90) + (10×0.92) + (10×0.95) + (5×0.88)
              = 23.75 + 19.4 + 13.5 + 9.2 + 9.5 + 4.4 = 79.75

  Base Score = 63.74 / 79.75 = 0.799 × 100 = 79.9

ANOMALY CHECK:
  Z-score of total signals: 2.8 (> 2.0 threshold)
  → Anomaly multiplier: 1.05 (5% boost)
  → Anomaly detected: TRUE

CONFIDENCE FACTOR:
  6 of 8 signals present = 0.75 confidence

FINAL SCORE:
  79.9 × 1.05 × 0.75 = 62.9 → ...

  Actually, confidence doesn't multiply the score directly.
  Confidence is reported separately.

  FINAL: 79.9 × 1.05 = 83.9 → rounded to 84.0
```

### What the User Sees

```json
{
  "entity_name": "Neuromorphic Labs",
  "composite_score": 84.0,
  "trend": "rising",
  "anomaly_detected": true,
  "anomaly_z_score": 2.8,
  "confidence": 0.75,
  "attribution": [
    {"signal": "funding_round",    "contribution": 19.0,  "weight": 25, "freshness": 0.95},
    {"signal": "sec_filing",       "contribution": 14.55, "weight": 20, "freshness": 0.97},
    {"signal": "job_posting_spike","contribution": 12.15, "weight": 15, "freshness": 0.90},
    {"signal": "news_mention",     "contribution":  8.08, "weight": 10, "freshness": 0.95},
    {"signal": "github_trend",     "contribution":  6.44, "weight": 10, "freshness": 0.92},
    {"signal": "social_buzz",      "contribution":  3.52, "weight":  5, "freshness": 0.88}
  ],
  "missing_signals": ["patent_filed", "website_change"],
  "pattern_detected": "Scaling Signal (funding + hiring within 30 days)",
  "pattern_boost": "+15"
}
```

---

## 8. Step 7: Agent Analysis

### How 50+ Agents Analyze the Same Data

After the scoring engine produces a score, 50+ specialized agents run deeper analysis:

```
ENTITY: Neuromorphic Labs (Score: 84.0)
                │
                ▼
┌───────────────────────────────────────────────────────────────────────┐
│                                                                       │
│  FAILURE PATTERN AGENT                                                │
│  "3 similar AI chip startups failed in 2019-2023"                     │
│  "Common cause: Supply chain dependency on TSMC"                      │
│  "Second cause: Customer concentration (>60% revenue from 1 client)"  │
│  "Failure probability in this pattern: 67%"                           │
│                                                                       │
│  SURVIVAL ANALYSIS AGENT                                              │
│  "Austin, TX semiconductor startups: 58% survive 3 years"             │
│  "AI chip sector: 42% survive 5 years"                                │
│  "Series A funded: 65% make it to Series B"                           │
│                                                                       │
│  REVIVAL OPPORTUNITY AGENT                                            │
│  "2 failed AI chip startups had revivable IP"                         │
│  "Patent portfolio from ChipForge (failed 2022) available"            │
│  "Revival opportunity score: 82/100"                                  │
│  "CHIPS Act eligible: Yes ($5-50M potential subsidy)"                 │
│                                                                       │
│  RISK SCORER                                                          │
│  "Overall risk: 0.35 (low)"                                           │
│  "Supply chain risk: 0.65 (medium) — single fab dependency"           │
│  "Market risk: 0.25 (low) — growing demand"                           │
│  "Team risk: 0.20 (low) — experienced founders"                       │
│  "Regulatory risk: 0.15 (low) — CHIPS Act supportive"                 │
│                                                                       │
│  WHALE INVESTOR AGENT                                                 │
│  "Horizon Ventures invested in 15 AI/ML startups"                     │
│  "12 of 15 are still active (80% success rate)"                       │
│  "Horizon typically follows on (Series B probability: 70%)"           │
│  "Sarah Chen is ex-Google AI, strong network signal"                  │
│                                                                       │
│  GEOGRAPHIC STRATEGY AGENT                                            │
│  "Austin, TX: #3 metro for semiconductor jobs"                        │
│  "Texas tax incentives: 10-year property tax abatement"               │
│  "Compare: Ohio (similar incentives, lower talent pool)"              │
│  "Compare: Arizona (best incentives, growing talent pool)"            │
│  "Recommendation: Stay in Austin"                                     │
│                                                                       │
│  GLOBAL MARKET VIABILITY AGENT                                        │
│  "US AI chip market: $45B TAM, 35% growth YoY"                        │
│  "India AI chip market: $8B TAM, 52% growth YoY (faster growth)"     │
│  "EU AI chip market: $12B TAM, 28% growth YoY"                        │
│  "Best market for expansion: US (current), India (Year 3-4)"          │
│                                                                       │
│  KNOWLEDGE GRAPH AGENT                                                │
│  "Neuromorphic Labs is 2 hops from NVIDIA (via shared investor)"      │
│  "Competitor QuantumScape is 1 hop away (same sector, Austin)"        │
│  "3 former Tesla engineers founded similar startups (2 succeeded)"    │
│                                                                       │
│  NEWS INTELLIGENCE AGENT                                              │
│  "15 positive articles in last 30 days"                               │
│  "Key themes: 'AI chip innovation', 'Austin tech boom'"               │
│  "No negative coverage detected"                                      │
│  "Media sentiment trend: improving (+0.12 this month)"                │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

### How Agents Coordinate

```
Orchestrator calls agents in dependency order:

Level 1 (Independent — run first, in parallel):
  ├── Collection Agent (gather data)
  ├── Failure Pattern Agent
  ├── Survival Analysis Agent
  ├── Knowledge Graph Agent
  └── News Intelligence Agent

Level 2 (Depends on Level 1):
  ├── Revival Opportunity Agent (needs failure patterns)
  ├── Geographic Strategy Agent (needs survival data)
  ├── Risk Scorer (needs failure + survival + news)
  └── Whale Investor Agent (needs knowledge graph)

Level 3 (Depends on Level 2):
  ├── Global Market Viability (needs geographic strategy)
  └── Opportunity Pipeline Agent (needs all above)

Level 4 (Final synthesis):
  ├── Report Generator (compiles all agent outputs)
  ├── Alert Dispatcher (checks thresholds)
  └── Dashboard Agent (updates visualizations)
```

---

## 9. Step 8: Alerting

### When and How Alerts Fire

```
THRESHOLD CHECK (after scoring):
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  IF opportunity_score > 80                              │
│  THEN → Send "High Opportunity" alert                   │
│                                                         │
│  IF risk_score > 0.7                                    │
│  THEN → Send "High Risk" alert                          │
│                                                         │
│  IF anomaly_detected == true AND z_score > 2.5          │
│  THEN → Send "Anomaly" alert                            │
│                                                         │
│  IF pattern_detected in ["Distress Signal"]             │
│  THEN → Send "Distress" alert                           │
│                                                         │
│  IF new_failed_startup in watched_sectors               │
│  THEN → Send "Sector Alert"                             │
│                                                         │
└─────────────────────────────────────────────────────────┘

ALERT CHANNELS:
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  Slack:       #opportunities channel                    │
│               "🚀 Neuromorphic Labs: Score 84.0         │
│                Rising trend. Scaling signal detected.    │
│                $5M Series A from Horizon Ventures."      │
│                                                         │
│  Email:       Daily digest at 8 AM                      │
│               "Top 5 opportunities today..."             │
│                                                         │
│  Discord:     #signals channel                          │
│               Real-time alerts for community             │
│                                                         │
│  Webhook:     POST to your-server.com/webhook           │
│               JSON payload with full signal data         │
│                                                         │
│  Dashboard:   Red/green highlighting                    │
│               Push notification via SSE                  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 10. Step 9: Reporting

### Automated Report Types

```
DAILY REPORT (generated at 8 AM):
┌─────────────────────────────────────────────────────────┐
│  Opportunity Intelligence — Daily Digest                 │
│  January 15, 2024                                        │
│                                                          │
│  📊 TOP 5 OPPORTUNITIES                                  │
│  1. Neuromorphic Labs — Score: 84.0 (↑ +12.5)          │
│  2. SolarGrid Systems — Score: 79.3 (↑ +3.1)           │
│  3. BioTech Innovations — Score: 76.8 (new)             │
│  4. EV Battery Corp — Score: 74.2 (→ stable)           │
│  5. CleanEnergy Mfg — Score: 72.1 (↓ -1.3)            │
│                                                          │
│  🚨 ALERTS TRIGGERED                                    │
│  - Scaling signal: Neuromorphic Labs                    │
│  - Distress signal: OldFactory Inc. (risk: 0.78)       │
│  - New competitor: Quantum Chips entered AI chip sector │
│                                                          │
│  📈 SIGNALS COLLECTED                                    │
│  - 145 news articles                                    │
│  - 23 funding events                                    │
│  - 12 SEC filings                                       │
│  - 89 Reddit posts                                      │
│  - 34 GitHub trending repos                             │
│                                                          │
│  🏭 MANUFACTURING REVIVAL                               │
│  - 3 new reshoring announcements                        │
│  - CHIPS Act: 2 new applications                        │
│  - Best revival opportunity: PCB Assembly (score: 82)  │
│                                                          │
└─────────────────────────────────────────────────────────┘

WEEKLY REPORT (generated Sunday 6 AM):
  - Full sector analysis
  - Trend comparisons vs. last week
  - New failed startups + pattern analysis
  - Market correlation changes
  - Agent performance metrics
  - Top 10 opportunities with detailed attribution

MONTHLY REPORT (generated 1st of month):
  - Deep-dive into 3-5 key sectors
  - Geographic strategy updates
  - Investor activity summary
  - Knowledge graph growth metrics
  - Score accuracy review (did predictions hold?)
  - Recommended watchlist updates
```

---

## 11. Step 10: User Access

### How Different Users Interact

```
FOUNDER:
┌─────────────────────────────────────────────────────────┐
│  Opens dashboard → sees opportunity map                  │
│  Searches: "AI chip manufacturing"                       │
│  Finds: 3 failed startups, 2 success stories            │
│  Clicks "Revival Opportunity" → sees score 82/100       │
│  Asks AI Chat: "Why did the 3 fail?"                    │
│  Gets: "Supply chain, talent shortage, regulatory"      │
│  Asks: "Best city to start?"                            │
│  Gets: "Austin TX (score 85) or Phoenix AZ (score 78)"  │
│  Downloads report as PDF                                │
│  DECISION: Starts company in Austin with supply chain    │
│  strategy informed by failure data                      │
└─────────────────────────────────────────────────────────┘

INVESTOR:
┌─────────────────────────────────────────────────────────┐
│  Gets Slack alert at 9:05 AM                            │
│  "Neuromorphic Labs: Score 84, Scaling Signal"          │
│  Opens API → pulls full score with attribution          │
│  Sees: Funding $5M + 12 jobs + positive news            │
│  Checks knowledge graph: founder's network              │
│  Sees: "Founder worked at Tesla (5 yrs), Stanford PhD"  │
│  Checks risk: 0.35 (low)                                │
│  Checks comparable: "Similar to QuantumScape pre-Series A│
│  which returned 40x"                                    │
│  DECISION: Schedules meeting with founder               │
└─────────────────────────────────────────────────────────┘

RESEARCHER:
┌─────────────────────────────────────────────────────────┐
│  Queries API: "All AI chip startups, 2020-2024"         │
│  Gets: 45 startups, 30 failed, 15 active                │
│  Queries: "Failure reasons breakdown"                   │
│  Gets: Supply chain 40%, talent 25%, market 20%, other  │
│  Queries: "Survival by geography"                       │
│  Gets: Austin 58%, Silicon Valley 52%, Boston 48%       │
│  Downloads: CSV for statistical analysis                │
│  DECISION: Publishes paper on AI chip startup survival  │
└─────────────────────────────────────────────────────────┘

GOVERNMENT POLICYMAKER:
┌─────────────────────────────────────────────────────────┐
│  Opens enterprise dashboard                             │
│  Views: "Manufacturing sector health index"             │
│  Sees: Semiconductor reshoring up 35% YoY              │
│  Queries: "Which sectors need policy support?"          │
│  Gets: EV battery (high opportunity, policy gap)        │
│  Sees: "If 20% tax incentive → estimated 5,000 jobs"   │
│  Downloads: Policy brief PDF                            │
│  DECISION: Proposes EV battery manufacturing incentive  │
└─────────────────────────────────────────────────────────┘
```

---

## 12. The Full Loop — How It Self-Improves

```
WEEK 1:
  Score for "Startup X" = 75.0
  Based on: funding + hiring + news

WEEK 4:
  New signal: Startup X lays off 20% of staff
  Score drops to 55.0
  Pattern detected: "Distress Signal"

WEEK 8:
  Startup X files for bankruptcy
  Score drops to 10.0

WEEK 9 (SELF-IMPROVEMENT):
  The ML model reviews its predictions:
  "Did we predict this failure?"
  "Score was 55 at week 4 — we should have alerted earlier"
  "Distress signal was detected — good"
  "But we missed the layoff signal's importance"

  ADJUSTMENT:
  - Layoff signal weight increased from 5.0 → 10.0
  - Distress pattern threshold lowered from 14 days → 7 days
  - New pattern added: "Layoff + Executive Departure = Imminent Failure"

  NEXT TIME:
  Similar situation → alert fires 2 weeks earlier
  Score more accurately reflects risk
```

---

## 13. Timing — How Long Each Step Takes

### Real-Time Path (Minutes)

```
Event occurs in real world
    │
    ├─ 0-15 min: Collector detects event
    ├─ 0-1 sec:  Signal normalized
    ├─ 1-5 sec:  Stream processed (Bytewax)
    ├─ 1-3 sec:  NLP enrichment
    ├─ 1-2 sec:  Score calculated
    ├─ 1-5 sec:  Alert dispatched
    │
    ╰─ TOTAL: 15-25 minutes from real-world event to user alert
```

### Batch Path (Daily Pipeline)

```
Daily pipeline runs at 8 AM UTC
    │
    ├─ 0-5 min:   Run all collectors (fetch new data)
    ├─ 5-20 min:  Normalize + dedup signals
    ├─ 20-30 min: Stream processing (missed real-time events)
    ├─ 30-50 min: NLP enrichment (batch)
    ├─ 50-70 min: Knowledge graph update
    ├─ 70-85 min: Scoring engine (all entities)
    ├─ 85-100 min: Agent analysis (50+ agents)
    ├─ 100-110 min: Report generation
    ├─ 110-115 min: Alert dispatch
    ├─ 115-120 min: Dashboard update
    │
    ╰─ TOTAL: ~2 hours for full daily pipeline
```

### Weekly Deep Analysis

```
Weekly pipeline runs Sunday 6 AM UTC
    │
    ├─ 0-30 min:   Full collection refresh
    ├─ 30-60 min:  Cross-source correlation
    ├─ 60-120 min: Deep agent analysis (all agents, full data)
    ├─ 120-150 min: ML model retraining (if needed)
    ├─ 150-180 min: Knowledge graph full rebuild
    ├─ 180-200 min: Weekly report generation
    ├─ 200-210 min: Score accuracy review
    │
    ╰─ TOTAL: ~3.5 hours for weekly deep dive
```

---

*Last updated: June 5, 2026*
