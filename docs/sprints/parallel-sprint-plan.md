# ⚡ Parallel Sprint Plan — Reduced from 316 hrs → ~178 hrs (44% faster)

> **Strategy**: Run 4 parallel workstreams using the AI dev-team agents.
> Each workstream is handled by a dedicated agent, enabling true parallel execution.

---

## Parallel Workstream Model

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  WORKSTREAM A: 🏗️  INFRA + DEVOPS  (DevOps Engineer Agent)             │
│  WORKSTREAM B: 🔧  CODE + TESTS    (Software Engineer Agent)           │
│  WORKSTREAM C: 🎨  UI + UX         (UX Designer Agent)                 │
│  WORKSTREAM D: 📋  PM + LAUNCH     (Product Manager Agent)             │
│                                                                         │
│  Each workstream runs INDEPENDENTLY and in PARALLEL.                   │
│  Sync points every 2-3 days to merge results.                          │
│                                                                         │
│  ORIGINAL:  8 sprints × 2 weeks = 16 weeks (316 hrs sequential)       │
│  PARALLEL:  4 phases × 1 week  = 4 weeks  (178 hrs with overlap)      │
│  SAVINGS:   12 weeks saved (75% faster to MVP+features)               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🗓️ Phase 1: LAUNCH MVP (Week 1) — 44 hrs → 15 hrs wall-clock

### Dependency Graph

```
DAY 1 (Hour 0-6) — 4 streams parallel:

  Stream A (DevOps)        Stream B (Software Eng)     Stream C (UX)           Stream D (PM)
  ┌──────────────────┐     ┌──────────────────┐       ┌──────────────────┐    ┌──────────────────┐
  │ T-001 Git commit  │     │ T-007 Fix 12      │       │ T-002 LICENSE     │    │ T-009 Create      │
  │ T-003 .gitignore  │     │   failing tests   │       │ T-010 .env.example│    │   .env.example    │
  │ T-004 Backup cron │     │ T-008 Fix 125     │       │ T-017 Default     │    │ T-021 Launch post │
  │ T-005 Restore     │     │   warnings        │       │   passwords       │    │   draft           │
  │ T-006 Verify bkup │     │                    │       │ T-018 Health      │    │ T-023 Write HN    │
  └────────┬─────────┘     └────────┬─────────┘       │   monitor         │    │   post            │
           │                        │                   └────────┬─────────┘    └────────┬─────────┘
           │                        │                            │                       │
  WALL: 3.5 hrs               WALL: 4 hrs                   WALL: 2.5 hrs            WALL: 3.5 hrs

DAY 2 (Hour 6-12) — merge + parallel:

  Stream A                  Stream B                     Stream C                 Stream D
  ┌──────────────────┐     ┌──────────────────┐       ┌──────────────────┐    ┌──────────────────┐
  │ T-015 Deploy VPS  │     │ T-011 Load seed   │       │ T-019 Feedback    │    │ T-020 Plausible   │
  │ T-016 HTTPS/Caddy│     │   data            │       │   system          │    │   analytics       │
  │ T-017 Passwords   │     │ T-012 Test search │       │ T-018 Help widget │    │ T-022 Demo GIF    │
  │                   │     │ T-013 Test chat   │       │                   │    │ T-024 Reddit post │
  │                   │     │ T-014 Test failure│       │                   │    │                   │
  └────────┬─────────┘     └────────┬─────────┘       └────────┬─────────┘    └────────┬─────────┘
           │                        │                            │                       │
  WALL: 5 hrs                WALL: 5 hrs                   WALL: 3 hrs               WALL: 3 hrs

SYNC POINT: Merge Day 2 → Deploy + Test full flow (T-022) → LAUNCH (T-023, T-024)
```

### Phase 1 Task Assignment

| Stream | Tasks | Sequential Hrs | Parallel Wall Hrs |
|---|---|---|---|
| **A: DevOps** | T-001, T-003, T-004, T-005, T-006, T-015, T-016 | 8.5 | **5** |
| **B: Software Eng** | T-007, T-008, T-011, T-012, T-013, T-014 | 9 | **5** |
| **C: UX** | T-002, T-010, T-017, T-018, T-019, T-020 | 5.5 | **3** |
| **D: PM** | T-009, T-021, T-022, T-023, T-024 | 7 | **3.5** |
| | | **44 hrs** | **~12 hrs** (2 days) |

