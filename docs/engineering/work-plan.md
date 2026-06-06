# 📋 Work Plan — User Stories, Estimates, Priorities, Incremental Delivery

> "Break big things into small things.
>  Small things get done. Big things don't."

---

## The Method

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  FORMAT: User Story + Task + Estimate + Priority + Deliverable      │
│                                                                      │
│  USER STORY:  As a [persona], I want [goal], so that [benefit].     │
│  TASK:        The specific technical work to do.                     │
│  ESTIMATE:    S = 1-2 hours, M = 3-4 hours, L = 1 day, XL = 2+ days│
│  PRIORITY:    P0 = ship now, P1 = this sprint, P2 = next sprint,   │
│               P3 = backlog                                          │
│  DELIVERABLE: What's done when the task is complete.                │
│                                                                      │
│  TOTAL TASKS: 107                                                    │
│  SPRINTS:      8 sprints (16 weeks)                                  │
│  SPRINT LENGTH: 2 weeks                                              │
│                                                                      │
│  EFFORT DISTRIBUTION:                                                │
│  S (1-2 hrs):  ████████████████████████████  48 tasks               │
│  M (3-4 hrs):  ████████████████████          30 tasks               │
│  L (1 day):    ██████████████                20 tasks               │
│  XL (2+ days): ████████                      9 tasks                │
│                                                                      │
│  PRIORITY DISTRIBUTION:                                              │
│  P0 (Ship Now):     ██████████████          26 tasks                │
│  P1 (This Sprint):  ████████████████████    34 tasks                │
│  P2 (Next Sprint):  ██████████████          26 tasks                │
│  P3 (Backlog):      ██████████              21 tasks                │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Sprint Overview — 8 Sprints, 16 Weeks

```
SPRINT 1 (Week 1-2):   LAUNCH THE MVP          ─ 14 tasks
SPRINT 2 (Week 3-4):   CORE INFRASTRUCTURE     ─ 16 tasks
SPRINT 3 (Week 5-6):   FEEDBACK + ANALYTICS     ─ 14 tasks
SPRINT 4 (Week 7-8):   AUTH + SECURITY          ─ 14 tasks
SPRINT 5 (Week 9-10):  WATCHLISTS + ALERTS      ─ 14 tasks
SPRINT 6 (Week 11-12): EXPORT + INTEGRATIONS    ─ 13 tasks
SPRINT 7 (Week 13-14): PRO TIER + BILLING       ─ 12 tasks
SPRINT 8 (Week 15-16): POLISH + V1 RELEASE      ─ 10 tasks
```

---

## Sprint 1: LAUNCH THE MVP (Week 1-2)

> **Goal**: Deploy a working demo that 3 features work end-to-end.
> **Success Criteria**: Demo live, 500+ visitors in first week, 0 P0 bugs.

---

### EPIC 1.0: Git Safety (Day 1, 1 hour)

| # | User Story | Task | Effort | Priority | Deliverable |
|---|---|---|---|---|---|
| T-001 | As a developer, I want all code committed and pushed so I don't lose work. | `git add -A && git commit -m "feat: add all working files" && git push` | **S** | **P0** | 45 files committed, 0 untracked |
| T-002 | As a developer, I want a LICENSE file so users can legally use the project. | Create LICENSE (MIT). | **S** | **P0** | MIT LICENSE file |
| T-003 | As a developer, I want a .gitignore so secrets and junk aren't committed. | Audit .gitignore, add .env, __pycache__, data/backups, *.pyc. | **S** | **P0** | Updated .gitignore |

---

### EPIC 1.1: Database Safety (Day 1, 2 hours)

| # | User Story | Task | Effort | Priority | Deliverable |
|---|---|---|---|---|---|
| T-004 | As a developer, I want automated daily backups so data is never lost. | Create `scripts/backup_db.sh`. Test manually. Set cron for 2 AM daily. | **S** | **P0** | Backup script + cron job |
| T-005 | As a developer, I want to restore from backup so I can recover from failure. | Create `scripts/restore_db.sh`. Test restore on a copy. | **S** | **P0** | Restore script + tested |
| T-006 | As a developer, I want to verify backups work so I trust them. | Run backup, check file size, run restore, verify row counts. | **S** | **P0** | Verified backup cycle |

---

### EPIC 1.2: Fix Known Bugs (Day 2, 4 hours)

| # | User Story | Task | Effort | Priority | Deliverable |
|---|---|---|---|---|---|
| T-007 | As a developer, I want 0 failing tests so I trust the test suite. | Fix 12 failing tests in `test_semantic_search.py`. Diagnose each, fix, verify. | **M** | **P0** | `pytest` → 0 failed |
| T-008 | As a developer, I want no test warnings so CI is clean. | Fix 125 test warnings (deprecations, import issues). | **M** | **P1** | `pytest -W error` passes |
| T-009 | As a user, I want the dashboard to load without errors. | Fix broken HTML, missing imports, placeholder content in Streamlit pages. | **M** | **P0** | All 11 Streamlit pages load |
| T-010 | As a developer, I want a .env.example file so setup is documented. | Create .env.example with all required env vars documented. | **S** | **P1** | .env.example file |

---

### EPIC 1.3: Load Seed Data (Day 3, 4 hours)

| # | User Story | Task | Effort | Priority | Deliverable |
|---|---|---|---|---|---|
| T-011 | As a user, I want to see real data when I open the dashboard. | Run `python seed_data.py`, then run 5 collectors, verify data in DB. | **M** | **P0** | 50+ entities scored, 100+ signals |
| T-012 | As a user, I want to search for startups and get results. | Test unified search with 10 queries. Fix empty results. | **S** | **P0** | Search returns results for "Tesla", "Rivian", etc. |
| T-013 | As a user, I want to ask questions and get AI answers. | Test `/api/chat` with 10 questions. Fix Ollama connection if needed. | **S** | **P0** | Chat works for "Why did Fisker fail?" |
| T-014 | As a user, I want to browse failure patterns. | Test failure pattern browser. Verify 50+ startups with patterns. | **S** | **P0** | Failure patterns page works |

---

### EPIC 1.4: Deploy Demo (Day 4-5, 8 hours)

