# 🎯 Goals, Success Criteria & Feature Prioritization

> "What does success look like, how do we measure it, and what must we build first?"

---

## Part 1: The 5 Goals

Every goal is tied to a problem from `PROBLEM_DEFINITION.md` and a user from `USE_CASES.md`.

---

### GOAL 1: Replace Crunchbase as the Default Startup Intelligence Tool

```
PROBLEM:     Crunchbase charges $490/mo for raw data with zero intelligence
USER:        All 8 user types (Founders, Investors, Researchers, etc.)
SUCCESS:     10,000 users choose OIP over Crunchbase within 12 months
MEASURABLE:  GitHub stars, daily active users, Pro conversions

WHY THIS GOAL:
  Crunchbase has 80M+ users and charges $490/mo.
  If we give away a better tool for free, users WILL switch.
  This is our wedge into the market — free + better = adoption.

  This single goal drives 80% of our early decisions.
```

### GOAL 2: Predict Startup Failure Accurately Enough That Users Trust the Score

```
PROBLEM:     90% of startups fail, but nobody predicts which ones
USER:        Investors (decide where to put $), Founders (avoid mistakes)
SUCCESS:     Our risk score predicts failure with >75% accuracy at 12 months
MEASURABLE:  Backtested accuracy, false positive rate, user trust surveys

WHY THIS GOAL:
  If users don't trust the score, they won't use the platform.
  Trust = accuracy + explainability.
  "Scored 84 because funding contributed 19 points" = user understands WHY.
  We need >75% accuracy to be taken seriously by investors.
```

### GOAL 3: Deliver Intelligence Within 15 Minutes of a Real-World Event

```
PROBLEM:     Investors find out about opportunities too late (hours/days)
USER:        Investors, M&A Teams, Accelerators (speed = money)
SUCCESS:     Median time from event to user notification < 15 minutes
MEASURABLE:  End-to-end latency, signal freshness, alert delivery time

WHY THIS GOAL:
  An investor who gets the alert first wins the deal.
  Crunchbase updates daily. We update in minutes.
  15 minutes is fast enough to act before competitors.
```

### GOAL 4: Make Failure Patterns Visible and Actionable

```
PROBLEM:     The same 6 failure patterns repeat endlessly; nobody learns
USER:        Founders (avoid mistakes), Researchers (publish papers), Governments (make policy)
SUCCESS:     OIP data cited in 10+ research papers and 5+ government reports within 24 months
MEASURABLE:  Academic citations, government references, media mentions

WHY THIS GOAL:
  This is the "NTSB for startups" function.
  If universities teach with OIP and governments cite OIP data,
  we become the standard. Standards don't get displaced.
```

### GOAL 5: Build a Self-Sustaining Open-Source Community

```
PROBLEM:     One team can't build 50+ collectors and agents alone
USER:        The platform itself (needs community contributions to scale)
SUCCESS:     200+ contributors, 50+ community-built agents/collectors by Year 2
MEASURABLE:  GitHub contributors, PRs merged, Discord members, community agents

WHY THIS GOAL:
  Linux beat Windows because thousands of contributors built it.
  Kubernetes beat Docker Swarm for the same reason.
  Community-built features are free, diverse, and fast.
  Without community, we're just another startup. With community, we're a movement.
```

---

## Part 2: Success Criteria (Measurable Outcomes)

---

### Year 1 Success Criteria

| # | What We Measure | Target | How We Measure It | Why This Number |
|---|---|---|---|---|
| **S1** | GitHub stars | 15,000 by Month 12 | GitHub API | Proves developer interest. Linux had 10K stars in Year 1. |
| **S2** | Daily active users | 3,000 by Month 12 | API analytics (unique IPs/tokens) | 3K DAU = product-market fit signal |
| **S3** | Pro subscribers | 200 by Month 12 | Stripe subscription count | 200 × $99/mo = $19.8K MRR. Proves willingness to pay. |
| **S4** | Enterprise customers | 5 by Month 12 | CRM / contracts | 5 enterprise = $15-25K MRR. Proves B2B viability. |
| **S5** | Signal freshness | < 15 min median latency | Pipeline metrics in Redis | Core value prop: real-time intelligence |
| **S6** | Score accuracy | > 75% prediction accuracy | Backtesting against actual outcomes | Below 75% = users won't trust it |
| **S7** | False positive rate | < 20% | "Said high-risk but survived" / total high-risk | Too many false alarms = users ignore alerts |
| **S8** | Test coverage | > 500 tests passing | `pytest --co -q` | Prevents regression. Currently at 681. |
| **S9** | Contributors | 50 by Month 12 | GitHub contributors graph | Community health metric |
| **S10** | NPS score | > 40 by Month 12 | Quarterly user survey | >40 = "very good." >50 = "excellent." |
| **S11** | MRR | $25K by Month 12 | Stripe + manual tracking | Path to $3M ARR by Year 2 |
| **S12** | Uptime | > 99.5% | API health checks | 4+ hours downtime/month = lost trust |