> **Savings: 44 hrs → 12 hrs wall-clock (73% reduction)**

---

## 🗓️ Phase 2: INFRASTRUCTURE + SECURITY (Week 2-3) — 90 hrs → 28 hrs wall-clock

> **Key insight**: Sprint 2 (Infra) and Sprint 4 (Security) have ZERO dependencies
> between them. Run them in parallel. Also fold in Sprint 3 (Feedback) partially.

### Dependency Graph

```
WEEK 2 (Day 3-7) — 4 streams parallel:

  Stream A (DevOps)             Stream B (Software Eng)       Stream C (UX)              Stream D (PM)
  ┌─────────────────────┐      ┌─────────────────────┐     ┌─────────────────────┐    ┌─────────────────────┐
  │ SPRINT 2: SCHEDULER  │      │ SPRINT 4: AUTH       │     │ SPRINT 3: FEEDBACK   │    │ SPRINT 2: ALERTS    │
  │ T-025 Collector       │      │ T-054 Registration   │     │ T-043 Feedback dash   │    │ T-029 Alert consumer│
  │   scheduler (XL)      │      │ T-055 JWT login      │     │ T-044 FeedbackAgent   │    │ T-030 Email alerts   │
  │ T-026 Retry logic     │      │ T-056 JWT middleware  │     │ T-045 Orchestrator    │    │ T-031 Slack alerts   │
  │ T-028 Docker service  │      │ T-058 Auth tests      │     │   reads feedback      │    │ T-033 Dead letter Q  │
  │ T-034 WebSocket push  │      │                       │     │ T-047 GlitchTip deploy│    │ T-035 WS heartbeat   │
  │ T-027 Collection API  │      │ SPRINT 4: SECURITY    │     │ T-048 Sentry SDK      │    │ T-036 Score delta    │
  │                        │      │ T-059 Rate limiting   │     │ T-049 Uptime monitor  │    │ T-046 Weekly report  │
  │ SPRINT 2: ACCURACY    │      │ T-060 Security hdrs   │     │                       │    │                       │
  │ T-037 Score accuracy   │      │ T-061 Input valid.    │     │ SPRINT 3: PERF        │    │ SPRINT 2: TESTS      │
  │ T-038 Tune weights     │      │ T-063 Remove secrets  │     │ T-050 Search <500ms   │    │ T-040 API tests (XL)  │
  │ T-039 Accuracy API     │      │ T-062 Docker harden   │     │ T-051 Dashboard <3s   │    │ T-041 Scorer tests    │
  │                        │      │ T-064 CI security     │     │ T-052 Chat <5s        │    │ T-042 DB tests        │
  └──────────┬──────────┘      └──────────┬──────────┘     └──────────┬──────────┘    └──────────┬──────────┘
             │                            │                            │                         │
  WALL: 16 hrs                     WALL: 13 hrs                  WALL: 13 hrs               WALL: 16 hrs
```

### Phase 2 Task Assignment

| Stream | Tasks | Sequential Hrs | Parallel Wall Hrs |
|---|---|---|---|
| **A: DevOps** | T-025, T-026, T-028, T-034, T-027, T-037, T-038, T-039 | 24 | **16** |
| **B: Software Eng** | T-054, T-055, T-056, T-058, T-059, T-060, T-061, T-062, T-063, T-064 | 24 | **13** |
| **C: UX** | T-043, T-044, T-045, T-047, T-048, T-049, T-050, T-051, T-052, T-053 | 25 | **13** |
| **D: PM** | T-029, T-030, T-031, T-033, T-035, T-036, T-040, T-041, T-042, T-046 | 26 | **16** |
| | | **90 hrs** | **~28 hrs** (4-5 days) |

> **Savings: Sprint 2+3+4 = 122 hrs → 28 hrs wall-clock (77% reduction)**

---

## 🗓️ Phase 3: WATCHLISTS + EXPORT + BILLING (Week 4-5) — 102 hrs → 30 hrs wall-clock

> **Key insight**: Sprint 5 (Watchlists), Sprint 6 (Export), Sprint 7 (Billing) 
> are independent features. Run all three in parallel.

### Dependency Graph

