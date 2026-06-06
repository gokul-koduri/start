# 🧪 Test Early and Often — Testing Strategy for Every Stage

> "Finding bugs early is much cheaper than fixing them later.
>  A bug caught in development costs $1.
>  A bug caught in testing costs $10.
>  A bug caught in production costs $100."

---

## The Current State (Audit Results — June 5, 2026)

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  TEST INVENTORY:                                                     │
│                                                                      │
│  Test files:         56                                              │
│  Test functions:     699                                             │
│  Pass rate:          98.3% (687 passed, 12 failed)                  │
│  Execution time:     1.4 seconds (entire suite)                     │
│  Warnings:           125 (mostly deprecation)                       │
│                                                                      │
│  WHAT'S GOOD:                                                        │
│  ✅ 699 tests exist and run in 1.4 seconds                         │
│  ✅ 98.3% pass rate                                                │
│  ✅ Shared conftest.py with auto-mock for pymysql                  │
│  ✅ GitHub Actions CI (daily-pipeline.yml + deploy.yml)            │
│  ✅ MySQL service container in CI                                   │
│  ✅ Phase integration tests exist (P4, P5, P6)                     │
│                                                                      │
│  WHAT'S BROKEN:                                                      │
│  ❌ 12 failing tests (test_semantic_search.py)                     │
│  ❌ 52 of 54 agents have NO test files                             │
│  ❌ api_server.py (34 endpoints) has ZERO tests                    │
│  ❌ db/schema.py (76 tables) has ZERO tests                        │
│  ❌ stream/ (4 modules) has only 1 test file                       │
│  ❌ NO performance tests                                            │
│  ❌ NO user acceptance tests (UAT)                                  │
│  ❌ NO end-to-end (E2E) tests                                      │
│  ❌ NO load/stress tests                                            │
│  ❌ NO test coverage measurement (no coverage.py)                  │
│  ❌ NO test gates on deploy (deploy.yml ignores test results)      │
│  ❌ CI runs pipeline but does NOT run tests                        │
│  ❌ No pytest.ini or pyproject.toml test config                    │
│                                                                      │
│  COVERAGE ESTIMATE:                                                  │
│  699 tests / 185 Python files ≈ 3.8 tests/file average             │
│  But 52 agents untested = ~28% of code has zero test coverage     │
│  Estimated line coverage: ~15-20%                                   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Part 1: Testing Parameters by Stage

---

