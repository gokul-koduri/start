# ✂️ Problem → Feature Validation Map

> "A well-defined problem prevents building features that nobody needs."
> Every feature must earn its place by solving a documented problem for a real user.

---

## The Rule

```
BEFORE BUILDING ANY FEATURE, ANSWER THESE 4 QUESTIONS:

  1. WHICH PROBLEM does this solve?        (from PROBLEM_DEFINITION.md)
  2. WHICH USER has this problem?          (from the 8 user personas)
  3. HOW OFTEN does this problem occur?    (daily / weekly / rarely)
  4. WHAT HAPPENS if we don't build it?    (users leave / nice-to-have)

  If you can't answer all 4 → DON'T BUILD IT.
```

---

## Problem → Feature Map (The Keepers)

### PROBLEM 1: "I can't predict which startups will succeed or fail"

> Users: Founders, Investors, Job Seekers, M&A Teams
> Frequency: Every time they make a decision (daily/weekly)
> Impact: $50K-135M+ per wrong decision

| Feature | Agent/Component | Status | Why It Solves The Problem |
|---|---|---|---|
| **Composite Opportunity Score** | OpportunityScorerAgent | ✅ Built | Converts scattered signals into a single 0-100 number. User doesn't need to read 24 data sources. |
| **Risk Score (0-1.0)** | RiskScorerAgent | ✅ Built | Directly answers "will this startup fail?" Founder sees 0.65 → knows it's risky. Investor sees 0.2 → confident. |
| **Failure Pattern Matching** | FailurePatternAgent | ✅ Built | "3 similar startups failed for the same reason you're about to." This is the NTSB-for-startups function. |
| **Survival Probability** | SurvivalAnalysisAgent | ✅ Built | "Startups with your profile: 58% survive 3 years." Job seeker uses this to choose employer. |
| **Feature Attribution** | CompositeScorer output | ✅ Built | "Scored 84 because funding contributed 19 points." Without this, score is a black box nobody trusts. |
| **ML Failure Predictor** | MLPredictorAgent | ✅ Built | Machine-learned failure prediction from historical patterns. Complements rule-based scoring. |
| **Anomaly Detection** | Stream processor (Z-score) | ✅ Built | "15 signals this week vs. normal 3" = something unusual happening. Catches rapid changes. |

**Verdict: KEEP ALL. Every one directly solves "can I predict outcome?" Core value proposition.**

---

### PROBLEM 2: "I spend 20 hours researching each company manually"

> Users: Investors, Researchers, Journalists
> Frequency: Every deal / every paper / every article
> Impact: $1,000+ per company in labor; 18 months wasted per paper

| Feature | Agent/Component | Status | Why It Solves The Problem |
|---|---|---|---|
| **24 Automated Collectors** | All collectors | ✅ Built | Replaces manual browsing of Crunchbase, SEC, GitHub, news, Reddit, HN, patents, etc. Machine does in minutes what human does in 20 hours. |
| **Knowledge Graph** | KnowledgeGraphAgent | ✅ Built | "Founder → worked at Tesla → Tesla invested in Competitor X." Takes hours to research manually; graph returns in milliseconds. |
| **AI Chat (/api/chat)** | AIAnalystAgent | ✅ Built | "Why did Startup X fail?" → instant answer from all collected data. Replaces 20 hours of Googling. |
| **Semantic Search** | SemanticSearchAgent | ✅ Built | "Find startups similar to Neuromorphic Labs" → returns matches by meaning, not just keywords. |
| **Entity Resolution** | EntityResolverAgent | ✅ Built | "Meta" = "Facebook" = "Meta Platforms Inc." Without this, manual dedup takes hours. |
| **Report Generator** | ReportGeneratorAgent | ✅ Built | Weekly/monthly automated reports replace manual slide decks. |
| **Bulk Data Export** | API endpoints | ✅ Built | Researchers download CSV/JSON in seconds instead of scraping for months. |
| **Founder Background** | FounderBackgroundAgent | ✅ Built | "CEO: ex-Tesla 5 years, Stanford PhD, 1 exit." Would take 30 minutes of LinkedIn stalking manually. |
| **News Intelligence** | NewsIntelligenceAgent | ✅ Built | "15 positive articles in 30 days, sentiment +0.75." Replaces reading 15 articles. |
| **Competitive Landscape** | CompetitiveLandscapeAgent | ✅ Built | "12 competitors, 3 funded >$10M, white space: edge inference." Takes hours of manual research. |

