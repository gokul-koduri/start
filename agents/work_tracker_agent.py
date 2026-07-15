"""Work Tracker Agent - Tracks project work progress and provides status recovery."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

_logger = logging.getLogger(__name__)

# Default state file location
STATE_FILE = Path(__file__).parent.parent / "work_state.json"

# Greeting triggers - simple messages that should trigger welcome
GREETINGS = {'hi', 'hey', 'hello', 'start', 'continue', 'resume'}

# Command aliases
COMMANDS = {
    'status', 'stat', 'progress', 'state',
    'resume', 'continue', 'start',
    'track', 'log', 'note',
    'help', 'h', '?",
}


def is_greeting(message: str) -> bool:
    """Check if message is a simple greeting (hi/hey/hello)."""
    cleaned = message.lower().strip().rstrip('.!?')
    return cleaned in GREETINGS


def is_command(message: str) -> bool:
    """Check if message starts with a known command."""
    cleaned = message.lower().strip().lstrip('/')
    first_word = cleaned.split()[0] if cleaned else ''
    return first_word in COMMANDS


class WorkTracker:
    """Track and restore project work state."""

    def __init__(self, state_file: Path = STATE_FILE):
        self.state_file = state_file
        self.action_count = 0
        self.AUTO_SAVE_INTERVAL = 5  # Auto-save every N actions
        self.state = self._load_state()

    def _load_state(self) -> dict:
        """Load state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                _logger.warning("Invalid state file, using empty state")
        return self._create_empty_state()

    def _create_empty_state(self) -> dict:
        """Create empty state structure."""
        return {
            "version": 1,
            "last_active": None,
            "last_message": "",
            "tasks": {},
        }

    def save(self):
        """Save state to file."""
        self.state["last_active"] = datetime.now().isoformat()
        with open(self.state_file, "w") as f:
            json.dump(self.state, f, indent=2)

    def should_greet(self, message: str = None) -> bool:
        """Check if we should greet based on message."""
        if message is None:
            return True  # No message = show status by default
        return is_greeting(message) or is_command(message)

    def track_action(self, action_type: str, details: str, task_id: str = None):
        """Track a significant action and auto-save periodically."""
        self.action_count += 1
        self.set_last_message(f"{action_type}: {details}")
        if task_id:
            self.update_task(task_id, last_action=f"{action_type}: {details}")

        # Auto-save every N actions
        if self.action_count % self.AUTO_SAVE_INTERVAL == 0:
            self.save()
            _logger.info("[Auto-saved] Progress tracked automatically")

    def get_status(self) -> str:
        """Get human-readable status of all tasks."""
        lines = []

        if self.state.get("last_message"):
            lines.append(f"**Last Activity**: {self.state['last_message']}")
            lines.append("")

        for task_id, task in self.state.get("tasks", {}).items():
            status = task.get("status", "unknown")
            phase = task.get("phase", "")
            name = task.get("name", task_id)

            lines.append(f"## {name}")
            lines.append(f"**Status**: {status}")
            if phase:
                lines.append(f"**Phase**: {phase}")

            last_action = task.get("last_action")
            if last_action:
                lines.append(f"**Last Action**: {last_action}")

            completed = task.get("completed_items", [])
            remaining = task.get("remaining_items", [])

            if completed:
                lines.append(f"**Completed** ({len(completed)}):")
                for item in completed[-3:]:  # Show last 3
                    lines.append(f"  - {item}")
                if len(completed) > 3:
                    lines.append(f"  ... and {len(completed) - 3} more")

            if remaining:
                lines.append(f"**Remaining** ({len(remaining)}):")
                for item in remaining:
                    lines.append(f"  - {item}")

            notes = task.get("notes", [])
            if notes:
                lines.append(f"**Notes** ({len(notes)}):")
                for note in notes[:2]:  # Show last 2
                    lines.append(f"  - {note[:80]}...")

            lines.append("")

        return "\n".join(lines)

    def get_options(self) -> list[dict]:
        """Get available action options for CLI."""
        options = [
            {
                "id": "continue",
                "label": "Continue where we left off",
                "description": "Resume the last task being worked on",
                "emoji": "▶️",
            },
            {
                "id": "status",
                "label": "View full project status",
                "description": "See detailed status of all tasks",
                "emoji": "📊",
            },
        ]

        # Add task-specific options
        for task_id, task in self.state.get("tasks", {}).items():
            if task.get("remaining_items"):
                options.append({
                    "id": f"continue_{task_id}",
                    "label": f"Continue: {task.get('name', task_id)}",
                    "description": f"Work on remaining: {', '.join(task.get('remaining_items', [])[:2])}",
                    "emoji": "🔧",
                })

        options.append({
            "id": "new_task",
            "label": "Start new task",
            "description": "Begin work on something new",
            "emoji": "✨",
        })

        options.append({
            "id": "help",
            "label": "Show help",
            "description": "Display all available commands",
            "emoji": "❓",
        })

        return options

    def display_welcome(self, extended: bool = True) -> str:
        """Display welcome message with status.

        Args:
            extended: If True, show full task details. If False, show brief greeting.
        """
        lines = [
            "=" * 60,
            "Hi! Welcome back to Startup Research Report",
            "=" * 60,
            "",
        ]

        # Show last active time
        last_active = self.state.get("last_active")
        if last_active:
            try:
                dt = datetime.fromisoformat(last_active)
                lines.append(f"Last active: {dt.strftime('%Y-%m-%d %H:%M')}")
            except (ValueError, TypeError):
                lines.append(f"Last active: {last_active}")
            lines.append("")

        # Show what was being worked on
        last_msg = self.state.get("last_message")
        if last_msg and extended:
            lines.append(f"Last work: {last_msg}")
            lines.append("")

        # Show current tasks with full details
        tasks = self.state.get("tasks", {})
        if tasks:
            # Find the most recent/in-progress task
            in_progress_tasks = [
                (tid, t) for tid, t in tasks.items()
                if t.get("remaining_items")
            ]

            if in_progress_tasks:
                lines.append("--- CURRENT TASKS ---")
                for task_id, task in in_progress_tasks:
                    name = task.get("name", task_id)
                    status = task.get("status", "unknown")
                    phase = task.get("phase", "")
                    current_step = task.get("current_step", "")
                    suggested_next = task.get("suggested_next", "")
                    completed = task.get("completed_items", [])
                    remaining = task.get("remaining_items", [])
                    last_action = task.get("last_action", "")

                    lines.append(f"\n{name}")
                    lines.append(f"Status: {status}" + (f" [{phase}]" if phase else ""))
                    lines.append(f"Progress: {len(completed)} completed, {len(remaining)} remaining")

                    if current_step:
                        lines.append(f"Current step: {current_step}")
                    if suggested_next:
                        lines.append(f"Next: {suggested_next}")
                    if last_action:
                        lines.append(f"Last action: {last_action}")

                    if remaining and extended:
                        lines.append(f"Remaining items:")
                        for item in remaining:
                            lines.append(f"  - {item}")

                    lines.append("")

            # Show completed tasks
            completed_tasks = [
                (tid, t) for tid, t in tasks.items()
                if not t.get("remaining_items")
            ]
            if completed_tasks and extended:
                lines.append("--- COMPLETED TASKS ---")
                for task_id, task in completed_tasks:
                    name = task.get("name", task_id)
                    status = task.get("status", "done")
                    lines.append(f"  {name} ({status})")

        else:
            lines.append("No active tasks.")
            lines.append("")
            lines.append("Say 'hi' when you want to start tracking work.")

        # Show options
        lines.append("")
        lines.append("Available commands:")
        lines.append("  /status  - View full project status")
        lines.append("  /resume  - Continue where we left off")
        lines.append("  /track   - Track progress on current task")
        lines.append("  /track completed X - Mark item as complete")

        lines.append("")

        return "\n".join(lines)

    def update_task(self, task_id: str, **kwargs):
        """Update a task's state."""
        if task_id not in self.state["tasks"]:
            self.state["tasks"][task_id] = {"name": task_id}

        self.state["tasks"][task_id].update(kwargs)
        self.state["last_message"] = kwargs.get("last_action", "")
        self.save()

    def complete_task_item(self, task_id: str, item: str):
        """Move an item from remaining to completed."""
        if task_id not in self.state["tasks"]:
            return False

        task = self.state["tasks"][task_id]
        remaining = task.get("remaining_items", [])
        completed = task.get("completed_items", [])

        if item in remaining:
            remaining.remove(item)
            completed.append(item)
            task["remaining_items"] = remaining
            task["completed_items"] = completed
            self.save()
            return True
        return False

    def set_last_message(self, message: str):
        """Update the last action message."""
        self.state["last_message"] = message
        self.save()

    def new_task(self, task_id: str, name: str, remaining_items: list = None,
                 phase: str = "Starting", current_step: str = None, suggested_next: str = None):
        """Create a new task and set it as current.

        Args:
            task_id: Unique identifier for the task
            name: Human-readable task name
            remaining_items: List of items to complete
            phase: Current phase (e.g., "Planning", "Implementing", "Testing")
            current_step: What you're working on right now
            suggested_next: What should be done next

        Returns:
            The created task dict
        """
        self.state["tasks"][task_id] = {
            "name": name,
            "status": "0%",
            "phase": phase,
            "last_action": f"Task created: {name}",
            "completed_items": [],
            "remaining_items": remaining_items or [],
            "file_progress": {},
            "notes": [],
        }
        if current_step:
            self.state["tasks"][task_id]["current_step"] = current_step
        if suggested_next:
            self.state["tasks"][task_id]["suggested_next"] = suggested_next

        self.state["last_message"] = f"Started: {name}"
        self.save()
        return self.state["tasks"][task_id]

    def update_task_progress(self, task_id: str, completed_count: int, total_count: int):
        """Update task progress percentage."""
        if task_id in self.state["tasks"]:
            pct = int(completed_count / total_count * 100) if total_count > 0 else 0
            self.state["tasks"][task_id]["status"] = f"{pct}%"
            self.save()


# Singleton instance
_tracker: Optional[WorkTracker] = None


def get_tracker() -> WorkTracker:
    """Get the singleton tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = WorkTracker()
    return _tracker


if __name__ == "__main__":
    tracker = get_tracker()
    print(tracker.display_welcome())