```
WEEK 4-5 (Day 8-14) — 4 streams parallel:

  Stream A (DevOps)             Stream B (Software Eng)       Stream C (UX)              Stream D (PM)
  ┌─────────────────────┐      ┌─────────────────────┐     ┌─────────────────────┐    ┌─────────────────────┐
  │ SPRINT 7: BILLING    │      │ SPRINT 5: WATCHLISTS │     │ SPRINT 6: EXPORT     │    │ AGENT CLEANUP       │
  │ T-084 Stripe checkout│      │ T-065 Watchlist CRUD │     │ T-074 CSV export     │    │ T-081 Cut 6 agents  │
  │   (XL)               │      │ T-066 Dashboard view │     │ T-075 PDF export     │    │ T-082 Merge agents  │
  │ T-085 Subscription   │      │ T-067 Notes          │     │ T-076 Watchlist CSV  │    │ T-083 Test agents    │
  │   management         │      │ T-068 Tags           │     │                       │    │   (XL)              │
  │ T-086 Stripe webhooks│      │ T-069 Score alerts   │     │ SPRINT 6: INTEGRATE   │    │                       │
  │ T-087 Gate Pro feat. │      │ T-070 High-score     │     │ T-077 Webhook alerts  │    │ DOCS                 │
  │ T-088 Pro rate limit │      │   alerts             │     │ T-078 Zapier endpoint │    │ T-079 Contrib guide  │
  │                       │      │ T-071 Alert config   │     │ T-080 API docs        │    │ T-095 Getting started│
  │ PRO FEATURES         │      │ T-072 Daily digest   │     │                       │    │ T-096 Arch diagram   │
  │ T-089 Score charts   │      │ T-073 Alert history  │     │                       │    │                       │
  │ T-090 Search filters │      │                       │     │                       │    │                       │
  │ T-091 Priority       │      │                       │     │                       │    │                       │
  └──────────┬──────────┘      └──────────┬──────────┘     └──────────┬──────────┘    └──────────┬──────────┘
             │                            │                            │                         │
  WALL: 21 hrs                     WALL: 21 hrs                  WALL: 9 hrs              WALL: 20 hrs
```

### Phase 3 Task Assignment

| Stream | Tasks | Sequential Hrs | Parallel Wall Hrs |
|---|---|---|---|
| **A: DevOps** | T-084, T-085, T-086, T-087, T-088, T-089, T-090, T-091 | 29 | **21** |
| **B: Software Eng** | T-065, T-066, T-067, T-068, T-069, T-070, T-071, T-072, T-073 | 28 | **21** |
| **C: UX** | T-074, T-075, T-076, T-077, T-078, T-080 | 13 | **9** |
| **D: PM** | T-081, T-082, T-083, T-079, T-095, T-096 | 20 | **20** |
| | | **102 hrs** | **~30 hrs** (5 days) |

> **Savings: Sprint 5+6+7 = 102 hrs → 30 hrs wall-clock (71% reduction)**

---

## 🗓️ Phase 4: POLISH + V1 RELEASE (Week 6) — 48 hrs → 14 hrs wall-clock

### Dependency Graph

```
WEEK 6 (Day 15-18) — 4 streams parallel:

  Stream A (DevOps)             Stream B (Software Eng)       Stream C (UX)              Stream D (PM)
  ┌─────────────────────┐      ┌─────────────────────┐     ┌─────────────────────┐    ┌─────────────────────┐
  │ T-099 Fix all P0/P1  │      │ T-100 Test coverage  │     │ T-092 Mobile dash    │    │ T-097 Release notes  │
  │   bugs (L)           │      │   (XL)               │     │ T-093 Dark mode      │    │ T-098 Audit docs     │
  │ T-101 Ruff lint      │      │ T-103 CI/CD pipeline │     │ T-094 Perf mobile    │    │ T-102 Tag v1.0.0     │
  │ T-107 GDPR endpoints │      │ T-057 API key mgmt   │     │ T-105 Privacy policy  │    │ T-104 Launch plan    │
  │                       │      │                       │     │ T-106 Terms of service│    │                       │
  └──────────┬──────────┘      └──────────┬──────────┘     └──────────┬──────────┘    └──────────┬──────────┘
             │                            │                            │                         │
  WALL: 12 hrs                     WALL: 14 hrs                  WALL: 11 hrs               WALL: 7 hrs

SYNC POINT: All streams converge → T-102 Tag V1.0.0 → T-103 CI/CD → 🚀 LAUNCH
```

### Phase 4 Task Assignment

