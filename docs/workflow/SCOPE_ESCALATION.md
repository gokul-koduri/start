# Scope Change Handling

**Version:** 1.0  
**Date:** 2026-07-09  

---

## Overview

This document defines how to handle scope changes during implementation. Scope changes require stoppage, documentation, re-planning, and re-approval.

---

## What Constitutes a Scope Change

A scope change is any significant deviation from the approved plan:

### Triggers Re-approval Required:
- Adding new files or modules not in original scope
- Removing planned functionality
- Changing API contracts or data models
- Adding new dependencies
- Changing target architecture
- Extending timeline beyond original estimate by >25%
- Discovering work that was "hidden" but necessary

### Does NOT Require Re-approval:
- Minor implementation detail adjustments (within boundaries)
- Bug fixes discovered during implementation that are within scope
- Performance optimizations that don't change behavior
- Documentation updates
- Adding tests for existing functionality

---

## Scope Change Protocol

When scope change is identified:

```
┌────────────────────────────────────────────────────────────────┐
│                    SCOPE CHANGE PROTOCOL                        │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  1. STOP — Do not continue implementation                      │
│         ↓                                                      │
│  2. DOCUMENT — Record what changed and why                     │
│         ↓                                                      │
│  3. RE-PLAN — Create updated plan version (v2, v3, etc.)       │
│         ↓                                                      │
│  4. RE-APPROVAL — Submit for approval with changes noted      │
│         ↓                                                      │
│  5. RESUME — Only after explicit approval                      │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## Scope Change Documentation

### Document in Plan File

Update the plan with scope change section:

```markdown
## Scope Change Log

### Change #1 — YYYY-MM-DD
**Type:** [Discovery | Requirement Change | External Factor]
**What Changed:**
- Original: [Original scope item]
- New: [New scope item]

**Impact:**
- Effort: [+/- N hours]
- Timeline: [+/- N days]
- Risk: [Increased / Decreased / Same]

**Approved By:** [Name] on [Date]
```

### Create New Plan Version

If changes are extensive, create new version:
- `PLAN-2026-001.md` → v2, v3, etc.
- `PLAN-2026-001-v2.md`

---

## Handling Discoveries During Implementation

If you discover something that requires scope change:

### 1. Impact Assessment
- Estimate effort of new work
- Assess risk of including vs. deferring
- Consider downstream effects

### 2. Decision Framework

| Discovery Type | Recommended Action |
|----------------|-------------------|
| Hidden work needed to complete current task | Include in scope, re-approve |
| New feature identified | Create separate plan |
| Bug discovered that blocks work | Create bugfix plan (expedite if P0/P1) |
| Technical constraint found | Re-evaluate approach, may need re-plan |

### 3. Communication

Notify stakeholders immediately:
```
**Type:** SCOPE_CHANGE (URGENT)
**Triggered By:** [Discovery description]
**Impact:** [Assessment of impact]
**Recommendation:** [Include now / Defer / Separate plan]
**Request:** RE-APPROVAL or Guidance
```

---

## Re-approval Requirements

| Change Impact | Required Action |
|---------------|-----------------|
| < 1 hour additional work | Document and continue (notify only) |
| 1-4 hours additional | Quick approval (async OK) |
| > 4 hours or new files | Full re-approval required |
| Changes behavior | Full re-approval required |
| Affects other teams | Notify and coordinate |

---

## Scope Creep Prevention

### Guardrails to Prevent Uncontrolled Scope Creep:

1. **Clear boundaries** — Define what's IN and OUT in initial plan
2. **Checkpoints** — Verify alignment at phase boundaries
3. **Early escalation** — Flag potential changes immediately
4. **No surprises** — Keep stakeholders informed

### Warning Signs of Scope Creep:
- "While we're at it..." requests
- Expanding scope without formal change process
- Missing alignment checkpoints
- Cumulative small changes adding up

---

## Related Documents

- [RULES.md](RULES.md) — Core workflow rules
- [COMMUNICATION.md](COMMUNICATION.md) — Communication interface
- [APPROVAL.md](APPROVAL.md) — Approval process