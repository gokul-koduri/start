# 🚀 MVP First — Minimum Viable Product Plan

> "If you're not embarrassed by your first version, you launched too late." — Reid Hoffman

---

## The Brutal Truth

```
CURRENT STATE:
  55 agents, 26 collectors, 76 tables, 681 tests, 185 Python files
  5 of 6 phases complete, 63 sessions of development
  0 paying users. 0 validated assumptions.

THE QUESTION:
  What's the SMALLEST thing we can ship that proves
  someone will use this and maybe even pay for it?

THE ANSWER:
  Not 55 agents. Not 26 collectors. Not 76 tables.

  3 capabilities. 1 demo. 2 weeks.
```

---

## Part 1: What Is the MVP?

---

### 1.1 The MVP in One Sentence

```
"Type a startup name → get a score, a risk assessment, and
 an explanation of WHY — in 2 seconds, for free."
```

That's it. Everything else is a feature, not the MVP.

### 1.2 What the MVP Proves (Validation Hypotheses)

| # | Hypothesis | How the MVP Tests It | Success = |
|---|---|---|---|
| **H1** | Users want startup intelligence | Do people try the demo? | 500+ demo visitors in Month 1 |
| **H2** | Our scoring is useful | Do users trust the score? | 30%+ search a second company |
| **H3** | Users will return | Do people come back? | 10%+ return within 7 days |
| **H4** | Users will pay | Do people ask for more? | 20+ "how do I get alerts?" emails |
| **H5** | Our data is good enough | Do users find what they search? | 70%+ searches return a result |

### 1.3 What the MVP Does NOT Need

```
THESE ARE NOT MVP:

❌ Real-time streaming (users don't know it's missing yet)
❌ 26 collectors (seed data is enough for MVP)
❌ Slack/Email alerts (nice-to-have, not day-1)
❌ WebSocket live updates (dashboard loads on refresh)
❌ Authentication/API keys (MVP is public and free)
❌ Multi-tenancy (one instance serves everyone)
❌ PDF export (browser print works)
❌ CRM integration (nobody has asked for this yet)
❌ Watchlists (requires auth which requires users first)
❌ Pro tier ($0 MRR proves nothing — users prove everything)
❌ Dagster orchestration (cron works for MVP)
❌ Prometheus monitoring (logs are enough)
❌ ClickHouse analytics (MySQL handles MVP scale)
❌ TimescaleDB (Redis metrics are enough)
❌ SSE endpoint (refresh button works)
❌ NLP async worker (keyword sentiment is enough)
```

---

## Part 2: The MVP Scope

---

### 2.1 MVP Feature 1: Instant Startup Score

```
WHAT:    User types a company name → gets a composite score (0-100)
         with feature attribution explaining WHY.

WHY:     This is the core value proposition.
         If this doesn't work, nothing else matters.

STATUS:  ✅ ALREADY BUILT
         POST /api/score          → scores any startup
         GET /api/opportunities    → lists all scored entities
         GET /api/opportunities/{name} → one entity with full breakdown

WHAT USER SEES:
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  🔍 Search: [Rivian]                    [Search]             │
│                                                              │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                              │
│  RIVIAN AUTOMOTIVE                                          │
│  Score: 61/100    Risk: 0.42    Trend: ▼ declining          │
│                                                              │
│  WHY 61:                                                     │
│  ┌────────────────┬────────┬──────────────────────────┐     │
│  │ Factor         │ Points │ Detail                    │     │
│  ├────────────────┼────────┼──────────────────────────┤     │
│  │ Funding        │ +18    │ Raised $5.5B (Series F)   │     │
│  │ SEC Filings    │ +12    │ Active 10-K, 8-K filings  │     │
│  │ Patents        │  +8    │ 47 patents granted         │     │
│  │ Job Postings   │  +6    │ 200+ active postings       │     │
│  │ News Sentiment │  -3    │ Negative coverage (layoffs)│     │
│  │ Failure Pattern│ -18    │ Similar to Fisker, Lordstown│    │
│  └────────────────┴────────┴──────────────────────────┘     │
│                                                              │
│  SIMILAR FAILED STARTUPS:                                    │
│  • Fisker (score was 58 before failure) — same EV sector    │
│  • Lordstown Motors (score was 55) — same manufacturing     │
│  • Better Place (score was 52) — same business model        │
│                                                              │
│  KNOWLEDGE GRAPH:                                            │
│  Connected to: Amazon (investment), Ford (partnership),     │
│  US DOE (loan), Samsung SDI (battery supply)                │
│                                                              │
└──────────────────────────────────────────────────────────────┘

BUILT? YES. This works RIGHT NOW.
```

