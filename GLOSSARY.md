# 📋 Opportunity Intelligence Platform — Glossary & Data Dictionary

> Every term, metric, table, and concept explained in plain English

---

## Core Concepts

### Signal
Any piece of data from any source that tells us something about a startup or market.
```
Examples:
- A funding round announcement (funding_round signal)
- A job posting spike (job_posting_spike signal)
- A negative news article (news_mention signal)
- A patent filing (patent_filed signal)
- A GitHub repo trending (github_trend signal)
```

### SignalEnvelope
The standardized format that all signals are converted into, regardless of source.
```
Every signal becomes:
{
  signal_id, source, signal_type, entity_name, entity_type,
  timestamp, raw_data, normalized_data, confidence, dedup_hash
}
```

### Composite Score
The main score (0-100) that tells you how interesting an opportunity is.
```
How it's calculated:
  1. Gather all signals for an entity
  2. Weight each signal (funding = 25%, SEC = 20%, etc.)
  3. Apply time decay (recent signals matter more)
  4. Check for anomalies (unusual activity = boost)
  5. Calculate confidence (more signals = higher confidence)
  6. Output: "Neuromorphic Labs: Score 84.0"

What it means:
  0-30:   Not interesting
  30-50:  Watch
  50-70:  Interesting
  70-85:  High opportunity
  85-100: Exceptional opportunity
```

### Risk Score
A probability (0.0-1.0) that a startup will fail.
```
What it means:
  0.0-0.2: Very low risk (strong company)
  0.2-0.4: Low risk
  0.4-0.6: Medium risk (watch carefully)
  0.6-0.8: High risk (intervention needed)
  0.8-1.0: Very high risk (failure likely)
```

### Opportunity Score
How good a revival or investment opportunity is. Composite of:
```
  Market size (TAM/SAM/SOM)
  × Revival potential
  × Policy support
  × Talent availability
  × Competitive landscape
  × Timing
  = Score 0-100
```

### Knowledge Graph
A network of connected entities showing who is related to whom and how.
```
Nodes (entities):     startup, investor, person, technology, patent, region, sector
Edges (relationships): funded_by, founded_by, competes_with, uses_tech, located_in

Example:
  Neuromorphic Labs --funded_by--> Horizon Ventures
  Neuromorphic Labs --founded_by--> ex-Tesla engineer
  Neuromorphic Labs --competes_with--> QuantumScape
  Neuromorphic Labs --uses_tech--> PyTorch
  Neuromorphic Labs --located_in--> Austin, TX
```

### Entity Resolution
The process of figuring out that different names refer to the same entity.
```
"Meta" = "Facebook" = "Meta Platforms Inc." = "meta-platforms"
"OpenAI" = "Open AI" = "OpenAI Inc." = "openai"

How:
  1. Fuzzy string matching (Jaro-Winkler similarity)
  2. Abbreviation expansion
  3. Alias table lookup
  4. Context matching (same sector, same city = likely same entity)
```

### Time Decay
Recent signals are worth more than old signals. We use exponential decay.
```
Formula: freshness = e^(-λ × hours_since_event)

Signal half-lives:
  Funding round:  ~1 year  (λ=0.003) — funding from 1 year ago still matters
  SEC filing:     ~6 months (λ=0.005)
  Job posting:    ~2 months (λ=0.01)
  GitHub trend:   ~1 month  (λ=0.02)
  Social buzz:    ~2 weeks  (λ=0.03)
  Website change: ~1 week   (λ=0.05)
```

### Anomaly Detection
Detecting when something unusual is happening using Z-scores.
```
Z-score = (current_signal_count - average) / standard_deviation

  Z < 2.0: Normal
  Z 2.0-3.0: Unusual activity (anomaly multiplier: 1.05)
  Z > 3.0: Very unusual (anomaly multiplier: 1.10)

Example:
  Neuromorphic Labs normally gets 3 signals/week
  This week: 15 signals (Z-score = 2.8)
  → Anomaly detected! Score gets 5% boost
  → Alert fired: "Unusual activity detected"
```

