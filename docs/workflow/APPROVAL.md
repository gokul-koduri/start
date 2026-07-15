# Approval Process

**Version:** 1.0  
**Date:** 2026-07-09  

---

## Overview

This document defines the approval process for plans in the Startup Research Report project.

---

## Approval Flow

```
┌────────────────────────────────────────────────────────────────┐
│                        APPROVAL FLOW                           │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  1. Plan Created (Status: DRAFT)                               │
│         ↓                                                      │
│  2. Plan Submitted for Review (Status: PENDING_APPROVAL)      │
│         ↓                                                      │
│  3. Reviewer(s) Evaluate                                       │
│         ↓                                                      │
│     ┌───────────────────────────────────┐                      │
│     ↓         ↓              ↓          ↓                      │
│  APPROVED  REJECTED   REQUEST_CHANGES   SKIP (Research)        │
│     ↓         ↓              ↓                                 │
│     └────→ IN_PROGRESS ←──────┘                                │
│              (revised)                                          │
│                       ↓                                          │
│              VALIDATING → COMPLETED                            │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## Approval Levels

| Level | When Required | Approvers | Minimum Approvals |
|-------|---------------|-----------|-------------------|
| **P0 - Critical** | Production down, security issues | Tech Lead | 1 (expedited allowed) |
| **P1 - High** | Major features, breaking changes | Tech Lead | 1 |
| **P2 - Medium** | Features, significant refactors | Tech Lead or Peer | 1 |
| **P3 - Low** | Small changes, non-critical | Peer review | 1 (lazy approval) |

---

## Review Criteria

When reviewing a plan, evaluate:

### 1. Alignment Check
- [ ] Aligns with product vision and roadmap
- [ ] Addresses stated requirements
- [ ] No unintended side effects identified

### 2. Technical Soundness
- [ ] Approach is technically feasible
- [ ] Dependencies are identified and manageable
- [ ] Risks are acknowledged with mitigation plans

### 3. Completeness
- [ ] All required sections filled
- [ ] Critical files listed
- [ ] Acceptance criteria clear
- [ ] Rollback plan documented

### 4. Efficiency
- [ ] Implementation steps are clear
- [ ] No unnecessary complexity
- [ ] Leverages existing patterns/code

---

## Approval Actions

### APPROVED ✓
Plan is ready for implementation. Log in approval table:
```
| Reviewer | APPROVED | 2026-07-09 | Notes |
```

### REJECTED ✗
Plan must be revised. Log in approval table:
```
| Reviewer | REJECTED | 2026-07-09 | Reason: [explanation] |
```
Return to DRAFT status, address feedback, resubmit.

### REQUEST_CHANGES ⚠
Specific sections need changes. Log in approval table:
```
| Reviewer | REQUEST_CHANGES | 2026-07-09 | Section: [which], Changes needed: [what] |
```
Returnplan to DRAFT status, make changes, resubmit.

---

## Expedited Approval (P0/P1 Bugs)

For critical bugs where time is essential:

1. Create plan with "EXPEDITED" flag
2. Submit to Tech Lead with urgency note
3. Tech Lead reviews within 2 hours
4. If approved, implementation starts immediately
5. Full documentation completed post-factum

---

## Approval Checklist for Submitter

Before requesting approval:

- [ ] Plan follows TEMPLATE.md structure
- [ ] All sections completed (no TODOs left)
- [ ] Critical files verified to exist
- [ ] Alignment check completed
- [ ] Tests planned for validation
- [ ] Rollback plan documented

---

## Related Documents

- [RULES.md](RULES.md) — Core workflow rules
- [COMMUNICATION.md](COMMUNICATION.md) — Communication interface
- [SCOPE_ESCALATION.md](SCOPE_ESCALATION.md) — Scope change handling