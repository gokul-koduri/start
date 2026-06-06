# Product Requirements Document

## Product Vision

The **Opportunity Intelligence Platform (OIP)** is an open-source, self-hosted, real-time,
multi-agent alternative to Crunchbase/PitchBook/Tracxn. It helps investors, analysts,
and entrepreneurs discover revival opportunities in failed startup sectors.

## MVP Scope (2 Weeks)

### Must-Have (P0)
1. **Score a startup** — Composite scoring from multiple signals
2. **Chat with data** — AI chat about failure patterns
3. **Failure patterns** — Deep analysis of why startups fail
4. **Search** — Find startups, signals, entities
5. **Collector Scheduler** — 24/7 continuous data collection
6. **Alert Consumer** — Kafka → Slack/email notifications
7. **WebSocket Score Push** — Real-time score updates

### Should-Have (P1)
8. **User auth** — Register, login, JWT tokens
9. **Rate limiting** — Prevent API abuse
10. **Security headers** — HTTPS, CSP, CORS whitelist
11. **Input validation** — Pydantic models on all endpoints

### Nice-to-Have (P2)
12. **Watchlists** — Track favorite startups
13. **CSV export** — Download data
14. **Feedback system** — Rate scores, request features

## Success Metrics

| Metric | Target (Month 1) | Target (Month 3) |
|---|---|---|
| Registered users | 50 | 500 |
| Weekly active users | 20 | 200 |
| Searches/day | 100 | 1,000 |
| Chat messages/day | 50 | 500 |
| Score feedback count | 20 | 200 |
| Pro subscribers | 0 | 5 |

## Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Score accuracy too low | HIGH | Measure against known outcomes, iterate |
| Ollama too slow for chat | MEDIUM | Add loading indicator, consider smaller model |
| Scope creep | HIGH | Strict MVP, defer everything else |
| No users | HIGH | Launch on HN/Reddit, collect feedback |
| MySQL data loss | CRITICAL | Daily backups, backup encryption |

*See PROBLEM_DEFINITION.md and GOALS_AND_PRIORITIES.md for full details.*
