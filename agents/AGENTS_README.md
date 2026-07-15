# Claude Code Agents

**NOTE**: These agent definition files are staging copies. Move them to `.claude/agents/` for use.

## Overview

These agents complement the **Python agent system** in the top-level `agents/` directory:

| Directory | Purpose | Technology |
|-----------|---------|------------|
| `agents/` | Application runtime agents | Python (`BaseAgent` classes) |
| `.claude/agents/` | Claude Code assistant agents | Markdown definitions |

## Purpose

Claude Code agents (in `.claude/agents/`) are **contextual assistants** that help you work with this codebase. They understand the project structure, conventions, and patterns.

## Available Agents

| Agent | File | Purpose |
|-------|------|---------|
| **Explore** | `explore.md` | Read-only code exploration and discovery |
| **Plan** | `planner.md` | Architecture and implementation planning |
| **Research** | `researcher.md` | Market and company research |
| **Analyst** | `analyst.md` | Startup analysis and risk assessment |
| **Developer** | `developer.md` | Code implementation and review |
| **Reporter** | `reporter.md` | Report generation and insights |

## Usage

Agents are invoked via the Agent tool with the appropriate subagent type:

```python
Agent(
    description="Analyze startup risk",
    prompt="Evaluate [company] for investment potential...",
    subagent_type="analyst"
)
```

## Relationship to Python Agents

### Python Agents (`agents/`)
- **Runtime**: Execute in the pipeline, API server, background workers
- **Purpose**: Data collection, analysis, ML predictions, report generation
- **Examples**: `RiskScorerAgent`, `DashboardAgent`, `MLTrainerAgent`
- **Triggered by**: Cron jobs, API calls, webhooks

### Claude Code Agents (`.claude/agents/`)
- **Runtime**: Assist during development sessions
- **Purpose**: Help you understand code, plan implementations, write better code
- **Examples**: Explore, Plan, Developer, Analyst
- **Triggered by**: Developer requests in Claude Code

## Moving to Production

To activate these agents, move the `.md` files:

```bash
mv agents/explore.md .claude/agents/
mv agents/planner.md .claude/agents/
mv agents/researcher.md .claude/agents/
mv agents/analyst.md .claude/agents/
mv agents/developer.md .claude/agents/
mv agents/reporter.md .claude/agents/
```