| # | User Story | Task | Effort | Priority | Deliverable |
|---|---|---|---|---|---|
| T-015 | As a user, I want to access the platform at a public URL. | Deploy Docker Compose to VPS (DigitalOcean $5/mo). Configure DNS. | **L** | **P0** | Live demo at demo.opportunity-intel.org |
| T-016 | As a user, I want the demo to have HTTPS. | Set up Caddy reverse proxy with auto-HTTPS (Let's Encrypt). | **M** | **P0** | HTTPS working |
| T-017 | As a user, I want the default password changed. | Create .env with strong passwords. Remove hardcoded defaults. | **S** | **P0** | No default passwords |
| T-018 | As a developer, I want health monitoring on the demo. | Deploy `scripts/health_monitor.py` with cron on the VPS. | **S** | **P0** | Health checks every 5 min |
| T-019 | As a user, I want to give feedback on scores. | Deploy feedback system (4 tables + 5 endpoints + widgets). See FEEDBACK_STRATEGY.md. | **L** | **P0** | Thumbs up/down works on demo |
| T-020 | As a developer, I want analytics on user behavior. | Add Plausible analytics script to dashboard. | **S** | **P1** | Page views tracked |
| T-021 | As a user, I want a help button on the dashboard. | Add in-app help widget (💬 button linking to FAQ + GitHub Issues). | **S** | **P1** | Help widget visible on all pages |
| T-022 | As a developer, I want to record a demo for marketing. | Record 30-second GIF of Score + Chat + Failure Patterns. | **M** | **P1** | demo.gif in README |
| T-023 | As a developer, I want to launch on HN. | Write "Show HN" post. See GTM_STRATEGY.md. | **M** | **P1** | Post ready |
| T-024 | As a developer, I want to launch on Reddit. | Post to r/startups, r/SideProject, r/opensource. | **S** | **P1** | Posts live |

---

### Sprint 1 Summary

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  SPRINT 1 — LAUNCH THE MVP (Week 1-2)                              │
│                                                                      │
│  Tasks: 24                                                           │
│  Effort: 10S + 7M + 2L = ~44 hours                                 │
│                                                                      │
│  Daily Breakdown:                                                    │
│  Day 1: Git safety + DB backup (T-001 to T-006)         3 hours     │
│  Day 2: Fix bugs + tests (T-007 to T-010)               4 hours     │
│  Day 3: Load data + test features (T-011 to T-014)      4 hours     │
│  Day 4: Deploy demo + HTTPS + security (T-015 to T-018) 6 hours     │
│  Day 5: Feedback + analytics + demo GIF (T-019 to T-022)6 hours     │
│  Day 6-7: Buffer for unexpected issues                  6 hours      │
│  Day 8: Write launch posts (T-023 to T-024)             3 hours     │
│  Day 9: LAUNCH 🚀                                       2 hours     │
│  Day 10-14: Monitor, fix, respond to feedback           10 hours    │
│                                                                      │
│  Definition of Done:                                                 │
│  ✅ Demo live at public URL with HTTPS                              │
│  ✅ Score, Chat, Failure Patterns all work                          │
│  ✅ 0 failing tests                                                  │
│  ✅ Feedback collecting (thumbs up/down)                             │
│  ✅ Analytics tracking visitors                                      │
│  ✅ Database backing up daily                                        │
│  ✅ Launched on HN + Reddit + Twitter                                │
│  ✅ 500+ visitors in first week                                      │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Sprint 2: CORE INFRASTRUCTURE (Week 3-4)

> **Goal**: Build the 3 critical gaps (Scheduler, Alert Consumer, Score Push).
> **Success Criteria**: Data collects 24/7, alerts fire, scores update in real-time.

---

### EPIC 2.1: Collector Scheduler (24/7 Data Collection)

| # | User Story | Task | Effort | Priority | Deliverable |
|---|---|---|---|---|---|
| T-025 | As a user, I want data to be fresh without manual triggers. | Build collector scheduler: runs collectors on cron-like schedule. Reads config/settings.yaml pipelines. | **XL** | **P0** | `scripts/collector_scheduler.py` runs 24/7 |
| T-026 | As a developer, I want to know when collectors fail. | Add retry logic (3 retries with exponential backoff). Log failures to collection_runs table. | **M** | **P0** | Failed collections auto-retry |
| T-027 | As a developer, I want to see collection status. | Add `/api/collection/status` endpoint showing last run time, success/fail, record count per collector. | **S** | **P1** | Collection status visible in API |
| T-028 | As a user, I want the scheduler to start with Docker. | Add scheduler as a Docker service in docker-compose.yml. | **S** | **P0** | `docker compose up` starts scheduler |

---

### EPIC 2.2: Alert Consumer (Kafka → Notifications)

| # | User Story | Task | Effort | Priority | Deliverable |
|---|---|---|---|---|---|
| T-029 | As an investor, I want to be notified when a high-opportunity startup appears. | Build alert consumer: reads from Kafka `alerts` topic, sends notifications. | **XL** | **P0** | `agents/alert_consumer.py` |
| T-030 | As a user, I want to receive alerts via email. | Add email notification (SMTP). Template: "[OIP Alert] {startup} scored {score} — {reason}". | **M** | **P1** | Email alerts working |
| T-031 | As a user, I want to receive alerts via Slack webhook. | Add Slack notification via webhook URL. | **S** | **P1** | Slack alerts working |
| T-032 | As a user, I want to configure which alerts I receive. | Add alert preferences table + `/api/alerts/preferences` endpoint. | **M** | **P2** | Alert preference API |
| T-033 | As a developer, I want alert delivery to be reliable. | Add dead letter queue for failed alerts. Retry 3 times. | **M** | **P1** | Failed alerts don't disappear |

---

### EPIC 2.3: Score Push (Real-Time Dashboard Updates)

| # | User Story | Task | Effort | Priority | Deliverable |
|---|---|---|---|---|---|
| T-034 | As a user, I want scores to update on my dashboard without refreshing. | Build WebSocket score push: consume Kafka `scores.updates`, push to connected WebSocket clients. | **L** | **P0** | Scores update in < 5 seconds |
| T-035 | As a developer, I want WebSocket connections to be stable. | Add ping/pong heartbeat, auto-reconnect on disconnect, connection tracking. | **M** | **P1** | WebSocket stays connected |
| T-036 | As a user, I want to see WHAT changed in a score. | Add score delta view: "Tesla 78→82 (+4): Funding +2, Market +2". | **M** | **P1** | Score changes explained |

---

### EPIC 2.4: Score Accuracy Validation

| # | User Story | Task | Effort | Priority | Deliverable |
|---|---|---|---|---|---|
| T-037 | As a developer, I want to know if our scores are accurate. | Score 20 known startups (10 successes, 10 failures). Compare our score to actual outcome. Target: ≥ 50% accuracy. | **L** | **P0** | Accuracy report: X/20 correct |
| T-038 | As a developer, I want to tune scoring weights based on accuracy. | If accuracy < 50%, adjust factor weights in config/settings.yaml. Re-score. | **M** | **P0** | Score accuracy ≥ 50% |
| T-039 | As a developer, I want scoring accuracy tracked over time. | Add `/api/score/accuracy` endpoint returning weekly accuracy metrics. | **S** | **P1** | Accuracy tracked in API |

---

### EPIC 2.5: API Endpoint Tests (Critical Gap)

| # | User Story | Task | Effort | Priority | Deliverable |
|---|---|---|---|---|---|
| T-040 | As a developer, I want API tests so changes don't break endpoints. | Write tests for all 34 API endpoints. Test happy path + error cases. | **XL** | **P1** | `test_api_endpoints.py` with 68 tests |
| T-041 | As a developer, I want scorer tests so scoring changes don't break things. | Write 15 tests for opportunity_scorer: edge cases, negative inputs, large numbers. | **M** | **P1** | `test_opportunity_scorer.py` with 15 tests |
| T-042 | As a developer, I want tests for the database layer. | Write tests for db/connection.py and db/schema.py: connection, CRUD, error handling. | **M** | **P1** | `test_db_layer.py` with 10 tests |

---

### Sprint 2 Summary

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  SPRINT 2 — CORE INFRASTRUCTURE (Week 3-4)                         │
│                                                                      │
│  Tasks: 18 (T-025 to T-042)                                         │
│  Effort: 5S + 7M + 2L + 2XL = ~62 hours                           │
│                                                                      │
│  Week 3: Scheduler (T-025 to T-028) + Alert Consumer (T-029-T033)  │
│  Week 4: Score Push (T-034 to T-036) + Accuracy (T-037-039)        │
│          + API Tests (T-040 to T-042)                                │
│                                                                      │
│  Definition of Done:                                                 │
│  ✅ Collectors run 24/7 automatically                               │
│  ✅ Alerts sent via email + Slack                                   │
│  ✅ Dashboard scores update in real-time via WebSocket               │
│  ✅ Score accuracy measured ≥ 50%                                   │
│  ✅ 68 API endpoint tests + 15 scorer tests + 10 DB tests          │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Sprint 3: FEEDBACK + ANALYTICS (Week 5-6)

> **Goal**: Close the feedback loop. Users drive priorities.
> **Success Criteria**: Weekly feedback review, priorities adjusted by data.

---

### EPIC 3.1: Feedback Dashboard

| # | User Story | Task | Effort | Priority | Deliverable |
|---|---|---|---|---|---|
| T-043 | As a developer, I want a feedback dashboard so I can see what users want. | Build Streamlit "📊 Feedback" page showing top searches, chat questions, score ratings, feature requests. | **L** | **P1** | Feedback page in dashboard |
| T-044 | As a developer, I want the FeedbackAnalyzerAgent to run weekly. | Schedule FeedbackAnalyzerAgent in weekly pipeline. Output to `feedback_analysis` table. | **M** | **P1** | Agent runs weekly, output stored |
| T-045 | As a developer, I want orchestrator to read feedback priorities. | Modify orchestrator to check feedback_analyzer output before scheduling agents. | **M** | **P1** | Agents run based on user demand |
| T-046 | As a developer, I want a weekly progress report generated. | Build weekly report template. Auto-post to GitHub Discussions. | **M** | **P2** | Weekly report posted automatically |

---

### EPIC 3.2: Error Tracking

| # | User Story | Task | Effort | Priority | Deliverable |
|---|---|---|---|---|---|
| T-047 | As a developer, I want to know when users hit errors. | Deploy GlitchTip (self-hosted Sentry clone) via Docker. | **L** | **P1** | GlitchTip running at :8001 |
| T-048 | As a developer, I want Python errors reported automatically. | Add `sentry-sdk` (GlitchTip compatible) to api_server.py. | **S** | **P1** | Errors flow to GlitchTip |
| T-049 | As a developer, I want to know when the site is down. | Set up UptimeRobot (free) or health_monitor.py with Slack alerts. | **S** | **P1** | Alerts on downtime |

---

### EPIC 3.3: Performance Optimization

| # | User Story | Task | Effort | Priority | Deliverable |
|---|---|---|---|---|---|
| T-050 | As a user, I want search results in < 500ms. | Profile search endpoint. Add Redis caching for top queries. Optimize MySQL indexes. | **M** | **P2** | Search < 500ms p95 |
| T-051 | As a user, I want the dashboard to load in < 3 seconds. | Profile Streamlit pages. Add caching (@st.cache_data). Optimize DB queries. | **M** | **P2** | Dashboard < 3s load |
| T-052 | As a user, I want chat responses in < 5 seconds. | Profile Ollama inference. Optimize prompt. Add response streaming. | **M** | **P2** | Chat < 5s first token |
| T-053 | As a developer, I want to monitor performance over time. | Add response time tracking to query_log table. Build performance chart. | **S** | **P2** | Performance tracked per endpoint |

---

### Sprint 3 Summary

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  SPRINT 3 — FEEDBACK + ANALYTICS (Week 5-6)                        │
│                                                                      │
│  Tasks: 11 (T-043 to T-053)                                         │
│  Effort: 2S + 5M + 2L = ~32 hours                                  │
│                                                                      │
│  Definition of Done:                                                 │
│  ✅ Feedback dashboard showing user behavior                        │
│  ✅ FeedbackAnalyzerAgent runs weekly                               │
│  ✅ Error tracking via GlitchTip                                    │
│  ✅ Search < 500ms, Dashboard < 3s, Chat < 5s                      │
│  ✅ Weekly progress reports posted                                  │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Sprint 4: AUTH + SECURITY (Week 7-8)

> **Goal**: Users can create accounts. Platform is secure.
> **Success Criteria**: Auth working, security scan passes, rate limiting active.

---

### EPIC 4.1: Authentication

| # | User Story | Task | Effort | Priority | Deliverable |
|---|---|---|---|---|---|
| T-054 | As a user, I want to create an account. | Build user registration: `/api/auth/register` with email + password. Hash passwords (bcrypt). Store in `users` table. | **L** | **P1** | Users can register |
| T-055 | As a user, I want to log in. | Build login: `/api/auth/login` returning JWT token. | **M** | **P1** | Users can log in, get token |
| T-056 | As a user, I want to access protected endpoints with my token. | Add JWT middleware. Protect write endpoints. Public: search, score, health. | **M** | **P1** | Token required for write ops |
| T-057 | As a user, I want an API key for programmatic access. | Build API key management: `/api/auth/api-keys` (generate, list, revoke). | **M** | **P2** | API keys work |
| T-058 | As a developer, I want to test auth flows. | Write tests: register, login, token refresh, protected endpoint, API key. | **M** | **P1** | 10 auth tests passing |

---

### EPIC 4.2: Security Hardening

| # | User Story | Task | Effort | Priority | Deliverable |
|---|---|---|---|---|---|
| T-059 | As a developer, I want rate limiting so the API can't be abused. | Add slowapi rate limiting: 60 req/min per IP. | **S** | **P0** | Rate limiting active |
| T-060 | As a developer, I want security headers on all responses. | Add security middleware: X-Content-Type, CSP, X-Frame-Options, etc. | **S** | **P0** | Security headers present |
| T-061 | As a developer, I want input validation on all endpoints. | Add `sanitize_input()` to all user-facing endpoints. Block SQL injection patterns. | **M** | **P0** | No injection possible |
| T-062 | As a developer, I want Docker containers secured. | Add resource limits, cap_drop ALL, non-root user to docker-compose.yml. | **M** | **P1** | Docker security hardened |
| T-063 | As a developer, I want no hardcoded secrets. | Move all passwords to .env. Audit code for hardcoded values. | **S** | **P0** | No secrets in code |
| T-064 | As a developer, I want security scanning in CI. | Add `bandit` + `pip-audit` to GitHub Actions. Fail on HIGH/CRITICAL CVEs. | **M** | **P1** | CI scans for vulnerabilities |

---

### Sprint 4 Summary

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  SPRINT 4 — AUTH + SECURITY (Week 7-8)                              │
│                                                                      │
│  Tasks: 11 (T-054 to T-064)                                         │
│  Effort: 3S + 5M + 1L = ~28 hours                                  │
│                                                                      │
│  Definition of Done:                                                 │
│  ✅ Users can register, login, get JWT tokens                       │
│  ✅ API key management working                                      │
│  ✅ Rate limiting active (60 req/min)                               │
│  ✅ Security headers on all responses                               │
│  ✅ Input validation on all endpoints                               │
│  ✅ Docker containers secured                                       │
│  ✅ CI scans for vulnerabilities                                    │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Sprint 5: WATCHLISTS + ALERTS (Week 9-10)

> **Goal**: Users can track startups they care about and get notified.
> **Success Criteria**: Watchlists work, alerts fire on score changes.

---

### EPIC 5.1: Watchlists

| # | User Story | Task | Effort | Priority | Deliverable |
|---|---|---|---|---|---|
| T-065 | As an investor, I want to save startups I'm tracking. | Build watchlist: `watchlists` table + `/api/watchlist` CRUD endpoints. | **L** | **P1** | Watchlist CRUD working |
| T-066 | As an investor, I want to see all my tracked startups' scores at a glance. | Build watchlist dashboard view: table of startups with current score, change, alerts. | **M** | **P1** | Watchlist view in dashboard |
| T-067 | As an investor, I want to add notes to tracked startups. | Add notes field to watchlist items. Add/edit/delete notes. | **S** | **P2** | Notes on watchlist items |
| T-068 | As an investor, I want to group startups into folders/tags. | Add tags/labels to watchlist. Filter by tag. | **M** | **P2** | Watchlist tags working |

---

### EPIC 5.2: Smart Alerts

| # | User Story | Task | Effort | Priority | Deliverable |
|---|---|---|---|---|---|
| T-069 | As an investor, I want alerts when a tracked startup's score changes > 10 points. | Build score change alert: compare daily scores, fire alert if delta > threshold. | **L** | **P1** | Score change alerts working |
| T-070 | As an investor, I want alerts when a new startup scores above 80. | Build high-score alert: check new scores daily, notify if > 80. | **M** | **P1** | High-score alerts working |
| T-071 | As an investor, I want to configure alert thresholds. | Add alert settings: score threshold, frequency (immediate/daily/weekly digest). | **M** | **P2** | Alert preferences working |
| T-072 | As an investor, I want a daily email digest of changes. | Build daily digest email: "5 startups changed, 2 new above 80, 1 alert triggered". | **M** | **P2** | Daily digest email |
| T-073 | As a user, I want to see alert history. | Add `alert_history` table + `/api/alerts/history` endpoint. | **S** | **P2** | Alert history visible |

---

### Sprint 5 Summary

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  SPRINT 5 — WATCHLISTS + ALERTS (Week 9-10)                        │
│                                                                      │
│  Tasks: 9 (T-065 to T-073)                                          │
│  Effort: 2S + 4M + 2L = ~28 hours                                  │
│                                                                      │
│  Definition of Done:                                                 │
│  ✅ Watchlist CRUD with notes and tags                              │
│  ✅ Score change alerts (email + Slack)                             │
│  ✅ High-score alerts for new startups                              │
│  ✅ Daily email digest                                              │
│  ✅ Alert history                                                   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Sprint 6: EXPORT + INTEGRATIONS (Week 11-12)

> **Goal**: Users can export data and connect to other tools.
> **Success Criteria**: CSV/PDF export, CRM webhook, REST API complete.

---

### EPIC 6.1: Data Export

| # | User Story | Task | Effort | Priority | Deliverable |
|---|---|---|---|---|---|
| T-074 | As an analyst, I want to export search results to CSV. | Build `/api/export/csv` endpoint: query → CSV download. | **M** | **P1** | CSV export works |
| T-075 | As an analyst, I want to export score reports to PDF. | Build `/api/export/pdf` endpoint: startup profile → PDF with score, factors, history. Use reportlab. | **L** | **P2** | PDF export works |
| T-076 | As an analyst, I want to export my watchlist. | Add "Export Watchlist" button → CSV download. | **S** | **P2** | Watchlist CSV export |

---

### EPIC 6.2: External Integrations

| # | User Story | Task | Effort | Priority | Deliverable |
|---|---|---|---|---|---|
| T-077 | As an investor, I want to send alerts to my CRM. | Build webhook integration: POST alert to user-configured URL (Salesforce, HubSpot, custom). | **M** | **P2** | Webhook alerts working |
| T-078 | As an investor, I want Zapier/Make.com integration. | Build a Zapier-friendly REST endpoint: `/api/zapier/new-alerts` returning recent alerts. | **S** | **P3** | Zapier-compatible endpoint |
| T-079 | As a developer, I want to add a new data source easily. | Write contributor guide for adding collectors. Template collector file. | **M** | **P2** | CONTRIBUTING.md updated |
| T-080 | As a developer, I want API documentation auto-generated. | Set up Swagger/OpenAPI auto-docs from FastAPI. Add examples. | **S** | **P2** | /docs page complete |

---

### EPIC 6.3: Agent Cleanup

| # | User Story | Task | Effort | Priority | Deliverable |
|---|---|---|---|---|---|
| T-081 | As a developer, I want to remove agents that don't solve user problems. | Cut 6 agents: LLMPortfolio, LLMPricing, LLMBenchmark, LLMCostOptimizer, Span, ProjectMonitor. | **M** | **P3** | 6 agents removed, tests updated |
| T-082 | As a developer, I want to merge redundant agents. | Merge: Report+ReportGenerator, InternetResearch+AIAnalyst, IntentClassifier→keywords. | **M** | **P3** | 4 agents merged into 2 |
| T-083 | As a developer, I want all remaining agents tested. | Write basic tests for the 52 untested agents (smoke tests: import + run with mock data). | **XL** | **P2** | All agents have ≥ 1 test |

---

### Sprint 6 Summary

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  SPRINT 6 — EXPORT + INTEGRATIONS (Week 11-12)                     │
│                                                                      │
│  Tasks: 10 (T-074 to T-083)                                         │
│  Effort: 2S + 4M + 1L + 1XL = ~40 hours                            │
│                                                                      │
│  Definition of Done:                                                 │
│  ✅ CSV and PDF export working                                      │
│  ✅ Webhook alerts to external tools                                │
│  ✅ 6 agents cut, 4 agents merged                                   │
│  ✅ All agents have ≥ 1 test                                        │
│  ✅ API documentation complete                                      │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Sprint 7: PRO TIER + BILLING (Week 13-14)

> **Goal**: Revenue. Users can pay for advanced features.
> **Success Criteria**: Stripe working, Pro tier live, first paying customer.

---

### EPIC 7.1: Billing

| # | User Story | Task | Effort | Priority | Deliverable |
|---|---|---|---|---|---|
| T-084 | As a user, I want to upgrade to Pro ($49/mo). | Integrate Stripe Checkout: `/api/billing/checkout` → Stripe hosted page. | **XL** | **P1** | Stripe checkout works |
| T-085 | As a user, I want to manage my subscription. | Build subscription management: `/api/billing/portal` → Stripe Customer Portal. | **M** | **P1** | Users can cancel/upgrade |
| T-086 | As a developer, I want Stripe webhooks to update user tier. | Handle `checkout.session.completed`, `customer.subscription.updated`, `subscription.deleted`. | **M** | **P1** | Tier updated automatically |
| T-087 | As a developer, I want to gate Pro features. | Add `require_pro` decorator. Pro features: export, watchlists, alerts, API keys > 3. | **M** | **P1** | Pro features gated |

---

### EPIC 7.2: Pro Features

| # | User Story | Task | Effort | Priority | Deliverable |
|---|---|---|---|---|---|
| T-088 | As a Pro user, I want unlimited API calls. | Raise rate limit for Pro users to 1000/min. | **S** | **P1** | Pro: 1000 req/min |
| T-089 | As a Pro user, I want historical score charts. | Build time-series chart for entity scores over time using TimescaleDB data. | **L** | **P2** | Score history chart |
| T-090 | As a Pro user, I want advanced search filters. | Add filters: sector, stage, score range, funding amount, geography. | **M** | **P2** | Search filters working |
| T-091 | As a Pro user, I want priority support. | Add Pro badge to GitHub Issues. Prioritize Pro user issues in triage. | **S** | **P2** | Pro users get priority |

---

### Sprint 7 Summary

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  SPRINT 7 — PRO TIER + BILLING (Week 13-14)                        │
│                                                                      │
│  Tasks: 8 (T-084 to T-091)                                          │
│  Effort: 2S + 3M + 1L + 1XL = ~34 hours                            │
│                                                                      │
│  Definition of Done:                                                 │
│  ✅ Stripe checkout + subscription management                       │
│  ✅ Pro features gated behind subscription                          │
│  ✅ Unlimited API calls for Pro users                               │
│  ✅ Historical score charts                                         │
│  ✅ Advanced search filters                                         │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Sprint 8: POLISH + V1 RELEASE (Week 15-16)

> **Goal**: Ship V1.0.0. Everything works. Everything is documented.
> **Success Criteria**: V1.0.0 tagged, release notes, 0 known P0/P1 bugs.

---

### EPIC 8.1: Mobile + Polish

| # | User Story | Task | Effort | Priority | Deliverable |
|---|---|---|---|---|---|
| T-092 | As a user, I want the dashboard to work on mobile. | Make Streamlit dashboard responsive. Test on iPhone + Android. | **L** | **P2** | Dashboard works on mobile |
| T-093 | As a user, I want a dark mode. | Add dark mode toggle to Streamlit dashboard. | **S** | **P3** | Dark mode toggle |
| T-094 | As a user, I want the dashboard to be fast. | Cache expensive queries. Add loading states. Optimize Streamlit reruns. | **M** | **P2** | Dashboard < 3s on mobile |

---

### EPIC 8.2: Documentation + Release

| # | User Story | Task | Effort | Priority | Deliverable |
|---|---|---|---|---|---|
| T-095 | As a user, I want a getting started guide. | Write step-by-step setup guide in README: clone → docker compose up → open dashboard. | **M** | **P1** | README with setup guide |
| T-096 | As a user, I want an architecture diagram. | Create system architecture diagram (Mermaid or Excalidraw). Add to README. | **M** | **P2** | Architecture diagram in README |
| T-097 | As a developer, I want V1 release notes. | Write release notes summarizing all features. Create GitHub Release. | **M** | **P1** | V1.0.0 release on GitHub |
| T-098 | As a developer, I want all docs up to date. | Audit all .md files. Update outdated info. Fix broken links. | **L** | **P1** | All docs current |

---

### EPIC 8.3: V1 Hardening

| # | User Story | Task | Effort | Priority | Deliverable |
|---|---|---|---|---|---|
| T-099 | As a developer, I want 0 P0/P1 bugs at V1 release. | Fix all open P0/P1 issues. Run full test suite. Run security scan. | **L** | **P0** | 0 P0/P1 issues open |
| T-100 | As a developer, I want ≥ 80% test coverage on new code. | Run coverage.py. Add tests for uncovered critical paths. | **XL** | **P2** | ≥ 80% coverage on new code |
| T-101 | As a developer, I want a clean codebase. | Run `ruff check --fix`. Fix all linting issues. Remove unused imports. | **M** | **P2** | 0 linting errors |
| T-102 | As a developer, I want to tag V1.0.0. | `git tag -a v1.0.0 -m "V1.0.0: Production Release" && git push origin v1.0.0` | **S** | **P1** | V1.0.0 tagged |
| T-103 | As a developer, I want CI/CD fully automated. | GitHub Actions: tests on PR, security scan weekly, deploy on tag. | **M** | **P1** | Push tag → auto-deploy |
| T-104 | As a developer, I want a launch plan. | Plan V1 launch: HN post, Twitter thread, blog post, Product Hunt. | **M** | **P1** | Launch plan ready |
| T-105 | As a user, I want a privacy policy. | Write privacy policy. Add /privacy page. | **S** | **P2** | Privacy policy page |
| T-106 | As a user, I want terms of service. | Write ToS. Add /terms page. | **S** | **P2** | Terms of service page |
| T-107 | As a developer, I want GDPR basics covered. | Add data export (right to portability) + data deletion (right to erasure) endpoints. | **M** | **P2** | GDPR endpoints working |

---

### Sprint 8 Summary

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  SPRINT 8 — POLISH + V1 RELEASE (Week 15-16)                       │
│                                                                      │
│  Tasks: 16 (T-092 to T-107)                                         │
│  Effort: 3S + 5M + 3L + 1XL = ~48 hours                            │
│                                                                      │
│  Definition of Done:                                                 │
│  ✅ Dashboard responsive on mobile                                  │
│  ✅ All documentation current                                       │
│  ✅ V1.0.0 tagged and released                                      │
│  ✅ 0 P0/P1 bugs                                                    │
│  ✅ ≥ 80% test coverage on new code                                 │
│  ✅ Privacy policy + terms of service                               │
│  ✅ GDPR basics: data export + deletion                             │
│  ✅ Launch plan ready                                               │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Full Plan at a Glance

---

### All 107 Tasks — Sorted by Priority

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  P0 — SHIP NOW (26 tasks)                                           │
│  ───────────────────────────                                        │
│  T-001  Git commit + push                              S  Sprint 1  │
│  T-002  Create LICENSE file                            S  Sprint 1  │
│  T-003  Audit .gitignore                               S  Sprint 1  │
│  T-004  Create backup script                           S  Sprint 1  │
│  T-005  Create restore script                          S  Sprint 1  │
│  T-006  Verify backup cycle                            S  Sprint 1  │
│  T-007  Fix 12 failing tests                           M  Sprint 1  │
│  T-009  Fix broken dashboard pages                     M  Sprint 1  │
│  T-011  Load seed data (50+ entities)                  M  Sprint 1  │
│  T-012  Test search returns results                    S  Sprint 1  │
│  T-013  Test chat works                                S  Sprint 1  │
│  T-014  Test failure patterns browser                  S  Sprint 1  │
│  T-015  Deploy demo to VPS                             L  Sprint 1  │
│  T-016  Set up HTTPS                                   M  Sprint 1  │
│  T-017  Change default passwords                       S  Sprint 1  │
│  T-018  Deploy health monitor                          S  Sprint 1  │
│  T-025  Build collector scheduler                      XL Sprint 2  │
│  T-028  Add scheduler to Docker                        S  Sprint 2  │
│  T-029  Build alert consumer                           XL Sprint 2  │
│  T-034  Build WebSocket score push                     L  Sprint 2  │
│  T-037  Measure score accuracy (20 startups)           L  Sprint 2  │
│  T-038  Tune scoring weights                           M  Sprint 2  │
│  T-059  Add rate limiting                              S  Sprint 4  │
│  T-060  Add security headers                           S  Sprint 4  │
│  T-061  Add input validation                           M  Sprint 4  │
│  T-063  Remove hardcoded secrets                       S  Sprint 4  │
│  T-099  Fix all P0/P1 bugs for V1                     L  Sprint 8  │
│                                                                      │
│  Total P0: 15S + 7M + 3L + 2XL = ~78 hours                         │
│                                                                      │
│  P1 — THIS SPRINT (34 tasks)                                        │
│  ─────────────────────────────                                      │
│  T-008, T-010, T-019-T-024, T-026-T-027, T-030-T-031,              │
│  T-033, T-035-T-036, T-039-T-042, T-043-T-048,                     │
│  T-054-T-058, T-062, T-064-T-066, T-069-T-070,                     │
│  T-074, T-084-T-087, T-095, T-097-T-098, T-102-T-104              │
│                                                                      │
│  Total P1: ~100 hours                                                │
│                                                                      │
│  P2 — NEXT SPRINT (26 tasks)                                        │
│  ──────────────────────────────                                     │
│  T-032, T-046, T-050-T-053, T-057, T-067-T-068,                    │
│  T-071-T-073, T-075-T-076, T-079-T-080, T-083,                     │
│  T-089-T-091, T-094, T-096, T-101, T-105-T-107                    │
│                                                                      │
│  Total P2: ~80 hours                                                 │
│                                                                      │
│  P3 — BACKLOG (21 tasks)                                            │
│  ──────────────────────────                                         │
│  T-078, T-081-T-082, T-093                                          │
│  (most P3 tasks from later sprints, deferred)                       │
│                                                                      │
│  Total P3: ~20 hours                                                 │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### Effort Summary

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  EFFORT BY SIZE:                                                     │
│                                                                      │
│  S (1-2 hrs):  48 tasks × 1.5 hrs avg =  72 hours                  │
│  M (3-4 hrs):  30 tasks × 3.5 hrs avg = 105 hours                  │
│  L (1 day):    20 tasks × 7 hrs avg  = 140 hours                   │
│  XL (2+ days):  9 tasks × 16 hrs avg = 144 hours                   │
│                                               ──────────             │
│                          TOTAL ESTIMATED:    461 hours               │
│                                                                      │
│  AT 6 HOURS/DAY (realistic pace):                                    │
│  461 hours ÷ 6 hrs/day = 77 days = ~16 weeks = 8 sprints ✅        │
│                                                                      │
│  EFFORT BY SPRINT:                                                   │
│  Sprint 1: 44 hrs   ████████████████████░░░░░░░░░░░░░  (Launch)     │
│  Sprint 2: 62 hrs   ████████████████████████████░░░░░  (Infra)      │
│  Sprint 3: 32 hrs   ██████████████░░░░░░░░░░░░░░░░░░░  (Feedback)   │
│  Sprint 4: 28 hrs   ████████████░░░░░░░░░░░░░░░░░░░░░  (Security)   │
│  Sprint 5: 28 hrs   ████████████░░░░░░░░░░░░░░░░░░░░░  (Watchlists) │
│  Sprint 6: 40 hrs   █████████████████░░░░░░░░░░░░░░░░  (Export)     │
│  Sprint 7: 34 hrs   ███████████████░░░░░░░░░░░░░░░░░░  (Billing)    │
│  Sprint 8: 48 hrs   ██████████████████████░░░░░░░░░░░  (V1 Release) │
│                                                                      │
│  CUMULATIVE DELIVERY:                                                │
│  Week  2:  44 hrs  → MVP LAUNCHED ✅                                │
│  Week  4: 106 hrs  → 24/7 data + alerts + real-time scores ✅      │
│  Week  6: 138 hrs  → Feedback loop closed ✅                        │
│  Week  8: 166 hrs  → Auth + security hardened ✅                    │
│  Week 10: 194 hrs  → Watchlists + smart alerts ✅                   │
│  Week 12: 234 hrs  → Export + integrations ✅                       │
│  Week 14: 268 hrs  → Revenue (Pro tier) ✅                          │
│  Week 16: 316 hrs  → V1.0.0 RELEASED ✅                            │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Deliverables at Each Sprint Boundary

---

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  SPRINT 1 DONE → USER CAN:                                          │
│  • Visit a public URL                                                │
│  • Search for any startup                                            │
│  • See a composite score (0-100)                                     │
│  • Chat with AI about startups                                       │
│  • Browse failure patterns                                           │
│  • Give feedback (thumbs up/down)                                    │
│  • Request features                                                  │
│  • Read FAQ                                                          │
│                                                                      │
│  SPRINT 2 DONE → USER CAN ALSO:                                     │
│  • See fresh data (collected 24/7)                                   │
│  • Receive email/Slack alerts                                        │
│  • See scores update in real-time                                    │
│  • Trust scores (accuracy measured ≥ 50%)                           │
│                                                                      │
│  SPRINT 3 DONE → USER CAN ALSO:                                     │
│  • See feedback-driven improvements                                  │
│  • Get fast search (< 500ms)                                         │
│  • Get fast chat (< 5s)                                              │
│                                                                      │
│  SPRINT 4 DONE → USER CAN ALSO:                                     │
│  • Create an account                                                 │
│  • Log in and get API token                                          │
│  • Trust that the platform is secure                                 │
│                                                                      │
│  SPRINT 5 DONE → USER CAN ALSO:                                     │
│  • Save startups to a watchlist                                      │
│  • Add notes and tags to watchlist items                             │
│  • Get alerts when scores change                                     │
│  • Get daily email digest                                            │
│                                                                      │
│  SPRINT 6 DONE → USER CAN ALSO:                                     │
│  • Export data to CSV/PDF                                            │
│  • Send alerts to external webhooks                                  │
│                                                                      │
│  SPRINT 7 DONE → USER CAN ALSO:                                     │
│  • Upgrade to Pro ($49/mo)                                           │
│  • Get unlimited API calls                                           │
│  • See historical score charts                                       │
│  • Use advanced search filters                                       │
│                                                                      │
│  SPRINT 8 DONE → V1.0.0 RELEASED:                                   │
│  • Mobile-friendly dashboard                                         │
│  • Complete documentation                                            │
│  • Privacy policy + terms of service                                 │
│  • GDPR compliance basics                                            │
│  • 0 P0/P1 bugs                                                      │
│  • ≥ 80% test coverage on new code                                  │
│  • Tagged release with notes                                         │
│                                                                      │
│  EACH SPRINT DELIVERS INCREMENTAL VALUE.                            │
│  USERS GET SOMETHING NEW EVERY 2 WEEKS.                             │
│  NOTHING IS HELD BACK FOR A "BIG BANG" RELEASE.                    │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Risk Register — What Could Go Wrong Per Sprint

---

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  SPRINT  RISK                            MITIGATION                  │
│  ────────────────────────────────────────────────────────────────    │
│                                                                      │
│  1       VPS deployment fails          Test Docker Compose locally   │
│          first, then deploy. Use same docker-compose.yml.           │
│                                                                      │
│  1       Score accuracy < 50%          Accept it. Label as "beta".   │
│          Improve iteratively based on feedback.                      │
│                                                                      │
│  2       Collector scheduler crashes   Add restart policy (Docker    │
│          restart: unless-stopped). Log failures. Auto-retry.        │
│                                                                      │
│  2       Kafka connection issues       Already handles: falls back   │
│          to MySQL-only. Test both paths.                            │
│                                                                      │
│  3       GlitchTip too complex         Start with simple error log   │
│          file. Add GlitchTip only if needed.                        │
│                                                                      │
│  4       Auth takes longer than L      Use FastAPI-Users library     │
│          instead of building from scratch.                          │
│                                                                      │
│  5       Watchlist queries slow        Add MySQL indexes on          │
│          watchlist table. Cache in Redis.                            │
│                                                                      │
│  6       PDF generation complex        Use simple HTML → PDF         │
│          (WeasyPrint) instead of reportlab.                         │
│                                                                      │
│  7       Stripe integration bugs       Test in Stripe test mode      │
│          first. Don't go live until it works perfectly.             │
│                                                                      │
│  8       V1 launch gets no attention   Already have audience from    │
│          Sprint 1 HN launch. Build in public throughout.            │
│                                                                      │
│  GLOBAL  Burnout (bus factor = 1)      6 hrs/day max. 1 day off     │
│          per week. Skip P3 tasks. Cut scope, not sleep.             │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## How to Use This Plan

---

### Daily Standup (5 minutes)

```
Ask yourself 3 questions:
1. What did I complete yesterday? (check off tasks)
2. What am I doing today? (pick next task from current sprint)
3. Is anything blocking me? (if yes → fix blocker first)
```

### Sprint Planning (30 minutes, every 2 weeks)

```
1. Review: Did we complete last sprint's tasks?
2. Demo: Show what was built to a real or imaginary user.
3. Plan: Pick tasks for next sprint from this document.
4. Adjust: Reprioritize based on user feedback from /api/feedback/dashboard.
5. Commit: Write the sprint's tasks on a GitHub Project board.
```

### Sprint Retrospective (15 minutes, every 2 weeks)

```
1. What went well? (keep doing it)
2. What went wrong? (fix it next sprint)
3. What should we start doing? (process improvement)
4. Update effort estimates (were S/M/L/XL accurate?)
```

---

## Quick Reference: All 107 Tasks

---

| # | Task | Effort | Priority | Sprint |
|---|---|---|---|---|
| T-001 | Git commit + push all files | S | P0 | 1 |
| T-002 | Create LICENSE (MIT) | S | P0 | 1 |
| T-003 | Audit .gitignore | S | P0 | 1 |
| T-004 | Create backup_db.sh | S | P0 | 1 |
| T-005 | Create restore_db.sh | S | P0 | 1 |
| T-006 | Verify backup cycle | S | P0 | 1 |
| T-007 | Fix 12 failing tests | M | P0 | 1 |
| T-008 | Fix 125 test warnings | M | P1 | 1 |
| T-009 | Fix broken dashboard pages | M | P0 | 1 |
| T-010 | Create .env.example | S | P1 | 1 |
| T-011 | Load seed data (50+ entities) | M | P0 | 1 |
| T-012 | Test search returns results | S | P0 | 1 |
| T-013 | Test chat works | S | P0 | 1 |
| T-014 | Test failure patterns browser | S | P0 | 1 |
| T-015 | Deploy demo to VPS | L | P0 | 1 |
| T-016 | Set up HTTPS | M | P0 | 1 |
| T-017 | Change default passwords | S | P0 | 1 |
| T-018 | Deploy health monitor | S | P0 | 1 |
| T-019 | Deploy feedback system | L | P0 | 1 |
| T-020 | Add Plausible analytics | S | P1 | 1 |
| T-021 | Add in-app help widget | S | P1 | 1 |
| T-022 | Record demo GIF | M | P1 | 1 |
| T-023 | Write "Show HN" post | M | P1 | 1 |
| T-024 | Launch on HN + Reddit | S | P1 | 1 |
| T-025 | Build collector scheduler | XL | P0 | 2 |
| T-026 | Add retry logic to collectors | M | P0 | 2 |
| T-027 | Add /api/collection/status | S | P1 | 2 |
| T-028 | Add scheduler to Docker | S | P0 | 2 |
| T-029 | Build alert consumer | XL | P0 | 2 |
| T-030 | Add email notifications | M | P1 | 2 |
| T-031 | Add Slack notifications | S | P1 | 2 |
| T-032 | Add alert preferences | M | P2 | 2 |
| T-033 | Add dead letter queue for alerts | M | P1 | 2 |
| T-034 | Build WebSocket score push | L | P0 | 2 |
| T-035 | Add WebSocket heartbeat + reconnect | M | P1 | 2 |
| T-036 | Add score delta view | M | P1 | 2 |
| T-037 | Measure score accuracy (20 startups) | L | P0 | 2 |
| T-038 | Tune scoring weights | M | P0 | 2 |
| T-039 | Add /api/score/accuracy endpoint | S | P1 | 2 |
| T-040 | Write 68 API endpoint tests | XL | P1 | 2 |
| T-041 | Write 15 scorer tests | M | P1 | 2 |
| T-042 | Write 10 DB layer tests | M | P1 | 2 |
| T-043 | Build feedback dashboard page | L | P1 | 3 |
| T-044 | Schedule FeedbackAnalyzerAgent | M | P1 | 3 |
| T-045 | Orchestrator reads feedback | M | P1 | 3 |
| T-046 | Weekly progress report | M | P2 | 3 |
| T-047 | Deploy GlitchTip (error tracking) | L | P1 | 3 |
| T-048 | Add error reporting to API | S | P1 | 3 |
| T-049 | Set up uptime monitoring | S | P1 | 3 |
| T-050 | Optimize search < 500ms | M | P2 | 3 |
| T-051 | Optimize dashboard < 3s | M | P2 | 3 |
| T-052 | Optimize chat < 5s | M | P2 | 3 |
| T-053 | Track performance per endpoint | S | P2 | 3 |
| T-054 | Build user registration | L | P1 | 4 |
| T-055 | Build JWT login | M | P1 | 4 |
| T-056 | Add JWT middleware | M | P1 | 4 |
| T-057 | Build API key management | M | P2 | 4 |
| T-058 | Write auth tests | M | P1 | 4 |
| T-059 | Add rate limiting (slowapi) | S | P0 | 4 |
| T-060 | Add security headers | S | P0 | 4 |
| T-061 | Add input validation | M | P0 | 4 |
| T-062 | Harden Docker containers | M | P1 | 4 |
| T-063 | Remove hardcoded secrets | S | P0 | 4 |
| T-064 | Add security scan to CI | M | P1 | 4 |
| T-065 | Build watchlist CRUD | L | P1 | 5 |
| T-066 | Build watchlist dashboard view | M | P1 | 5 |
| T-067 | Add notes to watchlist | S | P2 | 5 |
| T-068 | Add tags to watchlist | M | P2 | 5 |
| T-069 | Build score change alerts | L | P1 | 5 |
| T-070 | Build high-score alerts | M | P1 | 5 |
| T-071 | Add alert threshold config | M | P2 | 5 |
| T-072 | Build daily digest email | M | P2 | 5 |
| T-073 | Build alert history | S | P2 | 5 |
| T-074 | Build CSV export | M | P1 | 6 |
| T-075 | Build PDF export | L | P2 | 6 |
| T-076 | Build watchlist export | S | P2 | 6 |
| T-077 | Build webhook alerts | M | P2 | 6 |
| T-078 | Build Zapier endpoint | S | P3 | 6 |
| T-079 | Write collector contributor guide | M | P2 | 6 |
| T-080 | Auto-generate API docs | S | P2 | 6 |
| T-081 | Cut 6 agents | M | P3 | 6 |
| T-082 | Merge 4 agents | M | P3 | 6 |
| T-083 | Test 52 untested agents | XL | P2 | 6 |
| T-084 | Stripe checkout integration | XL | P1 | 7 |
| T-085 | Subscription management | M | P1 | 7 |
| T-086 | Stripe webhook handler | M | P1 | 7 |
| T-087 | Gate Pro features | M | P1 | 7 |
| T-088 | Pro rate limit (1000/min) | S | P1 | 7 |
| T-089 | Historical score charts | L | P2 | 7 |
| T-090 | Advanced search filters | M | P2 | 7 |
| T-091 | Priority support for Pro | S | P2 | 7 |
| T-092 | Mobile-friendly dashboard | L | P2 | 8 |
| T-093 | Dark mode toggle | S | P3 | 8 |
| T-094 | Dashboard performance on mobile | M | P2 | 8 |
| T-095 | Getting started guide | M | P1 | 8 |
| T-096 | Architecture diagram | M | P2 | 8 |
| T-097 | V1 release notes | M | P1 | 8 |
| T-098 | Audit all documentation | L | P1 | 8 |
| T-099 | Fix all P0/P1 bugs | L | P0 | 8 |
| T-100 | ≥ 80% test coverage | XL | P2 | 8 |
| T-101 | Clean codebase (ruff) | M | P2 | 8 |
| T-102 | Tag V1.0.0 | S | P1 | 8 |
| T-103 | Full CI/CD pipeline | M | P1 | 8 |
| T-104 | V1 launch plan | M | P1 | 8 |
| T-105 | Privacy policy page | S | P2 | 8 |
| T-106 | Terms of service page | S | P2 | 8 |
| T-107 | GDPR data export + delete | M | P2 | 8 |

---

*Last updated: June 5, 2026*
