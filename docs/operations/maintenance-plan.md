# 🔧 Maintenance Plan — Bug Fixes, Updates, Security, User Support

> "Ship it. Then keep it alive."
> The unsexy work that determines whether your product survives its first 100 users.

---

## Maintenance Audit (June 5, 2026)

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  WHAT EXISTS TODAY:                                                  │
│  ✅ Health check endpoint (/api/health)                             │
│  ✅ Prometheus metrics (monitoring/metrics.py)                       │
│  ✅ System health checker (monitoring/health.py)                     │
│  ✅ Daily collection scripts (scripts/daily_*.sh)                    │
│  ✅ Weekly collection scripts (scripts/weekly_*.sh)                  │
│  ✅ Docker healthchecks on all 11 services                          │
│  ✅ 24 known issues tracked (KI-001 to KI-024)                      │
│  ✅ 21 risks documented (R1-R21)                                    │
│  ✅ GitHub Actions CI (daily pipeline)                               │
│  ✅ Logging in most Python modules                                   │
│                                                                      │
│  WHAT'S MISSING:                                                     │
│  ❌ No database backup script                                        │
│  ❌ No automated update/patch pipeline                               │
│  ❌ No security scanning (no Snyk, no Trivy, no bandit)             │
│  ❌ No dependency update process (no Dependabot/Renovate)            │
│  ❌ No rollback mechanism                                            │
│  ❌ No error tracking (no Sentry/GlitchTip)                         │
│  ❌ No user support system (no help desk, no FAQ)                    │
│  ❌ No on-call / incident response process                           │
│  ❌ No maintenance schedule                                          │
│  ❌ No runbooks for common fixes                                     │
│  ❌ No changelog management                                          │
│  ❌ No version pinning strategy                                      │
│  ❌ No CVE monitoring                                                │
│  ❌ No rate limiting or WAF                                          │
│  ❌ No SSL/TLS termination                                           │
│  ❌ No CONTRIBUTING.md (community bug reports)                       │
│                                                                      │
│  THIS DOCUMENT FIXES ALL 16 GAPS.                                   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Part 1: Bug Fixes — Find, Triage, Fix, Prevent

---

### 1.1 Bug Classification System

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  SEVERITY LEVELS:                                                    │
│                                                                      │
│  🔴 P0 — OUTAGE (fix in < 1 hour)                                   │
│  • API server is down (500 errors on all endpoints)                 │
│  • Database connection lost                                           │
│  • Docker containers crash-looping                                    │
│  • Data loss occurred                                                 │
│  • Security breach detected                                           │
│  TRIGGER: Wake up, fix now. Cancel plans.                            │
│                                                                      │
│  🟠 P1 — BROKEN (fix in < 24 hours)                                 │
│  • Key endpoint returns wrong data                                   │
│  • Scoring produces negative scores                                  │
│  • Search returns zero results for valid queries                     │
│  • Dashboard shows error on a page                                   │
│  • 12 failing tests (current state)                                  │
│  TRIGGER: Fix same day. Move to top of sprint.                       │
│                                                                      │
│  🟡 P2 — DEGRADED (fix in < 1 week)                                 │
│  • API response time > 5 seconds                                     │
│  • Some collectors fail intermittently                               │
│  • Dashboard loads slowly                                            │
│  • Edge case produces wrong score                                    │
│  TRIGGER: Add to current sprint. Fix this week.                      │
│                                                                      │
│  🟢 P3 — ANNOYING (fix in < 1 month)                                │
│  • UI typo or misalignment                                           │
│  • Minor data formatting issue                                       │
│  • Non-critical warning in logs                                      │
│  • Feature works but UX is confusing                                 │
│  TRIGGER: Add to backlog. Fix when convenient.                       │
│                                                                      │
│  🔵 P4 — COSMETIC (fix when convenient)                             │
│  • Spelling in documentation                                         │
│  • Color scheme issue                                                │
│  • Log message could be clearer                                      │
│  TRIGGER: Fix during cleanup sprints.                                │
│                                                                      │
│  KNOWN BUGS RIGHT NOW:                                               │
│  🔴 P0: None (system runs)                                           │
│  🟠 P1: 12 failing tests (KI-001), no backup (KI-002)              │
│  🟡 P2: No rate limiting (KI-006), 35 localhost refs (KI-007)      │
│  🟢 P3: No .env.example (KI-013), no CONTRIBUTING.md (KI-022)     │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 1.2 Bug Discovery Pipeline

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  HOW BUGS GET FOUND:                                                 │
│                                                                      │
│  SOURCE                  CHANNEL          RESPONSE TIME               │
│  ────────────────────────────────────────────────────────────────    │
│                                                                      │
│  Automated tests         CI pipeline       < 1 hour (on commit)      │
│  Error tracking          Sentry/GlitchTip  < 5 min (on error)       │
│  Health check failures   Cron job          < 15 min (on failure)     │
│  User bug report         GitHub Issues     < 24 hours                │
│  User chat/email         Support inbox     < 24 hours                │
│  Social media mention    Twitter/HN        < 48 hours                │
│  Code review             PR review         Before merge              │
│  Security scanner        Trivy/Snyk        Weekly                    │
│  Performance monitor     Grafana           Weekly                    │
│                                                                      │
│  BUG → TRIAGE → FIX → TEST → DEPLOY → VERIFY                       │
│                                                                      │
│  ┌─────────┐   ┌─────────┐   ┌──────┐   ┌──────┐   ┌──────┐       │
│  │ FOUND   │──►│ TRIAGE  │──►│ FIX  │──►│ TEST │──►│ SHIP │       │
│  │         │   │ (P0-P4) │   │      │   │      │   │      │       │
│  └─────────┘   └─────────┘   └──────┘   └──────┘   └──────┘       │
│       │              │                                           │
│       │              ▼                                           │
│       │         ┌──────────────────────┐                         │
│       │         │ If P0: wake up now   │                         │
│       │         │ If P1: fix today     │                         │
│       │         │ If P2: fix this week │                         │
│       │         │ If P3: add to sprint │                         │
│       │         │ If P4: add to backlog│                         │
│       │         └──────────────────────┘                         │
│       │                                                          │
│       ▼                                                          │
│  ┌──────────────────┐                                            │
│  │ LOG THE BUG:     │                                            │
│  │ GitHub Issue:    │  "bug: [description]"                     │
│  │ Label: bug       │                                            │
│  │ Priority: P0-P4  │                                            │
│  │ Milestone: Sprint │                                            │
│  │ Assignee: @you   │                                            │
│  └──────────────────┘                                            │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 1.3 Bug Fix Runbooks

#### RUNBOOK: API Server Down (P0)

