# Findings Report - Security Audit

**Audit Phase:** Phase 1: Security Audit
**Date:** 2026-07-09
**Status:** IN PROGRESS

---

## Critical Findings

| ID | Finding | Location | Severity | CVSS | Status |
|----|---------|----------|----------|------|--------|
| SEC-001 | JWT default secret fallback | `auth/jwt_handler.py:35` | HIGH | 7.5 | OPEN |

**SEC-001 Detail:**
```python
self.secret = self.config.get(
    "jwt_secret", auth_config.get("jwt_secret", "change-me-in-production")
)
```
**Issue:** If no JWT_SECRET is configured in environment, the application uses "change-me-in-production" as the signing key.
**Risk:** Predictable JWT secrets allow token forgery.
**Remediation:** Raise an error or generate a random secret if JWT_SECRET is not set in production.

## High Findings

| ID | Finding | Location | Severity | CVSS | Status |
|----|---------|----------|----------|------|--------|
| SEC-002 | CORS origin from env not validated | `api_server.py:95` | MEDIUM | 5.3 | OPEN |
| SEC-003 | Webhook signature verification not visible | `api/v2/webhooks.py` | MEDIUM | - | NEEDS REVIEW |

## Medium Findings

| ID | Finding | Location | Priority | Status |
|----|---------|----------|----------|--------|
| SEC-004 | Rate limiting depends on slowapi | `api_server.py:170` | LOW | OK (warns if missing) |
| SEC-005 | No explicit signature verification | `api/v2/webhooks.py` | MEDIUM | OPEN |

## Low Findings

| ID | Finding | Location | Priority | Status |
|----|---------|----------|----------|--------|
| SEC-006 | Mock JWT fallback when PyJWT missing | `auth/jwt_handler.py:42-44` | LOW | OK (warns) |

---

## Security Controls Verified ✅

### Authentication
| Check | Status | Notes |
|-------|--------|-------|
| JWT tokens (HS256) | ✅ GOOD | Uses pyjwt with proper algorithm |
| Password hashing (bcrypt) | ✅ GOOD | bcrypt>=4.1.0 required |
| Password validation | ✅ GOOD | min_length=8 for RegisterRequest |
| Role validation | ✅ GOOD | Pattern: `^(viewer|analyst|admin)$` |

### Authorization (RBAC)
| Check | Status | Notes |
|-------|--------|-------|
| Role hierarchy defined | ✅ GOOD | viewer(1) < analyst(2) < admin(3) |
| Least privilege principle | ✅ GOOD | viewer has read-only access |
| Resource-level permissions | ✅ GOOD | 20+ permission categories defined |

### Input Validation
| Check | Status | Notes |
|-------|--------|-------|
| Pydantic BaseModel usage | ✅ GOOD | All critical endpoints use validation |
| Query parameter bounds | ✅ GOOD | `ge=1, le=100` for limit |
| SQL parameterized queries | ✅ GOOD | `cursor.execute(query, params)` pattern |

### Security Headers
| Header | Status | Notes |
|--------|--------|-------|
| X-Content-Type-Options: nosniff | ✅ GOOD | api_server.py:110 |
| X-Frame-Options: DENY | ✅ GOOD | api_server.py:111 |
| Content-Security-Policy | ✅ GOOD | api_server.py:117 |
| Strict-Transport-Security | ✅ GOOD | api_server.py:125 |

### Rate Limiting
| Check | Status | Notes |
|-------|--------|-------|
| slowapi integration | ✅ GOOD | api_server.py:165-172 |
| Default limit | ✅ GOOD | 60/minute |
| Handler registered | ✅ GOOD | RateLimitExceeded handler |

### CORS Configuration
| Check | Status | Notes |
|-------|--------|-------|
| Credentials allowed | ✅ GOOD | `allow_credentials=True` |
| Origin from env var | ⚠️ WARN | `_cors_origin` - validate this is not `*` |

---

## Secret Scan Results

### Hardcoded Credentials
```bash
# grep -rn "password\s*=" --include="*.py"
agents/alert_dispatcher_agent.py:385:        smtp_password = config.get("smtp_password")  # ✅ Config lookup
scripts/alert_consumer.py:137:    smtp_password = config.get("smtp_password")  # ✅ Config lookup
```
**Status:** ✅ No hardcoded passwords

### API Keys
```bash
collectors/crunchbase.py:60:        api_key = api_config.get("api_key", "")  # ✅ Config lookup
```
**Status:** ✅ API keys loaded from configuration

### JWT Secret Default
```python
# auth/jwt_handler.py:35
self.secret = self.config.get(
    "jwt_secret", auth_config.get("jwt_secret", "change-me-in-production")  # ⚠️ SECURITY RISK
)
```
**Status:** ⚠️ Uses predictable default if JWT_SECRET not set

---

## SQL Injection Test

```python
# api/v2/webhooks.py:171-181 - SAFE
query = "SELECT * FROM api_webhooks WHERE 1=1"
params = []
if active is not None:
    query += " AND active = %s"  # Parameterized
    params.append(int(active))
query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"  # Parameterized
params.extend([limit, offset])
cursor.execute(query, params)  # Safe!
```
**Status:** ✅ Using parameterized queries

---

## Recommendations

### Immediate (Before Next Deploy)
1. [HIGH] Set JWT_SECRET in environment, remove default fallback
2. [MEDIUM] Validate CORS_ORIGIN is not `*` or `null` in production
3. [MEDIUM] Implement full webhook signature verification (if not already done)

### Short-term (This Week)
1. [MEDIUM] Add webhook signature verification tests
2. [LOW] Document security configuration requirements
3. [LOW] Add security audit to CI/CD pipeline

---

**Total Findings:** 6
**Critical:** 0 | **High:** 1 | **Medium:** 3 | **Low:** 2

**Auditor:** Claude Code Agent  
**Date:** 2026-07-09