### Year 2 Success Criteria

| # | What We Measure | Target | Why |
|---|---|---|---|
| **S13** | GitHub stars | 35,000 | Top 100 open-source projects |
| **S14** | Daily active users | 12,000 | Scale validation |
| **S15** | Paying customers | 1,200 Pro + 30 Enterprise | $3M ARR |
| **S16** | Score accuracy | > 80% | More data = better model |
| **S17** | Academic citations | 10+ papers citing OIP data | Standard-setting |
| **S18** | Media mentions | 50+ articles referencing OIP | Brand awareness |
| **S19** | Community agents | 50+ agents built by community | Community-driven growth |
| **S20** | University adoptions | 15+ universities teaching with OIP | Next-generation adoption |

### Year 3 Success Criteria

| # | What We Measure | Target | Why |
|---|---|---|---|
| **S21** | GitHub stars | 50,000 | Industry standard status |
| **S22** | Daily active users | 25,000 | Dominance |
| **S23** | ARR | $3.56M | Sustainable business |
| **S24** | "OIP Score" mentions | 200+ in media | Becoming a standard term |
| **S25** | Government references | 5+ policy papers citing OIP | Institutional trust |

---

## Part 3: Feature Prioritization

---

### The Framework

Every feature gets scored on 3 axes:

```
AXIS 1: PROBLEM SEVERITY (Does it solve a top problem?)
  3 = Solves a critical problem ($100K+ impact)
  2 = Solves an important problem ($10K+ impact)
  1 = Solves a minor problem
  0 = Doesn't solve a documented problem

AXIS 2: USER DEMAND (How many users need it?)
  3 = All or most user types need it
  2 = Multiple user types need it
  1 = One user type needs it
  0 = No user has asked for this

AXIS 3: TECHNICAL FEASIBILITY (How fast can we ship it?)
  3 = < 1 week (already 80% built)
  2 = 1-4 weeks
  1 = 1-3 months
  0 = 3+ months or uncertain

TOTAL SCORE = Problem + User Demand + Feasibility
  7-9 = MUST-HAVE (build now)
  4-6 = SHOULD-HAVE (build next)
  1-3 = NICE-TO-HAVE (build later)
  0   = DON'T BUILD (cut)
```

---

### MUST-HAVE (Score 7-9): Build These First

Features without which the product doesn't solve its core problems.

| # | Feature | Problem | Users | Score | Status |
|---|---|---|---|---|---|
| **M1** | **Collector Scheduler** — 24/7 continuous collection | Real-time intelligence | All | 3+3+3 = **9** | 🔨 Not built |
| **M2** | **Alert Consumer** — Read Kafka → send Slack/Email | Find opportunities early | Investor, M&A | 3+3+3 = **9** | 🔨 Not built |
| **M3** | **Score Push to Dashboard** — Kafka → WebSocket | Stale data on dashboard | All | 3+3+3 = **9** | 🔨 Not built |
| **M4** | **Composite Score (0-100)** | Can't predict outcomes | Investor, Founder | 3+3+2 = **8** | ✅ Built |
| **M5** | **Risk Score (0-1.0)** | Can't predict failure | Investor, Founder | 3+3+2 = **8** | ✅ Built |
| **M6** | **Feature Attribution** ("scored 84 because...") | Black box = no trust | All | 3+3+2 = **8** | ✅ Built |
| **M7** | **Failure Pattern Matching** | Same mistakes repeat | Founder, Researcher | 3+3+2 = **8** | ✅ Built |
| **M8** | **Knowledge Graph** ("who's connected to whom") | 20 hrs manual research | Investor, Researcher | 3+2+2 = **7** | ✅ Built |
| **M9** | **AI Chat** ("why did Startup X fail?") | Manual research is slow | All | 3+3+1 = **7** | ✅ Built |
| **M10** | **24 Data Collectors** | Data is fragmented | All | 3+3+1 = **7** | ✅ Built |
| **M11** | **Stream Processing Pipeline** (Bytewax) | Real-time processing | All | 3+3+1 = **7** | ✅ Built |
| **M12** | **Docker Compose** (one-command deploy) | Must be easy to try | All new users | 2+3+3 = **8** | ✅ Built |
| **M13** | **Public Demo Instance** | Users need to try before installing | All new users | 2+3+2 = **7** | 🔨 Not built |
| **M14** | **Free Tier (full core)** | Crunchbase costs $490/mo | All | 3+3+3 = **9** | ✅ Built |

