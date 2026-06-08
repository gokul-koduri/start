# 🎯 Product Vision — The User's Experience

> *"The best products feel like magic. The user asks a question, and the answer
> is already there — or it appears within seconds."*

---

## Who Is She?

**Dr. Priya Sharma**, 32, is a research analyst at a mid-size VC fund in Bangalore.

She tracks 200+ startups across SaaS, FinTech, and CleanTech. Her morning ritual:
open Crunchbase, PitchBook, TechCrunch, Reddit, GitHub trending, SEC EDGAR,
LinkedIn, and 3 Google Alerts — all before her first coffee.

She pays **$490/month for Crunchbase**, **$1,000/month for PitchBook**, and still:
- Discovers funding rounds **days after** they happen
- Has **no idea** what made 3 portfolio companies in her sector succeed last quarter
- Can't connect "hiring spike at rival X" → "product launch imminent"
- Spends **4 hours every Monday** building weekly intelligence reports manually

**Priya is our user.** Not the developer. Not the data engineer. The person who
needs to *make decisions* with this information.

---

## The Moment She Discovers Us

### Scenario A: Hacker News

```
Show HN: We built an open-source Crunchbase alternative
         with 50+ AI agents that reveals why startups succeed

She's scrolling HN on her phone during commute.
"Open-source Crunchbase? With AI agents? That reveals why startups succeed?"

She clicks. Skims the architecture. Sees:
  - 24 data sources, real-time
  - 50+ AI agents doing actual analysis
  - Self-hosted → her fund's data stays private
  - Reveals what makes startups thrive and how they overcome challenges
  - Free

"Hmm. Let me try this on the staging server."
```

### Scenario B: Reddit r/startups

```
"I was paying $490/mo for Crunchbase. Then I found an open-source
 alternative that reveals what makes startups thrive and how founders overcome challenges."

She's browsing r/startups during lunch.
The post has 347 upvotes. Comments are positive.
Someone in the thread says: "The knowledge graph feature alone
is worth setting it up."

She bookmarks the repo.
```

### Scenario C: A Colleague's Dashboard

```
Her colleague Arjun shares his screen during a meeting:
"Look, I set up this tool over the weekend. It sent me an alert
that Neonify just raised a Series B — 15 minutes after the SEC filing.
And it showed me that 3 similar startups thrived by pivoting to enterprise."

Priya: "Wait, what tool is this?"
Arjun: "It's open-source. I self-hosted it. Took me 30 minutes."

She opens the repo on her laptop during the meeting.
```

---

## Her First 5 Minutes — The "Aha!" Moment

```
She clones the repo, runs docker compose up.

                          ┌─────────────────────────────────────┐
                          │                                     │
                          │   📡 RADAR — Opportunity Intelligence │
                          │                                     │
                          │   ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐
                          │   │ 142  │ │  23  │ │ 891  │ │  3   │
                          │   │signals│ │opps  │ │tracked│ │alerts│
                          │   │today  │ │scored│ │starts│ │active│
                          │   └──────┘ └──────┘ └──────┘ └──────┘
                          │                                     │
                          │   🟢 Live Signal Feed               │
                          │   ┌─────────────────────────────┐   │
                          │   │ ● Stripe raised $1.2B       │   │
                          │   │   SEC EDGAR · 12 min ago    │   │
                          │   ├─────────────────────────────┤   │
                          │   │ ● Neonify hiring 15 SWEs    │   │
                          │   │   Job Boards · 2 hrs ago    │   │
                          │   ├─────────────────────────────┤   │
                          │   │ ● "Why 80% of FinTech       │   │
                          │   │   startups thrive"           │   │
                          │   │   Reddit · 4 hrs ago        │   │
                          │   └─────────────────────────────┘   │
                          │                                     │
                          │   🔥 Top Opportunities              │
                          │   ┌─────────────────────────────┐   │
                          │   │ 87  Neuromorphic Labs  ▲    │   │
                          │   │ 82  Quantum Dynamics   ▲    │   │
                          │   │ 79  CleanForge         →    │   │
                          │   └─────────────────────────────┘   │
                          │                                     │
                          │   🗺️ Sector Heat Map               │
                          │   AI/ML  SaaS  CleanTech  FinTech   │
                          │    🔥     🟡     🟢        🟡      │
                          │                                     │
                          └─────────────────────────────────────┘

Her reaction: "Wait — this is live? Where is this data coming from?"
```

