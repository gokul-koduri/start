#!/usr/bin/env python3
"""
Workflow CLI for plan management.

Usage:
    python scripts/workflow_cli.py create <name>
    python scripts/workflow_cli.py list [--status STATUS]
    python scripts/workflow_cli.py status <plan-id> <new-status>
    python scripts/workflow_cli.py approve <plan-id>
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
PLANS_DIR = PROJECT_ROOT / "docs" / "plans"
TEMPLATE = PLANS_DIR / "TEMPLATE.md"
README = PLANS_DIR / "README.md"


def create_plan(name: str) -> Path:
    """Create a new plan from template."""
    if not TEMPLATE.exists():
        print(f"Error: Template not found at {TEMPLATE}")
        sys.exit(1)

    # Generate plan ID
    today = datetime.now().strftime("%Y-%m-%d")
    existing = list(PLANS_DIR.glob("PLAN-*-*.md"))
    plan_num = len(existing) + 1
    plan_id = f"PLAN-{datetime.now().year}-{plan_num:03d}"

    # Sanitize name for filename
    safe_name = name.lower().replace(" ", "-").replace("_", "-")
    filename = f"{today}-{safe_name}.md"
    plan_path = PLANS_DIR / filename

    if plan_path.exists():
        print(f"Error: Plan already exists at {plan_path}")
        sys.exit(1)

    # Read template and replace placeholders
    content = TEMPLATE.read_text()
    content = content.replace("[Task Name]", name)
    content = content.replace("YYYY-MM-DD", today)
    content = content.replace("PLAN-YYYY-NNN", plan_id)
    content = content.replace("[Your Name]", "Workflow CLI")

    # Write plan
    plan_path.write_text(content)
    print(f"Created: {plan_path}")
    print(f"Plan ID: {plan_id}")

    return plan_path


def list_plans(status: str = None):
    """List all plans."""
    plans = sorted(PLANS_DIR.glob("PLAN-*.md")) + sorted(PLANS_DIR.glob("????-??-??-*.md"))

    if not plans:
        print("No plans found.")
        return

    print(f"\n{'Plan ID':<15} {'Status':<18} {'Title'}")
    print("-" * 70)

    for plan_path in plans:
        content = plan_path.read_text()
        plan_id = "N/A"
        plan_status = "DRAFT"

        for line in content.split("\n"):
            if line.startswith("**Plan ID:**"):
                plan_id = line.split("**Plan ID:**")[1].strip()
            elif line.startswith("**Status:**"):
                plan_status = line.split("**Status:**")[1].strip()
                break

        if status and plan_status.upper() != status.upper():
            continue

        title = plan_path.stem
        print(f"{plan_id:<15} {plan_status:<18} {title}")


def update_status(plan_id: str, new_status: str):
    """Update plan status."""
    found = None

    for plan_path in list(PLANS_DIR.glob("*.md")):
        if plan_id.replace("-", "-") in plan_path.stem or plan_id in plan_path.read_text():
            found = plan_path
            break

    if not found:
        print(f"Error: Plan '{plan_id}' not found")
        sys.exit(1)

    content = found.read_text()
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("**Status:**"):
            lines[i] = f"**Status:** {new_status.upper()}"
            break

    # Add to status history
    history_marker = "## Status History"
    if history_marker not in content:
        lines.append(f"\n{history_marker}\n")
        lines.append("| Date | Status | Updated By | Notes |")
        lines.append("|------|--------|------------|-------|")

    today = datetime.now().strftime("%Y-%m-%d")
    for i, line in enumerate(lines):
        if line.startswith("| [Name] | PENDING | - | - |"):
            lines[i] = f"| Workflow CLI | {new_status.upper()} | {today} | CLI update |"

    found.write_text("\n".join(lines))
    print(f"Updated {found.name} to status: {new_status}")


def main():
    parser = argparse.ArgumentParser(description="Plan management CLI")
    sub = parser.add_subparsers(dest="command", help="Commands")

    # create command
    create_parser = sub.add_parser("create", help="Create a new plan")
    create_parser.add_argument("name", help="Plan name")
    create_parser.set_defaults(func=lambda args: create_plan(args.name))

    # list command
    list_parser = sub.add_parser("list", help="List all plans")
    list_parser.add_argument("--status", help="Filter by status (e.g., DRAFT, APPROVED)")
    list_parser.set_defaults(func=lambda args: list_plans(args.status))

    # status command
    status_parser = sub.add_parser("status", help="Update plan status")
    status_parser.add_argument("plan_id", help="Plan ID (e.g., PLAN-2026-001)")
    status_parser.add_argument("new_status", help="New status")
    status_parser.set_defaults(func=lambda args: update_status(args.plan_id, args.new_status))

    # approve command
    approve_parser = sub.add_parser("approve", help="Approve a plan")
    approve_parser.add_argument("plan_id", help="Plan ID (e.g., PLAN-2026-001)")
    approve_parser.set_defaults(func=lambda args: update_status(args.plan_id, "APPROVED"))

    # init command
    init_parser = sub.add_parser("init", help="Initialize plans directory")
    init_parser.set_defaults(func=lambda _: init_directories())

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


def init_directories():
    """Initialize the plans directory structure."""
    PLANS_DIR.mkdir(parents=True, exist_ok=True)
    (PLANS_DIR / "templates").mkdir(parents=True, exist_ok=True)
    print(f"Initialized: {PLANS_DIR}")


if __name__ == "__main__":
    main()