### 1.1 The Testing Pyramid for OIP

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│                    ╱╲                                                │
│                   ╱  ╲         PERFORMANCE TESTS                    │
│                  ╱ E2E╲        Target: 10 tests                     │
│                 ╱ UAT  ╲       Run: Weekly                          │
│                ╱────────╲      Speed: 2-10 min each                 │
│               ╱          ╲                                            │
│              ╱ INTEGRATION╲    Target: 150 tests                    │
│             ╱   TESTS      ╲   Run: Every commit                    │
│            ╱────────────────╲  Speed: 5-30 sec each                 │
│           ╱                  ╲                                        │
│          ╱    UNIT TESTS      ╲  Target: 700+ tests                 │
│         ╱    (fast, isolated)  ╲ Run: Every save                    │
│        ╱────────────────────────╲ Speed: < 0.1 sec each            │
│                                                                      │
│  RATIO:  70% Unit : 20% Integration : 10% E2E/Performance          │
│                                                                      │
│  CURRENT:  699 Unit + Integration : 0 E2E : 0 Performance          │
│  TARGET:   700 Unit : 150 Integration : 10 E2E : 10 Performance   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 1.2 Stage-by-Stage Testing Parameters

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  STAGE 1: WRITE CODE (Development)                                  │
│  ═══════════════════════════════════                                 │
│                                                                      │
│  What:     Unit tests                                                │
│  When:     Before OR immediately after writing each function         │
│  Who:      Developer                                                 │
│  Speed:    < 100ms per test                                          │
│  Target:   Every public function has at least 1 test                │
│  Coverage: New code ≥ 80% line coverage                             │
│  Run:      Every file save (IDE integration or watch mode)           │
│                                                                      │
│  PARAMETERS:                                                         │
│  ┌────────────────────────────────────────────────────────────┐      │
│  │  P1.1: Every agent has a test file                        │      │
│  │        tests/test_<agent_name>.py exists for every agent   │      │
│  │        Minimum: 3 tests per agent (happy, sad, edge)      │      │
│  │                                                            │      │
│  │  P1.2: Every API endpoint has a test                      │      │
│  │        tests/test_api_endpoints.py covers all 34 routes    │      │
│  │        Minimum: 2 tests per endpoint (success + error)    │      │
│  │                                                            │      │
│  │  P1.3: Every utility function has a test                  │      │
│  │        tests/test_text_normalization.py (23 tests ✅)      │      │
│  │        tests/test_date_parsing.py (12 tests ✅)            │      │
│  │                                                            │      │
│  │  P1.4: No external dependencies in unit tests             │      │
│  │        All DB calls mocked (conftest.py does this ✅)     │      │
│  │        All API calls mocked                                │      │
│  │        All Ollama calls mocked                             │      │
│  │                                                            │      │
│  │  P1.5: Tests run in < 2 seconds total                     │      │
│  │        Current: 1.4 seconds ✅                             │      │
│  │                                                            │      │
│  │  P1.6: New code cannot merge without passing tests        │      │
│  │        CI must run tests before merge                      │      │
│  └────────────────────────────────────────────────────────────┘      │
│                                                                      │
│  STAGE 2: COMMIT CODE (Pre-Commit)                                  │
│  ═══════════════════════════════                                     │
│                                                                      │
│  What:     Unit + Integration tests                                  │
│  When:    Before every git commit                                    │
│  Who:      Developer (automated via git hook or manual)              │
│  Speed:    < 5 seconds                                               │
│  Target:   100% pass rate (zero failures before commit)             │
│                                                                      │
│  PARAMETERS:                                                         │
│  ┌────────────────────────────────────────────────────────────┐      │
│  │  P2.1: All 699+ tests pass before commit                  │      │
│  │        python -m pytest tests/ -q → 0 failed              │      │
│  │                                                            │      │
│  │  P2.2: Fix failing tests BEFORE committing new code       │      │
│  │        Currently 12 failing in test_semantic_search.py    │      │
│  │        FIX THESE FIRST                                    │      │
│  │                                                            │      │
│  │  P2.3: No test warnings > 0 in new code                   │      │
│  │        Current: 125 warnings — reduce to < 20             │      │
│  │                                                            │      │
│  │  P2.5: Run only affected tests for speed                  │      │
│  │        Changed agents/opportunity_scorer.py?              │      │
│  │        → pytest tests/test_opportunity_scorer.py          │      │
│  └────────────────────────────────────────────────────────────┘      │
│                                                                      │
│  STAGE 3: PUSH TO GITHUB (CI/CD Pipeline)                           │
│  ═══════════════════════════════                                     │
│                                                                      │
│  What:     Full test suite + linting + type checking                 │
│  When:    Every push to GitHub                                       │
│  Who:      GitHub Actions (automated)                                │
│  Speed:    < 3 minutes                                               │
│  Target:   All tests pass + lint clean + type check clean            │
│                                                                      │
│  PARAMETERS:                                                         │
│  ┌────────────────────────────────────────────────────────────┐      │
│  │  P3.1: GitHub Actions runs tests on every push            │      │
│  │        Currently: NO ❌ (only runs pipeline, not tests)    │      │
│  │        Need: test workflow in .github/workflows/test.yml  │      │
│  │                                                            │      │
│  │  P3.2: Test against Python 3.12                           │      │
│  │        One version for now (add 3.13 later)               │      │
│  │                                                            │      │
│  │  P3.3: MySQL service container for integration tests      │      │
│  │        Already configured in daily-pipeline.yml ✅        │      │
│  │                                                            │      │
│  │  P3.4: Upload test results as artifact                    │      │
│  │        JUnit XML for test history tracking                 │      │
│  │                                                            │      │
│  │  P3.5: Block merge if tests fail (when using PRs)         │      │
│  │        Branch protection: require status checks            │      │
│  └────────────────────────────────────────────────────────────┘      │
│                                                                      │
│  STAGE 4: PRE-DEPLOY (Acceptance)                                   │
│  ═══════════════════════════                                         │
│                                                                      │
│  What:     Integration tests + smoke tests                          │
│  When:    Before deploying to demo server                            │
│  Who:      Developer (manual trigger)                                │
│  Speed:    < 5 minutes                                               │
│  Target:   All critical paths work end-to-end                        │
│                                                                      │
│  PARAMETERS:                                                         │
│  ┌────────────────────────────────────────────────────────────┐      │
│  │  P4.1: Docker compose up succeeds                         │      │
│  │        All 11 services start healthy                      │      │
│  │                                                            │      │
│  │  P4.2: API responds to health check                       │      │
│  │        curl http://localhost:8000/health → 200            │      │
│  │                                                            │      │
│  │  P4.3: Score a startup works                               │      │
│  │        curl -X POST /api/score-a-startup → 200            │      │
│  │                                                            │      │
│  │  P4.4: Chat endpoint responds                              │      │
│  │        curl -X POST /api/chat → 200 (may be slow)        │      │
│  │                                                            │      │
│  │  P4.5: Dashboard loads                                     │      │
│  │        curl http://localhost:8000/site/ → 200             │      │
│  │                                                            │      │
│  │  P4.6: Database has seed data                              │      │
│  │        SELECT COUNT(*) FROM failed_startups > 0           │      │
│  └────────────────────────────────────────────────────────────┘      │
│                                                                      │
│  STAGE 5: POST-DEPLOY (Smoke Tests on Live)                         │
│  ═══════════════════════════════                                     │
│                                                                      │
│  What:     Smoke tests against live server                           │
│  When:    After every deploy                                         │
│  Who:      Automated (cron or deploy script)                         │
│  Speed:    < 30 seconds                                              │
│  Target:   All 5 critical endpoints respond                          │
│                                                                      │
│  PARAMETERS:                                                         │
│  ┌────────────────────────────────────────────────────────────┐      │
│  │  P5.1: Health check passes on live server                 │      │
│  │        curl https://demo.opportunity-intel.org/health     │      │
│  │                                                            │      │
│  │  P5.2: Search returns results                              │      │
│  │        curl /api/search?q=tesla → has results             │      │
│  │                                                            │      │
│  │  P5.3: Score returns a number                              │      │
│  │        curl /api/opportunities/Fisker → score exists      │      │
│  │                                                            │      │
│  │  P5.4: Response time < 2 seconds for search               │      │
│  │        curl -w "%{time_total}" → < 2.0                    │      │
│  │                                                            │      │
│  │  P5.5: No 500 errors on any public page                   │      │
│  │        curl / → 200, curl /site/ → 200, curl /api/ → 200 │      │
│  └────────────────────────────────────────────────────────────┘      │
│                                                                      │
│  STAGE 6: WEEKLY (Regression + Performance)                         │
│  ═════════════════════════════                                       │
│                                                                      │
│  What:     Full regression + performance baseline                    │
│  When:    Weekly (every Monday)                                      │
│  Who:      GitHub Actions (automated)                                │
│  Speed:    < 15 minutes                                              │
│  Target:   No regressions, performance within 20% of baseline       │
│                                                                      │
│  PARAMETERS:                                                         │
│  ┌────────────────────────────────────────────────────────────┐      │
│  │  P6.1: Full test suite still passes                       │      │
│  │        All 699+ tests pass                                 │      │
│  │                                                            │      │
│  │  P6.2: API response time regression check                 │      │
│  │        /api/search < 500ms (p95)                           │      │
│  │        /api/score-a-startup < 2s (p95)                    │      │
│  │        /api/chat < 30s (p95)                               │      │
│  │                                                            │      │
│  │  P6.3: Score accuracy check                               │      │
│  │        Score known startups → verify within expected range │      │
│  │        Fisker: expect score 40-70, risk > 0.3             │      │
│  │        Northvolt: expect score 20-50, risk > 0.5          │      │
│  │                                                            │      │
│  │  P6.4: Data freshness check                               │      │
│  │        Newest signal < 24 hours old                        │      │
│  │        Collector ran successfully in last 6 hours         │      │
│  └────────────────────────────────────────────────────────────┘      │
│                                                                      │
│  STAGE 7: MONTHLY (Load + Security)                                 │
│  ═══════════════════════════                                         │
│                                                                      │
│  What:     Load tests + security scan                               │
│  When:    Monthly (first Monday)                                     │
│  Who:      Developer (manual or automated)                           │
│  Speed:    < 30 minutes                                              │
│  Target:   System handles 100 concurrent users without errors       │
│                                                                      │
│  PARAMETERS:                                                         │
│  ┌────────────────────────────────────────────────────────────┐      │
│  │  P7.1: Load test: 100 concurrent users                    │      │
│  │        Use locust or k6 to simulate traffic               │      │
│  │        Target: < 1% error rate, < 2s p95 response         │      │
│  │                                                            │      │
│  │  P7.2: SQL injection resistance                           │      │
│  │        Attempt injection on all input fields               │      │
│  │        Target: 0 successful injections                     │      │
│  │                                                            │      │
│  │  P7.3: XSS resistance                                     │      │
│  │        Attempt XSS on search, chat inputs                  │      │
│  │        Target: 0 successful XSS                            │      │
│  │                                                            │      │
│  │  P7.4: Dependency vulnerability scan                       │      │
│  │        pip-audit or safety check on requirements.txt      │      │
│  │        Target: 0 critical/high vulnerabilities             │      │
│  └────────────────────────────────────────────────────────────┘      │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Part 2: Unit Testing — The Foundation

