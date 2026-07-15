#!/usr/bin/env python3
"""Save task state to markdown files for persistence across sessions.

This script reads the current work state from work_state.json and saves it
to a dated markdown file in the tasks/ directory for human-readable persistence.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Default tasks directory
TASKS_DIR = PROJECT_ROOT / "tasks"
INDEX_FILE = TASKS_DIR / "index.md"
STATE_FILE = PROJECT_ROOT / "work_state.json"

# Frontmatter template following memory/ format
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


def ensure_tasks_dir():
    """Ensure tasks directory exists."""
    TASKS_DIR.mkdir(exist_ok=True)


def load_work_state() -> dict:
    """Load work state from work_state.json."""
    import json

    if not STATE_FILE.exists():
        print(f"No work state found at {STATE_FILE}")
        return {"tasks": {}, "last_active": None, "last_message": ""}

    with open(STATE_FILE, "r") as f:
        return json.load(f)


def build_content(state: dict, date: str) -> str:
    """Build markdown content from state dictionary."""
    tasks = state.get("tasks", {})
    total_tasks = len(tasks)
    completed_tasks = sum(
        1 for t in tasks.values()
        if not t.get("remaining_items")
    )

    # Calculate session times
    last_active = state.get("last_active")
    started = ""
    ended = datetime.now().strftime("%H:%M")

    if last_active:
        try:
            dt = datetime.fromisoformat(last_active)
            started = dt.strftime("%H:%M")
        except (ValueError, TypeError):
            started = last_active[:16] if len(last_active) >= 16 else last_active

    # Build frontmatter
    content = FRONTMATTER_TEMPLATE.format(
        date=date,
        created=datetime.now().isoformat(),
        updated=datetime.now().isoformat(),
        session_id=f"{date}-{datetime.now().strftime('%H%M')}",
        task_count=total_tasks,
        completed_count=completed_tasks,
    )

    # Session summary
    content += f"# Daily Tasks: {date}\n\n"
    content += "## Session Summary\n\n"
    content += "| Field | Value |\n|-------|-------|\n"
    content += f"| Started | {started or 'N/A'} |\n"
    content += f"| Ended | {ended} |\n"
    content += f"| Tasks Active | {total_tasks} |\n"
    content += f"| Completed | {completed_tasks} |\n\n"

    if state.get("last_message"):
        content += f"**Last Activity:** {state['last_message']}\n\n"

    content += "---\n\n"

    # Task details
    for task_id, task in tasks.items():
        name = task.get("name", task_id)
        status = task.get("status", "unknown")
        phase = task.get("phase", "")
        remaining = task.get("remaining_items", [])
        completed = task.get("completed_items", [])
        current_step = task.get("current_step", "")
        suggested_next = task.get("suggested_next", "")
        last_action = task.get("last_action", "")
        notes = task.get("notes", [])

        content += f"## Task: {name}\n\n"
        content += "| Field | Value |\n|-------|-------|\n"
        content += f"| Task ID | {task_id} |\n"
        content += f"| Status | {status} |\n"
        if phase:
            content += f"| Phase | {phase} |\n"
        if current_step:
            content += f"| Current Step | {current_step} |\n"
        if suggested_next:
            content += f"| Suggested Next | {suggested_next} |\n"
        content += "\n"

        if remaining:
            content += "### Remaining Items\n"
            for item in remaining:
                content += f"- [ ] {item}\n"
            content += "\n"

        if completed:
            content += "### Completed Items\n"
            for item in completed:
                content += f"- [x] {item}\n"
            content += "\n"

        if notes:
            content += "### Notes\n"
            for note in notes[:5]:  # Limit to last 5 notes
                content += f"- {note[:100]}"
                if len(note) > 100:
                    content += "..."
                content += "\n"
            content += "\n"

        if last_action:
            content += f"**Last Action:** {last_action}\n\n"

        content += "---\n\n"

    # Next steps section
    content += "## Next Steps\n\n"
    next_steps_count = 0

    for task_id, task in tasks.items():
        remaining = task.get("remaining_items", [])
        if remaining:
            name = task.get("name", task_id)
            next_steps_count += 1
            content += f"{next_steps_count}. **{name}:** {remaining[0]}"
            if len(remaining) > 1:
                content += f" (and {len(remaining) - 1} more)"
            content += "\n"

    if next_steps_count == 0:
        content += "_No pending items._\n"

    return content


def update_index(date: str, target_file: Path):
    """Update the tasks index file."""
    if not INDEX_FILE.exists():
        # Create new index
        content = "# Task Persistence Index\n\n"
        content += "Daily task files for session tracking.\n\n"
        content += "## Files\n\n"
        content += f"- [{date}]({target_file.name}) - {datetime.now().strftime('%H:%M')}\n"

        with open(INDEX_FILE, "w") as f:
            f.write(content)
    else:
        # Append to existing index
        with open(INDEX_FILE, "r") as f:
            content = f.read()

        # Check if date already exists
        if f"[{date}]" not in content:
            # Find insertion point (before "---" if it exists)
            insert_marker = "\n## Files\n\n"
            if insert_marker in content:
                # Find the line after "## Files\n\n"
                idx = content.find(insert_marker) + len(insert_marker)
                lines = content[:idx].split("\n")
                lines.append(f"- [{date}]({target_file.name}) - {datetime.now().strftime('%H:%M')}")
                content = "\n".join(lines) + content[idx:]
            else:
                content += f"- [{date}]({target_file.name}) - {datetime.now().strftime('%H:%M')}\n"

            with open(INDEX_FILE, "w") as f:
                f.write(content)


def save_tasks(date: str = None, dry_run: bool = False, update_idx: bool = True) -> Path:
    """Save current task state to markdown file.

    Args:
        date: Date in YYYY-MM-DD format (defaults to today)
        dry_run: If True, print content without saving
        update_idx: If True, update the index file

    Returns:
        Path to the saved file
    """
    ensure_tasks_dir()

    # Determine target date
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    target_file = TASKS_DIR / f"{date}.md"

    # Load current state
    state = load_work_state()

    # Build content
    content = build_content(state, date)

    if dry_run:
        print(content)
        print(f"\nWould save to: {target_file}")
        return target_file

    # Write file
    with open(target_file, "w") as f:
        f.write(content)

    print(f"Saved to: {target_file}")

    # Update index
    if update_idx:
        update_index(date, target_file)
        print(f"Index updated: {INDEX_FILE}")

    return target_file


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Save task state to markdown files for persistence."
    )
    parser.add_argument(
        "--date",
        help="Date in YYYY-MM-DD format (defaults to today)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print content without saving to file"
    )
    parser.add_argument(
        "--no-index",
        action="store_true",
        help="Don't update the index file"
    )

    args = parser.parse_args()

    save_tasks(
        date=args.date,
        dry_run=args.dry_run,
        update_idx=not args.no_index
    )