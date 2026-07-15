# Feature Plan: [Feature Name]

**Created:** YYYY-MM-DD  
**Status:** DRAFT  
**Plan ID:** PLAN-YYYY-NNN  
**Type:** Feature  
**Author:** [Your Name]

---

## Context

### Feature Description
Brief description of the feature.

### Problem Statement
What problem does this solve?

### User Story
As a [user type], I want [goal] so that [benefit].

### Dependencies
- [ ] Related feature PLAN-YYYY-NNN (if exists)
- [ ] External dependency (if any)

---

## Analysis

### Current Behavior
How does this work today?

### Proposed Behavior
How will it work after implementation?

### Alternatives Considered
1. Alternative approach A — why rejected
2. Alternative approach B — why rejected

---

## Implementation Plan

### Phase 1: Research
- [ ] Research existing patterns in codebase
- [ ] Review similar PRDs in docs/prd/
- [ ] Define API contracts if needed

### Phase 2: Design
- [ ] Design data model changes
- [ ] Design API endpoints
- [ ] Design UI/UX changes
- [ ] Create/update PRD

### Phase 3: Backend Implementation
- [ ] Implement data models
- [ ] Implement API endpoints
- [ ] Add business logic
- [ ] Write database migrations

### Phase 4: Frontend Implementation (if applicable)
- [ ] Implement UI components
- [ ] Connect to API
- [ ] Add error handling

### Phase 5: Testing
- [ ] Add unit tests
- [ ] Add integration tests
- [ ] Manual testing checklist

### Phase 6: Documentation
- [ ] Update API docs
- [ ] Update user docs
- [ ] Update docs/prd/

---

## Critical Files

| File | Change Type | Description |
|------|-------------|-------------|
| `db/schema.py` | Modify | Add new tables/columns |
| `api/v2/endpoint.py` | Create | New API endpoint |
| `agents/agent.py` | Modify | Add new logic |

---

## Rollback Plan

```bash
# Rollback commands
git revert [commit-hash]
```

---

## Acceptance Criteria

- [ ] Feature works as specified in user story
- [ ] All API endpoints return correct responses
- [ ] All tests pass
- [ ] No breaking changes to existing features
- [ ] Documentation updated

---

## Approval

| Reviewer | Role | Status | Date | Notes |
|----------|------|--------|------|-------|
| [Name] | Tech Lead | PENDING | - | - |
| [Name] | Product | PENDING | - | - |

**Minimum Approvals Required:** 1 (Tech Lead)

---

*Feature template from docs/plans/templates/feature-plan.md*