**The aha moment is instant**: she sees real-time signals flowing in, scored
opportunities ranked by composite ML score, and a sector heat map — all from
a tool she just set up for free.

---

## Her First 30 Minutes — The Journey Deepens

### Step 1: She searches for a competitor (Search page)

```
She types "Razorpay" into the search bar.

                          ┌─────────────────────────────────────┐
                          │  🔍 Search                          │
                          │                                     │
                          │  [ Razorpay                    ✕ ]  │
                          │                                     │
                          │  Hybrid  |  Semantic  |  Full-Text  │
                          │                                     │
                          │  12 results for "Razorpay"          │
                          │                                     │
                          │  ┌─────────────────────────────┐    │
                          │  │ 82  Razorpay                │    │
                          │  │     FinTech · India  ▲      │    │
                          │  │     14 signals              │    │
                          │  ├─────────────────────────────┤    │
                          │  │ 74  Razorpay acquired Ezetap│    │
                          │  │     SEC EDGAR · funding     │    │
                          │  ├─────────────────────────────┤    │
                          │  │ 68  "Razorpay vs Stripe..." │    │
                          │  │     Reddit · discussion     │    │
                          │  └─────────────────────────────┘    │
                          └─────────────────────────────────────┘

She clicks on Razorpay → opportunity detail page.
```

### Step 2: She explores the knowledge graph (Graph page)

```
She types "Razorpay" into the graph search.

                          ┌─────────────────────────────────────┐
                          │  🔗 Knowledge Graph                 │
                          │                                     │
                          │  [ Razorpay                   ]     │
                          │                                     │
                          │        ○ Sequoia                    │
                          │       /                            │
                          │  Stripe ──── competes_with         │
                          │       \    \                        │
                          │        ○   Razorpay ── uses ── ○   │
                          │    ○ YC    /              React    │
                          │     \    /                         │
                          │      ○ ○                           │
                          │    funded_by                       │
                          │                                     │
                          │  ● startup  ● investor  ● tech     │
                          │  ● person   ● region    ● market   │
                          │                                     │
                          │  18 nodes · 23 edges               │
                          └─────────────────────────────────────┘

She clicks on "Sequoia" → sees all Sequoia investments.
She clicks on "competes_with" → sees Stripe's competitors.

"Wait, I can see the ENTIRE competitive landscape as a graph?
 This would take me hours to build in a spreadsheet."
```

### Step 3: She asks the AI a question (Chat)

```
She opens the chat bubble in the bottom-right corner.

                          ┌─────────────────────────────┐
                          │  💬 AI Analyst               │
                          │                             │
                          │  You: Which FinTech sectors │
                          │  are thriving the most in   │
                          │  India?                     │
                          │                             │
                          │  AI: Based on analysis of   │
                          │  163 thriving startups and  │
                          │  BLS growth data:           │
                          │                             │
                          │  1. Digital Lending (32%    │
                          │     top-quartile growth, n=42)│
                          │  2. Crypto Exchange (28%)   │
                          │  3. Neobanking (45%         │
                          │     survivor rate)          │
                          │                             │
                          │  Key pattern: digital       │
                          │  lending startups that      │
                          │  raised >$10M Series A      │
                          │  had 2.3x higher growth when│
                          │  they invested in regulatory│
                          │                             │
                          │  [ Ask follow-up ]          │
                          └─────────────────────────────┘

"What?? This would have taken me a WEEK to research."
```

### Step 4: She checks the Signals feed (Signals page)

