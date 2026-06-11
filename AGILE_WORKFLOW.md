# 🏃 Agile Workflow Guide

> How the Opportunity Intelligence Platform team uses Scrum + Kanban to ship incrementally.

---

## Table of Contents

- [Philosophy](#philosophy)
- [Roles](#roles)
- [Artifacts](#artifacts)
- [Ceremonies](#ceremonies)
- [Sprint Lifecycle](#sprint-lifecycle)
- [Definition of Ready (DoR)](#definition-of-ready-dor)
- [Definition of Done (DoD)](#definition-of-done-dod)
- [Story Point Estimation](#story-point-estimation)
- [GitHub Project Board](#github-project-board)
- [Branching Strategy](#branching-strategy)
- [PR Process](#pr-process)
- [Velocity & Metrics](#velocity--metrics)
- [Automated Enforcement](#automated-enforcement)
- [Quick Reference](#quick-reference)

---

## Philosophy

We follow **ScrumBan** — Scrum ceremonies + Kanban flow:
- **2-week sprints** with fixed goals (Scrum)
- **Continuous flow** within sprints — pull, don't push (Kanban)
- **WIP limits** per column to prevent bottlenecks
- **No task exceeds 2 hours** — split if larger
- **Every PR is a potentially shippable increment**

---

## Roles

| Role | Who | Responsibility |
|---|---|---|
| **Product Owner** | Product Manager Agent + Human | Backlog priority, acceptance criteria, scope |
| **Scrum Master** | Sprint Validator + Human | Remove blockers, enforce DoD, run ceremonies |
| **Development Team** | Software Engineer Agent + Human | Implementation, testing, review |
| **QA** | QA Engineer Agent | Test health, coverage, regressions |
| **DevOps** | DevOps Engineer Agent | CI/CD, deployment, monitoring |

---

## Artifacts

### 1. Product Backlog (`docs/sprints/backlog.md`)
- Ordered list of all desired work
- Each item is a **User Story** or **Technical Task**
- Top items are refined and estimated

### 2. Sprint Backlog (`docs/sprints/sprint-tracker.yaml`)
- Tasks pulled from product backlog for current sprint
- Machine-readable YAML for automated validation
- Updated in real-time as work progresses

### 3. Increment (Working Software)
- Each merged PR = one increment
- Must pass all tests, linting, security scans
- Must meet Definition of Done

### 4. Sprint Board (GitHub Project)
- Kanban board with columns: Backlog → To Do → In Progress → In Review → Done
- Automated via GitHub Actions
- WIP limits enforced

---

## Ceremonies

### Sprint Planning (Day 1 of Sprint) — 1 hour
```
1. Review previous sprint velocity
2. Select stories from product backlog
3. Break stories into ≤2-hour tasks
4. Assign story points
5. Commit to sprint goal
6. Update sprint-tracker.yaml
```
**Script**: `make sprint-plan` or `python scripts/agile_cli.py planning`

### Daily Standup (Every Day) — 10 minutes
```
1. What did I complete yesterday?
2. What am I working on today?
3. Any blockers?
```
**Script**: `make standup` or `python scripts/agile_cli.py standup`
**Output**: Updates `docs/sprints/standups/YYYY-MM-DD.md`

### Sprint Review (Day 14 of Sprint) — 30 minutes
```
1. Demo completed features
2. Show metrics vs targets
3. Collect feedback
4. Update product backlog
```
**Script**: `make sprint-review` or `python scripts/agile_cli.py review`

### Sprint Retrospective (Day 14 of Sprint) — 20 minutes
```
1. What went well? (Keep)
2. What didn't go well? (Problem)
3. What can we improve? (Action)
4. Assign action items to next sprint
```
**Script**: `make sprint-retro` or `python scripts/agile_cli.py retrospective`

### Backlog Refinement (Mid-Sprint) — 30 minutes
```
1. Review upcoming stories
2. Add acceptance criteria
3. Estimate story points
4. Split large stories
5. Remove stale items
```
**Script**: `make backlog-refine` or `python scripts/agile_cli.py refine`

---

## Sprint Lifecycle

```
Week 1                          Week 2
┌───────────────────────┐      ┌───────────────────────┐
│ Day 1: Sprint Planning│      │ Day 8: Mid-sprint     │
│                       │      │   check-in            │
│ Day 2-4: Development  │      │                       │
│   Daily standups      │      │ Day 9-12: Development │
│   PRs → Review → Done │      │   Daily standups      │
│                       │      │   PRs → Review → Done │
│ Day 5: Backlog        │      │                       │
│   Refinement          │      │ Day 13: Sprint Review │
│                       │      │ Day 14: Retro +       │
│                       │      │   Next Sprint Planning│
└───────────────────────┘      └───────────────────────┘
```

### Sprint Gate Rules
1. **No sprint may start until the previous sprint is 100% complete**
2. Gate check runs automatically via `sprint_validator.py`
3. All 6 categories must pass: Tasks, Objectives, Deliverables, AC, Metrics, DoD
4. Blockers >48 hours must be escalated

---

## Definition of Ready (DoR)

A story/task is **ready** for sprint when:
- [ ] Clear description with user story format ("As a ___, I want ___, so that ___")
- [ ] Acceptance criteria defined (testable)
- [ ] Story points estimated
- [ ] Dependencies identified and resolved
- [ ] No open questions / ambiguity
- [ ] Mockup/design reference (if UI)
- [ ] Estimated effort ≤ 2 hours (if task)

---

## Definition of Done (DoD)

A feature is **complete** only when ALL of:
- [ ] Code implemented and working
- [ ] All tests passing (0 failures in suite)
- [ ] Test coverage ≥ 80% for new code
- [ ] Linting passes (`ruff check .`)
- [ ] Security scan clean (Bandit + pip-audit)
- [ ] Documentation updated (docs/ or root .md)
- [ ] Code reviewed (at least 1 approval on PR)
- [ ] PR merged to develop branch
- [ ] CI/CD pipeline green
- [ ] Feature flag added (if gradual rollout)

---

## Story Point Estimation

We use **Fibonacci** scale (1, 2, 3, 5, 8, 13):

| Points | Meaning | Time Equivalent |
|---|---|---|
| 1 | Trivial, <30 min | Config change, typo fix |
| 2 | Simple, 30 min - 1 hr | Add a test, update a doc |
| 3 | Standard, 1-2 hr | New endpoint, collector |
| 5 | Complex, 2-4 hr | New agent with tests |
| 8 | Very Complex, 4-8 hr | Multi-component feature |
| 13 | Epic (must split) | Major cross-cutting feature |

**Rule**: If a task is estimated > 3 points, split it.

---

## GitHub Project Board

### Columns & WIP Limits

```
┌──────────┬─────────┬──────────────┬──────────┬──────┐
│ Backlog  │ To Do   │ In Progress  │ In Review│ Done │
│ (unlim)  │ (≤10)   │ (≤4)         │ (≤3)     │(unlim│
└──────────┴─────────┴──────────────┴──────────┴──────┘
```

### Automation Rules
- **New issue** → Backlog
- **Issue assigned** → To Do
- **PR opened** (linked to issue) → In Review
- **PR merged** → Done (closes issue)
- **Stale >7 days** → Label `stale`
- **Stale >14 days** → Auto-close

### Labels
| Label | Color | Purpose |
|---|---|---|
| `sprint/1` through `sprint/8` | Blue | Sprint assignment |
| `priority/P0` | Red | Critical, ship-blocking |
| `priority/P1` | Orange | Important, sprint goal |
| `priority/P2` | Yellow | Nice to have |
| `type/story` | Green | User story |
| `type/task` | Light green | Technical task |
| `type/spike` | Purple | Research/exploration |
| `type/bug` | Red | Bug fix |
| `type/chore` | Gray | Maintenance |
| `status/blocked` | Red | Blocked by dependency |
| `status/in-progress` | Yellow | Currently worked on |
| `epic/launch` | Dark blue | Launch epic |
| `epic/infra` | Dark blue | Infrastructure epic |

---

## Branching Strategy

```
main          ← Stable, tagged releases (v0.9.0, v1.0.0)
              ← Protected: requires PR + 1 approval + green CI
develop       ← Integration branch (current sprint work)
              ← Protected: requires green CI
feature/*     ← Individual features (max 2 hours of work)
bugfix/*      ← Bug fixes
hotfix/*      ← Emergency production fixes
spike/*       ← Research spikes (may be discarded)
release/*     ← Release preparation
```

### Branch Naming
```
feature/T-001-add-scheduler
bugfix/T-007-fix-semantic-search
spike/research-dagster-alternatives
hotfix/fix-auth-bypass
```

---

## PR Process

### Opening a PR
1. Create branch from `develop`
2. Implement changes (≤2 hours of work)
3. Write/update tests
4. Run `make test` + `make lint`
5. Open PR with template filled out
6. Link to issue (e.g., `Closes #42`)
7. CI runs automatically

### PR Template Fields
- **What**: Summary of changes
- **Why**: Business justification
- **How**: Technical approach
- **Testing**: How to verify
- **Checklist**: DoD items

### Review Criteria
- [ ] Code follows project standards
- [ ] Tests cover happy + sad paths
- [ ] No security issues
- [ ] Documentation updated
- [ ] No unnecessary complexity
- [ ] PR is small enough to review (<400 lines)

### Merge Rules
- At least 1 approval required
- All CI checks green
- No merge conflicts
- Branch is up to date with develop

---

## Velocity & Metrics

### Tracked Metrics
| Metric | Source | Target |
|---|---|---|
| Sprint Velocity | Story points completed/sprint | Predictable |
| Throughput | Tasks completed/sprint | Improving |
| Cycle Time | Time from In Progress → Done | ≤2 days |
| PR Review Time | Time from PR open → merge | ≤4 hours |
| Test Pass Rate | pytest results | 100% |
| Code Coverage | coverage.py | ≥80% |
| Defect Escape Rate | Bugs found post-merge | ≤5% |

### Velocity Tracking
Stored in `docs/sprints/velocity.md`:
```
Sprint 1: 24 tasks / 44 story points → 100% completion
Sprint 2: -- tasks / -- story points → IN PROGRESS
...
```

---

## Automated Enforcement

### CI/CD Pipeline (`.github/workflows/`)

| Workflow | Trigger | Purpose |
|---|---|---|
| `ci.yml` | PR to develop/main | Test, lint, security scan |
| `sprint-board.yml` | Issues/PRs events | Auto-manage board |
| `daily-standup.yml` | Daily 9 AM | Create standup template |
| `sprint-review.yml` | Manual | Generate sprint report |
| `validate-sprint.yml` | PR to main | Gate check enforcement |
| `daily-pipeline.yml` | Daily 8 AM UTC | Data pipeline |
| `deploy.yml` | Push to main | Deploy to GitHub Pages |
| `security-scan.yml` | Weekly + push | Security audit |

### Pre-commit Hooks (optional)
```bash
# Install
pre-commit install

# Hooks run:
# - ruff format
# - ruff check
# - pytest (fast tests only)
# - bandit (security)
```

---

## Quick Reference

```bash
# Sprint Management
make sprint-status          # Current sprint status
make sprint-plan            # Start sprint planning
make standup                # Daily standup template
make sprint-review          # Sprint review report
make sprint-retro           # Retrospective template
make backlog-refine         # Backlog refinement
make sprint-gate            # Gate check (pass/fail)

# Agile CLI
python scripts/agile_cli.py planning       # Sprint planning
python scripts/agile_cli.py standup         # Daily standup
python scripts/agile_cli.py review          # Sprint review
python scripts/agile_cli.py retrospective   # Retro
python scripts/agile_cli.py backlog         # Show backlog
python scripts/agile_cli.py metrics         # Velocity & metrics
python scripts/agile_cli.py create-task     # Create a task
python scripts/agile_cli.py move-task       # Move task to column

# Validation
python scripts/sprint_validator.py          # Current sprint status
python scripts/sprint_validator.py --all    # All sprints
python scripts/sprint_validator.py --gate   # Gate check

# Standard Development
make test                   # Run all tests
make lint                   # Lint code
make pr                     # Create PR (interactive)
```

---

*Related: [ROADMAP.md](ROADMAP.md), [STATUS.md](STATUS.md), [CONTRIBUTING.md](CONTRIBUTING.md)*
*Last updated: June 2026*
