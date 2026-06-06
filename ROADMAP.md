# 🗺️ Opportunity Intelligence Platform — Master Roadmap

> Open-source, real-time, multi-agent alternative to Crunchbase / PitchBook / Tracxn
> Self-hosted. 62 agents. 26 collectors. 76 tables. 207 Python files.

---

## AI Product Development Team

This project follows a **structured AI Product Development workflow** with 7 specialized agents:

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  🤖 AI PRODUCT DEVELOPMENT TEAM (7 Agents)                          │
│                                                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │ Product Manager  │  │ Business Analyst │  │ Solution        │     │
│  │ Agent            │  │ Agent            │  │ Architect Agent │     │
│  │                 │  │                 │  │                 │     │
│  │ • Backlog mgmt  │  │ • Requirements  │  │ • Architecture  │     │
│  │ • Priorities    │  │ • Cost-benefit  │  │ • Tech debt     │     │
│  │ • Sprint status │  │ • Market fit    │  │ • ADRs          │     │
│  │ • Scope control │  │ • ROI analysis  │  │ • Refactoring   │     │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘     │
│                                                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │ UX Designer     │  │ Software        │  │ QA Engineer     │     │
│  │ Agent           │  │ Engineer Agent  │  │ Agent           │     │
│  │                 │  │                 │  │                 │     │
│  │ • Usability     │  │ • Code quality  │  │ • Test health   │     │
│  │ • Accessibility │  │ • Standards     │  │ • Coverage      │     │
│  │ • Interaction   │  │ • Anti-patterns │  │ • Regressions   │     │
│  │ • Design system │  │ • Test coverage │  │ • DoD compliance│     │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘     │
│                                                                      │
│                    ┌─────────────────┐                                │
│                    │ DevOps Engineer │                                │
│                    │ Agent           │                                │
│                    │                 │                                │
│                    │ • Docker health │                                │
│                    │ • Deploy ready  │                                │
│                    │ • CI/CD status  │                                │
│                    │ • Backups       │                                │
│                    └─────────────────┘                                │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### Working Rules

1. **All work broken into tasks ≤ 2 hours**
2. Every task has: ID, Description, Acceptance Criteria, Estimated Time, Dependencies, Status
3. No task may exceed 2 hours — split if needed

### 7-Phase Project Flow

| Phase | Description | Status | Deliverables |
|---|---|---|---|
| 1. Discovery | Analyze requirements, define MVP | ✅ COMPLETE | Product Vision, Scope, Risk Assessment |
| 2. User Stories | Write stories with AC, test cases, priority | ✅ COMPLETE | 107 tasks, user stories for each |
| 3. Architecture | System design, DB, API, security, deploy strategy | ✅ COMPLETE | DESIGN_BEFORE_CODING.md, SOLUTION_DESIGN.md |
| 4. Sprint Planning | Break stories into ≤2-hour tasks | ✅ COMPLETE | WORK_PLAN.md, 8 sprints planned |
| 5. Development | Implement, test, review, document | ⏳ IN PROGRESS | Sprint 1 tasks (44 hours) |
| 6. Quality Assurance | Unit, integration, E2E, performance tests | ⏳ PARTIAL | 699 tests (687 pass, 12 fail) |
| 7. Deployment | CI/CD, infrastructure, monitoring, rollback | ⏳ PLANNED | Docker Compose, Caddy, UptimeRobot |

---

## Current Progress

### Overall: 83% Built (5 of 6 phases complete)

| Metric | Current | Target V1.0 |
|---|---|---|
| Python files | 207 | 220+ |
| AI Agents | 62 (+ 7 dev team) | 70+ |
| Data Collectors | 26 | 26 |
| API Endpoints | 34 | 49 |
| Database Tables | 76 | 88 |
| Tests | 699 (687 pass) | 800+ (all pass) |
| Docker Services | 11 | 12 (+ Caddy) |
| Schema Version | 16 | 17 |
| Documentation Files | 44 markdown | 50+ |

### Phase Completion

| Phase | Status | Key Deliverables |
|---|---|---|
| Phase 1: Foundation | ✅ COMPLETE | Scoring engine, 4 collectors, API server, Streamlit |
| Phase 2: Intelligence | ✅ COMPLETE | NLP, entity resolution, semantic search, knowledge graph |
| Phase 3: Scale | ✅ COMPLETE | Stream processing, Redis, 6 Docker services |
| Phase 4: Deep Collection | ✅ COMPLETE | 12 new collectors, schema v14 |
| Phase 5: Advanced Intelligence | ✅ COMPLETE | 16 new agents, graph algorithms, topic modeling |
| Phase 6: Operations | ⏳ 40% | Auth, webhooks, monitoring (partially built) |

---