### 2.2 MVP Feature 2: AI Chat — "Ask Anything About Startups"

```
WHAT:    User types a question → gets an AI answer grounded in
         OIP's data (failed startups, scores, news, patterns).

WHY:     This proves users will interact with the intelligence
         layer, not just read static scores.
         Also: this is the "wow" moment that makes people share.

STATUS:  ✅ ALREADY BUILT
         POST /api/chat  → AI answers using Ollama + OIP data

WHAT USER SEES:
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  💬 Ask anything about startups:                             │
│                                                              │
│  [Why did Juicero fail?                          ] [Ask]     │
│                                                              │
│  AI: Juicero (2016-2017) raised $118M from investors        │
│  including Kleiner Perkins and Google Ventures.              │
│                                                              │
│  It failed for 3 reasons:                                    │
│                                                              │
│  1. NO MARKET NEED (42% of failures share this)             │
│     A $400 WiFi-connected juicer that squeezed proprietary   │
│     bags. Bloomberg discovered hands squeezed bags faster.   │
│                                                              │
│  2. UNIT ECONOMICS (29% of failures share this)             │
│     $400 device with $15M+ in manufacturing costs.          │
│     400 custom parts for a commodity function.              │
│                                                              │
│  3. OVER-ENGINEERING                                         │
│     Investors valued the technology, not the problem.        │
│     Pattern: same as GoPro Karma, Jawbone UP, Peloton Tread│
│                                                              │
│  Similar startups at risk: [view 5 companies scoring < 40]  │
│                                                              │
│  📊 This answer used data from:                             │
│     failed_startups table (1 entry), news_articles (23),    │
│     failure_reasons_taxonomy (3 categories)                 │
│                                                              │
└──────────────────────────────────────────────────────────────┘

BUILT? YES. This works RIGHT NOW with Ollama.
```

### 2.3 MVP Feature 3: Failure Pattern Browser

```
WHAT:    User browses failure patterns by category, sector,
         geography, and funding level.

WHY:     This is the "NTSB for startups" function.
         Researchers, founders, and journalists need this.
         It's what no other tool provides.

STATUS:  ✅ ALREADY BUILT
         GET /api/startups         → all failed startups
         GET /api/risk-scores      → risk assessments
         GET /api/survival-rates   → BLS survival data
         Dashboard charts already show failure patterns

WHAT USER SEES:
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  FAILURE PATTERNS BY CATEGORY                                │
│                                                              │
│  ■ No Market Need     42%  ████████████████████░░░░  254    │
│  ■ Ran Out of Cash    29%  ██████████████░░░░░░░░░░  175    │
│  ■ Team Issues        14%  ███████░░░░░░░░░░░░░░░░░   85    │
│  ■ Competition         8%  ████░░░░░░░░░░░░░░░░░░░░   48    │
│  ■ Legal/Regulatory    4%  ██░░░░░░░░░░░░░░░░░░░░░░   24    │
│  ■ Other               3%  █░░░░░░░░░░░░░░░░░░░░░░░   18    │
│                                                              │
│  FILTER: [All Sectors ▼] [All Regions ▼] [All Years ▼]      │
│                                                              │
│  TOP FAILED STARTUPS (by funding burned):                    │
│  1. Northvolt       $14B+    Battery Mfg    Sweden    2024   │
│  2. Byju's          $5.4B+   EdTech         India     2024   │
│  3. Katerra         $2B+     Construction   US        2021   │
│  4. Fisker          $1B+     EV/Auto        US        2024   │
│  5. Quibi           $1.75B   Streaming      US        2020   │
│                                                              │
│  SURVIVAL RATES (BLS Data):                                  │
│  Manufacturing: Year 1: 79% → Year 3: 56% → Year 5: 45%   │
│  Tech:          Year 1: 84% → Year 3: 62% → Year 5: 52%   │
│                                                              │
│  [Download CSV]  [Export JSON]                               │
│                                                              │
└──────────────────────────────────────────────────────────────┘

BUILT? YES. Seed data has 50+ failed startups. Dashboard has charts.
```