**Verdict: KEEP ALL. Every one reduces research time from hours to seconds. Core value.**

---

### PROBLEM 3: "Crunchbase is expensive and shows raw data, not intelligence"

> Users: All 8 user types
> Frequency: Daily
> Impact: $490-1,000/mo per user wasted on raw databases

| Feature | Agent/Component | Status | Why It Solves The Problem |
|---|---|---|---|
| **Free & Open-Source** | Entire platform | ✅ Built | Crunchbase charges $490/mo. We're free. This alone is reason to switch for 90% of users. |
| **Self-Hostable** | Docker Compose | ✅ Built | Enterprises can't put data on Crunchbase's servers. Self-hosted = full data control. |
| **Real-Time Stream Processing** | Bytewax pipeline | ✅ Built | Crunchbase updates daily. We update in minutes. Real-time alerts on score changes. |
| **WebSocket Live Updates** | /ws/live | ✅ Built | Dashboard updates automatically. No refresh needed. Crunchbase has nothing like this. |
| **Explainable Scores** | Attribution in CompositeScorer | ✅ Built | "Scored 84 because..." Crunchbase doesn't explain anything. Trust requires transparency. |
| **50+ Analysis Agents** | All agents | ✅ Built | Crunchbase has zero agents. Zero analysis. Zero AI. We have 50+ specialized analysts. |
| **Cross-Market Intelligence** | GeographicStrategyAgent, GlobalMarketViabilityAgent | ✅ Built | "This failed in the US but works in Mexico." No existing tool does this. |
| **Revival Opportunities** | RevivalOpportunityAgent | ✅ Built | "Failed startup with revivable IP, 82/100 score." Nobody else identifies these. |

**Verdict: KEEP ALL. These are the competitive advantages over Crunchbase/PitchBook.**

---

### PROBLEM 4: "I find out about opportunities too late"

> Users: Investors, M&A Teams, Accelerators
> Frequency: Multiple times per day
> Impact: $135M+ per missed acquisition; competitors get deals first

| Feature | Agent/Component | Status | Why It Solves The Problem |
|---|---|---|---|
| **Real-Time Collectors** | HN Live, Reddit Stream, Twitter | ✅ Built | Stream APIs detect events in seconds, not hours. |
| **Kafka Message Bus** | Redpanda (in docker-compose) | ✅ Built | Signals flow through Kafka in milliseconds. |
| **Alert Dispatcher** | AlertDispatcherAgent | ✅ Built | Triggers when score > threshold. Sends to Slack/Email/Discord. |
| **Scaling Signal Detection** | Stream pattern matching | ✅ Built | "Funding + hiring within 30 days = scaling." Alerts investor immediately. |
| **Distress Signal Detection** | Stream pattern matching | ✅ Built | "Negative news + job posting drop = distress." Alerts accelerator partner to intervene. |
| **Opportunity Pipeline** | OpportunityPipelineAgent | ✅ Built | Tracks entities through stages: detected → screened → analyzed → alerted. |

**Verdict: KEEP ALL. Speed is the #1 competitive advantage for investors and M&A.**

---

### PROBLEM 5: "Nobody learns from startup failures"

> Users: Founders, Researchers, Governments
> Frequency: Every time a startup fails
> Impact: Same mistakes repeat endlessly, $270B/year lost

| Feature | Agent/Component | Status | Why It Solves The Problem |
|---|---|---|---|
| **Failed Startup Database** | seed_data.py + collectors | ✅ Built | 50+ failures with failure reasons, categories, funding lost. Growing with every new failure. |
| **Failure Pattern Analysis** | FailurePatternAgent | ✅ Built | Groups failures by sector, funding bracket, year, geography. Reveals repeating patterns. |
| **Manufacturing Failure Taxonomy** | seed data (mfg_cats) | ✅ Built | Capital Intensity 35%, Pilot-to-Scale 25%, Supply Chain 20%. Data-backed, not opinion. |
| **Cohort Analysis** | CohortAnalysisAgent | ✅ Built | Compare 2020 cohort vs 2023 cohort. Do failures improve over time? |
| **Trend Detection** | TrendDetectorAgent | ✅ Built | "AI chip failures up 200% this year." Emerging patterns before they peak. |
| **Sector Rotation** | SectorRotationAgent | ✅ Built | "Capital flowing from crypto → AI." Shows where the money is moving. |
| **Knowledge Graph Over Time** | TemporalGraphAgent | ✅ Built | "Northvolt's investor also backed Solyndra (failed 2011)." Historical connections. |