**12 of 14 must-haves are already built.** The remaining 3 are the critical gaps identified in `PROBLEM_FEATURE_MAP.md`.

---

### SHOULD-HAVE (Score 4-6): Build Next

Features that significantly improve the product but aren't blocking.

| # | Feature | Problem | Users | Score | Status |
|---|---|---|---|---|---|
| **S1** | **Watchlist** — track specific entities | Can't follow companies | All | 2+3+2 = **7** | 🔨 Not built |
| **S2** | **Opportunity Feed** — ranked by score | Can't browse top opportunities | Investor, Founder | 2+3+2 = **7** | 🔨 Not built |
| **S3** | **Score Delta View** — "what changed since yesterday" | Can't see why score moved | All | 2+3+2 = **7** | 🔨 Not built |
| **S4** | **Custom Alert Thresholds** — per entity/sector | One-size-fits-all threshold (80) | Investor | 2+2+2 = **6** | 🔨 Not built |
| **S5** | **PDF Report Export** | Can't share reports | Investor, Govt | 2+2+2 = **6** | 🔨 Not built |
| **S6** | **Historical Score Charts** | Can't see trends over time | All | 2+2+2 = **6** | 🔨 Not built |
| **S7** | **Survival Probability** | Job seeker can't evaluate employer | Job Seeker, Founder | 2+2+2 = **6** | ✅ Built |
| **S8** | **Geographic Strategy** | Wrong location costs $200K | Founder, Industrialist | 3+2+1 = **6** | ✅ Built |
| **S9** | **Revival Opportunities** | Can't find distressed assets | Industrialist, Govt | 2+2+1 = **5** | ✅ Built |
| **S10** | **Whale Investor Tracking** | Can't track big investors | Investor | 2+2+1 = **5** | ✅ Built |
| **S11** | **Competitive Landscape** | Can't map competitors | Investor, Founder | 2+2+1 = **5** | ✅ Built |
| **S12** | **Founder Background** | Can't evaluate team | Investor | 2+2+1 = **5** | ✅ Built |
| **S13** | **CRM Integration** (Salesforce/HubSpot) | Manual data copy | Investor, M&A | 2+2+1 = **5** | 🔨 Not built |
| **S14** | **Company Comparison** — side by side | Can't compare options | Investor, Founder | 1+2+2 = **5** | 🔨 Not built |
| **S15** | **SSE Endpoint** — for non-WebSocket users | Can't use real-time | All | 1+2+3 = **6** | 🔨 Not built |
| **S16** | **NLP Worker** (spaCy + embeddings) | Shallow enrichment | Researcher, Investor | 2+2+1 = **5** | 🔨 Not built |
| **S17** | **Pro Tier ($99/mo)** — alerts, API, reports | Revenue | Business | 2+1+2 = **5** | 🔨 Not built |
| **S18** | **API Key Authentication** | Can't track usage | Pro/Enterprise | 2+2+2 = **6** | 🔨 Not built |

---

### NICE-TO-HAVE (Score 1-3): Build Later

Features that add polish but don't solve core problems.