```
She browses the real-time signal feed.

                          ┌─────────────────────────────────────┐
                          │  📡 Real-Time Signal Feed            │
                          │                                     │
                          │  Filter: [All Sources ▼]            │
                          │                                     │
                          │  ┌─────────────────────────────┐    │
                          │  │ SEC EDGAR · funding_round   │    │
                          │  │ Stripe raises $1.2B Series E│    │
                          │  │ "Stripe, Inc. filed Form D…"│    │
                          │  │ 12 minutes ago · Score: 82  │    │
                          │  │ → View in Knowledge Graph   │    │
                          │  ├─────────────────────────────┤    │
                          │  │ JOB BOARDS · hiring_spike   │    │
                          │  │ Neonify hiring 15 SWEs      │    │
                          │  │ "15 new job postings in 3…" │    │
                          │  │ 2 hours ago · Score: 71     │    │
                          │  │ → View in Knowledge Graph   │    │
                          │  ├─────────────────────────────┤    │
                          │  │ REDDIT · sentiment           │    │
                          │  │ "Why 80% of FinTech thrive" │    │
                          │  │ "r/startups · 347 comments" │    │
                          │  │ 4 hours ago · Score: 54     │    │
                          │  │ → View in Knowledge Graph   │    │
                          │  └─────────────────────────────┘    │
                          └─────────────────────────────────────┘

She notices the signals flow is sorted by score and recency.
Each signal has a type badge, a source badge, and a direct link
to the knowledge graph.

"This is what my Monday morning report looks like — but it's
 already done. Automatically. In real-time."
```

### Step 5: She browses sectors (Sectors page)

```
                          ┌─────────────────────────────────────┐
                          │  🗺️ Sectors                         │
                          │                                     │
                          │  ┌──────────┐ ┌──────────┐         │
                          │  │ 🔥 AI/ML │ │ 🟡 SaaS  │         │
                          │  │   87     │ │   72     │         │
                          │  │ 14 cos   │ │ 23 cos   │         │
                          │  ├──────────┤ ├──────────┤         │
                          │  │ 🟢 CleanT│ │ 🟡 FinTe │         │
                          │  │   65     │ │   71     │         │
                          │  │ 8 cos    │ │ 19 cos   │         │
                          │  └──────────┘ └──────────┘         │
                          │                                     │
                          │  Score Distribution                 │
                          │  AI/ML    ████████████████░░ 87     │
                          │  SaaS     ██████████████░░░░ 72     │
                          │  FinTech  █████████████░░░░░ 71     │
                          │  CleanTech████████████░░░░░░ 65     │
                          └─────────────────────────────────────┘

She clicks on "FinTech" → drills into 19 FinTech opportunities.
Clicks on the top one → detail page with full scoring breakdown.
```

---

## Her First Week — The Habit Forms

### Day 1: Set up
- Cloned the repo, ran `docker compose up`, data started flowing
- Searched for 5 competitors, explored knowledge graph
- Asked AI analyst 3 questions — got useful answers

### Day 2: Configured alerts
- Set up email digest for "FinTech" sector (daily)
- Created webhook for "hiring_spike" signals (Slack)
- Added "Razorpay" and "Stripe" to watchlist

### Day 3: Morning report
- Opened her email at 8 AM
- Found a daily digest waiting:
  - 3 new signals overnight
  - 1 score change: Razorpay 82→85 (rising)
  - 1 new opportunity scored >75: "PayFlow"
- Clicked through to the dashboard to investigate

### Day 4: Board meeting prep
- Exported a PDF report for the investment committee
- It included: sector heat map, top opportunities, risk scores,
  knowledge graph visualization for her portfolio companies
- Her report looked like it took a week to build. It took 10 minutes.

### Day 5: She tells her team
- "I found this open-source tool. It replaced Crunchbase for me.
  And it does things Crunchbase can't — like revealing what makes startups thrive
  and how founders overcome challenges. And it's free."
- Arjun (the developer): "Let me look at the API — I can wire
  it into our internal tools."

---

## Her Ongoing Experience — After a Month

```
Every morning:
  ┌──────────────────────────────────────────────────────────────┐
  │                                                              │
  │  8:00 AM — Daily digest email arrives                       │
  │  8:02 AM — 3 quick reads: new funding, hiring spike,       │
  │           sentiment shift in her sectors                     │
  │  8:05 AM — Clicks into dashboard to explore                 │
  │  8:10 AM — Asks AI: "Any new competitors in digital         │
  │           lending in India this week?"                       │
  │  8:12 AM — Adds 2 new startups to watchlist                 │
  │                                                              │
  │  Every Monday:                                               │
  │  Weekly PDF report auto-generated                            │
  │  → She forwards it to the investment committee               │
  │  → It takes her 0 minutes to produce                        │
  │                                                              │
  │  Ad hoc:                                                     │
  │  → Slack alert when a watchlist company raises funding       │
  │  → Knowledge graph exploration for due diligence             │
  │  → CSV export of all scored opportunities in a sector        │
  │                                                              │
  └──────────────────────────────────────────────────────────────┘
```