---

### 2.4 What We're Cutting From the MVP

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  FULL PRODUCT (what we're building toward):                          │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                                                                │  │
│  │  ████████████████████████████████████████████████████████████  │  │
│  │  ████████████████████████████████████████████████████████████  │  │
│  │  ████████████████████████████████████████████████████████████  │  │
│  │  ████████████████████████████████████████████████████████████  │  │
│  │                                                                │  │
│  │  55 agents, 26 collectors, 76 tables, real-time alerts,       │  │
│  │  Slack integration, CRM, watchlists, Pro tier, etc.           │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  MVP (what we ship first):                                           │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                                                                │  │
│  │  ██████████████████                                            │  │
│  │                                                                │  │
│  │  3 features. Seed data. Static dashboard. Public demo.        │  │
│  │                                                                │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  CUT FROM MVP (build after validation):                              │
│                                                                      │
│  Real-time pipeline    → Refresh button instead (ships now)         │
│  26 collectors         → Seed data + 5 RSS collectors (ships now)   │
│  Alert dispatch        → "Check back tomorrow" (ships Month 2)     │
│  Auth/API keys         → Public access (ships Month 2)              │
│  Watchlists            → Bookmark in browser (ships Month 3)       │
│  CRM integration       → Copy-paste (ships Month 3)                │
│  Pro tier              → Free for everyone (ships Month 2)          │
│  PDF export            → Browser Print > Save as PDF (now)         │
│  Score push WebSocket  → Page refresh (ships Month 2)              │
│  HuggingFace MCP       → Fixed models (ships Month 4)              │
│                                                                      │
│  PRINCIPLE: Ship the 20% that proves 80% of the value.             │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Part 3: MVP vs Full Product Comparison

---

### 3.1 Feature Comparison

| Feature | MVP (Week 2) | V1 (Month 2) | V2 (Month 6) | Full (Year 1) |
|---|---|---|---|---|
| **Score a startup** | ✅ Instant | ✅ | ✅ | ✅ |
| **AI chat** | ✅ Ollama | ✅ | ✅ + HF MCP | ✅ + models |
| **Failure patterns** | ✅ Seed data | ✅ + live data | ✅ | ✅ + predictions |
| **Dashboard** | ✅ Static charts | ✅ + live | ✅ + watchlist | ✅ + custom |
| **Search** | ✅ Full-text | ✅ + semantic | ✅ + hybrid | ✅ |
| **Knowledge graph** | ✅ Seed entities | ✅ | ✅ + temporal | ✅ + community |
| **Data sources** | ✅ 5 RSS + seed | 15 collectors | 26 collectors | 30+ |
| **Real-time alerts** | ❌ | ✅ Slack + Email | ✅ + Discord | ✅ + custom |
| **Authentication** | ❌ | ✅ API keys | ✅ + SSO | ✅ + RBAC |
| **Pro tier** | ❌ | ✅ $49/mo | ✅ $99/mo | ✅ + Enterprise |
| **Watchlists** | ❌ | ❌ | ✅ | ✅ |
| **PDF export** | ❌ (print) | ✅ | ✅ | ✅ |
| **CRM integration** | ❌ | ❌ | ✅ Salesforce | ✅ + HubSpot |
| **Score push** | ❌ (refresh) | ✅ WebSocket | ✅ + SSE | ✅ |
| **Continuous collection** | ❌ (manual) | ✅ Scheduler | ✅ + Dagster | ✅ |
| **Monitoring** | ❌ (logs) | ❌ | ✅ Prometheus | ✅ + Grafana |
| **HuggingFace MCP** | ❌ | ❌ | ❌ | ✅ dynamic models |
| **Mobile** | ❌ | ❌ | ❌ | ✅ PWA |

### 3.2 Cost Comparison

| | MVP | V1 | V2 | Full |
|---|---|---|---|---|
| **Development time** | 2 weeks | 8 weeks | 6 months | 12 months |
| **Infrastructure cost** | $0 (local) | $20/mo | $100/mo | $300/mo |
| **External API costs** | $0 | $0 | $0 | $50/mo |
| **Team size** | 1 person | 1 person | 2-3 people | 3-5 people |
| **Risk level** | 🟢 Low | 🟡 Medium | 🟡 Medium | 🔴 High |

---

## Part 4: The MVP Build Plan (2 Weeks)

---

### Week 1: Make What's Built Work End-to-End

```
DAY 1-2: DATA SETUP
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  Goal: Load enough data that the demo feels real             │
│                                                              │
│  Tasks:                                                      │
│  ☐ Run seed_data.py (50+ failed startups already there)     │
│  ☐ Run 5 RSS collectors to get live data:                   │
│     python run_collectors.py --collector google_news_rss     │
│     python run_collectors.py --collector techcrunch_rss      │
│     python run_collectors.py --collector failory_scraper     │
│     python run_collectors.py --collector bls_survival_rates  │
│     python run_collectors.py --collector reshoring_pdf       │
│  ☐ Run scoring pipeline:                                    │
│     python run_agent.py --pipeline analysis                  │
│  ☐ Verify 50+ scored entities exist                         │
│  ☐ Verify search returns results for known companies         │
│                                                              │
│  TARGET: 100+ entities scored, 500+ news articles,          │
│          50+ failed startups with full breakdowns            │
│                                                              │
│  TIME: 4-6 hours (everything is built, just run it)          │
│                                                              │
└──────────────────────────────────────────────────────────────┘

DAY 3-4: DASHBOARD FIXES
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  Goal: The dashboard looks professional on first visit       │
│                                                              │
│  Tasks:                                                      │
│  ☐ Fix any broken API calls in site/index.html               │
│  ☐ Ensure all Canvas charts render with real data            │
│  ☐ Add "Top 10 Opportunities" section to dashboard           │
│  ☐ Make search box actually call /api/search                 │
│  ☐ Make chat box actually call /api/chat                     │
│  ☐ Test: type "Fisker" → get score + risk + breakdown       │
│  ☐ Test: type "Why did Juicero fail?" → get AI answer       │
│  ☐ Mobile responsive check (site already has hamburger)      │
│                                                              │
│  TARGET: Anyone can open the page and get value in 10 sec   │
│                                                              │
│  TIME: 8-12 hours (mostly frontend polish)                   │
│                                                              │
└──────────────────────────────────────────────────────────────┘

DAY 5: DEPLOY
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  Goal: The demo is accessible at a public URL                │
│                                                              │
│  Tasks:                                                      │
│  ☐ Deploy to a $10/month VPS (DigitalOcean/Hetzner)         │
│  ☐ docker compose up -d (11 services)                        │
│  ☐ Configure nginx reverse proxy + HTTPS                    │
│  ☐ Set up demo.opportunity-intel.org DNS                    │
│  ☐ Load seed data on the server                             │
│  ☐ Run initial collection + scoring                         │
│  ☐ Set up cron job to run collectors every 6 hours          │
│     0 */6 * * * cd /app && python run_collectors.py --all   │
│     0 */6 * * * cd /app && python run_agent.py --pipeline analysis │
│  ☐ Verify the demo works from a fresh browser               │
│                                                              │
│  TARGET: demo.opportunity-intel.org is live                  │
│                                                              │
│  TIME: 4-6 hours                                             │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Week 2: Launch + Measure

```
DAY 6-7: LAUNCH CONTENT
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  Goal: People know the demo exists                           │
│                                                              │
│  Tasks:                                                      │
│  ☐ Record 60-second demo GIF (type name → get score)        │
│  ☐ Write "Show HN" post:                                    │
│     Title: "Show HN: Open-source Crunchbase with AI that    │
│             predicts startup failure"                        │
│     Body: 3 paragraphs + demo GIF + GitHub link              │
│  ☐ Write blog post: "We analyzed 500 failed startups"       │
│  ☐ Create GitHub README with badges, GIF, install steps     │
│  ☐ Set up Google Analytics or Plausible on demo             │
│  ☐ Set up a simple feedback form (Typeform/Tally)           │
│                                                              │
│  TIME: 8-12 hours                                            │
│                                                              │
└──────────────────────────────────────────────────────────────┘

DAY 8: LAUNCH
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  Goal: Get the first 500 visitors                            │
│                                                              │
│  Post to:                                                    │
│  ☐ Hacker News (Show HN) — biggest traffic source           │
│  ☐ Reddit r/startups — direct target audience               │
│  ☐ Reddit r/MachineLearning — AI angle                      │
│  ☐ Reddit r/dataisbeautiful — failure pattern charts         │
│  ☐ Twitter/X — tag relevant accounts                        │
│  ☐ LinkedIn — startup/investor groups                       │
│  ☐ Indie Hackers — founder community                        │
│                                                              │
│  MONITOR:                                                    │
│  ☐ Traffic (target: 500+ visitors)                          │
│  ☐ Search queries (what do people search for?)              │
│  ☐ Chat questions (what do people ask?)                     │
│  ☐ Server health (uptime, response time)                    │
│                                                              │
└──────────────────────────────────────────────────────────────┘

DAY 9-14: MEASURE + LEARN + ITERATE
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  Goal: Learn what users actually want                        │
│                                                              │
│  Every day, answer these questions:                          │
│                                                              │
│  1. HOW MANY VISITORS?                                       │
│     Target: 500+ total visitors in 2 weeks                  │
│     If < 200: positioning is wrong, not the product         │
│                                                              │
│  2. WHAT DO THEY SEARCH FOR?                                 │
│     Collect all search queries from API logs                │
│     Are they searching companies? Sectors? Questions?       │
│     This tells us what features to build next.              │
│                                                              │
│  3. DO THEY USE CHAT?                                        │
│     What questions do they ask?                              │
│     How many queries per user?                               │
│     If < 10% use chat: the score alone is enough.           │
│                                                              │
│  4. DO THEY COME BACK?                                       │
│     How many return within 7 days?                           │
│     If < 5%: the value isn't sticky enough.                 │
│                                                              │
│  5. WHAT DO THEY ASK FOR?                                    │
│     "Can I get alerts when scores change?" → Build alerts   │
│     "Can I track specific companies?" → Build watchlist     │
│     "Can I export this data?" → Build CSV/PDF export        │
│     "Can I integrate with my CRM?" → Build webhooks         │
│     "How accurate are your scores?" → Publish backtest      │
│                                                              │
│  THIS DATA DECIDES WHAT TO BUILD IN MONTH 2.                │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Part 5: Why MVP First Works (Benefits)

---

### 5.1 Faster Feedback

```
WITHOUT MVP:
  Build for 6 months → launch → discover users want
  different features → rebuild for 3 months → launch again

  Total: 9 months to first real user feedback
  Risk: You built the wrong thing for 6 months

WITH MVP:
  Ship in 2 weeks → measure for 2 weeks → learn what
  users want → build exactly that for 2 weeks → repeat

  Total: 4 weeks to first real user feedback
  Benefit: You know what to build because users told you

THE MATH:
  MVP cycle:  2 weeks build + 2 weeks measure = 4 weeks
  Full build: 6 months build + 0 weeks measure   = 24 weeks

  MVP gets feedback 6x faster.
  In the time it takes to build the full product,
  you can run 6 MVP cycles and validate 6 hypotheses.
```

### 5.2 Lower Cost

```
COST OF MVP:
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  Development:     $0 (your time, already-built components)       │
│  Infrastructure:  $10/month VPS                                 │
│  Domain:          $12/year                                       │
│  External APIs:   $0 (all free tier or self-hosted)              │
│  Marketing:       $0 (organic — HN, Reddit, Twitter)            │
│                                                                  │
│  TOTAL MVP COST: $22 for the first month                        │
│                                                                  │
│  If nobody uses it: you lost $22 and 2 weeks.                   │
│  If people love it: you have validated demand for free.          │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

COST OF BUILDING EVERYTHING FIRST:
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  6 months of development time                                    │
│  Infrastructure during dev: $600 (6 × $100)                     │
│  API costs during dev: $300 (various services)                  │
│  Marketing at launch: $500-2000                                  │
│                                                                  │
│  TOTAL: $1,400-3,100 + 6 months of opportunity cost             │
│                                                                  │
│  If nobody uses it: you lost $3,100 and 6 months.               │
│  If people love it: you still wasted 5.5 months of revenue.     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

RISK REDUCTION:
  MVP approach: $22 at risk
  Build-first: $3,100 at risk

  MVP is 141x cheaper in financial risk.
```

### 5.3 Reduced Risk

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  THE 5 RISKS THE MVP ELIMINATES:                                     │
│                                                                      │
│  RISK 1: NOBODY WANTS THIS                                          │
│  ──────────────────────────                                          │
│  Build-first: 6 months to discover this. Devastating.               │
│  MVP-first:   2 weeks. Pivot or kill. Move on.                      │
│                                                                      │
│  RISK 2: WRONG FEATURES                                             │
│  ──────────────────────                                              │
│  Build-first: You guess what users want. You guess wrong.           │
│  MVP-first:   Users tell you what they want. You build that.        │
│                                                                      │
│  RISK 3: WRONG PRICING                                              │
│  ─────────────────────                                               │
│  Build-first: You set $99/mo. Nobody pays. You don't know why.      │
│  MVP-first:   Users ask "how much?" → you learn what they'd pay.    │
│                                                                      │
│  RISK 4: WRONG AUDIENCE                                             │
│  ──────────────────────                                              │
│  Build-first: You built for investors. Teachers use it instead.     │
│  MVP-first:   You see WHO uses it → build for the right audience.   │
│                                                                      │
│  RISK 5: TECHNICAL OVER-INVESTMENT                                   │
│  ──────────────────────────────                                      │
│  Build-first: You built 26 collectors. Users only need 5.           │
│  MVP-first:   You built 5. Users ask for 3 more. You build those.   │
│                                                                      │
│  THE INSIGHT:                                                        │
│  Most startup failures are not technical failures.                  │
│  They are MARKET failures — building something nobody wants.        │
│  The MVP tests the market BEFORE you build the product.             │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Part 6: MVP Success Criteria

---

### 6.1 The MVP Pass/Fail Test

```
AFTER 2 WEEKS OF THE MVP BEING LIVE:

┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  GREEN LIGHT (proceed to V1):                                        │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ ☐ 500+ unique visitors to the demo                            │  │
│  │ ☐ 100+ search queries (people are trying it)                  │  │
│  │ ☐ 50+ chat questions (people are engaging)                    │  │
│  │ ☐ 10+ email/Twitter messages asking for features              │  │
│  │ ☐ 5+ people who visited 2+ times (returning users)            │  │
│  │ ☐ 2+ unsolicited mentions/shares on social media              │  │
│  │                                                                │  │
│  │ IF ALL 6: Build V1. The market wants this.                    │  │
│  │ IF 4-5:  Keep measuring. Promising but not proven.            │  │
│  │ IF < 4:   Pivot. The positioning or product is wrong.         │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  RED LIGHT (pivot or kill):                                          │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ ☐ < 100 unique visitors (nobody cares about the landing)      │  │
│  │ ☐ < 10 search queries (people visit but don't try)            │  │
│  │ ☐ < 3 chat questions (the AI isn't interesting)               │  │
│  │ ☐ 0 feature requests (nobody wants more)                      │  │
│  │ ☐ 0 returning users (not sticky)                              │  │
│  │                                                                │  │
│  │ IF 3+ RED: Stop building. Re-think the problem.               │  │
│  │   Possible pivots:                                             │  │
│  │   • Focus on failure data only (researchers)                  │  │
│  │   • Focus on geographic strategy only (founders)              │  │
│  │   • Focus on AI chat only (simpler product)                   │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 6.2 What the MVP Data Tells Us

| What Users Do | What It Means | What to Build Next |
|---|---|---|
| Search company names | They want scores | Improve scoring accuracy |
| Search sector names | They want sector analysis | Build sector dashboards |
| Ask "why did X fail?" | They want failure intelligence | Enhance failure patterns |
| Ask "should I invest in X?" | They want investment signals | Build alerting + watchlists |
| Search their own company | Founders are users | Build founder-specific views |
| Search competitors | Competitive intelligence | Build comparison feature |
| Ask about geography | Location matters | Build geographic strategy deeper |
| Use CSV export | Researchers are users | Build API + research tools |
| Ask "how accurate?" | Trust is the bottleneck | Publish backtest results |
| Ask "can I get alerts?" | They want real-time | Build alerting system |
| Ask "is there an API?" | Developers are users | Build API + SDK |
| Ask "how much?" | They'll pay | Build Pro tier |

---

## Part 7: MVP → V1 → V2 → Full Product Roadmap

---

```
WEEK 1-2: MVP (THIS DOCUMENT)
┌──────────────────────────────────────────────────────────────┐
│  3 features: Score, Chat, Failure Patterns                    │
│  5 collectors + seed data                                     │
│  Static dashboard (refresh for updates)                       │
│  Public demo, no auth, no payments                            │
│  Cost: $22    Time: 2 weeks    Risk: Minimal                 │
│  GOAL: Validate that users want this                          │
└──────────────────────────────────────────────────────────────┘
         │
         │ IF VALIDATED (500+ visitors, 50+ searches)
         ▼
MONTH 2: V1 — "The Useful Version"
┌──────────────────────────────────────────────────────────────┐
│  + Real-time alerts (Slack + Email)                           │
│  + Collector scheduler (24/7 collection)                      │
│  + WebSocket score push (live dashboard)                      │
│  + API key authentication                                     │
│  + Pro tier ($49/mo)                                          │
│  + 15 collectors                                              │
│  Cost: $50/mo    Time: 4 weeks    Risk: Low                  │
│  GOAL: First paying users ($500 MRR)                          │
└──────────────────────────────────────────────────────────────┘
         │
         │ IF GROWING (200+ Pro users, $10K MRR)
         ▼
MONTH 3-6: V2 — "The Complete Version"
┌──────────────────────────────────────────────────────────────┐
│  + Watchlists + Opportunity Feed                              │
│  + CRM integration (Salesforce webhook)                       │
│  + PDF export                                                 │
│  + Historical charts                                          │
│  + Company comparison                                         │
│  + All 26 collectors                                          │
│  + Score accuracy validation (backtest)                       │
│  Cost: $200/mo    Time: 4 months    Risk: Medium              │
│  GOAL: Product-market fit ($25K MRR)                          │
└──────────────────────────────────────────────────────────────┘
         │
         │ IF SCALING (1,000+ users)
         ▼
MONTH 7-12: V3 — "The Platform"
┌──────────────────────────────────────────────────────────────┐
│  + Enterprise tier (SSO, SLA, custom agents)                  │
│  + HuggingFace MCP integration                                │
│  + Community contributor tools                                │
│  + University program                                         │
│  + Ambassador program                                         │
│  + Mobile PWA                                                 │
│  + Dagster orchestration                                      │
│  + Prometheus + Grafana monitoring                            │
│  Cost: $500/mo    Time: 6 months    Risk: Low                 │
│  GOAL: Industry standard ($3M ARR)                            │
└──────────────────────────────────────────────────────────────┘
```

---

## Part 8: The One-Page MVP Plan

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  THE MVP: "Type a startup name → get a score, risk, and WHY"       │
│                                                                      │
│  3 FEATURES:                                                        │
│    1. Instant Startup Score (0-100 with attribution)    ✅ BUILT    │
│    2. AI Chat ("Why did X fail?")                       ✅ BUILT    │
│    3. Failure Pattern Browser (charts + taxonomy)       ✅ BUILT    │
│                                                                      │
│  WHAT'S CUT:                                                        │
│    Real-time, alerts, auth, watchlists, CRM, Pro tier,              │
│    PDF, mobile, MCP, monitoring — ALL deferred until validated      │
│                                                                      │
│  WHAT TO BUILD (2 weeks):                                           │
│    Week 1: Load data + fix dashboard + deploy demo                  │
│    Week 2: Record demo GIF + launch on HN + measure                 │
│                                                                      │
│  COST: $22 ($10 VPS + $12 domain)                                   │
│  TIME: 2 weeks                                                      │
│  RISK: Minimal — 83% of code is already built                       │
│                                                                      │
│  SUCCESS = 500 visitors, 50 searches, 10 feature requests           │
│  FAILURE = < 100 visitors → pivot or kill                           │
│                                                                      │
│  BENEFITS:                                                          │
│    Faster feedback: 2 weeks vs 6 months (6x faster)                │
│    Lower cost: $22 vs $3,100 (141x cheaper)                        │
│    Reduced risk: Test market BEFORE building the full product       │
│                                                                      │
│  95% of the MVP is already built.                                   │
│  The only thing missing is: deploy it and let people use it.        │
│                                                                      │
│  NEXT ACTION: Run seed data, deploy demo, launch.                   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

*Last updated: June 5, 2026*

---

## Feedback-Driven MVP Checklist

> **This section updates the MVP plan based on feedback infrastructure.**
> See `FEEDBACK_STRATEGY.md` for the complete process.

### Pre-Launch: Build the Ears (Add to MVP Week 1)

```
DAY 3 (additional, 3-4 hours):
☐ Add 4 feedback tables to db/schema.py
☐ Add feedback API endpoints (POST /api/feedback/score, /feature)
☐ Instrument search + chat endpoints with query logging
☐ Add thumbs up/down widget to dashboard
☐ Add feature request button to dashboard

DAY 4 (additional, 2-3 hours):
☐ Create agents/feedback_analyzer_agent.py
☐ Modify orchestrator to read feedback before scheduling
☐ Add /api/progress endpoint
☐ Create CHANGELOG.md
☐ Set up Plausible analytics
```

### Post-Launch: Measure → Learn → Adjust

```
EVERY MONDAY AFTER LAUNCH:
☐ Pull feedback dashboard data (GET /api/feedback/dashboard)
☐ Review top 20 searches + top 20 chat questions
☐ Review score accuracy + feature request votes
☐ Score signals → reorder priorities
☐ Update GOALS_AND_PRIORITIES.md with changes
☐ Post weekly update (#BuildInPublic)
☐ Feed priorities to agents via FeedbackAnalyzerAgent
```

### What Changes Based on Feedback

| User Signal | Current Plan | If Signal Appears | Adjusted Plan |
|---|---|---|---|
| Score rating < 3.0 | Build alerts next | 30%+ thumbs down | P0: Fix scoring first |
| 50+ alert requests | Alerts are P1 | Confirmed demand | Move alerts to P0 |
| 0 chat usage | Chat is P0 feature | < 5% of visitors use it | Deprioritize chat improvements |
| 200+ EV searches | No sector focus | EV is top topic | Build EV-specific features |
| 20+ "how much?" | Pro tier in Month 2 | Revenue signal | Build Pro tier immediately |
| Users search own name | Founders not a target | Founder persona | Add founder features |
