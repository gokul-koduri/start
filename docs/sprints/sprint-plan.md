# Sprint Plan — 8 Sprints, 16 Weeks

## Sprint Overview

| Sprint | Theme | Duration | Tasks | Hours |
|---|---|---|---|---|
| 1 | Launch MVP | Week 1-2 | 24 | 44 |
| 2 | Core Infrastructure | Week 3-4 | 16 | 62 |
| 3 | Feedback + Analytics | Week 5-6 | 14 | 42 |
| 4 | Auth + Security | Week 7-8 | 14 | 48 |
| 5 | Watchlists + Alerts | Week 9-10 | 12 | 36 |
| 6 | Export + Integrations | Week 11-12 | 12 | 38 |
| 7 | Pro Tier + Billing | Week 13-14 | 10 | 34 |
| 8 | Polish + V1 Release | Week 15-16 | 9 | 22 |

## Sprint 1: Launch MVP (Week 1-2) — 44 hours

### Tasks

| ID | Task | Hours | Priority | Status |
|---|---|---|---|---|
| T-001 | Git add all untracked files, commit, push | 0.5 | P0 | TODO |
| T-002 | Create LICENSE file (MIT) | 0.5 | P0 | TODO |
| T-003 | Audit and update .gitignore | 1 | P0 | TODO |
| T-004 | Create daily backup cron job | 1 | P0 | TODO |
| T-005 | Test backup/restore scripts | 1 | P0 | TODO |
| T-006 | Verify all Docker services start | 1 | P0 | TODO |
| T-007 | Fix 12 failing tests in test_semantic_search.py | 2 | P0 | ✅ DONE |
| T-008 | Fix 125 pytest warnings | 2 | P1 | ✅ DONE (0 warnings) |
| T-009 | Create .env.example with all variables | 1 | P0 | TODO |
| T-010 | Add startup secrets validation | 1 | P0 | TODO |
| T-011 | Load seed data into MySQL | 2 | P0 | TODO |
| T-012 | Test search endpoint with seed data | 1 | P0 | TODO |
| T-013 | Test chat endpoint with Ollama | 2 | P0 | TODO |
| T-014 | Test failure patterns visualization | 1 | P0 | TODO |
| T-015 | Deploy to VPS with Docker Compose | 3 | P0 | TODO |
| T-016 | Set up HTTPS with Caddy | 2 | P0 | TODO |
| T-017 | Add Google Analytics / Plausible | 1 | P1 | TODO |
| T-018 | Add feedback button to Streamlit | 1 | P1 | TODO |
| T-019 | Add feedback API endpoint | 1 | P1 | TODO |
| T-020 | Create GitHub Discussions for feedback | 0.5 | P1 | TODO |
| T-021 | Write launch blog post / HN comment | 2 | P1 | TODO |
| T-022 | Test full flow: search → score → chat → feedback | 2 | P0 | TODO |
| T-023 | Launch on Hacker News | 1 | P1 | TODO |
| T-024 | Launch on Reddit (r/startups, r/SideProject) | 1 | P1 | TODO |

### Sprint 1 Definition of Done

- [ ] All 699 tests pass (0 failures)
- [ ] Docker Compose starts all 11 services
- [ ] Search returns results from seed data
- [ ] Chat responds via Ollama
- [ ] Deployed to VPS with HTTPS
- [ ] Feedback collection working
- [ ] Launched on HN + Reddit

---

*See WORK_PLAN.md for full Sprint 2-8 details.*
