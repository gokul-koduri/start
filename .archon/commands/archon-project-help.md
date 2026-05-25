# /archon-project-help

You have access to the Startup Research Report project. Here's what you can do:

## Project Overview
This project maintains a research report on failed startups and manufacturing revival trends. Data is collected from multiple sources into SQLite, then generated as a markdown report.

## Available Workflows

| Workflow | When to Use |
|---|---|
| `collect-data` | Seed database and run all 5 data collectors (BLS, Google News, TechCrunch, Failory, Reshoring PDF) |
| `generate-report` | Regenerate the markdown report from the database |
| `full-pipeline` | Run the entire pipeline: collect → verify → generate → review |
| `add-failed-startup` | Research, classify, and add a new failed startup to the database |

## Project Structure
- `data/startup_research.db` — SQLite database (11 tables)
- `config/settings.yaml` — Collector configuration, RSS feeds, search queries
- `collectors/` — 5 data collectors (BLS, Google News, TechCrunch, Failory, Reshoring PDF)
- `report/generator.py` — Report generator (SQLite → Markdown)
- `seed_data.py` — Seeds database with existing report data
- `run_collectors.py` — CLI entry point for collectors
- `run_report.py` — CLI entry point for report generation
- `Failed_Startups_Manufacturing_Revival_Report.md` — The generated report

## Database Tables
1. `failed_startups` — 40+ startups with failure reasons, funding, sectors
2. `failure_reasons_taxonomy` — CB Insights top 9 failure reasons
3. `failure_idea_patterns` — 6 failed idea categories
4. `manufacturing_failure_categories` — 5 root cause categories
5. `bls_survival_rates` — BLS establishment survival data by NAICS
6. `news_articles` — RSS-collected news articles
7. `reshoring_data` — Industry-specific reshoring statistics
8. `reshoring_summary_stats` — Aggregate reshoring statistics
9. `revival_industries` — 6 industries returning to the US
10. `geographic_hotspots` — 6 geographic revival regions
11. `collection_runs` — Audit trail for data collection

## Quick Commands
```bash
# Collect data from all sources
python3 seed_data.py && python3 run_collectors.py --all

# Run a single collector
python3 run_collectors.py --collector google_news_rss

# Generate report
python3 run_report.py --output Failed_Startups_Manufacturing_Revival_Report.md

# Dry-run collectors (no DB writes)
python3 run_collectors.py --all --dry-run
```
