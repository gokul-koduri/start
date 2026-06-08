# r/SideProject Post

**Title**: `We built an open-source Crunchbase alternative that reveals why startups thrive`

---

## The Short Version

We got tired of paying $490+/month for Crunchbase when it only shows you data, not insights. So we built a free, open-source alternative that does something nobody else does — it systematically reveals **what makes startups thrive** and **how founders overcome challenges to achieve growth**.

**Repo**: https://github.com/gokul-koduri/start

## How It Started

We were researching manufacturing growth opportunities in the US and kept hitting the same wall: every startup intelligence platform only shows you surface-level data. Funding rounds, acquisitions, IPOs. But nobody was analyzing *why* some startups thrive while others in the same sector don't. Nobody was capturing the resilience patterns — how founders navigate setbacks and emerge stronger.

We started collecting data on hundreds of startups — both thriving ones and those that faced challenges — with detailed success factor analysis. Then we cross-referenced with BLS growth rates across sectors. Then we realized we were onto something bigger than a research project.

## What We Built

**Opportunity Intelligence Platform** — a self-hosted system that:

- **Collects data from 24 sources** in real-time: SEC filings, BLS growth data, Reddit, Hacker News, GitHub, Google News, patent databases, Product Hunt, StackOverflow, arXiv, and more
- **Runs 50+ AI agents** that analyze success patterns, score growth opportunities, identify manufacturing hotspots, track whale investors, and assess market viability
- **Serves everything through an API** (42 endpoints) with a built-in dashboard

## What the Dashboard Looks Like

When you fire it up, you get:

- **Search** across all collected startups and news
- **Success pattern analysis** — see what drives growth in specific sectors
- **Challenge navigation** — learn how startups overcome setbacks and thrive
- **Opportunity scoring** — ranked growth opportunities with explainable scores
- **AI chat** — ask questions like "What makes EV startups thrive?" or "How do successful founders overcome early challenges?"
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
- 1,014 tests (all passing)
- 14 Docker services

## What's Hard

Being honest — the hardest part was building the success factor taxonomy. There's no standard for categorizing what makes startups thrive. We built one from scratch based on BLS statistics, startup growth data, and our own analysis. It includes both success patterns AND how startups overcome challenges — because resilience is a key success factor. It's imperfect, but it's the only open one we know of.

## What We'd Love Feedback On

1. What data sources would you want added?
2. Is the success factor analysis + overcoming challenges angle useful for your work?
3. Any features you'd want to see in an open-source intelligence tool?
4. Would you use this? If not, what's missing?

**Repo**: https://github.com/gokul-koduri/start
