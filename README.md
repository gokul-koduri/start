# 🏭 Startup Research Report

> AI-powered market intelligence platform that studies **failed startups** and identifies **manufacturing revival opportunities**. Automated data collection, multi-agent analysis, and live dashboard reporting.

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?logo=mysql&logoColor=white)
![Ollama](https://img.shields.io/badge/LLM-Ollama%20%7C%20Llama3-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 📑 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Configuration](#configuration)
- [Usage](#usage)
  - [Data Collection](#data-collection)
  - [Report Generation](#report-generation)
  - [Agent Pipeline](#agent-pipeline)
  - [AI Analyst Chat](#ai-analyst-chat)
  - [Dashboard](#dashboard)
- [Data Sources](#data-sources)
- [Agent Catalog](#agent-catalog)
- [Scheduling](#scheduling)
- [Live Reports](#live-reports)
- [Contributing](#contributing)

---

## Overview

This platform automates the entire lifecycle of startup research:

1. **Collect** — Scrape and ingest data from government databases, news feeds, and startup failure databases
2. **Analyze** — Run specialized AI agents for pattern detection, survival analysis, and opportunity discovery
3. **Report** — Generate comprehensive Markdown reports and an interactive HTML dashboard
4. **Publish** — Auto-deploy to GitHub Pages via CI/CD

The core research focus areas are:
- **Why startups fail** — common failure patterns across industries and geographies
- **Manufacturing revival** — opportunities to restart failed manufacturing ventures
- **Global market viability** — sector-by-sector analysis across 10+ international markets
- **Investment intelligence** — whale investor tracking, reshoring trends, and funding patterns

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      Orchestrator Agent                        │
│                (coordinates pipeline stages)                   │
├──────────┬──────────┬──────────┬──────────┬──────────────────┤
│Collection│ Analysis │ Reports  │Dashboard │  Git Publisher   │
│  Agent   │ Agents   │+ Alerts  │  Agent   │    Agent         │
├──────────┼──────────┼──────────┼──────────┼──────────────────┤
│          │          │ Revenue  │ Pipeline │                   │
│  Data    │  MySQL   │+ Health  │ Health   │  Site / Pages     │
│Collectors│ Database │ Monitor  │ Monitor  │ (Live Dashboard) │
├──────────┴──────────┴──────────┴──────────┴──────────────────┤
│                    Ollama (Local LLM)                         │
│               llama3 — analysis & chat                        │
└──────────────────────────────────────────────────────────────┘
```

---

## Features

- **🤖 24+ Specialized AI Agents** — failure patterns, survival analysis, revival opportunities, geographic strategy, whale investors, knowledge graph, and more
- **📰 Multi-Source Data Collection** — BLS, Google News, TechCrunch, Failory, Reshoring PDFs
- **📊 Interactive Dashboard** — dark mode, mobile responsive, collapsible sections, search
- **💬 AI Analyst Chat** — ask natural language questions about the data
- **🌍 Global Market Viability** — 420+ sector evaluations across 10 international markets
- **🔗 Knowledge Graph** — entity relationships between startups, founders, investors, and failure patterns
- **📈 LLM Infrastructure** — pricing tracking, benchmarking, portfolio allocation, and cost optimization
- **🔔 Alert System** — email and webhook notifications for price changes, data freshness, and pipeline failures
- **📄 Automated Reports** — weekly digest and monthly deep dive reports with optional email delivery
- **💳 Revenue Monitoring** — Stripe payment tracking with auto license key generation (Pro-only)
- **🩺 Pipeline Health** — anomaly detection for agent duration, failure rates, and data drops
- **🔄 Automated Scheduling** — daily and weekly cron pipelines
- **🚀 CI/CD** — auto-deploy dashboard to GitHub Pages

---

## Project Structure

```
Startup_Research_Report/
├── agents/                          # AI agent modules
│   ├── orchestrator.py              # Pipeline coordinator
│   ├── base.py                      # Abstract base agent
│   ├── collection.py                # Data collection agent
│   ├── report.py                    # Report generation agent
│   ├── dashboard.py                 # HTML dashboard agent
│   ├── git_publisher.py             # GitHub Pages publisher
│   ├── ai_analyst_agent.py          # Natural language Q&A
│   ├── failure_pattern_agent.py     # Failure pattern detection
│   ├── survival_analysis_agent.py   # Statistical survival rates
│   ├── revival_opportunity_agent.py # Revival opportunity finder
│   ├── geographic_strategy_agent.py # Location-based insights
│   ├── news_intelligence_agent.py   # News monitoring & analysis
│   ├── whale_investor_agent.py      # Large investor tracking
│   ├── opportunity_pipeline_agent.py# Opportunity scoring
│   ├── correlation_agent.py         # Market correlation analysis
│   ├── global_market_viability_agent.py  # Global market analysis
│   ├── knowledge_graph_agent.py     # Entity relationship mapping
│   ├── internet_research.py         # Web research agent
│   ├── llm_pricing_agent.py         # LLM cost tracking
│   ├── llm_benchmark_agent.py       # LLM performance comparison
│   ├── llm_portfolio_agent.py       # LLM allocation strategy
│   ├── llm_cost_optimizer_agent.py  # Cost optimization
│   ├── license_agent.py             # License key management
│   ├── ollama_usage_tracker.py      # Ollama token usage tracking
│   ├── alert_dispatcher_agent.py    # Email + webhook alert dispatch
│   ├── report_generator_agent.py    # Scheduled report generation
│   ├── stripe_webhook.py            # Stripe payment polling + auto licenses
│   └── span_agent.py                # Pipeline health monitor
│
├── collectors/                      # Data collection modules
│   ├── base.py                      # Base collector class
│   ├── bls_survival_rates.py        # Bureau of Labor Statistics
│   ├── google_news_rss.py           # Google News RSS feed
│   ├── techcrunch_rss.py            # TechCrunch RSS feed
│   ├── failory_scraper.py           # Failory startup cemetery
│   └── reshoring_pdf.py             # Reshoring Initiative PDFs
│
├── config/                          # Configuration
│   ├── __init__.py                  # Config loader
│   ├── settings.yaml                # Main settings file
│   └── logging.yaml                 # Logging configuration
│
├── db/                              # Database layer
│   ├── connection.py                # MySQL connection pool
│   ├── schema.py                    # Table definitions & migrations
│   └── dedup.py                     # Record deduplication
│
├── report/                          # Report generation
│   └── generator.py                 # Markdown report builder
│
├── utils/                           # Shared utilities
│   ├── http_client.py               # HTTP request helper
│   ├── rate_limiter.py              # API rate limiting
│   ├── date_parsing.py              # Date normalization
│   └── text_normalization.py        # Text cleaning utilities
│
├── site/                            # Published dashboard
│   ├── index.html                   # Interactive HTML dashboard
│   └── data.json                    # Dashboard data payload
│
├── scripts/                         # Operational scripts
│   ├── daily_agent.sh               # Daily pipeline cron script
│   ├── daily_collect.sh             # Daily collection cron script
│   └── setup_github.sh              # GitHub repo setup (one-time)
│
├── data/                            # Runtime data (git-ignored)
│   ├── logs/                        # Application logs
│   ├── pdfs/                        # Downloaded PDF files
│   ├── cache/                       # Collection cache
│   └── reports/                     # Generated reports (markdown + html)
│
├── .github/workflows/
│   └── deploy.yml                   # GitHub Pages auto-deploy
│
├── run_agent.py                     # 🚀 Main entry point — agent pipeline
├── run_collectors.py                # Run data collectors directly
├── run_report.py                    # Generate report directly
├── seed_data.py                     # Seed DB with initial data (one-time)
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment variable template
└── .gitignore
```

---

## Getting Started

### Prerequisites

| Requirement       | Version  | Notes                                    |
|-------------------|----------|------------------------------------------|
| Python            | 3.12+    | Required for `str \| None` syntax        |
| MySQL             | 8.0+     | Database backend                         |
| Ollama            | Latest   | Local LLM for AI agents (`llama3`)       |
| Git               | 2.0+     | Version control & GitHub Pages deploys   |

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/gokul-koduri/start.git
cd start

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Copy and configure environment variables
cp .env.example .env
# Edit .env with your MySQL credentials and API keys

# 5. Set up MySQL database
# Create the database:
mysql -u root -p -e "CREATE DATABASE startup_research CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 6. Initialize the database schema
python seed_data.py

# 7. Install and start Ollama (for AI agents)
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull llama3
ollama serve
```

### Configuration

All configuration lives in **`config/settings.yaml`** and **`.env`**.

#### Environment Variables (`.env`)

| Variable            | Required | Description                              |
|---------------------|----------|------------------------------------------|
| `MYSQL_HOST`        | Yes      | MySQL host (default: `localhost`)        |
| `MYSQL_PORT`        | Yes      | MySQL port (default: `3306`)             |
| `MYSQL_USER`        | Yes      | MySQL username                           |
| `MYSQL_PASSWORD`    | Yes      | MySQL password                           |
| `MYSQL_DATABASE`    | Yes      | Database name (default: `startup_research`) |
| `BLS_API_KEY`       | No       | BLS API key (500 queries/day vs 25)      |
| `GITHUB_REPO`       | No       | For git publisher agent                  |
| `SMTP_HOST`         | No       | SMTP server for alerts/reports (e.g. smtp.gmail.com) |
| `SMTP_USER`         | No       | SMTP username                            |
| `SMTP_PASSWORD`     | No       | SMTP password                            |
| `SMTP_FROM`         | No       | Sender email address                     |
| `SLACK_WEBHOOK_URL` | No       | Slack incoming webhook URL               |
| `DISCORD_WEBHOOK_URL` | No     | Discord webhook URL                      |
| `STRIPE_SECRET_KEY` | No       | Stripe API secret key for payments       |
| `LOG_LEVEL`         | No       | DEBUG, INFO, WARNING, ERROR (default: INFO) |

#### Key Settings (`config/settings.yaml`)

- **`agents`** — Enable/disable individual agents and configure pipeline stages
- **`rss`** — RSS feed queries and sources
- **`scraping`** — Failory scraping categories, page limits, and rate limits
- **`bls_bed`** — BLS Bureau Employment Dynamics configuration
- **`report`** — Report output path and formatting options
- **`classification`** — Keywords for manufacturing and failure classification

---

## Usage

### Data Collection

```bash
# Run all collectors
python run_collectors.py --all

# Run a specific collector
python run_collectors.py --collector google_news_rss
python run_collectors.py --collector bls_survival_rates
python run_collectors.py --collector failory_scraper

# Dry run (log actions without writing to DB)
python run_collectors.py --all --dry-run

# Force collection (ignore incremental state)
python run_collectors.py --all --force
```

Available collectors: `bls_survival_rates`, `google_news_rss`, `techcrunch_rss`, `failory_scraper`, `reshoring_pdf`

### Report Generation

```bash
# Generate full report
python run_report.py

# Custom output path
python run_report.py --output my_report.md

# Generate a specific section only
python run_report.py --section part1
```

### Agent Pipeline

```bash
# Daily pipeline (fast collectors + report + publish)
python run_agent.py --pipeline daily

# Weekly pipeline (all collectors + deep research + publish)
python run_agent.py --pipeline weekly

# Run all analysis agents
python run_agent.py --pipeline analysis

# Full pipeline (collection + analysis + dashboard + publish)
python run_agent.py --pipeline full

# Individual stages
python run_agent.py --pipeline collect-only
python run_agent.py --pipeline report-only
python run_agent.py --pipeline publish-only

# Options
python run_agent.py --pipeline daily --dry-run    # Log without changes
python run_agent.py --pipeline daily --force       # Force report generation
```

### AI Analyst Chat

```bash
# Ask a question about the data
python run_agent.py --chat "What are the top failure reasons for EV startups?"
python run_agent.py --chat "Which manufacturing sectors have the best revival opportunities?"
python run_agent.py --chat "Compare failure rates between US and European startups"
```

### Dashboard

The interactive HTML dashboard is generated by the dashboard agent and deployed to `site/`. It includes:

- 📊 Key metrics and summary cards
- 📈 Survival rate charts
- 🗺️ Geographic distribution
- 🔍 Search and filter capabilities
- 🌙 Dark mode toggle
- 📱 Mobile responsive layout
- 📂 Collapsible sections for each analysis category
- 💰 Revenue monitoring (Pro-only) — MRR trends, tier distribution, payment history
- 🩺 Pipeline health — agent health scores, anomaly detection, duration trends
- 💎 Pro tier gating — advanced sections (portfolio, benchmarks, optimizer, revenue) locked behind license

---

## Data Sources

| Source                    | Type       | Data                                              |
|---------------------------|------------|---------------------------------------------------|
| **BLS (Bureau of Labor Statistics)** | API + Downloads | Business survival rates, establishment births/deaths by NAICS code |
| **Google News RSS**       | RSS Feed   | Startup failure, bankruptcy, and shutdown news     |
| **TechCrunch RSS**        | RSS Feed   | Startup and tech industry news                     |
| **Failory**               | Web Scrape | Failed startup profiles, reasons, and metadata     |
| **Reshoring Initiative**  | PDF        | Manufacturing reshoring statistics and case studies |

---

## Agent Catalog

| Agent                        | Purpose                                                    |
|------------------------------|------------------------------------------------------------|
| **Orchestrator**             | Coordinates pipeline stages and agent execution order       |
| **Collection**               | Runs data collectors and ingests into MySQL                |
| **Report**                   | Generates Markdown reports from database data              |
| **Dashboard**                | Builds interactive HTML dashboard with charts               |
| **Git Publisher**            | Commits and deploys to GitHub Pages                         |
| **AI Analyst**               | Natural language Q&A over the research data                 |
| **Failure Pattern**          | Detects common failure patterns across startups             |
| **Survival Analysis**        | Statistical analysis of startup survival rates              |
| **Revival Opportunity**      | Identifies opportunities to revive failed startups          |
| **Geographic Strategy**      | Location-based market analysis and recommendations          |
| **News Intelligence**        | Monitors and categorizes startup news                       |
| **Whale Investor**           | Tracks mega-investments and greenfield manufacturing deals  |
| **Opportunity Pipeline**     | Scores and ranks revival opportunities                      |
| **Correlation**              | Market correlation analysis across sectors                  |
| **Global Market Viability**  | 420+ sector evaluations across 10 international markets     |
| **Knowledge Graph**          | Maps entity relationships (startups, founders, investors)   |
| **Internet Research**        | Discovers new data sources and research material            |
| **LLM Pricing**              | Tracks LLM API pricing across providers                     |
| **LLM Benchmark**            | Compares LLM performance on analysis tasks                  |
| **LLM Portfolio**            | Optimal LLM allocation strategy                             |
| **LLM Cost Optimizer**       | Minimizes LLM infrastructure costs                          |
| **License Manager**          | Manages access keys and tiers                               |
| **Alert Dispatcher**         | Dispatches alerts via email, Slack, Discord, and webhooks    |
| **Report Generator**         | Generates weekly/monthly reports with optional email delivery |
| **Stripe Payments**          | Polls Stripe API, auto-generates license keys on payment    |
| **Span Monitor**             | Pipeline health monitoring with anomaly detection            |

---

## Scheduling

### Cron (Local)

```bash
# Edit crontab
crontab -e

# Daily pipeline at 8 AM
0 8 * * * /path/to/Startup_Research_Report/scripts/daily_agent.sh >> /path/to/Startup_Research_Report/data/logs/cron.log 2>&1

# Weekly deep analysis (Sundays at 6 AM)
0 6 * * 0 /path/to/Startup_Research_Report/scripts/daily_agent.sh --pipeline weekly >> /path/to/Startup_Research_Report/data/logs/cron.log 2>&1
```

### GitHub Actions

The project includes a GitHub Actions workflow (`.github/workflows/deploy.yml`) that auto-deploys the `site/` directory to GitHub Pages on every push to `main`.

---

## Live Reports

Generated reports are committed to the repository and include:

| Report                                            | Description                                      | Size   |
|---------------------------------------------------|--------------------------------------------------|--------|
| `Failed_Startups_Manufacturing_Revival_Report.md` | Comprehensive failure analysis & revival playbook | ~55 KB |
| `Global_Market_Viability.md`                      | 420 sector evaluations across 10 markets         | ~60 KB |
| `Market_Correlation_Analysis.md`                  | Cross-sector market correlation study             | ~7 KB  |

---

## Tech Stack

| Component      | Technology                                     |
|----------------|------------------------------------------------|
| Language       | Python 3.12                                    |
| Database       | MySQL 8.0 (PyMySQL)                            |
| AI/LLM         | Ollama — llama3 (local inference)              |
| Web Scraping   | BeautifulSoup4, lxml, feedparser               |
| PDF Parsing    | PyMuPDF                                        |
| Dashboard      | Vanilla HTML/CSS/JS (single-file)              |
| CI/CD          | GitHub Actions → GitHub Pages                  |
| Scheduling     | cron / shell scripts                           |

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -m 'Add my feature'`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License.

---

<p align="center">
  Built with 🤖 by <a href="https://github.com/gokul-koduri">Gokul Koduri</a>
</p>
