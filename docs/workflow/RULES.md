# Workflow Rules — Startup Research Report

**Version:** 1.0  
**Date:** 2026-07-09  
**Author:** Plan Agent (Codex)

---

## The 5-Step Task Execution Workflow

Every task follows this workflow **without exception**:

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     TASK EXECUTION WORKFLOW                              │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. TASK        → Define clearly, document at docs/plans/               │
│         ↓                                                                    │
│  2. CONTEXT     → Gather from codebase, read relevant files              │
│         ↓                                                                    │
│  3. PLAN        → Create plan using Plan Agent (Codex)                   │
│         ↓                                                                    │
│  4. APPROVAL    → Document plan, request approval, await response         │
│         ↓                                                                    │
│  5. IMPLEMENT   → Execute approved plan, validate results                │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Step Details

### Step 1: Task Definition
- Clearly define the task objective
- Assign a Plan ID (e.g., `PLAN-2026-001`)
- Document in `docs/plans/YYYY-MM-DD-task-name.md`

### Step 2: Context Gathering
- Research existing patterns in codebase
- Read relevant files before editing
- Document context gathered in plan

### Step 3: Plan Creation (Plan Agent / Codex)
For every task, send context to Plan Agent:
```
Task: [Description]
Context: [Relevant files, patterns, constraints]
Target: [Expected outcome]
Output: [Implementation plan]
```
- Create detailed implementation plan
- Identify critical files to modify
- Document dependencies and risks

### Step 4: Plan Approval
- Document plan in `docs/plans/`
- Request approval from designated approver
- Wait for explicit approval before proceeding

### Step 5: Implementation & Validation
- Implement according to approved plan
- Validate against acceptance criteria
- Update plan status to COMPLETED

---

## Scope Change Rule

**IF scope changes mid-implementation:**

```
STOP → Document the change
     → Create new plan version (PLAN-2026-001-v2)
     → Request new approval
     → DO NOT continue without re-approval
```

---

## Approval Requirements

| Task Type | Requires Plan | Requires Approval | Exception |
|-----------|--------------|-------------------|-----------|
| Feature (>2h) | Yes | Yes | - |
| Feature (<2h) | Yes | No | - |
| Bugfix (>1h) | Yes | Yes | Expedited for P0/P1 |
| Bugfix (<1h) | Yes | No | - |
| Hotfix | Post-factum | Retrospective | Must document after |
| Research/Spike | Yes | No | Informational only |
| Documentation | Yes (if >1h) | No | - |

---

## Alignment Checkpoints

Before any implementation, verify:

- [ ] Does this align with product vision?
- [ ] Does this align with current sprint goal?
- [ ] Does this align with roadmap?
- [ ] Are there any conflicting priorities?

**If NO to any:** STOP and escalate before proceeding.

---

## Plan Documentation

All plans MUST be documented at `docs/plans/YYYY-MM-DD-task-name.md`

Plans must include:
- ✓ Task objective
- ✓ Current vs target state
- ✓ Implementation steps with file paths
- ✓ Critical files list
- ✓ Validation criteria
- ✓ Rollback plan

---

## Trivial Task Exception

Tasks estimated under 30 minutes may skip the formal plan/approval cycle, but must:
- Document the change in a brief plan or commit message
- Be aligned with project objectives
- Include tests if modifying behavior

---

## Related Documents

- [COMMUNICATION.md](COMMUNICATION.md) — Communication interface specification
- [APPROVAL.md](APPROVAL.md) — Approval process
- [SCOPE_ESCALATION.md](SCOPE_ESCALATION.md) — Scope change handling