### Feature Attribution
Explaining WHY a score is what it is. Every score comes with a breakdown.
```
Score: 84.0
Attribution:
  Funding round contributed +19.0 points (weight: 25, freshness: 0.95)
  SEC filing contributed +14.6 points (weight: 20, freshness: 0.97)
  Job postings contributed +12.2 points (weight: 15, freshness: 0.90)
  News coverage contributed +8.1 points (weight: 10, freshness: 0.95)
  GitHub activity contributed +6.4 points (weight: 10, freshness: 0.92)
  Social buzz contributed +3.5 points (weight: 5, freshness: 0.88)
```

### Complex Event Pattern
A combination of signals within a time window that means something special.
```
"Scaling Signal" = funding + hiring spike (within 30 days)
"Innovation Signal" = patent + GitHub trend + SEC filing (within 90 days)
"Distress Signal" = negative news + declining jobs (within 14 days)
"Pivot Signal" = tech change + job role shift + website change (within 45 days)
"Market Entry" = new competitor + competitor hiring (within 60 days)
```

---

## Database Tables (Key Tables)

### Core Tables

| Table | What's In It | Updated By |
|---|---|---|
| `failed_startups` | 35+ failed startup profiles with failure reasons, sectors, funding | Seed data + collectors |
| `news_articles` | News articles about startups, categorized and sentiment-scored | News collectors |
| `raw_signals` | All signals in SignalEnvelope format | All collectors |
| `sec_filings` | SEC EDGAR filings (10-K, 8-K, 10-Q) | SEC collector |
| `job_postings` | Job postings from boards | Job collector |
| `github_trends` | GitHub repo activity, star velocity | GitHub collectors |
| `funding_events` | Funding rounds from Crunchbase/AngelList | Funding collector |
| `patent_filings` | USPTO patent filings and citations | Patent collector |
| `social_posts` | Reddit posts, HN stories, tweets | Social collectors |

### Intelligence Tables

| Table | What's In It | Updated By |
|---|---|---|
| `opportunity_scores` | Composite scores with attribution | Scoring engine |
| `signal_events` | Detected patterns (scaling, distress, etc.) | Stream processor |
| `kg_entities` | Knowledge graph entities (12 types) | Knowledge graph agent |
| `kg_relationships` | Knowledge graph edges (20+ types) | Knowledge graph agent |
| `kg_entity_aliases` | Entity name aliases | Entity resolver |
| `vector_embeddings` | Text embeddings for semantic search | NLP pipeline |
| `risk_scores` | Startup failure risk predictions | Risk scorer |

### Phase 4 Tables (New)

| Table | What's In It | Updated By |
|---|---|---|
| `company_profiles` | Company data from OpenCorporates | OpenCorporates collector |
| `arxiv_papers` | Research paper signals | arXiv collector |
| `product_launches` | Product Hunt launches | Product Hunt collector |
| `website_snapshots` | Website change history | Website monitor |
| `so_tag_stats` | Stack Overflow tag trends | StackOverflow collector |
| `package_downloads` | NPM/PyPI download trends | NPM/PyPI collector |
| `regulatory_filings` | Government regulatory filings | Regulatory collector |
| `newsletter_items` | Newsletter content | Newsletter collector |

---

## Agent Descriptions (Plain English)