---

### 2.1 Unit Test Parameters

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  RULES FOR UNIT TESTS:                                               │
│                                                                      │
│  1. ONE thing per test (test one function, one behavior)            │
│  2. NO external dependencies (mock DB, mock API, mock Ollama)       │
│  3. FAST (< 100ms per test)                                         │
│  4. REPEATABLE (same result every time)                              │
│  5. SELF-DOCUMENTING (test name explains what it tests)             │
│                                                                      │
│  NAMING CONVENTION:                                                  │
│  test_<function>_<scenario>_<expected_result>                        │
│                                                                      │
│  EXAMPLES:                                                           │
│  test_score_startup_with_funding_returns_high_score()                │
│  test_score_startup_with_no_data_returns_zero()                      │
│  test_normalize_funding_none_returns_zero()                          │
│  test_classify_intent_with_empty_string_returns_error()              │
│                                                                      │
│  STRUCTURE (AAA Pattern):                                            │
│  def test_<name>():                                                  │
│      # Arrange — set up test data                                    │
│      agent = OpportunityScorer(config={})                            │
│      data = {"funding_total": 5_000_000}                             │
│                                                                      │
│      # Act — run the function being tested                           │
│      result = agent.score(data)                                      │
│                                                                      │
│      # Assert — verify the result                                    │
│      assert result["score"] > 50                                     │
│      assert "funding" in result["factors"]                           │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 Unit Test Coverage Gaps (What Needs Tests NOW)