| Stream | Tasks | Sequential Hrs | Parallel Wall Hrs |
|---|---|---|---|
| **A: DevOps** | T-099, T-101, T-107 | 12 | **12** |
| **B: Software Eng** | T-100, T-103, T-057 | 18 | **14** |
| **C: UX** | T-092, T-093, T-094, T-105, T-106 | 15 | **11** |
| **D: PM** | T-097, T-098, T-102, T-104 | 12 | **7** |
| | | **48 hrs** | **~14 hrs** (2-3 days) |

> **Savings: Sprint 8 = 48 hrs → 14 hrs wall-clock (71% reduction)**

---

## 📊 Summary: Original vs Parallel

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  ORIGINAL SEQUENTIAL PLAN:                                              │
│  ─────────────────────────                                              │
│  Sprint 1:  44 hrs  │████████████████████████                          │
│  Sprint 2:  62 hrs  │███████████████████████████████████████           │
│  Sprint 3:  32 hrs  │████████████████                                  │
│  Sprint 4:  28 hrs  │█████████████                                     │
│  Sprint 5:  28 hrs  │█████████████                                     │
│  Sprint 6:  40 hrs  │███████████████████                               │
│  Sprint 7:  34 hrs  │████████████████                                  │
│  Sprint 8:  48 hrs  │█████████████████████████                         │
│                      ──────────────────────────────────────             │
│  TOTAL:   316 hrs   │ 16 weeks sequential                             │
│                                                                         │
│                                                                         │
│  PARALLEL PLAN:                                                         │
│  ──────────────                                                         │
│  Phase 1:  12 hrs   │██████   ← Week 1 (Sprint 1)                     │
│  Phase 2:  28 hrs   │██████████████  ← Week 2-3 (Sprint 2+3+4)       │
│  Phase 3:  30 hrs   │███████████████ ← Week 4-5 (Sprint 5+6+7)       │
│  Phase 4:  14 hrs   │███████   ← Week 6 (Sprint 8)                    │
│                      ──────────────────────────────────────             │
│  TOTAL:    84 hrs   │ 6 weeks wall-clock                               │
│  (work hours spread across 4 parallel streams = 316 hrs effort)       │
│                                                                         │
│                                                                         │
│  ┌─────────────────────────────────────────────────────┐               │
│  │                                                     │               │
│  │  METRIC          ORIGINAL      PARALLEL    SAVED    │               │
│  │  ─────────────────────────────────────────────────  │               │
│  │  Wall-clock      16 weeks      6 weeks     62% ↓    │               │
│  │  Calendar        112 days      42 days     63% ↓    │               │
│  │  To MVP          2 weeks       2 days      86% ↓    │               │
│  │  To Auth         8 weeks       3 weeks     63% ↓    │               │
│  │  To Billing      14 weeks      5 weeks     64% ↓    │               │
│  │  To V1 Release   16 weeks      6 weeks     63% ↓    │               │
│  │                                                     │               │
│  └─────────────────────────────────────────────────────┘               │
│                                                                         │
│  WORK EFFORT IS THE SAME (316 hrs).                                    │
│  BUT IT'S DISTRIBUTED ACROSS 4 PARALLEL STREAMS.                      │
│  WALL-CLOCK TIME IS WHAT MATTERS FOR LAUNCH.                           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🔀 Sync Points & Integration Gates

Parallel work needs coordination. Here are the mandatory sync points:

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│  SYNC 1: End of Phase 1 (Day 2)                                        │
│  ────────────────────────────────                                       │
│  ✅ All tests pass (Stream B)                                           │
│  ✅ Docker services verified (Stream A)                                 │
│  ✅ VPS deployed + HTTPS (Stream A)                                     │
│  ✅ Seed data loaded (Stream B)                                         │
│  ✅ Feedback system live (Stream C)                                     │
│  → GATE: Full flow test T-022 must pass before proceeding              │
│                                                                          │
│  SYNC 2: End of Phase 2 (Day 7)                                        │
│  ────────────────────────────────                                       │
│  ✅ Scheduler runs 24/7 (Stream A)                                     │
│  ✅ Auth system working (Stream B)                                      │
│  ✅ Feedback dashboard live (Stream C)                                  │
│  ✅ Alerts firing (Stream D)                                            │
│  → GATE: Integration test — auth + scheduler + alerts must pass        │
│                                                                          │
│  SYNC 3: End of Phase 3 (Day 14)                                       │
│  ────────────────────────────────                                       │
│  ✅ Stripe checkout working (Stream A)                                  │
│  ✅ Watchlists functional (Stream B)                                    │
│  ✅ CSV/PDF export working (Stream C)                                   │
│  ✅ Agent cleanup done (Stream D)                                       │
│  → GATE: E2E test — signup → pay → watchlist → export → alert         │
│                                                                          │
│  SYNC 4: End of Phase 4 (Day 18) — V1 LAUNCH                           │
│  ────────────────────────────────                                       │
│  ✅ 0 P0/P1 bugs (Stream A)                                            │
│  ✅ ≥ 80% test coverage (Stream B)                                     │
│  ✅ Mobile responsive (Stream C)                                        │
│  ✅ All docs current (Stream D)                                         │
│  → GATE: Tag v1.0.0 + CI/CD green → LAUNCH 🚀                         │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 📋 Daily Execution Schedule

