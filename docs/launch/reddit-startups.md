# r/startups Post

**Title**: `Free open-source tool that reveals what makes startups thrive and how founders overcome challenges — no API keys needed`

---

## TL;DR

We built a free, open-source tool that studies **what makes startups successful**, identifies growth opportunities, and reveals how founders overcome challenges and setbacks. It runs entirely on your machine — no API keys, no cloud accounts, no monthly fees.

**Repo**: https://github.com/gokul-koduri/start

## The Problem

Two things bothered us about the startup intelligence landscape:

1. **It's expensive.** Crunchbase is $490/month. PitchBook is $1,000+/month. Tracxn is $500+/month. Most founders can't justify that spend.
2. **Nobody studies success factors.** Every platform tracks funding, acquisitions, and basic metrics. But nobody analyzes *why* some startups thrive while others don't. Nobody reveals the growth patterns, the resilience strategies, or how founders navigate challenges and come out stronger.

## What We Built

The **Opportunity Intelligence Platform** — a self-hosted, open-source alternative that:

- Collects data from 24 sources (SEC filings, BLS growth rates, Reddit, HN, GitHub, Google News, patent databases, Product Hunt, and more)
- Runs 50+ AI agents that analyze success patterns, score growth opportunities, and track how startups overcome challenges
- Gives you an interactive dashboard and API to query everything
- Runs locally with Ollama (llama3) — your data never leaves your machine

## How Founders Can Use It

**Learn what makes startups thrive in your sector.** Ask the AI analyst questions like:
- "What are the key success factors for thriving EV startups?"
- "How do successful SaaS founders overcome early growth challenges?"
- "Which manufacturing sectors have the highest growth potential?"

**Discover comeback strategies.** The platform analyzes how startups that faced setbacks pivoted, adapted, and emerged stronger. Learn from their resilience patterns.

**Find growth opportunities.** The platform identifies sectors with the best conditions for startup success — reshoring hotspots, funding-friendly regions, underserved markets.

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
| **Startup Search** | Search across startups with success factor analysis and growth taxonomy |
| **Success Pattern Analysis** | Pattern analysis of what drives growth by sector, geography, and timeframe |
| **Challenge Navigation** | How startups overcome setbacks — pivot strategies, turnaround stories, resilience patterns |
| **Opportunity Scoring** | Ranked growth opportunities with explainable scores |
| **AI Chat** | Ask questions about startup success factors and growth strategies |
| **News Collection** | Real-time from 24 sources (Google News, TechCrunch, Reddit, HN, SEC, etc.) |
| **BLS Growth Data** | Bureau of Labor Statistics survival & growth rates by sector |
| **Manufacturing Growth** | Reshoring data, CHIPS Act opportunities, geographic growth hotspots |
| **API** | 42 REST endpoints for programmatic access |

## Why Open Source

We believe startup intelligence shouldn't be locked behind $500+/month paywalls. The data is out there — SEC filings are public, BLS data is public, news is public. We're just connecting the dots and revealing the success patterns.

The entire platform is MIT licensed. Fork it, modify it, build on it.

## The Numbers

- 244 Python files
- 68 AI agents + 7 dev team agents
- 24 data collectors
- 87 database tables
- 1,033 tests (0 failing)
- 20 Docker services

## What We Need From You

This is a side project that grew into something bigger. We'd love to know:

1. **What data sources matter most to you?** We have 24 collectors — what are we missing?
2. **What would make this genuinely useful?** Features, visualizations, exports?
3. **Would you actually use this?** If not, what's the blocker?

We're actively developing and sprinting toward v1.0. Feedback shapes the roadmap.

**Repo**: https://github.com/gokul-koduri/start