## Sprint Plan — 8 Sprints to V1.0

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  SPRINT    WEEK    THEME                  HOURS   STATUS            │
│  ──────    ────    ─────                  ─────   ──────            │
│  Sprint 1  1-2     Launch MVP              44     ⏳ Next           │
│  Sprint 2  3-4     Core Infrastructure     62     🔲               │
│  Sprint 3  5-6     Feedback + Analytics    42     🔲               │
│  Sprint 4  7-8     Auth + Security         48     🔲               │
│  Sprint 5  9-10    Watchlists + Alerts     36     🔲               │
│  Sprint 6  11-12   Export + Integrations   38     🔲               │
│  Sprint 7  13-14   Pro Tier + Billing      34     🔲               │
│  Sprint 8  15-16   Polish + V1 Release     22     🔲               │
│  ─────────────────────────────────────────────                     │
│  TOTAL             16 weeks              ~326 hrs                   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Architecture

```
Collectors (26) → Kafka Event Bus → Bytewax Stream → Enrich → Score → Alert
       │                                    │              │         │
       ▼                                    ▼              ▼         ▼
    MySQL (76 tables)    Redis (cache)   Qdrant + ES    opportunity_scores
                                         (search)       → dashboard + webhooks

AI Dev Team (7):
  product_manager → business_analyst → solution_architect
  ux_designer → software_engineer → qa_engineer → devops_engineer
```

---

## Git Branch Strategy

```
main        ← Stable, tagged releases (v0.9.0, v1.0.0)
develop     ← Integration branch (current work)
feature/*   ← Individual features (max 2 hours of work)
bugfix/*    ← Bug fixes
hotfix/*    ← Emergency production fixes
```

### Commit Format

```
type(scope): description

feat(auth): add login endpoint
fix(api): resolve token validation issue
docs(readme): update setup guide
test(agents): add tests for product_manager_agent
refactor(db): extract db helpers for boilerplate reduction
```

---

## Documentation Structure

```
Root:
  README.md             Project overview, quickstart
  ROADMAP.md            Master roadmap (this file)
  STATUS.md             Current status quick reference
  CONTRIBUTING.md       Community contribution guide

/docs
  /business             Plan, pitch deck, financials, GTM, competitive analysis
  /engineering          Problem def, solution design, coding standards, tests, risks
  /operations           Agent guide, API docs, deployment, security, monitoring
  /reports              Generated analysis reports
  /requirements         Product vision, scope, success metrics
  /adr                  Architecture Decision Records (ADR-001 to ADR-020)
  /api                  API specs, changelog
  /deployment           Checklists, runbooks, rollback
  /sprints              Sprint plans, burndown
  /user-stories         User stories with acceptance criteria
```

---

## Definition of Done

A feature is **complete** only when ALL of:

- [ ] Code implemented and working
- [ ] All tests passing (0 failures in suite)
- [ ] Documentation updated (docs/ or root .md)
- [ ] Code reviewed (self-review or PR review)
- [ ] Merged to develop branch
- [ ] Deployment verified on VPS

---

## Progress Tracking

Maintained in these locations:

| What | Where |
|---|---|
| Product Backlog | docs/engineering/work-plan.md (107 tasks) |
| Sprint Backlog | docs/sprints/sprint-plan.md |
| Burndown Status | Sprint completion % in work-plan.md |
| Risks | docs/engineering/risk-management.md (21 risks) |
| Blockers | GitHub Issues (bug_report.yml) |
| ADRs | docs/adr/ and docs/engineering/document-decisions.md |
| Daily Status | STATUS.md |

---

## AI Product Development Agent Files

| Agent | File | Responsibility |
|---|---|---|
| Product Manager | `agents/product_manager_agent.py` | Backlog, priorities, sprint status, scope |
| Business Analyst | `agents/business_analyst_agent.py` | Requirements, cost-benefit, market fit |
| Solution Architect | `agents/solution_architect_agent.py` | Architecture health, tech debt, ADRs |
| UX Designer | `agents/ux_designer_agent.py` | Usability, accessibility, design system |
| Software Engineer | `agents/software_engineer_agent.py` | Code quality, standards, anti-patterns |
| QA Engineer | `agents/qa_engineer_agent.py` | Test health, coverage, regressions |
| DevOps Engineer | `agents/devops_engineer_agent.py` | Docker, deploy readiness, CI/CD, backups |

Run all 7 agents:
```bash
python run_agent.py --agent product_manager
python run_agent.py --agent business_analyst
python run_agent.py --agent solution_architect
python run_agent.py --agent ux_designer
python run_agent.py --agent software_engineer
python run_agent.py --agent qa_engineer
python run_agent.py --agent devops_engineer
```

---

## Next Steps (Immediate)

1. **T-001**: `git add -A && git commit -m "feat(agents): add 7 AI product development team agents"`
2. **T-002**: Create LICENSE file (MIT)
3. **T-007**: Fix 12 failing tests in test_semantic_search.py
4. **T-009**: Create complete .env.example
5. **T-015**: Deploy to VPS with Docker Compose
6. **T-023**: Launch on Hacker News

---

*Last updated: June 5, 2026*
*Related: docs/engineering/work-plan.md, STATUS.md, docs/engineering/design-before-coding.md, docs/engineering/coding-standards.md*