| # | Feature | Score | Status | When |
|---|---|---|---|---|
| **N1** | Topic Modeling | 1+1+1 = **3** | ✅ Agent exists | Year 2 |
| **N2** | Influence Propagation | 1+1+1 = **3** | ✅ Agent exists | Year 2 |
| **N3** | Community Detection | 1+1+1 = **3** | ✅ Agent exists | Year 2 |
| **N4** | Technology Stack Detection | 1+2+1 = **3** | ✅ Agent exists | Month 9 |
| **N5** | Moat Analysis | 1+1+1 = **3** | ✅ Agent exists | Month 9 |
| **N6** | Timing Analysis | 1+1+1 = **3** | ✅ Agent exists | Year 2 |
| **N7** | Correlation Analysis | 1+1+1 = **3** | ✅ Agent exists | Month 9 |
| **N8** | Mobile App | 1+3+0 = **3** | Not built | Year 2 |
| **N9** | Browser Extension | 1+2+0 = **3** | Not built | Year 2 |
| **N10** | ChatGPT Plugin | 1+2+0 = **3** | Not built | Year 2 |
| **N11** | Multi-language (i18n) | 1+2+0 = **3** | Not built | Year 2 |
| **N12** | White-label Option | 0+1+1 = **2** | Not built | Year 3 |
| **N13** | Custom ML Model Training UI | 0+1+1 = **2** | Not built | Year 3 |
| **N14** | Embeddable Widgets | 0+1+0 = **1** | Not built | Year 3 |

---

### DON'T BUILD (Score 0): Cut Entirely

| # | Feature | Score | Why |
|---|---|---|---|
| **X1** | LLM Portfolio Agent | 0+0+0 = **0** | No user problem. Developer curiosity. |
| **X2** | LLM Pricing Agent | 0+0+0 = **0** | We use free local Ollama. No API costs. |
| **X3** | LLM Benchmark Agent | 0+0+0 = **0** | Nobody asked for LLM benchmarks. |
| **X4** | LLM Cost Optimizer Agent | 0+0+0 = **0** | Zero costs to optimize. |
| **X5** | Span Agent (distributed tracing) | 0+0+0 = **0** | Infrastructure, not intelligence. |
| **X6** | Project Monitor Agent | 0+0+0 = **0** | DevOps tool, not user value. |

---

## Part 4: The Build Order (What to Build, In What Order)

---

### Phase A: Complete the Must-Haves (Weeks 1-4)

```
WEEK 1: Close the 3 critical gaps
  ┌─────────────────────────────────────────────────────────────┐
  │  M1: Collector Scheduler                                    │
  │     → APScheduler-based 24/7 collector runner               │
  │     → Continuous: Twitter, Reddit, HN                       │
  │     → Scheduled: RSS every 15 min, SEC every 4 hrs, etc.    │
  │     → DELIVERABLE: python scheduler.py starts everything    │
  │                                                             │
  │  M2: Alert Consumer                                         │
  │     → Kafka consumer reads alerts.triggered topic           │
  │     → Dispatches to Slack webhook + Email via SMTP          │
  │     → DELIVERABLE: Alert arrives in Slack < 15 min          │
  │                                                             │
  │  M3: Score Push via Kafka                                   │
  │     → Background task reads scores.updates topic            │
  │     → Pushes to WebSocket clients                           │
  │     → DELIVERABLE: Dashboard updates in real-time           │
  └─────────────────────────────────────────────────────────────┘

WEEK 2: Validate end-to-end
  ┌─────────────────────────────────────────────────────────────┐
  │  • Run full pipeline: collector → Kafka → process → alert   │
  │  • Measure latency: event → alert delivery time             │
  │  • Target: < 15 minutes end-to-end                          │
  │  • Fix any data quality issues                              │
  │  • Write 20+ tests for the 3 new components                 │
  └─────────────────────────────────────────────────────────────┘

WEEK 3: Public demo
  ┌─────────────────────────────────────────────────────────────┐
  │  M13: Deploy demo.opportunity-intel.org                     │
  │     → Pre-loaded with real data                             │
  │     → "Type a startup name → get full analysis"             │
  │     → Must feel like magic                                  │
  │     → DELIVERABLE: Anyone can try OIP without installing    │
  └─────────────────────────────────────────────────────────────┘

WEEK 4: GitHub launch
  ┌─────────────────────────────────────────────────────────────┐
  │  • Clean up README.md with badges, screenshots, demo GIF    │
  │  • "Show HN: Open-source alternative to Crunchbase + AI"    │
  │  • Post to r/startups, r/MachineLearning                    │
  │  • DELIVERABLE: 2,000 GitHub stars in 2 weeks               │
  └─────────────────────────────────────────────────────────────┘
```

### Phase B: Should-Have Features (Months 2-3)

