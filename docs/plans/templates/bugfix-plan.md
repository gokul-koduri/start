# Bugfix Plan: [Bug Description]

**Created:** YYYY-MM-DD  
**Status:** DRAFT  
**Plan ID:** PLAN-YYYY-NNN  
**Type:** Bugfix  
**Severity:** P0 / P1 / P2 / P3  
**Author:** [Your Name]

---

## Context

### Bug Description
What is the bug? Be specific.

### Expected Behavior
What should happen?

### Actual Behavior
What actually happens?

### Steps to Reproduce
1. Go to [location]
2. Do [action]
3. See [error/incorrect behavior]

### Environment
- OS: [e.g., macOS 14.0]
- Browser: [e.g., Chrome 120]
- Version: [e.g., v1.0.0]

---

## Root Cause Analysis

### Initial Hypothesis
My initial guess at the cause.

### Investigation
What did I find?
- File:line — explanation
- File:line — explanation

### Root Cause
The actual root cause statement.

### Why It Wasn't Caught
Why did this pass testing?

---

## Implementation Plan

### Phase 1: Verify Reproduction
- [ ] Set up test environment
- [ ] Confirm bug exists
- [ ] Document exact conditions

### Phase 2: Implement Fix
- [ ] Fix in [file:line]
- [ ] Add regression test
- [ ] Verify fix works

### Phase 3: Validation
- [ ] Run existing tests
- [ ] Manual verification
- [ ] Check for side effects

---

## Critical Files

| File | Line(s) | Original | Fix |
|------|---------|----------|-----|
| `path/to/file.py` | 42-45 | buggy code | fixed code |

---

## Tests to Add

```python
# Unit test for this bug
def test_bug_description():
    """Test that [expected behavior]."""
    # test code
```

---

## Rollback Plan

```bash
git revert [commit-hash]
```

---

## Lesson Learned

What can we learn from this bug? How do we prevent it?

---

## Acceptance Criteria

- [ ] Bug reproduced in test environment
- [ ] Fix applied successfully
- [ ] Bug no longer occurs
- [ ] Regression test added
- [ ] All existing tests pass

---

## Approval

| Reviewer | Status | Date | Notes |
|----------|--------|------|-------|
| [Name] | PENDING | - | - |

**For P0/P1 bugs:** Expedited approval allowed (1 approval, verify then approve)

---

*Bugfix template from docs/plans/templates/bugfix-plan.md*