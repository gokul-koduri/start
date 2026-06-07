# Show HN: Open-source Crunchbase alternative that studies why startups fail

**Title**: `Show HN: We built an open-source Crunchbase alternative with 50+ AI agents that studies startup failures`

---

We were frustrated that startup intelligence tools (Crunchbase, PitchBook, Tracxn) cost $490-1,000/month but none of them systematically study why startups fail. So we built an open-source, self-hosted alternative that does.

## What it is

The **Opportunity Intelligence Platform** is a self-hosted market intelligence system that:

- Collects data from 24 sources (SEC filings, BLS survival rates, GitHub, Reddit, HN, Google News, patent databases, etc.)
- Runs 50+ specialized AI agents that analyze failure patterns, score opportunities, and identify manufacturing revival sectors
- Serves everything through a FastAPI REST API + Streamlit dashboard

## Why "failure intelligence"?

Everyone studies success. Nobody systematically studies failure.

We loaded 163 failed startups with detailed failure reason taxonomy, cross-referenced with BLS survival rate data across sectors, and built agents that identify patterns. The insight: understanding why startups fail in a sector is often more valuable than knowing which ones succeeded.

## Technical details

For the technically inclined:

- **68 AI agents** orchestrated via a multi-agent pipeline (collection → enrichment → scoring → alerting)
- **24 data collectors** pulling real-time data — Reddit, Hacker News, SEC EDGAR, arXiv, GitHub, Google News RSS, BLS, USPTO patents, StackOverflow, Product Hunt, and more
- **87 database tables** across MySQL 8.0 (schema v22)
- **968 tests**, 964 passing, 0 failing
- **14 Docker services** — MySQL, Redis, Kafka, Qdrant (vector search), Elasticsearch, ClickHouse (OLAP), TimescaleDB (time-series), Ollama (local LLM), Bytewax (stream processing), Streamlit, FastAPI, Caddy
- **Local LLM** via Ollama (llama3) — no data leaves your machine
- MIT licensed

## Architecture

```
Collectors (24) → Kafka → Bytewax Stream → Enrich → Score → Alert
       │                              │            │         │
       ▼                              ▼            ▼         ▼
    MySQL (87 tables)   Redis cache   Qdrant + ES   opportunity_scores
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

Or with Docker (14 services):

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
2. Is the "failure intelligence" angle useful, or should we focus more on opportunity discovery?
3. Any interest in contributing agents or collectors?

**Repo**: https://github.com/gokul-koduri/start