```
Symptoms:  All API endpoints return 500, health check fails
Impact:    Users see nothing, product is broken

DIAGNOSIS (2 minutes):
─────────────────────────
# Step 1: Check if API process is running
curl -s http://localhost:8000/api/health
# Expected: {"status": "healthy"}
# If connection refused → API process crashed

# Step 2: Check Docker containers
docker compose ps
# Look for: startup-research-api → status should be "Up"

# Step 3: Check API logs
docker compose logs api --tail=50
# Look for: Traceback, ImportError, ConnectionError

# Step 4: Check MySQL
docker compose exec mysql mysqladmin ping -h localhost -u root -pstartup2024
# If "mysqld is alive" → MySQL is fine
# If error → MySQL is the problem

FIX (5 minutes):
─────────────────
# If MySQL is down:
docker compose restart mysql
sleep 10
docker compose restart api

# If API crashed but MySQL is up:
docker compose restart api

# If config error:
git stash                    # revert bad changes
docker compose restart api   # restart with last known good config

# If dependency error:
docker compose build api     # rebuild
docker compose up -d api     # restart

VERIFY:
───────
curl -s http://localhost:8000/api/health
# Must return: {"status": "healthy"}
```

#### RUNBOOK: Database Connection Lost (P0)

```
Symptoms:  API returns "Can't connect to MySQL server"
Impact:    All data operations fail

DIAGNOSIS (1 minute):
──────────────────────
docker compose exec mysql mysql -u root -pstartup2024 -e "SELECT 1"

FIX (3 minutes):
─────────────────
docker compose restart mysql
sleep 15  # Wait for MySQL to be ready

# Verify
docker compose exec mysql mysqladmin ping -h localhost -u root -pstartup2024

# Restart dependent services
docker compose restart api streamlit pipeline

DATA LOSS CHECK:
────────────────
docker compose exec mysql mysql -u root -pstartup2024 -e "
  SELECT 'failed_startups' as tbl, COUNT(*) as cnt FROM failed_startups
  UNION ALL SELECT 'raw_signals', COUNT(*) FROM raw_signals
  UNION ALL SELECT 'opportunity_scores', COUNT(*) FROM opportunity_scores
" startup_research
```

#### RUNBOOK: Failing Tests (P1)

```
Symptoms:  pytest shows failures
Current:   12 failing in test_semantic_search.py

DIAGNOSIS (2 minutes):
──────────────────────
python -m pytest tests/ -q --tb=short 2>&1 | tail -20

FIX (per test):
───────────────
# Run only the failing file with full output
python -m pytest tests/test_semantic_search.py -v --tb=long

# Common causes and fixes:
# 1. Import error    → missing dependency: pip install <package>
# 2. AttributeError  → API changed: update test to match new API
# 3. Data mismatch   → fixture changed: update expected values
# 4. Connection error → service not running: start Docker services

# After fix, verify all tests pass:
python -m pytest tests/ -q
# Must show: 0 failed
```

#### RUNBOOK: Collector Failure (P2)

```
Symptoms:  No new data appearing, collector logs errors

DIAGNOSIS (2 minutes):
──────────────────────
# Check recent signals
docker compose exec mysql mysql -u root -pstartup2024 -e "
  SELECT source, COUNT(*) as cnt, MAX(created_at) as last_signal
  FROM raw_signals
  GROUP BY source ORDER BY last_signal DESC
" startup_research

# Test individual collector
python run_collectors.py --collector <name> --limit 1 --verbose

FIX (10 minutes):
─────────────────
# Common causes:
# 1. Website changed HTML → update collector parser
# 2. Rate limited → add delay: time.sleep(2) between requests
# 3. API key expired → update .env file
# 4. Network issue → check internet connectivity
```

#### RUNBOOK: Ollama / Chat Not Working (P2)

```
Symptoms:  Chat endpoint returns errors or empty responses

DIAGNOSIS (2 minutes):
──────────────────────
# Check Ollama is running
curl -s http://localhost:11434/api/tags
# Should return list of models

# Check if model is available
curl -s http://localhost:11434/api/tags | python -m json.tool | grep llama

FIX (5 minutes):
─────────────────
# If Ollama not running:
docker compose restart ollama
sleep 10

# If model not downloaded:
docker compose exec ollama ollama pull llama3:8b

# If Ollama runs out of memory — use smaller model:
docker compose exec ollama ollama pull llama3.2:1b
# Then update config to use smaller model
```

### 1.4 Automated Bug Detection — `scripts/health_monitor.py`

```python
"""
Automated health monitor — detects bugs before users report them.

Runs every 5 minutes via cron:
  */5 * * * * python /path/to/scripts/health_monitor.py >> /path/to/data/logs/health.log 2>&1
"""

import requests
import subprocess
import json
import sys
import os
from datetime import datetime

ALERT_WEBHOOK = os.environ.get("ALERT_WEBHOOK", "")  # Slack/Discord webhook
HEALTH_URL = "http://localhost:8000/api/health"


def send_alert(message: str):
    """Send alert to Slack/Discord."""
    if not ALERT_WEBHOOK:
        print(f"[ALERT] {message}")
        return
    try:
        requests.post(ALERT_WEBHOOK, json={"text": message}, timeout=5)
    except Exception:
        print(f"[ALERT] (webhook failed) {message}")


def check_api_health() -> bool:
    """Check if API server responds."""
    try:
        r = requests.get(HEALTH_URL, timeout=10)
        if r.status_code == 200 and r.json().get("status") == "healthy":
            return True
        send_alert(f"🔴 API health check failed: status={r.status_code}")
        return False
    except Exception as e:
        send_alert(f"🔴 API server unreachable: {e}")
        return False


def check_tests() -> bool:
    """Check if test suite passes."""
    import re
    result = subprocess.run(
        ["python", "-m", "pytest", "tests/", "-q", "--tb=no"],
        capture_output=True, text=True, timeout=60
    )
    output = result.stdout.splitlines()[-1] if result.stdout else ""
    failed = re.search(r'(\d+) failed', output)
    if failed and int(failed.group(1)) > 0:
        send_alert(f"🟠 {failed.group(1)} tests failing — regression detected")
        return False
    return True


def check_docker() -> bool:
    """Check all Docker containers are running."""
    result = subprocess.run(
        ["docker", "compose", "ps", "--format", "json"],
        capture_output=True, text=True, timeout=15
    )
    issues = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        try:
            container = json.loads(line)
            if container.get("Health") == "unhealthy" or \
               container.get("Status", "").startswith("Exit"):
                issues.append(f"{container.get('Name')}: {container.get('Status')}")
        except json.JSONDecodeError:
            pass

    if issues:
        send_alert(f"🟠 Docker issues: {', '.join(issues)}")
        return False
    return True


def check_disk_space() -> bool:
    """Check disk space > 10% free."""
    stat = os.statvfs("/")
    free_pct = (stat.f_bavail / stat.f_blocks) * 100
    if free_pct < 10:
        send_alert(f"🔴 Disk space critical: {free_pct:.1f}% free")
        return False
    elif free_pct < 25:
        send_alert(f"🟡 Disk space warning: {free_pct:.1f}% free")
    return True


if __name__ == "__main__":
    results = {
        "api": check_api_health(),
        "docker": check_docker(),
        "disk": check_disk_space(),
        # Tests checked weekly, not every 5 min
    }

    all_ok = all(results.values())
    status = "✅ All healthy" if all_ok else "❌ Issues detected"
    print(f"[{datetime.now():%Y-%m-%d %H:%M}] {status} — {results}")

    if not all_ok:
        sys.exit(1)
```

