# Communication Interface Specification

**Version:** 1.0  
**Date:** 2026-07-09  

---

## Overview

This document defines the communication interface for all tasks in the Startup Research Report project. Every component communicates through standardized message formats to maintain workflow alignment.

---

## Message Types

### 1. TASK_ASSIGNMENT

**Sent when:** Starting new work

```markdown
**From:** [Agent/Role]
**To:** [Agent/Role]
**Type:** TASK_ASSIGNMENT
**Task ID:** PLAN-2026-XXX
**Priority:** P0 | P1 | P2

**Task:** [Description]
**Context:** [Relevant background]
**Required Output:** [Deliverable]
**Alignment Check:** Confirmed against product vision ✓
```

### 2. PLAN_SUBMISSION

**Sent when:** Sending plan for approval

```markdown
**From:** Plan Agent / Claude
**To:** Approver
**Type:** PLAN_SUBMISSION
**Plan ID:** PLAN-2026-XXX
**Plan File:** docs/plans/YYYY-MM-DD-task-name.md

**Summary:**
- Scope: [What's included]
- Effort: [Estimated hours]
- Critical Files: [Top 5 files]
- Risks: [Identified risks]

**Request:** APPROVAL_REQUESTED
**Approver:** [Designated approver]
```

### 3. APPROVAL_RESPONSE

**Sent when:** Responding to plan submission

```markdown
**From:** Approver
**To:** Agent
**Type:** APPROVAL_RESPONSE
**Plan ID:** PLAN-2026-XXX
**Response:** APPROVED | REJECTED | REQUEST_CHANGES

**Feedback:**
[Approval notes or rejection reason]

**Conditions:** [Any conditions if approved]
```

### 4. SCOPE_CHANGE

**Sent when:** Scope changes during implementation

```markdown
**From:** [Agent/Role]
**To:** [Stakeholders]
**Type:** SCOPE_CHANGE
**Original Plan:** PLAN-2026-XXX
**New Plan:** PLAN-2026-XXX-v2

**What Changed:**
- Original: [Original scope]
- New: [What changed]

**Impact:**
- Effort: [Before → After]
- Timeline: [Before → After]
- Risk: [Change in risk level]

**Request:** RE-APPROVAL_REQUIRED
```

### 5. STATUS_UPDATE

**Sent when:** During implementation, at checkpoints

```markdown
**From:** [Agent/Role]
**To:** [Stakeholders]
**Type:** STATUS_UPDATE
**Task ID:** PLAN-2026-XXX

**Progress:** XX%
**Phase:** [Current phase]
**Last Completed:** [What was done]
**Next Step:** [What's next]
**Blockers:** [Any blockers or None]
**Confidence:** HIGH | MEDIUM | LOW
```

### 6. COMPLETION_REPORT

**Sent when:** Task finished

```markdown
**From:** [Agent/Role]
**To:** [Stakeholders]
**Type:** COMPLETION_REPORT
**Task ID:** PLAN-2026-XXX

**Summary:**
- Duration: [Actual time spent]
- Deliverables: [List of outputs]
- Validation: [How verified]

**Retrospective:**
- What went well: [Notes]
- What to improve: [Notes]
```

---

## State Machine

```
DRAFT → PENDING_APPROVAL → APPROVED → IN_PROGRESS → VALIDATING → COMPLETED
         ↓                  ↓
     REJECTED         REVISION_REQUESTED
         ↓
     DRAFT (revised)
```

---

## Filing Convention

All records filed at:
- Plans: `docs/plans/PLAN-YYYY-NNN-title.md`
- Status: Git commit messages (conventional commits)
- Approvals: Documented in plan file approval table
- Scope changes: Documented as plan revisions

---

## Response Time Expectations

| Message Type | Expected Response |
|--------------|-------------------|
| TASK_ASSIGNMENT | Within 4 hours |
| APPROVAL_REQUEST | Within 24 hours |
| SCOPE_CHANGE | Within 4 hours (urgent) |
| STATUS_UPDATE | Weekly or on phase completion |

---

## Related Documents

- [RULES.md](RULES.md) — Core workflow rules
- [APPROVAL.md](APPROVAL.md) — Approval process
- [SCOPE_ESCALATION.md](SCOPE_ESCALATION.md) — Scope change handling