### What she used to spend vs. what she spends now

| Task | Before | After | Saved |
|---|---|---|---|
| Monday intelligence report | 4 hours | 10 min (auto-generated) | 3h 50m |
| Tracking funding rounds | 2 hrs/day (manual) | 0 (real-time alerts) | 2 hrs/day |
| Competitive analysis | 3 hours/week | 30 min (knowledge graph) | 2.5 hrs |
| Due diligence research | 8 hours/startup | 2 hours (AI analyst + graph) | 6 hrs |
| **Total** | **~20 hrs/week** | **~4 hrs/week** | **~16 hrs/week** |

---

## The Upgrade to Pro ($99/month)

After a month on the free tier, Priya hits limits:

```
She gets a modal:

  ┌──────────────────────────────────────────────────────┐
  │                                                      │
  │  🔒 Pro Feature                                     │
  │                                                      │
  │  You've reached the free tier limit:                 │
  │  • 50 API calls/day (you used 47 today)              │
  │  • 3 watchlists (you have 3)                         │
  │  • Basic collectors only                             │
  │                                                      │
  │  Upgrade to Pro for:                                 │
  │  ✦ Unlimited API calls                               │
  │  ✦ Unlimited watchlists                              │
  │  ✦ All 24+ data collectors (real-time)               │
  │  ✦ Advanced ML scoring with feature attribution      │
  │  ✦ Daily/weekly automated email reports              │
  │  ✦ Slack + Discord webhook alerts                    │
  │  ✦ Priority support                                  │
  │                                                      │
  │  ┌──────────────┐  ┌──────────────┐                  │
  │  │  Maybe Later  │  │  Upgrade Pro  │                 │
  │  │               │  │  $99/month    │                 │
  │  └──────────────┘  └──────────────┘                  │
  │                                                      │
  └──────────────────────────────────────────────────────┘

She clicks "Upgrade Pro" → Stripe checkout → license key auto-generated
→ Pro features unlock instantly.
```

**Why she upgrades**: Not because she's forced — because the free tier already
delivered $1,490/month of value (replacing Crunchbase + PitchBook), and Pro
adds the real-time alerts and advanced scoring she now depends on.

---

## The Enterprise Conversation

After 3 months, Priya's fund wants to:

1. **Give every analyst their own dashboard** (multi-tenant)
2. **Integrate with their internal CRM** (API access)
3. **Custom data sources** (their proprietary deal flow database)
4. **White-label for LP reporting** (branded dashboards)

```
She emails us:

"We have 12 analysts who all want this. Can we get:
 - Custom data source integration
 - White-label dashboards for our LPs
 - On-premise deployment
 - SLA guarantee"

This is the $2,500/month enterprise conversation.
```

---

## The Three Surfaces the User Touches

### Surface 1: The Dashboard (where they live)

```
┌─────────────────────────────────────────────────────────────────┐
│  ⚡ Opportunity Intelligence                                     │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Radar  │ Signals │ Graph │ Opportunities │ Sectors │ Search ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                                                          │   │
│  │                    MAIN CONTENT AREA                     │   │
│  │                                                          │   │
│  │   Radar: KPIs + live feed + opportunities + heatmap     │   │
│  │   Signals: Real-time signal feed with filters           │   │
│  │   Graph: Interactive force-directed knowledge graph      │   │
│  │   Opportunities: Scored list with sort/filter/search     │   │
│  │   Sectors: Heat map + drill-down + distribution bars     │   │
│  │   Search: Semantic + fulltext + hybrid with mode tabs    │   │
│  │                                                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│                                          ┌────────────────┐     │
│                                          │ 💬 AI Analyst  │     │
│                                          │                │     │
│                                          │ Ask anything...│     │
│                                          └────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

### Surface 2: Email (where they get pulled back)

```
┌─────────────────────────────────────────────┐
│ 📧 Opportunity Intelligence Digest           │
│                                             │
│ Hi Priya, here's your daily briefing:       │
│                                             │
│ 📊 3 new signals in your watchlists         │
│ 🔥 Razorpay score up: 82 → 85              │
│ 🆕 New opportunity: PayFlow (score: 76)     │
│ ⚠️ Sentiment shift: FinTech → negative      │
│                                             │
│ [View Dashboard]                            │
│                                             │
│ ─── Opportunities ─────────────────────     │
│ 85 Razorpay ▲  │  76 PayFlow ▲  │ ...      │
│                                             │
│ ─── Sectors ──────────────────────────      │
│ AI/ML 🔥 │ SaaS 🟡 │ FinTech 🟡            │
│                                             │
│ You receive this because you subscribed     │
│ to daily digests for FinTech watchlist.     │
│ [Unsubscribe] [Change frequency]            │
└─────────────────────────────────────────────┘
```

### Surface 3: Slack/Discord (where they get interrupted)

```
🔔 [Opportunity Intelligence]
  New signal: Stripe raised $1.2B Series E
  Source: SEC EDGAR · Score: 82 · Sector: FinTech
  [View →]