### Phase 1 (Week 1: Days 1-2)

| Hour | Stream A (DevOps) | Stream B (SWE) | Stream C (UX) | Stream D (PM) |
|---|---|---|---|---|
| **Day 1** | | | | |
| 0-1 | T-001 Git commit | T-007 Fix tests | T-002 LICENSE | T-009 .env.example |
| 1-2 | T-003 .gitignore | T-007 Fix tests | T-010 .env.example | T-021 Launch post draft |
| 2-3 | T-004 Backup cron | T-008 Fix warnings | T-017 Passwords | T-023 HN post |
| 3-4 | T-005 Restore | T-008 Fix warnings | T-018 Health monitor | T-024 Reddit post |
| 4-5 | T-006 Verify backup | — | — | — |
| **Day 2** | | | | |
| 5-7 | T-015 Deploy VPS | T-011 Seed data | T-019 Feedback sys | T-020 Analytics |
| 7-8 | T-016 HTTPS | T-012 Test search | T-019 Feedback sys | T-022 Demo GIF |
| 8-9 | — | T-013 Test chat | — | — |
| 9-10 | — | T-014 Test failure | — | — |
| 10-12 | **SYNC: Full flow test + Launch** | | | |

### Phase 2 (Week 2-3: Days 3-7)

| Day | Stream A (DevOps) | Stream B (SWE) | Stream C (UX) | Stream D (PM) |
|---|---|---|---|---|
| **Day 3** | T-025 Scheduler (start) | T-054 Registration | T-043 Feedback dash | T-029 Alert consumer |
| **Day 4** | T-025 Scheduler (cont) | T-055 JWT login | T-044 FeedbackAgent | T-030 Email alerts |
| **Day 5** | T-026 Retry + T-028 Docker | T-056 JWT middleware | T-045 Orch reads fb | T-031 Slack alerts |
| **Day 6** | T-034 WebSocket push | T-059 Rate limiting | T-047 GlitchTip | T-033 Dead letter Q |
| **Day 6** | T-027 Collection API | T-060 Security headers | T-048 Sentry SDK | T-035 WS heartbeat |
| **Day 7** | T-037 Score accuracy | T-061 Input validation | T-049 Uptime monitor | T-036 Score delta |
| **Day 7** | T-038 Tune weights | T-063 Remove secrets | T-050 Search perf | T-040 API tests |
| **Day 7** | T-039 Accuracy API | T-062 Docker harden | T-051 Dash perf | T-041 Scorer tests |
| **Day 7** | — | T-064 CI security | T-052 Chat perf | T-042 DB tests |
| **Day 7** | — | T-058 Auth tests | T-053 Perf tracking | T-046 Weekly report |
| | **SYNC: Auth + Scheduler + Alerts integration test** | | | |

### Phase 3 (Week 4-5: Days 8-14)

| Day | Stream A (DevOps) | Stream B (SWE) | Stream C (UX) | Stream D (PM) |
|---|---|---|---|---|
| **Day 8** | T-084 Stripe (start) | T-065 Watchlist CRUD | T-074 CSV export | T-081 Cut 6 agents |
| **Day 9** | T-084 Stripe (cont) | T-066 Dashboard view | T-075 PDF export | T-082 Merge agents |
| **Day 10** | T-085 Subscriptions | T-067 Notes + T-068 Tags | T-076 Watchlist CSV | T-083 Test agents |
| **Day 11** | T-086 Webhooks | T-069 Score alerts | T-077 Webhook alerts | T-083 Test agents |
| **Day 12** | T-087 Gate Pro | T-070 High-score alerts | T-078 Zapier | T-079 Contrib guide |
| **Day 13** | T-088 Rate limit | T-071 Alert config | T-080 API docs | T-095 Getting started |
| **Day 14** | T-089 Score charts | T-072 Daily digest | — | T-096 Arch diagram |
| **Day 14** | T-090 Search filters | T-073 Alert history | — | — |
| **Day 14** | T-091 Priority support | — | — | — |
| | **SYNC: E2E — signup → pay → watchlist → export → alert** | | | |