**Verdict: KEEP ALL. This is the NTSB-for-startups function. Unique to OIP.**

---

### PROBLEM 6: "I need to know WHERE to start my company"

> Users: Founders, Industrialists, Governments
> Frequency: Once per venture (but high-stakes)
> Impact: $200K+ per wrong location choice

| Feature | Agent/Component | Status | Why It Solves The Problem |
|---|---|---|---|
| **Geographic Strategy** | GeographicStrategyAgent | ✅ Built | "Austin: 85/100 vs Ohio: 45/100 for semiconductor manufacturing." |
| **BLS Survival Rates** | BLSSurvivalRateCollector | ✅ Built | "Texas manufacturing: 62% survive 5 years. Ohio: 48%." Data from Bureau of Labor Statistics. |
| **Revival Opportunity Scoring** | RevivalOpportunityAgent | ✅ Built | "Factory in Gujarat available, 50% subsidy, revival score 82/100." |
| **Reshoring Data** | ReshoringPDFCollector | ✅ Built | "500 jobs reshored to Ohio this quarter." Manufacturing revival signals. |
| **Global Market Viability** | GlobalMarketViabilityAgent | ✅ Built | "US market: saturated. India market: 22% penetration, 52% growth. Go to India." |

**Verdict: KEEP ALL. Location is a $200K+ decision. Data-backed geography is unique to OIP.**

---

## The Cut List (Features That Don't Solve Core Problems)

These features exist in the codebase but don't directly solve any of the 6 core problems:

### 🟡 QUESTIONABLE — Solve Internal/Developer Problems, Not User Problems

| Feature | Agent | Problem It Solves | Verdict |
|---|---|---|---|
| **Git Publisher** | GitPublisherAgent | Publishes reports to GitHub Pages | **CUT or deprioritize.** Nice for internal workflow, doesn't solve user problems. Can be a script, not an agent. |
| **Project Monitor** | ProjectMonitorAgent | Monitors project health | **CUT.** Internal tool, not a user-facing feature. Move to DevOps. |
| **Span Agent** | SpanAgent | Distributed tracing | **CUT.** Infrastructure concern, not user value. Move to observability stack. |
| **Intent Classifier** | IntentClassifierAgent | Classifies user chat intent | **KEEP but MINIMAL.** Helps AI Chat route queries. But overengineered — simple keyword matching works. |
| **Internet Research** | InternetResearchAgent | Generic web research | **MERGE with AIAnalystAgent.** Redundant — AI Analyst already does this. |
| **License Agent** | LicenseAgent | Manages software licenses | **KEEP for monetization.** Needed for Pro/Enterprise tiers. But not a user-facing intelligence feature. |
| **Stripe Payment** | StripePaymentAgent | Processes payments | **KEEP for monetization.** Same — business infrastructure, not intelligence. |
| **Report Agent** | ReportAgent | Generates reports | **MERGE with ReportGeneratorAgent.** Redundant — two agents doing similar things. |
| **Dashboard Agent** | DashboardAgent | Updates dashboard | **KEEP but SIMPLIFY.** Should be a simple WebSocket push, not a full agent. |

### 🔴 CUT — No Clear Problem Solved

| Feature | Agent | Why Cut |
|---|---|---|
| **LLM Portfolio Agent** | LLMPortfolioAgent | Analyzes LLM usage patterns. Nobody asked for this. Users don't care which LLM we use internally. |
| **LLM Pricing Agent** | LLMPricingAgent | Compares LLM API prices. Internal cost optimization. Not a user-facing feature. |
| **LLM Benchmark Agent** | LLMBenchmarkAgent | Benchmarks LLM performance. Developer tool, not user value. |
| **LLM Cost Optimizer** | LLMCostOptimizerAgent | Optimizes LLM spending. Internal dev concern. |

**These 4 LLM agents are a classic example of building features nobody needs.** They solve the developer's curiosity, not the user's problem. We use Ollama (local, free) — there are no API costs to optimize. Cut them entirely.