```

---

## What "Done" Looks Like — V1.0 Launch Checklist

From the user's perspective, V1.0 is done when:

### Must-Have (Blockers)
- [ ] `docker compose up` → all services start, data flows in < 5 min
- [ ] Radar page shows live signals, scored opportunities, sector heatmap
- [ ] Search returns relevant results (semantic + fulltext)
- [ ] Knowledge graph renders and is explorable
- [ ] AI Chat answers questions about the data
- [ ] Signals page shows real-time feed from all collectors
- [ ] Sectors page shows heat map with drill-down
- [ ] Email digest sends daily summary to subscribers
- [ ] Feedback button captures user input
- [ ] Deployed to VPS with HTTPS
- [ ] Launched on HN + Reddit

### Should-Have (V1.1)
- [ ] Watchlists with alerts
- [ ] CSV/PDF export
- [ ] Slack/Discord webhooks
- [ ] User auth (login, API keys)
- [ ] Rate limiting
- [ ] Pro tier upgrade flow (Stripe)

### Nice-to-Have (V1.2)
- [ ] Mobile responsive
- [ ] Dark mode toggle
- [ ] Weekly automated PDF reports
- [ ] Zapier integration
- [ ] Data quality monitoring

---

## The North Star Metric

**Weekly Active Analysts (WAA)** — How many analysts use the platform
at least once per week?

- Week 1 (launch): Target 10 WAA
- Month 1: Target 50 WAA
- Month 3: Target 200 WAA (with Pro conversions)
- Month 6: Target 500 WAA

Every feature, every fix, every decision should be measured against:
**"Does this increase the chance that Priya opens our dashboard tomorrow?"**

---

## The Emotional Arc

```
Day 1:  "Wait, this is free?"           ← Discovery (HN/Reddit)
Day 1:  "Holy shit, this actually works" ← First search/result
Day 2:  "I need to show my team this"    ← Graph + AI chat
Week 1: "I'm saving 16 hours a week"    ← Habit formed
Month 1: "Take my money"                ← Pro upgrade
Month 3: "Can we get enterprise?"       ← Expansion
```

---

## What We Must NOT Forget While Building

1. **The dashboard is the product.** Not the agents, not the collectors,
   not the architecture. The user never sees those. They see 6 pages.

2. **Speed is a feature.** Every page must load in < 2 seconds.
   Search must return in < 500ms. Chat must respond in < 5 seconds.
   If it's slow, Priya goes back to Crunchbase.

3. **Data freshness is trust.** If Priya sees a signal that's 3 days old,
   she stops trusting the platform. Real-time means real-time.

4. **The free tier IS the marketing.** Every free user who has a good
   experience tells 5 people. The Pro upgrade is a natural consequence
   of the free tier being genuinely useful.

5. **Empty states are launch states.** On first install, before any data
   flows, the dashboard must still look professional and explain what
   will appear. Not broken empty divs.

6. **Errors must be invisible.** If a collector encounters issues, Priya doesn't care.
   She sees the other 23 sources. The system self-heals silently.

7. **Setbacks are lessons, not endings.** When showing data about challenges,
   always pair it with resilience strategies — how others in the same situation
   bounced back. This is what makes OIP unique.

---

*This document is the lens through which every engineering decision should
 be evaluated. Before writing code, ask: "How does this help Priya?"*
