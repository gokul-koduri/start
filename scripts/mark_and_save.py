#!/usr/bin/env python3
"""Mark a task item as complete and save to markdown file.

This script sets the condition: when marking an item as complete,
automatically save the current task state to the dated .md file.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
STATE_FILE = PROJECT_ROOT / "work_state.json"
TASKS_DIR = PROJECT_ROOT / "tasks"

# Frontmatter template
FRONTMATTER_TEMPLATE = """---
name: daily-tasks
date: {date}
created: {created}
updated: {updated}
session_id: "{session_id}"
metadata:
  type: task-persistence
  task_count: {task_count}
  completed_count: {completed_count}
---
"""


def load_state() -> dict:
    """Load work state from file."""
    if not STATE_FILE.exists():
        return {"tasks": {}, "last_active": None, "last_message": ""}
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_state(state: dict):
    """Save state to file."""
    state["last_active"] = datetime.now().isoformat()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def mark_complete(task_id: str, item: str, save: bool = True):
    """Mark an item as complete and persist to markdown.

    This sets the condition: when marking complete → save to file.
    """
    state = load_state()
    tasks = state.get("tasks", {})

    if task_id not in tasks:
        print(f"Task '{task_id}' not found")
        print(f"Available tasks: {list(tasks.keys())}")
        return False

    task = tasks[task_id]
    remaining = task.get("remaining_items", [])
    completed = task.get("completed_items", [])

    if item not in remaining:
        print(f"Item '{item}' not found in task '{task_id}'")
        print(f"Remaining items: {remaining}")
        return False

    # Mark complete
    remaining.remove(item)
    completed.append(item)
    task["remaining_items"] = remaining
    task["completed_items"] = completed

    save_state(state)
    print(f"✓ Marked complete: [{task_id}] {item}")

    # CONDITION: auto-save to markdown
    if save:
        date = datetime.now().strftime("%Y-%m-%d")
        target = save_tasks_to_file(date)
        print(f"✓ Saved to: {target}")

    return True


def build_content(state: dict, date: str) -> str:
    """Build markdown content from state."""
    tasks = state.get("tasks", {})
    total = len(tasks)
    done = sum(1 for t in tasks.values() if not t.get("remaining_items"))

    last_active = state.get("last_active")
    started = ""
    ended = datetime.now().strftime("%H:%M")
    if last_active:
        try:
            dt = datetime.fromisoformat(last_active)
            started = dt.strftime("%H:%M")
        except (ValueError, TypeError):
            started = last_active[:16] if len(last_active) >= 16 else last_active

    content = FRONTMATTER_TEMPLATE.format(
        date=date,
        created=datetime.now().isoformat(),
        updated=datetime.now().isoformat(),
        session_id=f"{date}-{datetime.now().strftime('%H%M')}",
        task_count=total,
        completed_count=done,
    )

    content += f"# Daily Tasks: {date}\n\n"
    content += "## Session Summary\n\n"
    content += "| Field | Value |\n|-------|-------|\n"
    content += f"| Started | {started or 'N/A'} |\n"
    content += f"| Ended | {ended} |\n"
    content += f"| Tasks Active | {total} |\n"
    content += f"| Completed | {done} |\n\n"
    if state.get("last_message"):
        content += f"**Last Activity:** {state['last_message']}\n\n"
    content += "---\n\n"

    for task_id, task in tasks.items():
        name = task.get("name", task_id)
        status = task.get("status", "unknown")
        phase = task.get("phase", "")
        remaining = task.get("remaining_items", [])
        completed = task.get("completed_items", [])
        last_action = task.get("last_action", "")

        content += f"## Task: {name}\n\n"
        content += "| Field | Value |\n|-------|-------|\n"
        content += f"| Task ID | {task_id} |\n"
        content += f"| Status | {status} |\n"
        if phase:
            content += f"| Phase | {phase} |\n"
        content += "\n"

        if remaining:
            content += "### Remaining Items\n"
            for i in remaining:
                content += f"- [ ] {i}\n"
            content += "\n"
        if completed:
            content += "### Completed Items\n"
            for i in completed:
                content += f"- [x] {i}\n"
            content += "\n"
        if last_action:
            content += f"**Last Action:** {last_action}\n\n"
        content += "---\n\n"

    content += "## Next Steps\n\n"
    count = 0
    for task_id, task in tasks.items():
        remaining = task.get("remaining_items", [])
        if remaining:
            name = task.get("name", task_id)
            count += 1
            content += f"{count}. **{name}:** {remaining[0]}"
            if len(remaining) > 1:
                content += f" (and {len(remaining) - 1} more)"
            content += "\n"
    if count == 0:
        content += "_No pending items._\n"

    return content


def save_tasks_to_file(date: str = None, update_idx: bool = True) -> Path:
    """Save current task state to markdown file."""
    TASKS_DIR.mkdir(exist_ok=True)
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    target = TASKS_DIR / f"{date}.md"
    state = load_state()
    content = build_content(state, date)

    with open(target, "w") as f:
        f.write(content)

    if update_idx:
        update_index(date, target)

    return target


def update_index(date: str, target: Path):
    """Update tasks index."""
    idx_file = TASKS_DIR / "index.md"
    marker = f"- [{date}]"

    if idx_file.exists():
        content = open(idx_file).read()
        if marker not in content:
            with open(idx_file, "a") as f:
                f.write(f"- [{date}]({target.name})\n")
    else:
        content = "# Task Persistence Index\n\nDaily task files.\n\n## Files\n\n"
        content += f"- [{date}]({target.name})\n"
        with open(idx_file, "w") as f:
            f.write(content)


def list_tasks():
    """List all tasks."""
    state = load_state()
    tasks = state.get("tasks", {})

    if not tasks:
        print("No tasks found.")
        return

    print("\nAvailable tasks:\n")
    for task_id, task in tasks.items():
        name = task.get("name", task_id)
        status = task.get("status", "unknown")
        remaining = task.get("remaining_items", [])
        completed = task.get("completed_items", [])

        print(f"## {name} [{status}]")
        print(f"   Task ID: {task_id}")
        if completed:
            print(f"   Completed ({len(completed)}):")
            for i in completed:
                print(f"     - ✓ {i}")
        if remaining:
            print(f"   Remaining ({len(remaining)}):")
            for i in remaining:
                print(f"     - [ ] {i}")
        else:
            print("   (All items completed)")
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Mark a task item as complete and save to markdown."
    )
    parser.add_argument("task_id", nargs="?", help="Task identifier ('list' to show all)")
    parser.add_argument("item", nargs="?", help="Item text to mark complete")
    parser.add_argument("--no-save", action="store_true", help="Don't save to markdown")
    parser.add_argument("--list", action="store_true", help="List all tasks")

    args = parser.parse_args()

    if args.list or (args.task_id and args.task_id.lower() == "list"):
        list_tasks()
        sys.exit(0)

    if not args.task_id or not args.item:
        print("Usage: mark_and_save.py <task_id> <item_text>")
        print("       mark_and_save.py --list")
        sys.exit(1)

    mark_complete(args.task_id, args.item, save=not args.no_save)