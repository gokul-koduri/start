# 📂 Documentation Index

> All project documentation is organized in this directory structure.

## Directory Structure

```
docs/
├── README.md                 ← You are here
├── requirements/             ← Business requirements, product vision, scope
├── architecture/             ← System design, database, API, security
├── api/                      ← API specifications, changelog
├── testing/                  ← Test strategy, results, coverage
├── deployment/               ← Deploy checklists, runbooks, rollback
├── adr/                      ← Architecture Decision Records
├── sprints/                  ← Sprint plans, burndown, retrospectives
└── user-stories/             ← User stories with acceptance criteria
```

## Quick Navigation

| What You Need | Where to Find It |
|---|---|
| Product vision & scope | `requirements/` |
| System architecture | `architecture/` |
| API endpoint specs | `api/` |
| Test strategy | `testing/` |
| How to deploy | `deployment/` |
| Why we chose X | `adr/` |
| Sprint planning | `sprints/` |
| User stories | `user-stories/` |

## Relationship to Root-Level Docs

Root-level `.md` files are **comprehensive reference documents** (each 15-100 KB).
Files in `docs/` are **working documents** — living docs that change every sprint.

| Root Document | docs/ Equivalent |
|---|---|
| PLAN_AND_MODEL.md | requirements/product-vision.md |
| DESIGN_BEFORE_CODING.md | architecture/system-design.md |
| API_DOCUMENTATION.md | api/specification.md |
| TESTING_STRATEGY.md | testing/strategy.md |
| DEPLOYMENT_GUIDE.md | deployment/runbook.md |
| DOCUMENT_DECISIONS.md | adr/ADR-001 through ADR-020 |
| WORK_PLAN.md | sprints/sprint-plan.md |
| USE_CASES.md | user-stories/stories.md |

## Documentation Rules

1. **Every feature gets a user story** in `user-stories/`
2. **Every architectural decision gets an ADR** in `adr/`
3. **Every sprint gets a plan** in `sprints/`
4. **Every API change goes in** `api/changelog.md`
5. **Every deploy uses the checklist** in `deployment/checklist.md`