```
MONTH 2: User-facing features
  ┌─────────────────────────────────────────────────────────────┐
  │  S1:  Watchlist (track specific entities)                   │
  │  S2:  Opportunity Feed (ranked by score, filterable)        │
  │  S3:  Score Delta View ("what changed since yesterday")     │
  │  S17: Pro Tier setup (Stripe + API keys + usage tracking)   │
  │  S18: API Key Authentication (for Pro users)                │
  └─────────────────────────────────────────────────────────────┘

MONTH 3: Polish + integrations
  ┌─────────────────────────────────────────────────────────────┐
  │  S4:  Custom Alert Thresholds (per entity/sector)           │
  │  S5:  PDF Report Export                                     │
  │  S6:  Historical Score Charts (time-series visualization)   │
  │  S13: CRM Integration (Salesforce webhook)                  │
  │  S14: Company Comparison (side-by-side view)                │
  │  S15: SSE Endpoint (for non-WebSocket users)                │
  │  S16: NLP Worker (spaCy + embeddings in separate process)   │
  └─────────────────────────────────────────────────────────────┘
```

### Phase C: Nice-to-Have (Months 4-12)

```
MONTHS 4-6:
  • Score accuracy improvements (backtesting, weight tuning)
  • Geographic strategy enhancement (more countries)
  • Revival opportunity expansion (more sectors)
  • Contributor onboarding (CONTRIBUTING.md, issue templates)

MONTHS 7-12:
  • Technology Stack Detection
  • Moat Analysis
  • Correlation Analysis
  • Mobile App (PWA)
  • Browser Extension
  • Multi-language support (Hindi, Portuguese, Mandarin)
```

---

## Part 5: The Success Dashboard

### Weekly Review — Ask These 7 Questions

```
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                        ║
║  WEEKLY SUCCESS CHECK                                                  ║
║                                                                        ║
║  1. ARE SIGNALS FLOWING?                                               ║
║     → How many signals collected this week? (target: 500+)             ║
║     → Are all 24 collectors running? (check collection_runs table)     ║
║     → Any collector failing? (check error logs)                        ║
║                                                                        ║
║  2. ARE SCORES ACCURATE?                                               ║
║     → How many entities scored this week? (target: 50+)                ║
║     → Any score > 90 that later failed? (false positive check)         ║
║     → Any score < 30 that later succeeded? (false negative check)      ║
║                                                                        ║
║  3. ARE ALERTS DELIVERING?                                             ║
║     → How many alerts sent this week? (target: 5-20)                   ║
║     → Alert delivery latency? (target: < 15 min)                       ║
║     → Alert accuracy? (did the user find the alert valuable?)          ║
║                                                                        ║
║  4. ARE USERS GROWING?                                                 ║
║     → New GitHub stars this week? (target: 100+)                       ║
║     → New Discord members? (target: 20+)                               ║
║     → New Pro subscribers? (target: 5+)                                ║
║                                                                        ║
║  5. IS THE PIPELINE HEALTHY?                                           ║
║     → Uptime this week? (target: > 99.5%)                              ║
║     → Throughput? (target: > 10 signals/min)                           ║
║     → Processing lag? (target: < 5 min)                                ║
║                                                                        ║
║  6. ARE TESTS PASSING?                                                 ║
║     → Total tests? (target: > 500)                                     ║
║     → Any failing? (target: 0 failures)                                ║
║     → New tests this week? (target: 10+)                               ║
║                                                                        ║
║  7. ARE WE BUILDING THE RIGHT THINGS?                                  ║
║     → Did we ship must-have features this week?                        ║
║     → Did we accidentally build nice-to-have instead?                  ║
║     → Are users asking for something we haven't prioritized?           ║
║                                                                        ║
╚══════════════════════════════════════════════════════════════════════════╝
```

---

## Part 6: The Decision Framework

