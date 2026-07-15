# AGENTIC DIRECTIVE

## CODING ENVIRONMENT
- Use the local virtual environment when available: `.venv/bin/python`, `.venv/bin/pytest`, and `.venv/bin/pip`.
- Install project dependencies from `requirements-dev.txt` for local development, or `requirements.txt` for the full stack.
- Read `.env.example` before changing runtime behavior or adding new configuration.
- Prefer targeted `pytest` runs for validation; keep tests close to the touched code.
- Keep changes minimal and consistent with the existing Python style.
- Add or update tests for behavior changes, especially error handling and edge cases.

## WORKFLOW RULES (All Agents)

Every task follows the **5-Step Workflow**:

```
Task → Gather Context → Plan Agent (Codex) → Get Plan → 
Plan Approval Request → Await Approval → Implement → Validate
```

### Workflow Integration

1. **Plans documented at:** `docs/plans/YYYY-MM-DD-task-name.md`
2. **Reference docs at:** `docs/workflow/RULES.md`
3. **Approval required** before implementation (unless trivial, < 30 min)
4. **Scope change = STOP → Document → Re-plan → Re-approve**

### Alignment Check

Before any implementation, verify:
- [ ] Aligns with product vision
- [ ] Aligns with current sprint goal
- [ ] No conflicting priorities

If not aligned, STOP and escalate.

## CLAUDE CODE AUTH

- For Claude Code login, use `claude auth login --console` for API usage billing or `claude auth login --claudeai` for a chat subscription.
- The bare `/login` command is not the correct CLI entrypoint in this workspace.
- If login stops at a browser page, complete the OAuth flow in the browser and let the terminal receive the callback.

## WORKING RULES

- Read relevant files before editing.
- Fix the root cause, not the symptom.
- Do not introduce unrelated refactors.
- Prefer existing scripts and project conventions when running checks.