```
CRITICAL GAPS — Tests that MUST be written before MVP launch:

TIER 1: MVP-CRITICAL (Score, Chat, Search)
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  ❌ api_server.py — 34 endpoints, ZERO tests                       │
│  Priority: P0 (this is the MVP's front door)                        │
│  Tests needed: 68 (2 per endpoint: success + error)                │
│                                                                      │
│  File: tests/test_api_endpoints.py (NEW)                            │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  def test_health_check_returns_200():                          │  │
│  │  def test_search_with_valid_query_returns_results():          │  │
│  │  def test_search_with_empty_query_returns_400():              │  │
│  │  def test_score_a_startup_with_known_company():               │  │
│  │  def test_score_a_startup_with_unknown_company():             │  │
│  │  def test_opportunities_list_returns_entities():              │  │
│  │  def test_opportunity_detail_returns_breakdown():             │  │
│  │  def test_chat_with_valid_message_returns_response():         │  │
│  │  def test_chat_with_empty_message_returns_400():              │  │
│  │  def test_survival_rates_returns_bls_data():                  │  │
│  │  ... 58 more                                                   │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ❌ agents/opportunity_scorer.py — THE CORE SCORER, ZERO tests     │
│  Priority: P0 (this IS the product)                                  │
│  Tests needed: 15                                                    │
│                                                                      │
│  File: tests/test_opportunity_scorer.py (NEW)                       │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  def test_score_with_high_funding_returns_high_score():        │  │
│  │  def test_score_with_no_data_returns_low_score():              │  │
│  │  def test_score_with_negative_sentiment_reduces_score():       │  │
│  │  def test_score_with_failure_pattern_match_reduces_score():    │  │
│  │  def test_score_deterministic_same_input_same_output():        │  │
│  │  def test_score_bounds_always_0_to_100():                      │  │
│  │  def test_score_factors_explain_total_score():                 │  │
│  │  def test_score_with_null_funding_handles_gracefully():        │  │
│  │  ... 7 more                                                    │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ❌ db/schema.py — 76 tables, ZERO tests                           │
│  Priority: P1 (schema bugs = data corruption)                        │
│  Tests needed: 10                                                    │
│                                                                      │
│  File: tests/test_schema.py (NEW)                                    │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  def test_init_schema_creates_all_tables():                    │  │
│  │  def test_schema_version_is_current():                         │  │
│  │  def test_all_tables_have_primary_key():                       │  │
│  │  def test_foreign_keys_reference_valid_tables():               │  │
│  │  def test_insert_and_retrieve_failed_startup():                │  │
│  │  ... 5 more                                                    │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘

TIER 2: IMPORTANT (Agents used by MVP features)
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  ❌ agents/failure_pattern_agent.py     — 5 tests needed            │
│  ❌ agents/nlp_enrichment_agent.py      — 8 tests needed            │
│  ❌ agents/orchestrator.py              — 10 tests needed            │
│  ❌ agents/knowledge_graph_agent.py     — 5 tests needed            │
│  ❌ agents/ai_analyst_agent.py          — 5 tests needed            │
│  ❌ agents/alert_dispatcher_agent.py    — 5 tests needed            │
│  ❌ stream/operators.py                 — 8 tests needed             │
│  ❌ stream/state.py                     — 4 tests needed             │
│  ❌ stream/metrics.py                   — 4 tests needed             │
│                                                                      │
│  Total Tier 2: 54 tests                                              │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘

TIER 3: NICE-TO-HAVE (Agents not in MVP)
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  43 agents without tests (from the audit)                            │
│  These can be tested after MVP launch, before V1.                   │
│  Priority: P2                                                        │
│  Target: 3 tests per agent = 129 tests                              │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.3 Fix the 12 Failing Tests FIRST

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  CURRENT FAILURES:                                                   │
│  tests/test_semantic_search.py — 12 tests FAILING                   │
│                                                                      │
│  These were passing before and broke. That means a recent change    │
│  introduced a regression. THIS IS EXACTLY WHY WE TEST.              │
│                                                                      │
│  ACTION:                                                             │
│  1. Run: pytest tests/test_semantic_search.py -v --tb=short        │
│  2. Read the error messages                                          │
│  3. Fix the root cause (likely import or interface change)          │
│  4. Re-run to confirm 0 failures                                    │
│  5. NEVER merge code that breaks existing tests                     │
│                                                                      │
│  PARAMETER P-ZERO:                                                   │
│  ZERO failing tests before ANY new work begins.                      │
│  If tests are red, fixing them is the ONLY priority.                │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Part 3: Integration Testing

---

### 3.1 Integration Test Parameters

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  WHAT INTEGRATION TESTS VERIFY:                                      │
│                                                                      │
│  "Do the pieces work TOGETHER?"                                      │
│                                                                      │
│  Unit test:     Does OpportunityScorer.score() work in isolation?    │
│  Integration:   Does API → Scorer → DB → Response chain work?       │
│                                                                      │
│  RULES:                                                              │
│  1. CAN use real database (MySQL test instance)                      │
│  2. CAN use real services (started in Docker for CI)                │
│  3. MUST clean up after themselves (no test data left in DB)        │
│  4. SLOWER than unit tests (< 30 seconds each)                     │
│  5. Run on every push (not every save)                               │
│                                                                      │
│  CURRENT INTEGRATION TESTS:                                          │
│  ✅ test_phase4_integration.py — 31 tests                           │
│  ✅ test_phase5_integration.py — 6 tests                            │
│  ✅ test_phase6_integration.py — 9 tests                            │
│  ✅ test_pipeline.py — 36 tests                                     │
│  Total: 82 integration tests ✅                                      │
│                                                                      │
│  MISSING INTEGRATION TESTS:                                           │
│  ❌ test_api_db_integration.py — API → Database round trip           │
│  ❌ test_collector_pipeline.py — Collector → Kafka → Stream → DB    │
│  ❌ test_score_pipeline.py — Full scoring pipeline end-to-end       │
│  ❌ test_chat_pipeline.py — Chat → Ollama → DB → Response          │
│  ❌ test_alert_pipeline.py — Score change → Alert → Dispatch        │
│                                                                      │
│  TARGET: 150 integration tests                                       │
│  CURRENT: 82                                                         │
│  GAP: 68 more needed                                                 │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.2 Integration Test Scenarios

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  SCENARIO 1: Full Scoring Pipeline                                  │
│  ─────────────────────────────────────                               │
│  1. Seed a test startup into MySQL                                  │
│  2. Add signals (news, funding, patents) to MySQL                   │
│  3. Call POST /api/score-a-startup                                  │
│  4. Verify:                                                          │
│     - Response has score (0-100)                                    │
│     - Response has risk (0-1)                                       │
│     - Response has factors explaining the score                     │
│     - Score is stored in opportunity_scores table                   │
│     - Knowledge graph entities updated                              │
│  5. Clean up test data                                               │
│                                                                      │
│  SCENARIO 2: Collector → Database Pipeline                          │
│  ──────────────────────────────────────                              │
│  1. Mock external API (or use recorded responses)                   │
│  2. Run a collector (e.g., GoogleNewsRSSCollector)                  │
│  3. Verify:                                                          │
│     - Raw signals inserted into raw_signals table                   │
│     - Deduplication prevents duplicates                             │
│     - Enrichment pipeline adds NLP data                             │
│     - Entities extracted and linked in knowledge graph              │
│                                                                      │
│  SCENARIO 3: Chat → AI Response Pipeline                            │
│  ──────────────────────────────────────                              │
│  1. Mock Ollama response                                             │
│  2. Send chat message to POST /api/chat                             │
│  3. Verify:                                                          │
│     - Response contains answer text                                 │
│     - Response references data sources used                         │
│     - Chat history stored if applicable                             │
│     - Error handling when Ollama is down                            │
│                                                                      │
│  SCENARIO 4: Alert Dispatch Pipeline                                │
│  ────────────────────────────────────                                │
│  1. Insert a score change into opportunity_scores                   │
│  2. Verify Kafka message produced on scores.updates topic           │
│  3. Verify alert consumer picks up the message                      │
│  4. Verify alert dispatched to configured channel (email/Slack)     │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Part 4: User Acceptance Testing (UAT)

---

### 4.1 UAT Parameters

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  WHAT IS UAT:                                                        │
│  "Does the product solve the user's problem?"                       │
│                                                                      │
│  UAT is NOT about code correctness.                                  │
│  UAT is about PRODUCT correctness.                                   │
│                                                                      │
│  WHO RUNS UAT:                                                       │
│  - The developer (self-UAT before launch)                           │
│  - 3-5 target users (after launch, before calling it "done")        │
│                                                                      │
│  FORMAT:                                                             │
│  Each UAT test is a USER SCENARIO, not a test function.             │
│  The user follows a script and reports PASS or FAIL.                │
│                                                                      │
│  PARAMETERS:                                                         │
│  ┌────────────────────────────────────────────────────────────┐      │
│  │  P-UAT-1: Self-UAT before every deploy                    │      │
│  │  Developer walks through each user scenario manually       │      │
│  │  Time: 15-30 minutes                                       │      │
│  │                                                            │      │
│  │  P-UAT-2: User UAT with 3-5 real users                    │      │
│  │  After MVP launch, recruit 5 target users                  │      │
│  │  Give them scenarios to try                                │      │
│  │  Collect feedback: PASS, PARTIAL, FAIL + comments          │      │
│  │                                                            │      │
│  │  P-UAT-3: Score quality validation                        │      │
│  │  Score 20 known startups                                   │      │
│  │  Compare against human intuition:                          │      │
│  │    - Failed startups should score < 50 (14/20 = 70%)      │      │
│  │    - Successful startups should score > 60 (14/20 = 70%)  │      │
│  │    - This is the ACCURACY GATE for launch                  │      │
│  │                                                            │      │
│  │  P-UAT-4: AI chat quality validation                      │      │
│  │  Ask 10 questions, rate each answer 1-5                   │      │
│  │  Target: Average ≥ 3.0 ("useful but not perfect")          │      │
│  │                                                            │      │
│  │  P-UAT-5: Dashboard usability                             │      │
│  │  New user (never seen product) tries to:                   │      │
│  │    1. Find a startup's score → should take < 30 seconds   │      │
│  │    2. Ask a question about a failure → < 30 seconds       │      │
│  │    3. Browse failure patterns → < 15 seconds               │      │
│  │  If any task takes > 60 seconds → UI needs improvement    │      │
│  └────────────────────────────────────────────────────────────┘      │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 4.2 UAT Test Scripts

```
UAT SCRIPT 1: "Score a Startup"
─────────────────────────────────────────────────────────────────────

