# r/startups Post

**Title**: `Free open-source tool that analyzes why startups fail and finds revival opportunities — no API keys needed`

---

## TL;DR

We built a free, open-source tool that studies why startups fail and identifies opportunities in manufacturing and other sectors. It runs entirely on your machine — no API keys, no cloud accounts, no monthly fees.

**Repo**: https://github.com/gokul-koduri/start

## The Problem

Two things bothered us about the startup intelligence landscape:

1. **It's expensive.** Crunchbase is $490/month. PitchBook is $1,000+/month. Tracxn is $500+/month. Most founders can't justify that spend.
2. **Nobody studies failure.** Every platform tracks funding, acquisitions, and success stories. But 90% of startups fail, and understanding why is arguably more valuable than tracking the ones that made it.

## What We Built

The **Opportunity Intelligence Platform** — a self-hosted, open-source alternative that:

- Collects data from 24 sources (SEC filings, BLS survival rates, Reddit, HN, GitHub, Google News, patent databases, Product Hunt, and more)
- Runs 50+ AI agents that analyze failure patterns, score opportunities, and track market trends
- Gives you an interactive dashboard and API to query everything
- Runs locally with Ollama (llama3) — your data never leaves your machine

## How Founders Can Use It

**Avoid failure patterns in your sector.** Ask the AI analyst questions like:
- "Why do most EV startups fail?"
- "What are the common failure reasons for SaaS startups in healthcare?"
- "Which manufacturing sectors have the highest survival rates?"

**Find revival opportunities.** The platform identifies sectors where startups previously failed but conditions have changed — reshoring, CHIPS Act funding, supply chain shifts.

**Track your market in real-time.** 24 collectors pull data continuously so you see news, discussions, and trends as they happen.

## Getting Started (2 minutes)

```bash
git clone https://github.com/gokul-koduri/start.git
cd start
pip install -r requirements.txt
python api_server.py
```

Opens:
- **Dashboard**: http://localhost:8000/
- **API docs**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/api/health

Or with Docker (14 services including MySQL, Redis, Elasticsearch, vector search):

```bash
docker compose up -d
```

## What You Get

| Feature | What It Does |
|---|---|
| **Startup Search** | Search across 163 failed startups with failure reason taxonomy |
| **Failure Analysis** | Pattern analysis by sector, geography, and timeframe |
| **Opportunity Scoring** | Ranked opportunities with explainable scores |
| **AI Chat** | Ask questions about startup failures and opportunities |
| **News Collection** | Real-time from 24 sources (Google News, TechCrunch, Reddit, HN, SEC, etc.) |
| **BLS Survival Data** | Bureau of Labor Statistics survival rates by sector |
| **Manufacturing Revival** | Reshoring data, CHIPS Act opportunities, geographic hotspots |
| **API** | 42 REST endpoints for programmatic access |

## Why Open Source

We believe startup intelligence shouldn't be locked behind $500+/month paywalls. The data is out there — SEC filings are public, BLS data is public, news is public. We're just connecting the dots.

The entire platform is MIT licensed. Fork it, modify it, build on it.

## The Numbers

- 244 Python files
- 68 AI agents + 7 dev team agents
- 24 data collectors
- 87 database tables
- 968 tests (0 failing)
- 14 Docker services

## What We Need From You

This is a side project that grew into something bigger. We'd love to know:

1. **What data sources matter most to you?** We have 24 collectors — what are we missing?
2. **What would make this genuinely useful?** Features, visualizations, exports?
3. **Would you actually use this?** If not, what's the blocker?

We're actively developing and sprinting toward v1.0. Feedback shapes the roadmap.

**Repo**: https://github.com/gokul-koduri/start
