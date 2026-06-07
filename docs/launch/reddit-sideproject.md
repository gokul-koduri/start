# r/SideProject Post

**Title**: `We built an open-source Crunchbase alternative that studies why startups fail`

---

## The Short Version

We got tired of paying $490+/month for Crunchbase when it only shows you successful startups. So we built a free, open-source alternative that does something nobody else does — it systematically studies why startups fail.

**Repo**: https://github.com/gokul-koduri/start

## How It Started

We were researching manufacturing revival opportunities in the US and kept hitting the same wall: every startup intelligence platform only shows you successes. Funding rounds, acquisitions, IPOs. But 90% of startups fail, and nobody was studying those failures systematically.

We started collecting data on failed startups — 163 of them with detailed failure reason taxonomy. Then we cross-referenced with BLS survival rates across sectors. Then we realized we were onto something bigger than a research project.

## What We Built

**Opportunity Intelligence Platform** — a self-hosted system that:

- **Collects data from 24 sources** in real-time: SEC filings, BLS survival data, Reddit, Hacker News, GitHub, Google News, patent databases, Product Hunt, StackOverflow, arXiv, and more
- **Runs 50+ AI agents** that analyze failure patterns, score opportunities, identify manufacturing revival sectors, track whale investors, and assess market viability
- **Serves everything through an API** (42 endpoints) with a built-in dashboard

## What the Dashboard Looks Like

When you fire it up, you get:

- **Search** across all collected startups and news
- **Failure pattern analysis** — see why startups fail in specific sectors
- **Opportunity scoring** — ranked opportunities with explainable scores
- **AI chat** — ask questions like "Why do most EV startups fail?" or "Which manufacturing sectors have revival opportunities?"
- **Performance dashboard** — latency, cache stats, error rates

## The Stack

For the curious:

| Component | Tech |
|---|---|
| Language | Python 3.12 |
| Database | MySQL 8.0 (87 tables) |
| AI/LLM | Ollama (llama3) — runs locally, no API calls |
| API | FastAPI |
| Dashboard | Streamlit |
| Search | Elasticsearch + Qdrant (vector) |
| Analytics | ClickHouse (OLAP) + TimescaleDB (time-series) |
| Streaming | Kafka + Bytewax |
| Cache | Redis |
| Deployment | Docker Compose (14 services) |
| License | MIT |

## Quick Start

```bash
git clone https://github.com/gokul-koduri/start.git
cd start
pip install -r requirements.txt
python api_server.py
```

That's it. Dashboard opens at http://localhost:8000.

Or with Docker:

```bash
docker compose up -d
```

## The Numbers

- 244 Python files
- 68 AI agents
- 24 data collectors
- 87 database tables
- 968 tests (964 pass, 0 fail)
- 14 Docker services

## What's Hard

Being honest — the hardest part was the failure taxonomy. There's no standard for categorizing why startups fail. We built one from scratch based on Failory data, BLS statistics, and our own analysis. It's imperfect, but it's the only open one we know of.

## What We'd Love Feedback On

1. What data sources would you want added?
2. Is the failure analysis angle useful for your work?
3. Any features you'd want to see in an open-source intelligence tool?
4. Would you use this? If not, what's missing?

**Repo**: https://github.com/gokul-koduri/start