### 🟠 DEFER — Solves a Problem, But Not in the Top 6

| Feature | Agent | Why Defer | When to Build |
|---|---|---|---|
| **Topic Modeling** | TopicModelingAgent | Interesting for researchers but not a daily need for any persona | Phase 5 (Year 2) |
| **Influence Propagation** | InfluencePropagationAgent | Graph analysis nice-to-have, no user has asked "who influences whom" | Phase 5 (Year 2) |
| **Community Detector** | CommunityDetectorAgent | Finds clusters in the graph. Academic interest, not practical user need | Phase 5 (Year 2) |
| **Technology Stack** | TechnologyStackAgent | Detects what tech a startup uses. Useful but secondary to scoring | Phase 4 (Month 9) |
| **Moat Analyzer** | MoatAnalyzerAgent | Evaluates competitive moat. Advanced analysis, not core scoring | Phase 4 (Month 9) |
| **Timing Agent** | TimingAgent | "Is now the right time?" Interesting but hard to validate | Phase 5 (Year 2) |
| **Correlation Agent** | CorrelationAgent | Finds correlations between signals. Useful but not core workflow | Phase 4 (Month 9) |
| **NLP Enrichment** | NLPEnrichmentAgent | Internal pipeline step, not a user-facing agent | Keep as infrastructure, not a named agent |

---

## The Gap List (Problems With No Feature Yet)

These are problems users have that NO current feature solves:

### 🔴 CRITICAL GAPS

| # | Problem | User | What's Missing | Priority |
|---|---|---|---|---|
| **G1** | "Alert me when a high-opportunity startup appears" | Investor | Alert dispatcher CONSUMER doesn't exist. Alerts go to Kafka but nobody reads them. | **P0 — Build this week** |
| **G2** | "Score updates appear on my dashboard instantly" | All users | WebSocket polls MySQL every 30 sec. Should consume Kafka scores.updates topic. | **P0 — Build this week** |
| **G3** | "Run all collectors continuously" | All users | No collector scheduler. Collectors run manually. Real-time requires 24/7 scheduling. | **P0 — Build this week** |
| **G4** | "Connect to my CRM (Salesforce, HubSpot)" | Investor, M&A | No CRM integration. Users must manually copy data. | **P1 — Month 2** |
| **G5** | "Show me a feed of opportunities ranked by score" | Investor, Founder | No ranked feed page on dashboard. Scores exist but no user-friendly way to browse them. | **P1 — Month 2** |
| **G6** | "Track a watchlist of companies I care about" | All users | No watchlist feature. Users can't say "alert me about these 10 companies." | **P1 — Month 2** |
| **G7** | "Compare two companies side by side" | Investor, Founder | No comparison view. "Startup A vs Startup B" requires manual API calls. | **P2 — Month 3** |
| **G8** | "What changed since yesterday?" | All users | No changelog/delta view. "Score went from 62 to 84 — what changed?" can't be answered. | **P2 — Month 3** |

### 🟡 IMPORTANT GAPS

| # | Problem | User | What's Missing | Priority |
|---|---|---|---|---|
| **G9** | "Export my portfolio analysis as PDF" | Investor | No PDF export. Only JSON/CSV. Investors need shareable reports. | **P2 — Month 3** |
| **G10** | "Set my own alert thresholds" | Investor | Threshold is hardcoded at 80. Users can't customize per sector or entity. | **P2 — Month 3** |
| **G11** | "See historical score trends as a chart" | All users | No time-series charting. Scores are stored but not visualized over time. | **P2 — Month 3** |
| **G12** | "Search in my language" | Non-English users | No i18n. Only English. India, Brazil, China users need local languages. | **P3 — Year 2** |
| **G13** | "Mobile app notifications" | All users | No mobile app. Browser only. Push notifications require native app or PWA. | **P3 — Year 2** |

---

## The Simplified Roadmap (Only What Solves Problems)

