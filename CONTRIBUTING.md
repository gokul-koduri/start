# Contributing to Opportunity Intelligence Platform

Thank you for considering contributing! 🎉

## Agile Workflow

This project follows a **ScrumBan** agile workflow. See [AGILE_WORKFLOW.md](AGILE_WORKFLOW.md) for full details.

### Quick Summary
- **2-week sprints** with 8 planned sprints (16 weeks total)
- **Sprint board**: GitHub Project with Kanban columns
- **Ceremonies**: Planning, Standup (daily), Review, Retro (bi-weekly)
- **Definition of Done**: All tests pass, docs updated, PR approved, CI green

---

## Report a Bug
1. Search [existing issues](https://github.com/gokul-koduri/start/issues) first
2. Click **New Issue** → **Sprint Bug**
3. Fill in: severity, steps to reproduce, expected vs actual behavior
4. Add appropriate labels: `type/bug`, `priority/P0/P1/P2`

## Request a Feature
1. Click **New Issue** → **User Story**
2. Follow "As a ___, I want ___, so that ___" format
3. Define acceptance criteria (testable)
4. Add labels: `type/story`, appropriate sprint label

## Create a Task
1. Click **New Issue** → **Sprint Task**
2. Fill in sprint, priority, component, description, acceptance criteria
3. Keep tasks ≤ 2 hours — split if larger
4. Link dependencies to other issues

## Development Workflow

### 1. Pick a Task
```bash
# View current sprint status
make sprint-status

# Or use the agile CLI
python scripts/agile_cli.py metrics
```

### 2. Create a Branch
```bash
git checkout develop
git pull origin develop
git checkout -b feature/T-001-add-scheduler
# or: bugfix/T-007-fix-semantic-search
# or: spike/research-dagster-alternatives
```

### 3. Implement
```bash
# Make changes (keep PRs < 400 lines)
# Write tests for all new code
```

### 4. Validate Locally
```bash
make test           # All tests must pass
make lint           # Code must be clean
```

### 5. Open a PR
```bash
git push origin feature/T-001-add-scheduler
# Open PR on GitHub with the template filled out
# Title: feat(scope): description (Conventional Commits)
# Link: "Closes #42"
```

### 6. Review & Merge
- At least 1 approval required
- All CI checks must be green
- PR title must follow Conventional Commits format
- Squash merge into `develop`

---

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): description

feat(auth): add login endpoint
fix(api): resolve token validation issue
docs(readme): update setup guide
test(agents): add tests for product_manager_agent
refactor(db): extract db helpers for boilerplate reduction
chore(sprint): plan sprint 2
ci: add PR validation workflow
perf(scoring): optimize score calculation
```

### Types
| Type | Use When |
|---|---|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `test` | Adding or updating tests |
| `refactor` | Code restructuring (no behavior change) |
| `chore` | Maintenance, configs, dependencies |
| `ci` | CI/CD changes |
| `perf` | Performance improvement |
| `style` | Formatting, whitespace (no logic change) |

---

## Code Style
- Python 3.12+
- Follow PEP 8 (use `ruff check .` to lint)
- Write docstrings for all public functions
- Max line length: 120 characters
- Type hints encouraged

---

## Code Review Guidelines

### For Authors
- Keep PRs small (<400 lines changed)
- Write a clear description with context
- Link to the issue
- Ensure CI is green before requesting review
- Respond to all comments

### For Reviewers
- Review within 4 hours of request
- Be constructive and specific
- Check: correctness, tests, security, docs
- Approve only when all concerns addressed

---

## Branching Strategy

```
main          ← Stable releases (protected, requires PR + approval + CI)
develop       ← Integration branch (protected, requires CI)
feature/*     ← Features (max 2 hours work)
bugfix/*      ← Bug fixes
hotfix/*      ← Emergency production fixes
spike/*       ← Research (may be discarded)
```

---

## Sprint Management CLI

```bash
# Ceremonies
make sprint-plan            # Sprint planning
make standup                # Daily standup
make sprint-review          # Sprint review
make sprint-retro           # Retrospective

# Status
make sprint-status          # Current sprint status
make sprint-gate            # Gate check (pass/fail)

# Full CLI
python scripts/agile_cli.py planning
python scripts/agile_cli.py standup
python scripts/agile_cli.py review --sprint 2
python scripts/agile_cli.py retrospective
python scripts/agile_cli.py metrics
python scripts/agile_cli.py create-task
python scripts/agile_cli.py move-task T-001 done
python scripts/agile_cli.py burndown
python scripts/agile_cli.py labels
```

---

## Questions?
Open a [GitHub Discussion](https://github.com/gokul-koduri/start/discussions). We respond within 24 hours.

---

*See [AGILE_WORKFLOW.md](AGILE_WORKFLOW.md) for the complete agile guide.*