Persona: Venture Capitalist
Goal:    Evaluate a potential investment

Steps:
  1. Open demo.opportunity-intel.org
  2. Search for "Rivian"
  3. Review the composite score (0-100)
  4. Read the factor breakdown
  5. Check the "Similar Failed Startups" section
  6. Review the knowledge graph connections

PASS CRITERIA:
  ☐ Score appears in < 5 seconds
  ☐ Score is between 0-100
  ☐ At least 3 factors explain the score
  ☐ At least 1 similar failed startup shown
  ☐ Score matches intuition (Rivian is struggling → score < 65)

FAIL CRITERIA:
  ☐ Score takes > 10 seconds
  ☐ Score is 0 or 100 (broken)
  ☐ No factors shown
  ☐ No similar startups shown


UAT SCRIPT 2: "Ask a Question"
─────────────────────────────────────────────────────────────────────

Persona: Startup Founder
Goal:    Learn from past failures

Steps:
  1. Open demo.opportunity-intel.org
  2. Type "Why did Quibi fail?" in the chat
  3. Read the AI response
  4. Check if the answer cites data from the platform

PASS CRITERIA:
  ☐ Response appears in < 15 seconds
  ☐ Answer mentions at least 2 failure reasons
  ☐ Answer references data (not generic AI knowledge)
  ☐ Answer is relevant and coherent

FAIL CRITERIA:
  ☐ Response takes > 30 seconds
  ☐ Answer is generic (could apply to any startup)
  ☐ Answer is incoherent or wrong


UAT SCRIPT 3: "Browse Failure Patterns"
─────────────────────────────────────────────────────────────────────

Persona: Researcher / Journalist
Goal:    Find trends in startup failures

Steps:
  1. Open demo.opportunity-intel.org
  2. Navigate to the failure patterns section
  3. Filter by sector (e.g., "EV/Automotive")
  4. Filter by geography (e.g., "US & Global")
  5. Find the top failure reason for EV startups

PASS CRITERIA:
  ☐ Charts render correctly
  ☐ Filters work (results update)
  ☐ Data appears accurate (matches known failures)
  ☐ At least 5 failure categories visible

FAIL CRITERIA:
  ☐ Charts don't render
  ☐ Filters don't update results
  ☐ Data is clearly wrong (e.g., "no failures in EV")


UAT SCRIPT 4: "Discover a New Opportunity"
─────────────────────────────────────────────────────────────────────

Persona: Innovation Manager
Goal:    Find underserved markets or revival opportunities

Steps:
  1. Open the opportunity feed/dashboard
  2. Look for high-opportunity, low-risk startups
  3. Find a sector with high failure rate but recent success signals
  4. Check if any failed startups have revival indicators

PASS CRITERIA:
  ☐ Opportunity feed shows ranked entities
  ☐ Can sort by score, risk, or trend
  ☐ At least some entities have revival indicators
  ☐ Dashboard provides actionable insight


UAT SCRIPT 5: "Self-Host the Platform"
─────────────────────────────────────────────────────────────────────

Persona: CTO at a VC firm
Goal:    Deploy OIP on company infrastructure

Steps:
  1. Clone the GitHub repo
  2. Run docker compose up -d
  3. Wait for all services to start
  4. Open localhost:8000
  5. Verify the platform works locally

PASS CRITERIA:
  ☐ docker compose up succeeds (all 11 services healthy)
  ☐ Platform accessible at localhost:8000 within 5 minutes
  ☐ Search returns results (seed data loaded)
  ☐ Chat works with local Ollama
  ☐ Documentation explains setup clearly