```
BUILD ORDER — STRICTLY BY PROBLEM PRIORITY:

═══════════════════════════════════════════════════════════════
WEEK 1-2: PLUG THE CRITICAL GAPS (P0)
═══════════════════════════════════════════════════════════════

  G3: Collector Scheduler       → Solves "information is stale"
  G1: Alert Consumer (Kafka)    → Solves "I find out too late"
  G2: Score Push (Kafka → WS)   → Solves "dashboard doesn't update"

  WHY FIRST: Without these, nothing else matters. The platform is
  batch-only without real-time delivery. All core value depends on
  signals flowing continuously and alerts reaching users.

═══════════════════════════════════════════════════════════════
WEEK 3-4: IMPROVE SCORING ACCURACY
═══════════════════════════════════════════════════════════════

  FailurePatternAgent enhancement → More failure categories, better matching
  RiskScorerAgent tuning          → Validate predictions against actual failures
  CompositeScorer weights         → Adjust based on what actually predicts success

  WHY NEXT: If the scores are wrong, users stop trusting the platform.
  Better to have 3 accurate agents than 50 inaccurate ones.

═══════════════════════════════════════════════════════════════
MONTH 2: USER-FACING FEATURES (P1)
═══════════════════════════════════════════════════════════════

  G5: Opportunity Feed (ranked by score) → Investor browses top opportunities
  G6: Watchlist (track specific entities) → User follows companies they care about
  G4: CRM Integration (Salesforce)       → Investor syncs deals to their workflow
  G8: Delta View ("what changed")        → User sees why score moved

═══════════════════════════════════════════════════════════════
MONTH 3: POLISH (P2)
═══════════════════════════════════════════════════════════════

  G7: Company comparison view
  G9: PDF report export
  G10: Custom alert thresholds
  G11: Historical score charts

═══════════════════════════════════════════════════════════════
CUT ENTIRELY:
═══════════════════════════════════════════════════════════════

  ✂️ LLMPortfolioAgent      — No user problem solved
  ✂️ LLMPricingAgent        — No user problem solved
  ✂️ LLMBenchmarkAgent      — No user problem solved
  ✂️ LLMCostOptimizerAgent  — No user problem solved
  ✂️ SpanAgent              — Infrastructure, not agent
  ✂️ ProjectMonitorAgent    — Internal DevOps tool

═══════════════════════════════════════════════════════════════
MERGE / SIMPLIFY:
═══════════════════════════════════════════════════════════════

  ⟶ ReportAgent + ReportGeneratorAgent → One agent
  ⟶ InternetResearchAgent + AIAnalystAgent → One agent
  ⟶ DashboardAgent → Simple WebSocket push, not a full agent
  ⟶ IntentClassifierAgent → Simple keyword matching, not a separate agent
  ⟶ NLPEnrichmentAgent → Pipeline infrastructure, not a named agent

═══════════════════════════════════════════════════════════════
DEFER TO YEAR 2:
═══════════════════════════════════════════════════════════════

  ⏳ TopicModelingAgent
  ⏳ InfluencePropagationAgent
  ⏳ CommunityDetectorAgent
  ⏳ MoatAnalyzerAgent
  ⏳ TimingAgent
  ⏳ CorrelationAgent
```

---

## The Scorecard: Current Feature Audit

### How Many of Our 52 Agents Actually Solve Core Problems?

```
SOLVES A CORE PROBLEM (KEEP):           26 agents   50%
  → FailurePatternAgent, RiskScorerAgent, OpportunityScorerAgent,
    SurvivalAnalysisAgent, GeographicStrategyAgent, WhaleInvestorAgent,
    KnowledgeGraphAgent, EntityResolverAgent, NLPEnrichmentAgent,
    SemanticSearchAgent, AIAnalystAgent, NewsIntelligenceAgent,
    ReportGeneratorAgent, AlertDispatcherAgent, CollectionAgent,
    OrchestratorAgent, RevivalOpportunityAgent, MarketSizingAgent,
    CompetitiveLandscapeAgent, FounderBackgroundAgent, GlobalMarketViabilityAgent,
    TrendDetectorAgent, SectorRotationAgent, CohortAnalysisAgent,
    TemporalGraphAgent, GraphTraversalAgent

INTERNAL INFRASTRUCTURE (SIMPLIFY):       8 agents   15%
  → DashboardAgent, GitPublisherAgent, SentimentAgent,
    RelationshipExtractorAgent, OpportunityPipelineAgent,
    LicenseAgent, StripePaymentAgent, MLPredictorAgent

REDUNDANT (MERGE):                        4 agents    8%
  → ReportAgent ≈ ReportGeneratorAgent
  → InternetResearchAgent ≈ AIAnalystAgent
  → IntentClassifierAgent ≈ part of AIAnalystAgent
  → TechnologyStackAgent ≈ part of KnowledgeGraphAgent

SOLVES NO USER PROBLEM (CUT):            6 agents   12%
  → LLMPortfolioAgent, LLMPricingAgent, LLMBenchmarkAgent,
    LLMCostOptimizerAgent, SpanAgent, ProjectMonitorAgent

NICE-TO-HAVE (DEFER):                    8 agents   15%
  → TopicModelingAgent, InfluencePropagationAgent,
    CommunityDetectorAgent, MoatAnalyzerAgent, TimingAgent,
    CorrelationAgent, NLPEnrichmentAgent(as named agent)

═══════════════════════════════════════════════════

RESULT:
  26 agents solve real problems → KEEP and IMPROVE
  6 agents solve nothing        → CUT
  4 agents are redundant        → MERGE
  8 agents are infrastructure   → SIMPLIFY
  8 agents are nice-to-have     → DEFER

  After cleanup: 26 core + 8 infrastructure = 34 meaningful agents
  vs. current 52 where 14 don't earn their place
```

