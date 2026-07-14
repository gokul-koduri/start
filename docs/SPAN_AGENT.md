# Unified Span Agent - Quick Reference

> **Tasks 2, 3, 4** combined into a single unified interface

---

## Usage

### Task 2: Pipeline Control

```bash
# Run pipelines
python run_agent.py --span run                          # Daily pipeline
python run_agent.py --span run --pipeline-arg weekly    # Weekly pipeline
python run_agent.py --span run --pipeline-arg full       # Full pipeline

# Check status
python run_agent.py --span status                       # Pipeline health JSON
```

### Task 3: Report Generation

```bash
# Generate reports
python run_agent.py --span report --type opportunity_report --topic "Ohio EV Battery"
python run_agent.py --span report --type market_viability_report
python run_agent.py --span report --type startup_success_report

# List available templates
python run_agent.py --list-templates
```

### Task 4: AI Research

```bash
# Ask questions
python run_agent.py --span ask --query "What sectors have manufacturing revival potential?"

# Compare sectors
python run_agent.py --span compare --sectors "EV Battery" "Solar" "Semiconductors"

# Find opportunities
python run_agent.py --span opportunities --min-score 70
```

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                 run_agent.py                      │
│              Unified CLI (--span)                 │
├─────────────────────────────────────────────────┤
│                 SpanAgent                         │
│  ├── Task 2: run_pipeline(), get_pipeline_status()│
│  ├── Task 3: generate_research_report()           │
│  └── Task 4: research(), compare_sectors()       │
├─────────────────────────────────────────────────┤
│  Reuses: Orchestrator, AIAnalystAgent, Reports    │
└─────────────────────────────────────────────────┘
```

---

## Templates

| Type | Description |
|------|-------------|
| `opportunity_report` | Manufacturing revival opportunities |
| `market_viability_report` | Global market analysis |
| `startup_success_report` | Success pattern analysis |

---

## Exit Codes

- `0` = Success
- `1` = Failed/partial (check logs for details)

---

*Generated: 2026-07-13*