```

---

## Part 5: Performance Testing

---

### 5.1 Performance Test Parameters

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  PERFORMANCE BUDGET (per endpoint):                                  │
│                                                                      │
│  Endpoint                  p50      p95      p99      Timeout      │
│  ────────────────────────────────────────────────────────────────    │
│  GET  /health              < 10ms   < 50ms   < 100ms   1s          │
│  GET  /api/search          < 200ms  < 500ms  < 1s      5s          │
│  GET  /api/opportunities   < 200ms  < 500ms  < 1s      5s          │
│  GET  /api/opportunities/X < 100ms  < 300ms  < 500ms   3s          │
│  POST /api/score-a-startup < 500ms  < 2s     < 5s      15s         │
│  POST /api/chat            < 5s     < 15s    < 30s     60s         │
│  GET  /api/startups        < 200ms  < 500ms  < 1s      5s          │
│  GET  /api/survival-rates  < 100ms  < 300ms  < 500ms   3s          │
│                                                                      │
│  LOAD TESTING TARGETS:                                               │
│                                                                      │
│  Scenario         Users    Duration    Target Error Rate             │
│  ──────────────────────────────────────────────────────              │
│  Light load       10       5 min       < 0.1%                       │
│  Normal load      50       10 min      < 1%                         │
│  Peak load        100      15 min      < 5%                         │
│  Stress load      200      10 min      < 10% (identify limit)      │
│  Spike test       0→100    2 min       < 5% (ramp-up test)         │
│                                                                      │
│  PERFORMANCE REGRESSION RULES:                                       │
│  - p95 response time must not increase by > 20% between releases    │
│  - Error rate must not increase between releases                     │
│  - Memory usage must not increase by > 30% between releases         │
│                                                                      │
│  SCALABILITY TARGETS:                                                │
│                                                                      │
│  Metric                MVP Target    V1 Target     Full Target      │
│  ────────────────────────────────────────────────────────            │
│  Concurrent users      10            100           1,000            │
│  Entities in DB        100           10,000        1,000,000        │
│  Signals per day       100           5,000         100,000          │
│  Search index size     1,000 docs    100,000 docs  10M docs         │
│  Kafka throughput      10 msg/sec    1,000 msg/s   100,000 msg/s   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 5.2 Performance Test Scenarios

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  PERF-1: Search Under Load                                          │
│  ────────────────────────                                            │
│  Tool: locust or k6                                                  │
│  Script:                                                             │
│    1. 50 concurrent users                                            │
│    2. Each user searches random startup names                        │
│    3. Run for 10 minutes                                             │
│  Assert:                                                             │
│    - p95 < 500ms                                                     │
│    - 0% 5xx errors                                                   │
│    - No memory leaks (RSS stable)                                    │
│                                                                      │
│  PERF-2: Score Calculation Benchmark                                │
│  ─────────────────────────────────                                   │
│  Script:                                                             │
│    1. Score 100 startups sequentially                                │
│    2. Score 100 startups with 10 concurrent requests                │
│  Assert:                                                             │
│    - Sequential: avg < 500ms per score                               │
│    - Concurrent: all complete within 60 seconds                      │
│    - Score results are deterministic (same input = same output)     │
│                                                                      │
│  PERF-3: Chat Response Time                                         │
│  ────────────────────────                                            │
│  Script:                                                             │
│    1. Send 20 different chat questions                               │
│    2. Measure time to first byte and total time                      │
│  Assert:                                                             │
│    - Median total time < 10 seconds                                  │
│    - All responses complete in < 30 seconds                          │
│    - Response quality doesn't degrade under load                     │
│                                                                      │
│  PERF-4: Database Query Performance                                  │
│  ──────────────────────────────                                      │
│  Script:                                                             │
│    1. Seed 10,000 entities                                           │
│    2. Run search queries                                             │
│    3. Run aggregation queries (top startups by score)               │
│  Assert:                                                             │
│    - Simple query: < 100ms                                           │
│    - Aggregation: < 500ms                                            │
│    - Full table scan: < 2s                                           │
│    - Proper indexes being used (EXPLAIN query)                       │
│                                                                      │
│  PERF-5: Docker Startup Time                                        │
│  ──────────────────────                                              │
│  Script:                                                             │
│    1. docker compose down                                            │
│    2. docker compose up -d                                           │
│    3. Measure time until health check passes                         │
│  Assert:                                                             │
│    - All services healthy in < 3 minutes                             │
│    - API responding in < 3 minutes                                   │
│    - No services crashing during startup                             │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Part 6: Testing at Every Stage — The Master Plan

---

### 6.1 Stage-Testing Matrix

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  WHEN              WHAT TESTS        RUN HOW         GATE?          │
│  ──────────────────────────────────────────────────────────────────  │
│                                                                      │
│  Every SAVE        Unit tests        IDE/terminal     No (feedback) │
│                    (changed files)   pytest watch                    │
│                                                                      │
│  Every COMMIT      All unit +        Pre-commit       YES           │
│                    integration       hook or manual                  │
│                    tests                                             │
│                                                                      │
│  Every PUSH        Full test suite   GitHub Actions   YES           │
│                    + linting         automated                       │
│                    + type check                                      │
│                                                                      │
│  Every DEPLOY      Smoke tests      Deploy script     YES           │
│                    (5 endpoints)     automated                       │
│                                                                      │
│  Weekly            Full regression   GitHub Actions   Report only   │
│                    + perf check      cron                            │
│                                                                      │
│  Monthly          Load testing      Manual trigger    Report only   │
│                    + security scan                                   │
│                                                                      │
│  Before launch    UAT (5 scripts)   Manual with       YES           │
│                    Score accuracy    real users                      │
│                    validation                                        │
│                                                                      │
│  GATES:                                                             │
│  - Commit gate:    0 failing tests                                  │
│  - Push gate:      CI passes (when configured)                       │
│  - Deploy gate:    Smoke tests pass                                 │
│  - Launch gate:    UAT passes + score accuracy ≥ 70%                │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 6.2 Test Targets by Milestone

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  MILESTONE         DATE        UNIT    INT    UAT   PERF   TOTAL    │
│  ──────────────────────────────────────────────────────────────────  │
│                                                                      │
│  MVP READY         Jun 2026    750     100    5      3     858      │
│  (what we need before launch)                                        │
│                                                                      │
│  V1 LAUNCH         Aug 2026    900     150    10     5     1,065    │
│  (alerts + auth + scheduler)                                         │
│                                                                      │
│  V2 COMPLETE       Dec 2026    1,100   200    15     10    1,325    │
│  (watchlists + CRM + 15 collectors)                                  │
│                                                                      │
│  STABLE v1.0       Jun 2027    1,500   300    20     15    1,835    │
│  (production-ready, documented API contract)                         │
│                                                                      │
│  CURRENT STATE     Jun 2026    617     82     0      0     699      │
│  (12 failing)                                                        │
│                                                                      │
│  GAP TO MVP:       +133       +18    +5     +3     +159            │
│                                                                      │
│  TIME TO CLOSE GAP:                                                 │
│  - 133 unit tests @ 10 tests/hour = 13 hours                        │
│  - 18 integration tests @ 3 tests/hour = 6 hours                    │
│  - 5 UAT scripts @ 30 min each = 2.5 hours                          │
│  - 3 perf tests @ 2 hours each = 6 hours                            │
│  TOTAL: ~28 hours (3-4 focused days)                                 │
│                                                                      │
│  RECOMMENDATION:                                                     │
│  Don't block MVP on 133 unit tests.                                 │
│  Write the 68 API endpoint tests + 15 scorer tests first (P0).      │
│  That's 83 tests = ~8 hours.                                        │
│  The rest can be written during Week 2 (measure phase of MVP).      │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Part 7: Test Infrastructure Setup

---

### 7.1 Create pytest Configuration

```
FILE: pytest.ini (NEW — create in project root)