---

## The Test: Would Any User Notice If We Removed It?

```
FEATURE REMOVAL TEST:

"Would a founder notice if we removed FailurePatternAgent?"
  → YES. They'd lose the "3 similar startups failed" insight.       KEEP ✅

"Would an investor notice if we removed OpportunityScorerAgent?"
  → YES. The entire score-based workflow depends on it.              KEEP ✅

"Would anyone notice if we removed LLMPortfolioAgent?"
  → NO. Nobody knows it exists or uses its output.                  CUT ✂️

"Would anyone notice if we removed SpanAgent?"
  → NO. It's distributed tracing — invisible to users.              CUT ✂️

"Would anyone notice if we removed AlertDispatcherAgent?"
  → YES. Alerts are the #1 reason investors pay for Pro tier.       KEEP ✅
  BUT: The agent exists, the Kafka consumer doesn't. GAP!          BUILD 🔨

"Would anyone notice if we removed ReportAgent?"
  → UNCLEAR. ReportGeneratorAgent does the same thing.              MERGE ⟶

"Would anyone notice if we removed KnowledgeGraphAgent?"
  → YES. "Who else did this investor fund?" breaks.                 KEEP ✅

"Would anyone notice if we removed TopicModelingAgent?"
  → NOT YET. Nobody depends on its output today.                    DEFER ⏳

"Would anyone notice if we removed the Collector Scheduler?"
  → YES. Because nothing would update in real-time.                 BUILD 🔨
```

---

## The One-Page Summary

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  6 CORE PROBLEMS → 26 CORE AGENTS → 4 CRITICAL GAPS                │
│                                                                      │
│  PROBLEM                    AGENTS THAT SOLVE IT        STATUS       │
│  ─────────────────────      ──────────────────────      ──────       │
│  Can't predict outcomes     7 agents (scoring/risk)     ✅ Built     │
│  20 hrs manual research     10 agents (automation)      ✅ Built     │
│  Tools expensive & stupid   8 agents (intelligence)     ✅ Built     │
│  Find out too late          6 agents (real-time)        ⚠️ 70% done  │
│  Nobody learns from failure 7 agents (patterns)         ✅ Built     │
│  Don't know WHERE to start  5 agents (geography)        ✅ Built     │
│                                                                      │
│  CRITICAL GAPS (problems with no feature):                          │
│  🔨 Alert Consumer (Kafka → Slack/Email)                            │
│  🔨 Score Push (Kafka → WebSocket)                                  │
│  🔨 Collector Scheduler (24/7 continuous collection)                │
│                                                                      │
│  CUT LIST (features with no problem):                               │
│  ✂️ 4 LLM agents, SpanAgent, ProjectMonitorAgent (6 agents)         │
│                                                                      │
│  MERGE LIST:                                                         │
│  ⟶ Report + ReportGenerator → one agent                             │
│  ⟶ InternetResearch + AIAnalyst → one agent                         │
│                                                                      │
│  BOTTOM LINE:                                                        │
│  Build 3 missing pieces. Cut 6 useless agents. Ship.                │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

*Last updated: June 5, 2026*