| Agent | What It Does (In One Sentence) |
|---|---|
| **Orchestrator** | Runs all the other agents in the right order |
| **Collection** | Runs all the data collectors and saves to database |
| **Failure Pattern** | Finds common reasons why startups fail |
| **Survival Analysis** | Calculates the probability of surviving X years |
| **Revival Opportunity** | Finds failed startups that could be restarted |
| **Geographic Strategy** | Recommends the best location for a startup |
| **News Intelligence** | Reads and categorizes startup news |
| **Whale Investor** | Tracks big investors and where they put their money |
| **Risk Scorer** | Predicts the probability of startup failure (0-100%) |
| **Knowledge Graph** | Builds a map of who's connected to whom |
| **Entity Resolver** | Figures out when two names mean the same company |
| **NLP Enrichment** | Reads text and extracts companies, people, products |
| **Semantic Search** | Finds similar content by meaning, not just keywords |
| **Opportunity Scorer** | Calculates the overall opportunity score (0-100) |
| **Report Generator** | Creates weekly and monthly reports automatically |
| **Alert Dispatcher** | Sends notifications via Slack, email, Discord |
| **AI Analyst** | Answers natural language questions about the data |
| **Market Sizing** | Estimates how big a market is (TAM/SAM/SOM) |
| **Competitive Landscape** | Maps competitors and their market positions |
| **Founder Background** | Researches founder track records |
| **Technology Stack** | Detects what technologies a startup uses |
| **Moat Analyzer** | Evaluates how defensible a startup's advantage is |
| **Timing Agent** | Determines if now is the right time for a sector |
| **Graph Traversal** | Finds paths and connections in the knowledge graph |
| **Community Detector** | Finds clusters of related people/companies |
| **Influence Propagation** | Determines who influences whom in the network |
| **Temporal Graph** | Tracks how relationships change over time |
| **Topic Modeling** | Discovers emerging themes across all data |
| **Trend Detector** | Identifies trends before they peak |
| **Sector Rotation** | Tracks capital flow between industry sectors |
| **Cohort Analysis** | Compares groups of startups by year/sector/geography |

---

## Metrics & KPIs Explained

### Platform Metrics

| Metric | What It Means | Target |
|---|---|---|
| **Signals per day** | How many data points collected daily | 500+ |
| **Signal freshness** | Time from real-world event to database | < 15 min |
| **Score accuracy** | Do high-scored entities actually succeed? | > 75% |
| **Pipeline uptime** | Is the system running without failures? | > 99.5% |
| **Agent coverage** | What % of entities have agent analysis? | > 80% |
| **Knowledge graph density** | How interconnected the graph is | Growing |

### Business Metrics

| Metric | What It Means | Formula |
|---|---|---|
| **MRR** | Monthly Recurring Revenue | Sum of all monthly subscriptions |
| **ARR** | Annual Recurring Revenue | MRR × 12 |
| **ARPU** | Average Revenue Per User | MRR / total paying users |
| **CAC** | Customer Acquisition Cost | Sales+marketing spend / new customers |
| **LTV** | Lifetime Value | ARPU × average lifetime in months |
| **Churn rate** | % of customers leaving per month | Lost customers / total customers |
| **Conversion rate** | % of free users becoming paid | Paid users / total free users |

---

## Abbreviations

| Abbreviation | Full Term |
|---|---|
| **OIP** | Opportunity Intelligence Platform |
| **TAM** | Total Addressable Market |
| **SAM** | Serviceable Addressable Market |
| **SOM** | Serviceable Obtainable Market |
| **NLP** | Natural Language Processing |
| **NER** | Named Entity Recognition |
| **ML** | Machine Learning |
| **LLM** | Large Language Model |
| **KG** | Knowledge Graph |
| **SSE** | Server-Sent Events |
| **WS** | WebSocket |
| **OLAP** | Online Analytical Processing |
| **API** | Application Programming Interface |
| **RBAC** | Role-Based Access Control |
| **JWT** | JSON Web Token |
| **MRR** | Monthly Recurring Revenue |
| **ARR** | Annual Recurring Revenue |
| **LTV** | Lifetime Value |
| **CAC** | Customer Acquisition Cost |
| **BLS** | Bureau of Labor Statistics |
| **SEC** | Securities and Exchange Commission |
| **USPTO** | United States Patent and Trademark Office |
| **EDGAR** | Electronic Data Gathering, Analysis, and Retrieval |
| **CI/CD** | Continuous Integration / Continuous Deployment |
| **GTM** | Go-To-Market |

---

*Last updated: June 5, 2026*