[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --tb=short
    --strict-markers
    -x
markers =
    unit: Unit tests (no external dependencies)
    integration: Integration tests (use real DB)
    slow: Tests that take > 1 second
    api: API endpoint tests
    agent: Agent-specific tests
    collector: Collector tests
    smoke: Smoke tests for deployment verification
    performance: Performance benchmark tests
    uat: User acceptance test scenarios
```

### 7.2 Create GitHub Actions Test Workflow

```yaml
FILE: .github/workflows/test.yml (NEW)

name: Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      mysql:
        image: mysql:8.0
        env:
          MYSQL_ROOT_PASSWORD: root
          MYSQL_DATABASE: startup_research_test
        ports:
          - 3306:3306
        options: >-
          --health-cmd="mysqladmin ping"
          --health-interval=10s
          --health-timeout=5s
          --health-retries=5

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-mock

      - name: Run unit tests
        run: pytest -m unit --tb=short -q

      - name: Run integration tests
        env:
          MYSQL_HOST: '127.0.0.1'
          MYSQL_PORT: '3306'
          MYSQL_USER: 'root'
          MYSQL_PASSWORD: 'root'
          MYSQL_DATABASE: 'startup_research_test'
        run: pytest -m integration --tb=short -q

      - name: Run all tests with coverage
        run: pytest --cov=. --cov-report=term-missing --tb=short -q

      - name: Check coverage threshold
        run: |
          pytest --cov=. --cov-fail-under=30 -q
          echo "Coverage threshold: 30% (increase over time)"
```

### 7.3 Update conftest.py

```python
FILE: tests/conftest.py (UPDATE)

"""Shared test fixtures and configuration."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(autouse=True)
def mock_pymysql(monkeypatch):
    """Auto-mock pymysql for all tests to prevent real DB connections."""
    mock_pymysql = MagicMock()
    mock_pymysql.cursors = MagicMock()
    mock_pymysql.cursors.DictCursor = MagicMock
    monkeypatch.setitem(sys.modules, "pymysql", mock_pymysql)
    monkeypatch.setitem(sys.modules, "pymysql.cursors", mock_pymysql.cursors)


@pytest.fixture
def mock_db_connection():
    """Provide a mock database connection for tests."""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return conn, cursor


@pytest.fixture
def mock_ollama():
    """Mock Ollama API calls for chat/embedding tests."""
    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "response": "Test AI response",
            "model": "llama3:8b"
        }
        yield mock_post


@pytest.fixture
def sample_startup_data():
    """Provide sample startup data for scoring tests."""
    return {
        "name": "TestCorp",
        "sector": "Technology",
        "country": "US",
        "funding_total": 50_000_000,
        "founded_year": 2020,
        "signals": [
            {"type": "news", "sentiment": 0.7, "date": "2026-01-01"},
            {"type": "funding", "amount": 50_000_000, "round": "Series B"},
            {"type": "patent", "count": 12},
        ]
    }


@pytest.fixture
def sample_failed_startup():
    """Provide sample failed startup data for pattern matching."""
    return {
        "name": "FailedCorp",
        "sector": "EV/Automotive",
        "country": "US",
        "funding_total": 1_000_000_000,
        "founded_year": 2016,
        "failed_year": 2024,
        "failure_reason": "pilot_to_scale_gap",
        "failure_category": "Unit Economics"
    }
```

---

## Part 8: Test-First Development Rules

---

### 8.1 Rules for Writing Code

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  RULE 1: NEW FEATURE = NEW TEST FIRST (for new features)            │
│                                                                      │
│  Before writing a new feature:                                       │
│  1. Write the test for what it SHOULD do                             │
│  2. Run the test → it FAILS (feature doesn't exist yet)             │
│  3. Write the feature code                                           │
│  4. Run the test → it PASSES                                         │
│                                                                      │
│  This is Test-Driven Development (TDD).                              │
│  It ensures every feature has a test from day one.                   │
│                                                                      │
│  RULE 2: BUG FIX = REGRESSION TEST FIRST                            │
│                                                                      │
│  When you find a bug:                                                │
│  1. Write a test that REPRODUCES the bug                             │
│  2. Run the test → it FAILS (bug exists)                             │
│  3. Fix the bug                                                      │
│  4. Run the test → it PASSES                                         │
│                                                                      │
│  This ensures the bug never comes back.                              │
│  Every fixed bug = one new test.                                     │
│                                                                      │
│  RULE 3: REFACTOR ONLY WHEN TESTS ARE GREEN                         │
│                                                                      │
│  Before refactoring code:                                            │
│  1. Ensure all existing tests pass                                   │
│  2. Refactor the code                                                │
│  3. Run all tests → they should still pass                           │
│                                                                      │
│  If tests break during refactor, the refactor is wrong.             │
│  Tests are the safety net for refactoring.                           │
│                                                                      │
│  RULE 4: NEVER COMMENT OUT OR SKIP FAILING TESTS                    │
│                                                                      │
│  A failing test is a signal that something is broken.               │
│  Fix the problem, don't hide the signal.                             │
│                                                                      │
│  Exception: @pytest.mark.skip with a linked issue number.            │
│  Example: @pytest.mark.skip("Issue #42: score NaN when null")        │
│                                                                      │
│  RULE 5: TESTS ARE FIRST-CLASS CODE                                 │
│                                                                      │
│  Tests get the same code quality as production code:                 │
│  - Clear naming                                                      │
│  - No duplication (use fixtures)                                     │
│  - Comments for complex test setup                                   │
│  - Reviewed like production code                                     │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 8.2 Bug Cost Escalation

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  THE COST OF A BUG:                                                  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │                                                              │    │
│  │  $1    Found by developer while writing code                 │    │
│  │         (unit test catches it immediately)                   │    │
│  │                                                              │    │
│  │  $10   Found by CI/CD before merge                          │    │
│  │         (integration test catches it)                        │    │
│  │                                                              │    │
│  │  $100  Found by QA or UAT before release                    │    │
│  │         (manual testing catches it)                          │    │
│  │                                                              │    │
│  │  $1,000  Found by a user after release                      │    │
│  │         (bug report, support ticket)                         │    │
│  │                                                              │    │
│  │  $10,000 Found by many users after release                  │    │
│  │         (reputation damage, emergency fix, lost trust)       │    │
│  │                                                              │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  FOR OIP SPECIFICALLY:                                               │
│                                                                      │
│  Bug Type                   Unit Cost  Production Cost  Multiplier   │
│  ──────────────────────────────────────────────────────────────      │
│  Wrong score                $1         $10,000+         10,000x     │
│  (wrong investment decision)                                        │
│                                                                      │
│  SQL injection             $1         $100,000+        100,000x     │
│  (data breach)                                                       │
│                                                                      │
│  API crash                  $1         $1,000+          1,000x       │
│  (downtime for all users)                                            │
│                                                                      │
│  Chat gives wrong answer   $1         $100+            100x         │
│  (user loses trust)                                                  │
│                                                                      │
│  Dashboard empty            $1         $500+            500x         │
│  (bad first impression)                                              │
│                                                                      │
│  CONCLUSION:                                                         │
│  Writing tests early costs $1 per bug.                               │
│  Not writing tests costs $100-$100,000 per bug.                     │
│  The ROI of testing is 100x-100,000x.                                │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Part 9: The Testing Priority Order

---

### 9.1 What to Test First (The MVP Test Plan)

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  PRIORITY ORDER FOR MVP:                                             │
│                                                                      │
│  STEP 0: FIX THE 12 FAILING TESTS (1-2 hours)                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  test_semantic_search.py: 12 failures                        │  │
│  │  Fix: likely import/interface change after refactoring       │  │
│  │  Gate: 0 failures before proceeding                         │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  STEP 1: API ENDPOINT TESTS (4-6 hours)                             │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  File: tests/test_api_endpoints.py (NEW)                     │  │
│  │  Tests: 68 (2 per endpoint × 34 endpoints)                  │  │
│  │  Why: API is the MVP's front door. If it's broken,           │  │
│  │       nothing else matters.                                  │  │
│  │  How: Mock DB, mock Ollama, test FastAPI TestClient          │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  STEP 2: SCORER TESTS (2-3 hours)                                   │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  File: tests/test_opportunity_scorer.py (NEW)                │  │
│  │  Tests: 15 (happy path, sad path, edge cases)               │  │
│  │  Why: Scoring IS the product. If it's wrong, users leave.   │  │
│  │  Key test: score bounds always 0-100                        │  │
│  │  Key test: score is deterministic                           │  │
│  │  Key test: factors explain the total score                  │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  STEP 3: DEPLOY SMOKE TESTS (1 hour)                                │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  File: tests/test_smoke.py (NEW)                             │  │
│  │  Tests: 5 (health, search, score, chat, dashboard)          │  │
│  │  Why: Catches deploy-time failures before users see them     │  │
│  │  How: Real HTTP requests to running server                   │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  STEP 4: UAT SELF-TEST (1-2 hours)                                  │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  Scripts: 5 UAT scenarios (Section 4.2)                      │  │
│  │  Why: Product-level validation before launch                  │  │
│  │  How: Manual walkthrough with checklist                       │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  TOTAL TIME: 9-14 hours (1-2 focused days)                          │
│  TOTAL NEW TESTS: 88                                                 │
│  RESULT: 787 tests (699 existing + 88 new)                          │
│                                                                      │
│  AFTER MVP LAUNCH (Week 2-4):                                       │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  STEP 5: Schema tests (10 tests, 2 hours)                    │  │
│  │  STEP 6: Stream pipeline tests (16 tests, 4 hours)           │  │
│  │  STEP 7: Remaining agent tests (54 tests, 2 days)            │  │
│  │  STEP 8: Performance tests (3 tests, 4 hours)                │  │
│  │  STEP 9: CI workflow (test.yml, 2 hours)                     │  │
│  │  STEP 10: Coverage measurement (pytest-cov, 1 hour)          │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Part 10: The One-Page Testing Plan

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  TESTING STRATEGY — ONE PAGE                                         │
│                                                                      │
│  CURRENT:  699 tests, 98.3% pass, 1.4s suite, 0 perf, 0 UAT       │
│  MVP TARGET: 787 tests, 100% pass, 5 smoke, 5 UAT                  │
│  V1 TARGET: 1,065 tests, CI/CD, coverage ≥ 50%                      │
│                                                                      │
│  7 TESTING STAGES:                                                   │
│  1. Every SAVE    → unit tests (changed files only)                 │
│  2. Every COMMIT  → all tests (0 failures gate)                     │
│  3. Every PUSH    → CI runs full suite + lint                        │
│  4. Every DEPLOY  → smoke tests (5 endpoints)                        │
│  5. Weekly        → regression + performance check                   │
│  6. Monthly       → load test (100 users) + security scan            │
│  7. Pre-launch    → UAT (5 scenarios) + score accuracy (70%)         │
│                                                                      │
│  4 TEST TYPES:                                                       │
│  Unit (70%):        700+ tests, < 100ms each, mock everything       │
│  Integration (20%): 150 tests, < 30s each, real DB                  │
│  UAT (5%):          5-20 scripts, manual, real users                 │
│  Performance (5%):  10 benchmarks, weekly, track p95                 │
│                                                                      │
│  IMMEDIATE ACTIONS:                                                  │
│  1. Fix 12 failing tests (1-2 hrs)                                  │
│  2. Write 68 API endpoint tests (4-6 hrs)                           │
│  3. Write 15 scorer tests (2-3 hrs)                                 │
│  4. Write 5 smoke tests (1 hr)                                      │
│  5. Run 5 UAT scripts manually (1-2 hrs)                            │
│  6. Create .github/workflows/test.yml (1 hr)                        │
│  7. Create pytest.ini with markers (15 min)                         │
│                                                                      │
│  GATES:                                                              │
│  Commit: 0 failing tests                                             │
│  Deploy: smoke tests pass                                            │
│  Launch: UAT passes + score accuracy ≥ 70%                          │
│                                                                      │
│  BUG COST: $1 in dev → $10 in CI → $100 in QA → $1K in prod        │
│  TESTING ROI: 100x - 100,000x                                        │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

*Last updated: June 5, 2026*