### 1.5 Bug Fix Workflow

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  STEP 1: REPRODUCE (5 min)                                          │
│  ─────────────────────────                                          │
│  • Confirm the bug exists                                            │
│  • Write the minimal reproduction steps                              │
│  • Check if it's already a known issue                               │
│  • git checkout -b fix/bug-description                               │
│                    │                                                  │
│                    ▼                                                  │
│  STEP 2: DIAGNOSE (10 min)                                          │
│  ──────────────────────────                                          │
│  • Read the error message and stack trace                            │
│  • Check recent commits:                                             │
│    git log --oneline -10                                             │
│    git diff HEAD~3..HEAD -- <file>                                   │
│  • Check if it's a data issue or code issue                          │
│  • Identify the exact file and line                                  │
│                    │                                                  │
│                    ▼                                                  │
│  STEP 3: FIX (15-60 min)                                            │
│  ─────────────────────────                                           │
│  • Write the fix (smallest possible change)                          │
│  • Write a test that catches the bug:                                │
│    def test_bug_<description>():                                     │
│        # reproduce bug → assert fix works                            │
│  • Run tests: python -m pytest tests/ -q                             │
│  • Run linter: ruff check <file>                                     │
│                    │                                                  │
│                    ▼                                                  │
│  STEP 4: VERIFY (5 min)                                             │
│  ──────────────────────                                              │
│  • All tests pass (0 failures)                                       │
│  • API health check passes                                           │
│  • Manual smoke test (curl the endpoint)                             │
│  • No new warnings                                                   │
│                    │                                                  │
│                    ▼                                                  │
│  STEP 5: SHIP (5 min)                                               │
│  ─────────────────────                                               │
│  • git add -A && git commit                                          │
│    fix: resolve <bug description> (closes #42)                       │
│  • git push origin fix/bug-description                               │
│  • Close the GitHub Issue                                            │
│  • Update CHANGELOG.md                                               │
│  • Deploy: docker compose up -d --build                              │
│                    │                                                  │
│                    ▼                                                  │
│  STEP 6: POST-MORTEM (if P0/P1)                                     │
│  ─────────────────────────────                                       │
│  • What caused it?                                                   │
│  • Why didn't tests catch it?                                        │
│  • What test should we add to prevent recurrence?                    │
│  • Document in DOCUMENT_DECISIONS.md                                 │
│                                                                      │
│  TARGET TIME:                                                        │
│  P0 bug: 30 min total (reproduce → fix → ship)                      │
│  P1 bug: 2 hours total                                              │
│  P2 bug: 1 day total                                                │
│  P3 bug: 1 week total                                               │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Part 2: Updates — Keep Everything Fresh

---

### 2.1 What Needs Updating (and How Often)

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  COMPONENT               UPDATE FREQ   RISK      METHOD              │
│  ────────────────────────────────────────────────────────────────    │
│                                                                      │
│  Python packages          Weekly       LOW       pip + test          │
│  Docker base images       Monthly      MEDIUM    docker pull + test  │
│  Ollama models            Quarterly    LOW       ollama pull         │
│  spaCy models             Quarterly    LOW       spacy download      │
│  Sentence transformers    Quarterly    MEDIUM    pip install         │
│  MySQL version             Yearly      HIGH      Full backup first   │
│  FastAPI version           Monthly     LOW       pip + test          │
│  GitHub Actions runners    Auto        LOW       uses: actions/...@v4│
│  SSL certificates         Auto         LOW       Let's Encrypt       │
│  OS security patches      Monthly      HIGH      apt upgrade         │
│  API endpoint logic       As needed    LOW       git push + deploy   │
│  Scoring weights          Weekly       MEDIUM    config update       │
│  Collector parsers        As needed    HIGH      manual fix          │
│  Documentation            Weekly       LOW       git push            │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 Dependency Update Script — `scripts/update_dependencies.sh`

```bash
#!/bin/bash
# Weekly Dependency Update Script
# Safe update: update, test, commit only if tests pass.

set -e
echo "=== Dependency Update — $(date) ==="

cd "$(git rev-parse --show-toplevel)"

# STEP 1: Create update branch
git checkout main
git pull origin main
git checkout -b chore/weekly-deps-update

# STEP 2: Update Python dependencies
echo ">>> Updating Python packages..."

# Create backup of current requirements
cp requirements.txt requirements.txt.bak

# Update all packages within version constraints
pip install --upgrade -r requirements.txt 2>&1 | tail -5

# Freeze updated versions
pip freeze | grep -v "^pip==" > requirements-freeze.txt

# STEP 3: Run tests
echo ">>> Running tests..."
python -m pytest tests/ -q --tb=short
TEST_RESULT=$?

if [ $TEST_RESULT -ne 0 ]; then
    echo "❌ Tests failed after update. Rolling back."
    cp requirements.txt.bak requirements.txt
    pip install -r requirements.txt -q
    git checkout requirements.txt
    git branch -D chore/weekly-deps-update
    echo "Rollback complete. Manual investigation needed."
    exit 1
fi

# STEP 4: Tests pass — commit the update
echo "✅ Tests pass. Committing updates."
mv requirements-freeze.txt requirements.txt
rm requirements.txt.bak

git add requirements.txt
git commit -m "chore: weekly dependency update

Updated all Python packages within version constraints.
All tests passing."

git push origin chore/weekly-deps-update
echo "✅ Update pushed. Merge when ready."

# STEP 5: Update Docker base images
echo ">>> Updating Docker images..."
docker compose pull
docker compose build --pull

echo "=== Update complete ==="
```

### 2.3 Dependabot Configuration — `.github/dependabot.yml`

```yaml
version: 2

updates:
  # Python dependencies — weekly
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
    open-pull-requests-limit: 5
    labels:
      - "dependencies"
      - "automated"
    commit-message:
      prefix: "chore"
      include: "scope"

  # Docker base images — monthly
  - package-ecosystem: "docker"
    directory: "/"
    schedule:
      interval: "monthly"
    labels:
      - "dependencies"
      - "docker"

  # GitHub Actions — monthly
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "monthly"
    labels:
      - "dependencies"
      - "ci"
```

### 2.4 Version Management Strategy

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  SEMANTIC VERSIONING: MAJOR.MINOR.PATCH                             │
│                                                                      │
│  MAJOR (v1.0.0 → v2.0.0):                                          │
│  • Breaking API changes, schema migrations, removed features         │
│  Frequency: Yearly                                                   │
│                                                                      │
│  MINOR (v1.0.0 → v1.1.0):                                          │
│  • New features, new agents, new endpoints, UI improvements         │
│  Frequency: Monthly                                                  │
│                                                                      │
│  PATCH (v1.0.0 → v1.0.1):                                          │
│  • Bug fixes, security patches, dependency updates, doc fixes       │
│  Frequency: Weekly                                                   │
│                                                                      │
│  VERSION ROADMAP:                                                    │
│  v0.1.0-dev  ← CURRENT (pre-release)                                │
│  v0.1.0      ← MVP launch (Score + Chat + Failure Patterns)        │
│  v0.2.0      ← Core Features (auth, alerts, scheduler)             │
│  v0.3.0      ← Polish (watchlists, export, security hardening)     │
│  v1.0.0      ← Production-ready (first major release)              │
│                                                                      │
│  TAGGING:                                                            │
│  git tag -a v0.1.0 -m "MVP launch"                                 │
│  git push origin v0.1.0                                             │
│                                                                      │
│  HOTFIX PROCESS (10 minutes):                                        │
│  1.  git checkout main                                               │
│  2.  git checkout -b hotfix/critical-fix                            │
│  3.  Fix the bug                                                     │
│  4.  python -m pytest tests/ -q                                      │
│  5.  git commit -m "fix: critical issue description"                 │
│  6.  git checkout main && git merge hotfix/critical-fix              │
│  7.  git tag -a v0.1.1 -m "Hotfix: description"                     │
│  8.  git push origin main --tags                                     │
│  9.  docker compose up -d --build                                    │
│  10. Verify: curl http://localhost:8000/api/health                   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.5 Update Schedule

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  DAILY (automated, 5 min):                                          │
│  • Health monitor runs every 5 minutes                              │
│  • Daily data collection at 8 AM                                    │
│  • Database backup at 2 AM                                          │
│                                                                      │
│  WEEKLY (Monday, 30 min):                                           │
│  • Review Dependabot PRs — merge if tests pass                      │
│  • Run: scripts/update_dependencies.sh                              │
│  • Run full test suite: python -m pytest tests/ -v                  │
│  • Run security scan: scripts/security_scan.sh                      │
│  • Review error tracker (Sentry/GlitchTip)                          │
│  • Review GitHub Issues, triage new ones                            │
│  • Review feedback data, adjust priorities                          │
│  • Database maintenance: OPTIMIZE TABLE on large tables             │
│  • Check backup exists and is recent                                │
│  • Clean old logs (> 30 days)                                       │
│  • Update CHANGELOG.md                                              │
│  • Weekly progress report (#BuildInPublic)                          │
│                                                                      │
│  MONTHLY (1st Saturday, 2 hours):                                   │
│  • Update Docker base images                                        │
│  • Security scan with Trivy                                         │
│  • Update Ollama model                                              │
│  • Review scoring accuracy                                          │
│  • Update documentation                                             │
│  • Financial review (budget vs. actual)                             │
│  • Close stale GitHub Issues                                        │
│                                                                      │
│  QUARTERLY (1 day):                                                  │
│  • Architecture review                                              │
│  • Performance benchmarking                                         │
│  • Full security audit                                              │
│  • Database schema optimization                                     │
│  • Roadmap update based on feedback                                 │
│                                                                      │
│  YEARLY (1 week):                                                   │
│  • Major version upgrade (Python, MySQL, etc.)                      │
│  • Full penetration test                                            │
│  • Legal/compliance review (GDPR, ToS)                              │
│  • Business model review                                            │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Part 3: Security Patches — Protect the Platform

---

### 3.1 Security Threat Model

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  THREAT                  LIKELIHOOD   IMPACT     CURRENT STATUS      │
│  ────────────────────────────────────────────────────────────────    │
│                                                                      │
│  SQL Injection            MEDIUM      CRITICAL   ❌ No protection    │
│  XSS                      MEDIUM      HIGH       ❌ No CSP headers   │
│  API abuse                HIGH        MEDIUM     ❌ No rate limiting  │
│  Data breach              LOW         CRITICAL   ⚠️ No backup       │
│  Dependency CVE           MEDIUM      HIGH       ❌ No scanning       │
│  Docker escape            LOW         CRITICAL   ⚠️ No limits       │
│  Hardcoded secrets        MEDIUM      HIGH       ⚠️ Default password │
│  Scraping legal           LOW         HIGH       ❌ No robots.txt     │
│  GDPR violation           LOW         CRITICAL   ❌ No privacy policy │
│  DDoS                     LOW         HIGH       ❌ No WAF/proxy      │
│  LLM prompt injection     LOW         MEDIUM     ⚠️ Basic sanitize   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.2 Security Patching Priority

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  IMMEDIATE (before launch — Day 1):                                  │
│  ──────────────────────────────────────                              │
│  1. Change default MySQL password     → .env file                   │
│  2. Add rate limiting to API          → slowapi middleware           │
│  3. Add security headers              → X-Content-Type, CSP, etc.   │
│  4. Close MySQL port to localhost     → "127.0.0.1:3306:3306"       │
│  5. Add .env to .gitignore            → prevent secret leaks        │
│                                                                      │
│  WEEK 1:                                                             │
│  ────────                                                            │
│  6. Set up Dependabot                 → automated CVE PRs           │
│  7. Set up Trivy                      → Docker image scanning       │
│  8. Add bandit                        → Python security linting     │
│  9. Set up GlitchTip                  → error tracking (free)       │
│                                                                      │
│  MONTH 1:                                                            │
│  ────────                                                            │
│  10. Add HTTPS (Let's Encrypt + Caddy)                              │
│  11. Full CSP headers                                                │
│  12. Input validation on all endpoints                               │
│  13. SQL injection audit                                             │
│  14. robots.txt                                                      │
│                                                                      │
│  MONTH 2:                                                            │
│  ────────                                                            │
│  15. Auth system (JWT tokens)                                        │
│  16. API key management                                              │
│  17. Privacy policy                                                  │
│  18. GDPR compliance review                                          │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.3 Security Hardening Code — Add to `api_server.py`

```python
# === SECURITY MIDDLEWARE (add after app initialization) ===

# 1. Rate Limiting
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter


# 2. Security Headers
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "connect-src 'self' http://localhost:*; "
    )
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=()"
    )
    return response


# 3. Input Validation
import re

def sanitize_input(input_string: str, max_length: int = 500) -> str:
    """Sanitize user input — strip HTML, limit length, block SQL patterns."""
    if not input_string:
        return ""
    cleaned = input_string.strip()[:max_length]
    cleaned = re.sub(r'<[^>]*>', '', cleaned)  # Strip HTML tags
    sql_patterns = [
        r'(--|;|/\*|\*/)',
        r'(DROP|DELETE|INSERT|UPDATE|ALTER|CREATE|TRUNCATE)\s',
        r'(UNION\s+SELECT)',
        r'(OR\s+1\s*=\s*1)',
        r"('\s*OR\s*')",
    ]
    for pattern in sql_patterns:
        if re.search(pattern, cleaned, re.IGNORECASE):
            raise HTTPException(400, "Invalid input")
    return cleaned
```

### 3.4 Docker Security Hardening — Add to `docker-compose.yml`

```yaml
# Apply to EVERY service for defense in depth:

services:
  mysql:
    ports:
      - "127.0.0.1:3306:3306"    # LOCALHOST ONLY — never expose publicly
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '2'
    cap_drop:
      - ALL

  api:
    ports:
      - "8000:8000"              # Public API (the only public port)
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1'
    user: "1000:1000"            # Run as non-root
    read_only: true
    tmpfs:
      - /tmp
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true

  redis:
    ports:
      - "127.0.0.1:6379:6379"   # LOCALHOST ONLY — never expose Redis
    deploy:
      resources:
        limits:
          memory: 512M

  # Repeat cap_drop + resource limits for ALL other services
```

### 3.5 Security Scanning Script — `scripts/security_scan.sh`

```bash
#!/bin/bash
# Security Scanner — run weekly or before releases.

echo "=== Security Scan — $(date) ==="
cd "$(git rev-parse --show-toplevel)"

# 1. Python dependency CVEs
echo ">>> Checking Python packages for CVEs..."
pip install pip-audit -q 2>/dev/null
pip-audit --desc 2>&1 | tail -20
echo ""

# 2. Python code security issues
echo ">>> Scanning Python code..."
pip install bandit -q 2>/dev/null
bandit -r . -ll --exclude "./tests,./.git,./venv" 2>&1 | tail -20
echo ""

# 3. Docker image vulnerabilities
echo ">>> Scanning Docker images..."
if command -v trivy &> /dev/null; then
    trivy image --severity HIGH,CRITICAL mysql:8.0 2>&1 | tail -10
else
    echo "Trivy not installed. Install: brew install trivy"
fi
echo ""

# 4. Hardcoded secrets
echo ">>> Checking for hardcoded secrets..."
if command -v gitleaks &> /dev/null; then
    gitleaks detect --source . --verbose 2>&1 | tail -10
else
    grep -rn "password\s*=" . --include="*.py" --include="*.yml" \
        | grep -v ".env" | grep -v "test" || echo "No obvious hardcoded passwords"
fi
echo ""

# 5. .gitignore check
if grep -q ".env" .gitignore 2>/dev/null; then
    echo "✅ .env is in .gitignore"
else
    echo "🔴 CRITICAL: .env is NOT in .gitignore!"
fi

echo "=== Scan complete ==="
```

### 3.6 Database Backup Script — `scripts/backup_db.sh` (CRITICAL)

```bash
#!/bin/bash
# MySQL Backup Script — RUN DAILY
# Cron: 0 2 * * * /path/to/scripts/backup_db.sh >> /path/to/data/logs/backup.log 2>&1
#
# RISK MITIGATION: R1 (MySQL data loss — CRITICAL risk)

set -e

DB_HOST="${MYSQL_HOST:-127.0.0.1}"
DB_PORT="${MYSQL_PORT:-3306}"
DB_USER="${MYSQL_USER:-root}"
DB_PASS="${MYSQL_PASSWORD:-startup2024}"
DB_NAME="${MYSQL_DATABASE:-startup_research}"
BACKUP_DIR="$(git rev-parse --show-toplevel)/data/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_${DATE}.sql.gz"
RETENTION_DAYS=30
S3_BUCKET="${S3_BACKUP_BUCKET:-}"    # Optional: s3://my-backups/oip-db

mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting backup of ${DB_NAME}..."

mysqldump \
    -h "$DB_HOST" \
    -P "$DB_PORT" \
    -u "$DB_USER" \
    -p"$DB_PASS" \
    --single-transaction \
    --routines \
    --triggers \
    --add-drop-table \
    --quick \
    "$DB_NAME" | gzip > "$BACKUP_FILE"

if [ -f "$BACKUP_FILE" ]; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "[$(date)] ✅ Backup created: $BACKUP_FILE ($SIZE)"
else
    echo "[$(date)] ❌ Backup FAILED!"
    exit 1
fi

# Optional S3 upload
if [ -n "$S3_BUCKET" ]; then
    echo "[$(date)] Uploading to S3..."
    aws s3 cp "$BACKUP_FILE" "$S3_BUCKET/$(basename $BACKUP_FILE)" \
        --storage-class STANDARD_IA 2>&1 && echo "[$(date)] ✅ S3 upload done" \
        || echo "[$(date)] ⚠️ S3 upload failed (local backup OK)"
fi

# Clean old backups
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null
echo "[$(date)] Cleaned backups older than $RETENTION_DAYS days"
echo "[$(date)] Backup complete."
```

### 3.7 Database Restore Script — `scripts/restore_db.sh`

```bash
#!/bin/bash
# Restore database from backup.
# Usage: ./scripts/restore_db.sh <backup_file.sql.gz>

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    echo "Available backups:"
    ls -la data/backups/*.sql.gz 2>/dev/null || echo "  No backups found"
    exit 1
fi

BACKUP_FILE="$1"
DB_HOST="${MYSQL_HOST:-127.0.0.1}"
DB_PORT="${MYSQL_PORT:-3306}"
DB_USER="${MYSQL_USER:-root}"
DB_PASS="${MYSQL_PASSWORD:-startup2024}"
DB_NAME="${MYSQL_DATABASE:-startup_research}"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ File not found: $BACKUP_FILE"
    exit 1
fi

echo "⚠️  WARNING: This will REPLACE the current database!"
echo "   Database: $DB_NAME"
echo "   Backup:   $BACKUP_FILE"
read -p "Continue? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then echo "Aborted."; exit 0; fi

# Safety backup first
echo "Creating safety backup of current state..."
./scripts/backup_db.sh

# Restore
echo "Restoring from $BACKUP_FILE..."
gunzip -c "$BACKUP_FILE" | mysql \
    -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASS" "$DB_NAME"

echo "✅ Restore complete. Verifying..."
mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" -e "
    SELECT 'failed_startups' as tbl, COUNT(*) as cnt FROM failed_startups
    UNION ALL SELECT 'raw_signals', COUNT(*) FROM raw_signals
    UNION ALL SELECT 'opportunity_scores', COUNT(*) FROM opportunity_scores
"
echo "✅ Verified."
```

---

## Part 4: User Support — Keep Users Happy

---

### 4.1 Support Channels

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  CHANNEL              SETUP TIME   COST     RESPONSE SLA             │
│  ────────────────────────────────────────────────────────────────    │
│                                                                      │
│  GitHub Issues        0 min        $0       < 24h (P0/P1)           │
│  GitHub Discussions   5 min        $0       < 24h                    │
│  FAQ Page             1 hour       $0       Self-service             │
│  Email                5 min        $0       < 24h                    │
│  Discord              5 min        $0       < 4h (active hours)      │
│  In-app help widget   10 min       $0       Self-service             │
│  Documentation        Ongoing      $0       Self-service             │
│                                                                      │
│  DAY 1 SETUP:                                                        │
│  1. GitHub Issues (already exists ✅)                               │
│  2. GitHub Discussions (enable in repo settings)                     │
│  3. FAQ page (site/faq.html)                                         │
│  4. CONTRIBUTING.md (bug report template)                            │
│  5. In-app help widget (💬 button on dashboard)                     │
│                                                                      │
│  MONTH 2 ADD:                                                        │
│  6. Discord server                                                   │
│  7. Chatwoot (self-hosted live chat, free)                           │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 4.2 GitHub Issue Templates

**`.github/ISSUE_TEMPLATE/bug_report.yml`:**

```yaml
name: Bug Report
description: Report a bug or unexpected behavior
labels: ["bug", "triage"]
body:
  - type: textarea
    id: description
    attributes:
      label: What happened?
      placeholder: "I searched for 'Tesla' and got a 500 error"
    validations:
      required: true
  - type: textarea
    id: expected
    attributes:
      label: What did you expect?
      placeholder: "I expected to see Tesla's score and profile"
    validations:
      required: true
  - type: textarea
    id: steps
    attributes:
      label: Steps to reproduce
      placeholder: |
        1. Go to dashboard
        2. Search 'Tesla'
        3. Press Enter
        4. See error
    validations:
      required: true
  - type: dropdown
    id: severity
    attributes:
      label: Severity
      options:
        - "P0 — Everything is broken"
        - "P1 — Key feature broken"
        - "P2 — Feature degraded"
        - "P3 — Minor annoyance"
    validations:
      required: true
  - type: textarea
    id: logs
    attributes:
      label: Error logs (if any)
      render: shell
```

**`.github/ISSUE_TEMPLATE/feature_request.yml`:**

```yaml
name: Feature Request
description: Suggest a new feature or improvement
labels: ["enhancement", "triage"]
body:
  - type: textarea
    id: problem
    attributes:
      label: What problem does this solve?
      placeholder: "I want alerts when a startup score changes"
    validations:
      required: true
  - type: textarea
    id: solution
    attributes:
      label: Proposed solution
      placeholder: "Email/Slack alerts when score moves > 10 points"
    validations:
      required: true
  - type: dropdown
    id: importance
    attributes:
      label: How important is this?
      options:
        - "Critical — Can't use the platform without it"
        - "Important — Would significantly improve experience"
        - "Nice to have — Helpful but not essential"
```

### 4.3 FAQ Page — `site/faq.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FAQ — Opportunity Intelligence Platform</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, sans-serif; max-width: 800px;
               margin: 0 auto; padding: 40px 20px; color: #1a1a1a; }
        h1 { font-size: 28px; margin-bottom: 8px; }
        .sub { color: #666; margin-bottom: 32px; }
        .cat { margin-bottom: 32px; }
        .cat h2 { font-size: 20px; color: #3b82f6; margin-bottom: 12px;
                   border-bottom: 2px solid #e5e7eb; padding-bottom: 8px; }
        .faq { margin-bottom: 16px; }
        .faq summary { font-weight: 600; cursor: pointer; padding: 8px 0; }
        .faq summary::before { content: "▶ "; color: #3b82f6; }
        .faq[open] summary::before { content: "▼ "; }
        .faq p { padding: 8px 0 8px 24px; color: #4a4a4a; line-height: 1.6; }
        code { background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-size: 14px; }
        .box { background: #f1f5f9; padding: 20px; border-radius: 8px; margin-top: 32px; }
        .box a { color: #3b82f6; display: block; padding: 4px 0; }
    </style>
</head>
<body>
    <h1>❓ Frequently Asked Questions</h1>
    <p class="sub">Opportunity Intelligence Platform — Help & Support</p>

    <div class="cat">
        <h2>🚀 Getting Started</h2>
        <details class="faq"><summary>What is the Opportunity Intelligence Platform?</summary>
        <p>An open-source, self-hosted platform that scores startups (0-100),
        analyzes failure patterns, and provides AI-powered insights — an
        alternative to Crunchbase/PitchBook that you run on your own machine.</p></details>
        <details class="faq"><summary>How do I install it?</summary>
        <p><code>git clone https://github.com/gokul-koduri/start.git && cd start && docker compose up -d</code><br>
        Open <code>http://localhost:8501</code> for the dashboard.</p></details>
        <details class="faq"><summary>System requirements?</summary>
        <p>Minimum: 4GB RAM, 10GB disk, Python 3.12+, Docker.
        Recommended: 8GB RAM (for Ollama LLM), 20GB disk. GPU: Optional.</p></details>
        <details class="faq"><summary>Is it really free?</summary>
        <p>Yes. 100% open source (MIT license). No feature gates. No user limits.
        Optional Pro tier ($49/mo) for cloud sync and team features.</p></details>
    </div>

    <div class="cat">
        <h2>🎯 Scoring</h2>
        <details class="faq"><summary>How does scoring work?</summary>
        <p>Composite score (0-100) from 6 factors: market timing, team strength,
        financial health, technology moat, competitive position, failure pattern
        similarity. Time-decay weighting — recent signals matter more.</p></details>
        <details class="faq"><summary>How accurate are the scores?</summary>
        <p>Continuously improving. Target: ≥ 50% correlation with outcomes.
        Rate scores with 👍👎 to help improve the algorithm.</p></details>
        <details class="faq"><summary>Can I customize scoring weights?</summary>
        <p>Yes. Edit <code>config/settings.yaml</code>. API support for custom
        profiles planned for V1.</p></details>
    </div>

    <div class="cat">
        <h2>🐛 Troubleshooting</h2>
        <details class="faq"><summary>"Can't connect to MySQL"</summary>
        <p>MySQL might not be ready. Wait 30 seconds, or:
        <code>docker compose restart mysql</code> then wait 15 seconds.</p></details>
        <details class="faq"><summary>Chat/AI responses are empty or slow</summary>
        <p>Ollama needs to download the model (~4.7GB). Run:
        <code>docker compose exec ollama ollama pull llama3:8b</code></p></details>
        <details class="faq"><summary>Search returns no results</summary>
        <p>Load seed data first: <code>python seed_data.py</code> then
        <code>python run_agent.py --pipeline daily</code></p></details>
        <details class="faq"><summary>Dashboard shows errors</summary>
        <p>Check services: <code>docker compose ps</code> (all should show "Up").
        Restart: <code>docker compose restart</code>.
        Logs: <code>docker compose logs --tail=20</code>.</p></details>
    </div>

    <div class="cat">
        <h2>🔒 Security & Privacy</h2>
        <details class="faq"><summary>Is my data private?</summary>
        <p>Yes. Everything runs on YOUR machine. No data sent externally.
        All LLM inference is local (Ollama). No third-party tracking.</p></details>
        <details class="faq"><summary>How do I change the default password?</summary>
        <p>Create <code>.env</code>: <code>MYSQL_PASSWORD=your-strong-password</code>
        Then: <code>docker compose up -d</code></p></details>
    </div>

    <div class="box">
        <h3>💬 Still need help?</h3>
        <a href="https://github.com/gokul-koduri/start/issues">🐛 Report a bug</a>
        <a href="https://github.com/gokul-koduri/start/issues">💡 Request a feature</a>
        <a href="https://github.com/gokul-koduri/start/discussions">❓ Ask a question</a>
    </div>
</body>
</html>
```

### 4.4 CONTRIBUTING.md

```markdown
# Contributing to Opportunity Intelligence Platform

Thank you for considering contributing! 🎉

## Report a Bug
1. Search [existing issues](https://github.com/gokul-koduri/start/issues)
2. Click "New Issue" → "Bug Report"
3. Fill in: description, steps to reproduce, expected behavior

## Request a Feature
1. Click "New Issue" → "Feature Request"
2. Describe the problem it solves (not just the solution)

## Submit Code
1. Fork → `git checkout -b fix/your-fix-name`
2. Make your change (smallest possible)
3. Add a test: `def test_bug_<description>(): ...`
4. Run tests: `python -m pytest tests/ -q`
5. Commit: `git commit -m "fix: description"`
6. Push and create Pull Request

## Development Setup
```bash
git clone https://github.com/gokul-koduri/start.git && cd start
pip install -r requirements.txt
docker compose up -d
python -m pytest tests/ -v
```

## Code Style
- Python 3.12+, PEP 8, use `ruff check .`
- Docstrings for public functions
- [Conventional Commits](https://www.conventionalcommits.org/)

## Questions?
Open a [GitHub Discussion](https://github.com/gokul-koduri/start/discussions).
We respond within 24 hours.
```

### 4.5 Support SLA

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  PRIORITY    RESPONSE      RESOLUTION     EXAMPLE                    │
│  ────────────────────────────────────────────────────────────────    │
│  🔴 P0       < 1 hour      < 4 hours      API down, data loss      │
│  🟠 P1       < 4 hours     < 24 hours     Key feature broken       │
│  🟡 P2       < 24 hours    < 1 week       Performance issue        │
│  🟢 P3       < 48 hours    < 1 month      UX issue, typo           │
│                                                                      │
│  SUPPORT TIERS:                                                      │
│  Free users:     P2-P3 SLA (best effort for P0-P1)                 │
│  Pro ($49/mo):   P1-P3 SLA (guaranteed response)                   │
│  Enterprise:     P0-P3 SLA (dedicated support + on-call)            │
│                                                                      │
│  ESCALATION:                                                         │
│  GitHub Issue → triage → P0-P4 → fix → close                       │
│  If P0: drop everything, fix now, hotfix release                    │
│                                                                      │
│  METRICS TO TRACK:                                                   │
│  • Average response time                                             │
│  • Average resolution time                                           │
│  • Issues opened vs closed per week                                  │
│  • User satisfaction (👍👎 on responses)                             │
│  • Repeat issue rate                                                 │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 4.6 In-App Help Widget

```html
<!-- Add to site/index.html — floating 💬 support button -->

<div id="supportWidget" style="position:fixed;bottom:20px;right:20px;z-index:9999;">
  <button onclick="toggleSupport()" style="width:50px;height:50px;border-radius:50%;
    background:#3b82f6;color:white;border:none;font-size:24px;cursor:pointer;
    box-shadow:0 2px 10px rgba(0,0,0,0.2);">💬</button>
</div>

<div id="supportPanel" style="display:none;position:fixed;bottom:80px;right:20px;
  width:320px;background:white;border-radius:12px;
  box-shadow:0 4px 20px rgba(0,0,0,0.15);overflow:hidden;z-index:9999;">
  <div style="background:#3b82f6;color:white;padding:16px;">
    <h4 style="margin:0;">Need help?</h4>
  </div>
  <div style="padding:16px;">
    <a href="https://github.com/gokul-koduri/start/discussions"
       style="display:block;padding:8px;color:#3b82f6;text-decoration:none;
       border-bottom:1px solid #eee;">❓ Ask a question</a>
    <a href="https://github.com/gokul-koduri/start/issues/new?template=bug_report.yml"
       style="display:block;padding:8px;color:#3b82f6;text-decoration:none;
       border-bottom:1px solid #eee;">🐛 Report a bug</a>
    <a href="https://github.com/gokul-koduri/start/issues/new?template=feature_request.yml"
       style="display:block;padding:8px;color:#3b82f6;text-decoration:none;
       border-bottom:1px solid #eee;">💡 Request a feature</a>
    <a href="/faq.html"
       style="display:block;padding:8px;color:#3b82f6;text-decoration:none;
       border-bottom:1px solid #eee;">📖 FAQ & Troubleshooting</a>
    <a href="https://github.com/gokul-koduri/start/blob/main/README.md"
       style="display:block;padding:8px;color:#3b82f6;text-decoration:none;">📚 Documentation</a>
  </div>
</div>

<script>
function toggleSupport() {
  const p = document.getElementById('supportPanel');
  p.style.display = p.style.display === 'none' ? 'block' : 'none';
}
</script>
```

---

## Part 5: Maintenance Operations — Daily/Weekly/Monthly Checklists

---

### 5.1 Daily Checklist (5 minutes, every morning)

```
☐ Check health monitor:    tail -20 data/logs/health.log
☐ Check API health:        curl -s http://localhost:8000/api/health
☐ Check Docker:            docker compose ps (all "Up" + "healthy")
☐ Check error logs:        docker compose logs api --tail=20 --since=24h
☐ Check disk space:        df -h / (must be > 25% free)
☐ Check feedback:          curl -s http://localhost:8000/api/feedback/dashboard
☐ Check backup:            ls -lt data/backups/ | head -3
```

### 5.2 Weekly Checklist (30 minutes, Monday)

```
☐ Run tests:               python -m pytest tests/ -v (target: 0 failed)
☐ Review Dependabot PRs:   github.com/gokul-koduri/start/pulls
☐ Run security scan:       ./scripts/security_scan.sh
☐ Run dependency update:   ./scripts/update_dependencies.sh
☐ Review GitHub Issues:    Triage new, close resolved, respond to discussions
☐ Review feedback:         Adjust priorities based on user data
☐ Database maintenance:    OPTIMIZE TABLE on raw_signals, opportunity_scores
☐ Check backup worked:     ls -la data/backups/ | tail -5
☐ Clean old logs:          find data/logs/ -name "*.log" -mtime +30 -delete
☐ Update CHANGELOG.md
☐ Post weekly progress report
```

### 5.3 Monthly Checklist (2 hours, 1st Saturday)

```
☐ Update Docker images:    docker compose pull && docker compose build --pull
☐ Trivy security scan:     trivy image startup-research-api
☐ Update Ollama model:     docker compose exec ollama ollama pull llama3:8b
☐ Score accuracy review:   GET /api/feedback/score-stats (target: ≥ 4.0/5)
☐ Update documentation     if APIs changed
☐ Financial review:        budget vs. actual
☐ Close stale Issues:      Issues with no activity > 30 days
☐ Test backup restore:     ./scripts/restore_db.sh data/backups/latest.sql.gz
```

### 5.4 Quarterly Checklist (1 day)

```
☐ Architecture review
☐ Performance benchmarking (API response times, query performance)
☐ Full security audit (Trivy + bandit + manual review)
☐ Database schema optimization (indexes, query plans)
☐ Roadmap update based on 3 months of user feedback
☐ Evaluate new tools and dependencies
☐ Update CONTRIBUTING.md and developer docs
```

---

## Part 6: Incident Response — When Things Go Wrong

---

### 6.1 Incident Severity Matrix

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  SEV     EXAMPLES                         ACTIONS                    │
│  ────────────────────────────────────────────────────────────────    │
│                                                                      │
│  SEV-1   • API down > 15 min             • Wake up immediately      │
│  (P0)    • Data loss confirmed            • Fix in < 1 hour          │
│          • Security breach detected       • Post incident report     │
│          • All Docker containers down     • Hotfix release           │
│                                                                      │
│  SEV-2   • Key endpoint broken            • Fix same day             │
│  (P1)    • Scores returning wrong data    • Communicate on GitHub    │
│          • Dashboard error on main page   • Patch release            │
│          • 20+ test failures                                          │
│                                                                      │
│  SEV-3   • Search slow (> 5s)            • Fix this week            │
│  (P2)    • Collector intermittently fails • Add to current sprint    │
│          • Minor data inconsistency      • Include in next release   │
│                                                                      │
│  SEV-4   • UI alignment issue             • Fix this month           │
│  (P3)    • Log warning (non-critical)     • Add to backlog           │
│          • Typo in documentation          • Batch with other fixes    │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 6.2 Incident Response Flow

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  DETECT → ASSESS → COMMUNICATE → FIX → VERIFY → POST-MORTEM        │
│                                                                      │
│  1. DETECT (automated)                                               │
│     Health monitor alert / user report / error tracker               │
│                    │                                                  │
│                    ▼                                                  │
│  2. ASSESS (5 min)                                                  │
│     curl /api/health → docker compose ps → docker compose logs      │
│     Assign severity: SEV-1/2/3/4                                    │
│                    │                                                  │
│                    ▼                                                  │
│  3. COMMUNICATE (5 min)                                             │
│     If SEV-1: Post to GitHub Discussions "⚠️ Investigating issue"  │
│     If SEV-2: Add comment to relevant GitHub Issue                  │
│                    │                                                  │
│                    ▼                                                  │
│  4. FIX (15-60 min)                                                 │
│     Follow the appropriate runbook (Part 1.3)                        │
│     git checkout -b hotfix/description                               │
│                    │                                                  │
│                    ▼                                                  │
│  5. VERIFY (5 min)                                                  │
│     Tests pass + health check OK + manual smoke test                │
│     Deploy: docker compose up -d --build                            │
│                    │                                                  │
│                    ▼                                                  │
│  6. POST-MORTEM (if SEV-1/2, 30 min)                               │
│     Write up in GitHub Issue:                                        │
│     • Timeline: when detected, when fixed, when resolved            │
│     • Root cause: what caused it                                     │
│     • Prevention: what test/process to add                          │
│     • Update CHANGELOG.md                                            │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Part 7: Implementation Checklist — What to Build

---

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  DAY 1: EMERGENCY FIXES (3-4 hours)                                 │
│  ────────────────────────────────────                                │
│  ☐ Create scripts/backup_db.sh (Part 3.6)                           │
│  ☐ Create scripts/restore_db.sh (Part 3.7)                          │
│  ☐ Create scripts/security_scan.sh (Part 3.5)                       │
│  ☐ Create scripts/health_monitor.py (Part 1.4)                      │
│  ☐ Add security headers to api_server.py (Part 3.3)                 │
│  ☐ Close MySQL port: "127.0.0.1:3306:3306" in docker-compose.yml   │
│  ☐ Create .github/dependabot.yml (Part 2.3)                         │
│  ☐ Set up cron: backup daily at 2 AM, health check every 5 min     │
│                                                                      │
│  WEEK 1: SUPPORT INFRASTRUCTURE (4-5 hours)                         │
│  ───────────────────────────────────────────                         │
│  ☐ Create .github/ISSUE_TEMPLATE/bug_report.yml (Part 4.2)         │
│  ☐ Create .github/ISSUE_TEMPLATE/feature_request.yml (Part 4.2)    │
│  ☐ Create site/faq.html (Part 4.3)                                  │
│  ☐ Create CONTRIBUTING.md (Part 4.4)                                │
│  ☐ Add in-app help widget to dashboard (Part 4.6)                   │
│  ☐ Enable GitHub Discussions in repo settings                        │
│  ☐ Create scripts/update_dependencies.sh (Part 2.2)                 │
│                                                                      │
│  MONTH 1: SECURITY HARDENING (6-8 hours)                            │
│  ───────────────────────────────────────────                         │
│  ☐ Add rate limiting (slowapi) to api_server.py                     │
│  ☐ Add Docker resource limits to docker-compose.yml                 │
│  ☐ Add input validation (sanitize_input) to all endpoints           │
│  ☐ Set up error tracking (GlitchTip, self-hosted)                   │
│  ☐ Add HTTPS (Caddy reverse proxy + Let's Encrypt)                  │
│  ☐ SQL injection audit of all queries                                │
│  ☐ Add robots.txt                                                    │
│                                                                      │
│  TOTAL NEW FILES: 10                                                 │
│  TOTAL MODIFIED FILES: 4 (api_server.py, docker-compose.yml,        │
│                            site/index.html, .gitignore)              │
│  TOTAL TIME: 13-17 hours (spread over 4 weeks)                      │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Summary: Maintenance at a Glance

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  🐛 BUG FIXES                                                        │
│  5 severity levels (P0-P4), each with time target                   │
│  5 runbooks for common issues (API down, DB lost, tests, etc.)      │
│  Automated detection: health_monitor.py (every 5 min)               │
│  Bug workflow: reproduce → diagnose → fix → test → ship             │
│                                                                      │
│  🔄 UPDATES                                                          │
│  Weekly dependency updates (safe: update + test + commit)           │
│  Dependabot for automated PRs                                       │
│  Semantic versioning (v0.1.0 → v0.2.0 → v1.0.0)                   │
│  Hotfix process (10 min: fix → tag → deploy)                        │
│                                                                      │
│  🔒 SECURITY                                                         │
│  11 threats identified, 18-step patching plan                       │
│  Security headers, rate limiting, input validation                  │
│  Docker hardening (resource limits, non-root, cap_drop)             │
│  Security scanning (pip-audit + bandit + trivy + gitleaks)         │
│  Database backup + restore scripts (fixes R1 risk)                  │
│                                                                      │
│  💬 USER SUPPORT                                                     │
│  6 channels (GitHub Issues, Discussions, FAQ, email, Discord, chat) │
│  Structured bug report + feature request templates                  │
│  FAQ page with 12 questions (getting started, scoring, troubleshooting)│
│  CONTRIBUTING.md for community contributions                        │
│  Support SLA (P0 < 1hr, P1 < 4hr, P2 < 24hr, P3 < 48hr)          │
│  In-app help widget (💬 floating button)                            │
│                                                                      │
│  📋 SCHEDULE                                                         │
│  Daily (5 min): health + logs + feedback                             │
│  Weekly (30 min): tests + deps + security + issues                  │
│  Monthly (2 hrs): Docker + models + accuracy + docs                 │
│  Quarterly (1 day): architecture + security + roadmap               │
│                                                                      │
│  NEW SCRIPTS TO CREATE:                                              │
│  scripts/backup_db.sh                                                │
│  scripts/restore_db.sh                                               │
│  scripts/security_scan.sh                                            │
│  scripts/health_monitor.py                                           │
│  scripts/update_dependencies.sh                                      │
│                                                                      │
│  NEW FILES TO CREATE:                                                │
│  .github/dependabot.yml                                              │
│  .github/ISSUE_TEMPLATE/bug_report.yml                               │
│  .github/ISSUE_TEMPLATE/feature_request.yml                          │
│  site/faq.html                                                       │
│  CONTRIBUTING.md                                                      │
│                                                                      │
│  COST: $0/month (all tools are free/open-source)                    │
│  TIME: 5 min/day + 30 min/week + 2 hrs/month                       │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

*Last updated: June 5, 2026*