### When You're Tempted to Build Something New, Ask:

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  SHOULD I BUILD THIS FEATURE?                                │
│                                                              │
│  1. Which of the 6 problems does it solve?                   │
│     → If none → DON'T BUILD                                 │
│                                                              │
│  2. Which user type needs it?                                │
│     → If no specific user → DON'T BUILD                     │
│                                                              │
│  3. How often does this problem occur?                       │
│     → If less than weekly → DEFER                           │
│                                                              │
│  4. What happens if we don't build it?                       │
│     → If "nothing breaks" → NICE-TO-HAVE                    │
│     → If "users can't do X" → MUST-HAVE                     │
│                                                              │
│  5. How long does it take to build?                          │
│     → If > 2 weeks and not MUST-HAVE → BREAK INTO SMALLER   │
│                                                              │
│  6. Can I measure its impact?                                │
│     → If no measurable outcome → DON'T BUILD                │
│                                                              │
│  7. Would a user notice if I removed it?                     │
│     → If no → DON'T BUILD IN THE FIRST PLACE                │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Part 7: Summary — The One-Page Plan

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  5 GOALS                                                             │
│  ─────────                                                           │
│  1. Replace Crunchbase (10K users in 12 months)                     │
│  2. Predict failure accurately (>75% accuracy)                       │
│  3. Real-time alerts (<15 min latency)                               │
│  4. Make patterns visible (10+ academic citations)                   │
│  5. Build community (200+ contributors)                              │
│                                                                      │
│  25 MEASURABLE OUTCOMES (S1-S25)                                     │
│  ─────────────────────────────                                       │
│  Year 1: 15K stars, 3K DAU, $25K MRR, 75% accuracy                  │
│  Year 2: 35K stars, 12K DAU, $250K MRR, 80% accuracy                │
│  Year 3: 50K stars, 25K DAU, $3.56M ARR, industry standard          │
│                                                                      │
│  14 MUST-HAVES (12 built, 3 to build)                                │
│  ──────────────────────────────                                      │
│  🔨 Collector Scheduler                                              │
│  🔨 Alert Consumer (Kafka → Slack/Email)                             │
│  🔨 Score Push (Kafka → WebSocket)                                   │
│  🔨 Public Demo Instance                                             │
│                                                                      │
│  18 SHOULD-HAVES (8 built, 10 to build)                              │
│  ──────────────────────────────────                                  │
│  Watchlist, Feed, Delta View, PDF Export, Charts, CRM, etc.          │
│                                                                      │
│  14 NICE-TO-HAVES (7 built, 7 not built)                             │
│  ──────────────────────────────────                                  │
│  Topic modeling, mobile app, browser extension, i18n, etc.           │
│                                                                      │
│  6 DON'T-BUILDS (cut from codebase)                                  │
│  ──────────────────────────────────                                  │
│  ✂️ 4 LLM agents, Span Agent, Project Monitor                        │
│                                                                      │
│  BUILD ORDER:                                                        │
│  ────────────                                                        │
│  Week 1-2: Close 3 critical gaps (scheduler, alerts, score push)     │
│  Week 3-4: Public demo + GitHub launch                               │
│  Month 2-3: Should-have features (watchlist, feed, Pro tier)         │
│  Month 4-12: Nice-to-have + accuracy improvements                    │
│                                                                      │
│  WEEKLY CHECK: 7 questions (signals, scores, alerts, users,          │
│  pipeline, tests, right-things)                                      │
│                                                                      │
│  DECISION RULE: If it doesn't solve a documented problem             │
│  for a named user type → DON'T BUILD IT.                             │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

*Last updated: June 5, 2026*

---

## Post-Launch Update: Feedback-Driven Priorities

> **This section will be updated weekly based on real user feedback.**
> See `FEEDBACK_STRATEGY.md` for the complete feedback-driven development process.

### Feedback Metrics (To Be Filled After Launch)

| Metric | Target | Actual | Status |
|---|---|---|---|
| Weekly visitors | 500+ | -- | 🔲 |
| Search queries/week | 1,000+ | -- | 🔲 |
| Chat questions/week | 200+ | -- | 🔲 |
| Avg score rating | ≥ 4.0/5 | -- | 🔲 |
| Feature requests | 20+/week | -- | 🔲 |
| Return user rate (7-day) | ≥ 10% | -- | 🔲 |

### Priority Adjustments (Updated Weekly)

| Week | Change | From → To | Evidence |
|---|---|---|---|
| -- | (No data yet — launch MVP first) | -- | -- |

### How to Update This Section

1. Run `GET /api/feedback/dashboard` every Monday
2. Score each signal: Volume (0-3) + Impact (0-3) + Alignment (0-3) + Urgency (0-1)
3. Reorder priorities based on scores
4. Update this table
5. Share on GitHub Discussions + Twitter

**Rules:**
- Score rating < 3.0 → P0 fix immediately
- 50+ feature requests → build next sprint
- 0 requests for a feature → deprioritize to P3
- Revenue signals ("how much?") → build Pro tier ASAP