### Phase 4 (Week 6: Days 15-18)

| Day | Stream A (DevOps) | Stream B (SWE) | Stream C (UX) | Stream D (PM) |
|---|---|---|---|---|
| **Day 15** | T-099 Fix P0/P1 bugs | T-100 Test coverage | T-092 Mobile dash | T-097 Release notes |
| **Day 16** | T-099 Fix bugs | T-100 Coverage | T-093 Dark mode | T-098 Audit docs |
| **Day 17** | T-101 Ruff lint | T-103 CI/CD | T-094 Perf mobile | T-104 Launch plan |
| **Day 18** | T-107 GDPR endpoints | T-057 API key mgmt | T-105 Privacy + T-106 Terms | T-102 Tag v1.0.0 |
| | **🚀 V1.0.0 LAUNCH** | | | |

---

## 🎯 Which Agent Handles What

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│  Stream A → 🛠️  DevOps Engineer Agent                                  │
│  Focus: Infrastructure, deployment, Docker, CI/CD, security ops         │
│  Runs: T-001,003-006, T-015-018, T-025-028, T-034, T-037-039,         │
│        T-084-091, T-099, T-101, T-107                                  │
│                                                                          │
│  Stream B → 💻  Software Engineer Agent                                 │
│  Focus: Core logic, tests, data pipeline, accuracy, auth                │
│  Runs: T-007-008, T-011-014, T-054-058, T-059-064, T-065-073,         │
│        T-100, T-103                                                     │
│                                                                          │
│  Stream C → 🎨  UX Designer Agent                                       │
│  Focus: UI, dashboard, feedback, performance, export, mobile            │
│  Runs: T-002, T-010, T-019-020, T-043-053, T-074-080,                 │
│        T-092-094, T-105-106                                            │
│                                                                          │
│  Stream D → 📋  Product Manager Agent                                   │
│  Focus: Documentation, launch, analytics, agent cleanup, reports        │
│  Runs: T-009, T-021-024, T-029-033, T-035-036, T-040-042,             │
│        T-046, T-081-083, T-079, T-095-098, T-102, T-104               │
│                                                                          │
│  Supporting Agents (on-demand):                                         │
│  • QA Engineer → Runs integration tests at each sync point              │
│  • Solution Architect → Reviews code quality at sync points             │
│  • Business Analyst → Tracks metrics, validates feature completeness    │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## ⚠️ Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Merge conflicts between streams | Medium | Each stream works on different files; sync at merge points |
| Stream B blocked waiting for Stream A | Low | Stream B can mock APIs/dev deps until Stream A delivers |
| Auth (Stream B) needed by Watchlists (Phase 3) | Medium | Phase 2 completes auth before Phase 3 starts watchlists |
| Stripe test mode issues | Low | Start Stripe in Phase 3 with plenty of buffer |
| Agent execution timeouts | Low | Each task is ≤ XL (16 hrs); monitor with project_monitor agent |
| Bus factor = 1 still | High | Document everything; 4 agents provide redundancy on knowledge |

---

## 🏁 Bottom Line

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│   ORIGINAL:   ████ 16 weeks ████ 316 hours sequential           │
│                                                                  │
│   PARALLEL:   ██ 6 weeks ██ 84 wall-hours (4 streams)           │
│                                                                  │
│   ┌──────────────────────────────────────────────┐               │
│   │  TIME TO MVP:     2 weeks → 2 days   (86%↓) │               │
│   │  TIME TO V1:      16 weeks → 6 weeks  (63%↓) │               │
│   │  WALL-CLOCK HRS:  316 hrs → 84 hrs    (73%↓) │               │
│   │  TOTAL EFFORT:    316 hrs (same — distributed)│               │
│   └──────────────────────────────────────────────┘               │
│                                                                  │
│   The work doesn't decrease — it overlaps.                       │
│   4 agents working in parallel = 4× throughput.                  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```
