# Show HN Post — Copy-Paste Ready

## Title (paste into HN title field)

```
Show HN: Open-source Crunchbase alternative that studies why startups succeed or fail
```

## Body (paste into HN text field)

---

We were frustrated that startup intelligence tools (Crunchbase, PitchBook, Tracxn) cost $490-1,000/month but none of them systematically study **what makes startups thrive**. They show you data — funding rounds, headcounts, valuations — but never the *why* behind success. So we built an open-source, self-hosted alternative that does.

## What it is

The **Opportunity Intelligence Platform** is a self-hosted market intelligence system that:

- Collects data from 24 sources (SEC filings, BLS growth rates, GitHub, Reddit, HN, Google News, patent databases, etc.)
- Runs 50+ specialized AI agents that analyze success patterns, score growth opportunities, and reveal how startups overcome challenges
- Serves everything through a FastAPI REST API + Streamlit dashboard

## Why "success intelligence"?

Everyone tracks what happened. Nobody systematically studies *why* it happened.

We loaded data from hundreds of startups — both thriving ones and those that faced setbacks — with detailed analysis of growth factors, pivot strategies, and turnaround stories. Cross-referenced with BLS growth rate data across sectors. The insight: understanding **what drives startup success** and **how founders overcome challenges** is far more valuable than just tracking funding rounds.

We also study setbacks — not to dwell on failure, but to extract the **resilience patterns**: how startups that stumbled recovered, pivoted, and emerged stronger. That's the intelligence nobody else provides.

## Technical details

For the technically inclined:

- **68 AI agents** orchestrated via a multi-agent pipeline (collection → enrichment → scoring → alerting)
- **24 data collectors** pulling real-time data — Reddit, Hacker News, SEC EDGAR, arXiv, GitHub, Google News RSS, BLS, USPTO patents, StackOverflow, Product Hunt, and more
- **87 database tables** across MySQL 8.0 (schema v22)
- **1,033 tests**, all passing, 0 failing
- **20 Docker services** — MySQL, Redis, Kafka, Qdrant (vector search), Elasticsearch, ClickHouse (OLAP), TimescaleDB (time-series), Ollama (local LLM), Bytewax (stream processing), Streamlit, FastAPI, Caddy
- **Local LLM** via Ollama (llama3) — no data leaves your machine
- MIT licensed

## Architecture

```
Collectors (24) → Kafka → Bytewax Stream → Enrich → Score → Alert
       │                              │            │         │
       ▼                              ▼            ▼         ▼
    MySQL (87 tables)   Redis cache   Qdrant + ES   growth_scores
                                     (search)      → dashboard + webhooks
```

## Quick start

```bash
git clone https://github.com/gokul-koduri/start.git
cd start
pip install -r requirements.txt
python api_server.py
```

Opens:
- Dashboard: http://localhost:8000/
- API docs: http://localhost:8000/docs

Or with Docker (20 services):

```bash
docker compose up -d
```

## What's next

We're actively working on:
- Watchlists and alerting (Sprint 5)
- Export to CSV/PDF/Excel (Sprint 6)
- Pro tier with additional data sources (Sprint 7)

## Ask HN

We'd love feedback on:

1. What data sources would be most valuable to add next?
2. Is the "success intelligence + overcoming challenges" angle useful?
3. Any interest in contributing agents or collectors?

**Repo**: https://github.com/gokul-koduri/start
