#!/usr/bin/env python3
"""
Setup Agile Workflow — One-time setup script

Creates GitHub labels, standup dirs, review dirs, and validates the setup.

Usage:
    python scripts/setup_agile.py          # Full setup
    python scripts/setup_agile.py --check  # Check setup status
    python scripts/setup_agile.py --labels # Create GitHub labels only
"""

import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SPRINTS_DIR = PROJECT_ROOT / "docs" / "sprints"


class C:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def check_dir(path, create=True):
    """Check if directory exists, create if needed."""
    if path.exists():
        print(f"  {C.GREEN}✅{C.RESET} {path.relative_to(PROJECT_ROOT)}/")
        return True
    elif create:
        path.mkdir(parents=True, exist_ok=True)
        print(f"  {C.GREEN}📁 Created:{C.RESET} {path.relative_to(PROJECT_ROOT)}/")
        return True
    else:
        print(f"  {C.RED}❌ Missing:{C.RESET} {path.relative_to(PROJECT_ROOT)}/")
        return False


def check_file(path):
    """Check if file exists."""
    if path.exists():
        print(f"  {C.GREEN}✅{C.RESET} {path.relative_to(PROJECT_ROOT)}")
        return True
    else:
        print(f"  {C.RED}❌ Missing:{C.RESET} {path.relative_to(PROJECT_ROOT)}")
        return False


def check_command(cmd):
    """Check if command is available."""
    try:
        subprocess.run(cmd, capture_output=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def create_labels():
    """Create GitHub labels using gh CLI."""
    if not check_command(["gh", "--version"]):
        print(f"\n  {C.YELLOW}⚠️ GitHub CLI (gh) not installed.{C.RESET}")
        print("  Install: https://cli.github.com/")
        print("  Then run: python scripts/agile_cli.py labels | bash")
        return False

    # Check if authenticated
    result = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"\n  {C.YELLOW}⚠️ GitHub CLI not authenticated.{C.RESET}")
        print("  Run: gh auth login")
        return False

    print(f"\n  {C.BOLD}Creating GitHub labels...{C.RESET}")
    subprocess.run(["python", "scripts/agile_cli.py", "labels"], cwd=str(PROJECT_ROOT))
    return True


def setup():
    """Run full agile setup."""
    print(f"\n{C.BOLD}{'='*60}{C.RESET}")
    print(f"{C.BOLD}  🏃 Agile Workflow Setup{C.RESET}")
    print(f"{'='*60}{C.RESET}\n")

    checks = []

    # 1. Directory structure
    print(f"  {C.BOLD}1. Directory Structure{C.RESET}")
    checks.append(check_dir(SPRINTS_DIR / "standups"))
    checks.append(check_dir(SPRINTS_DIR / "reviews"))
    checks.append(check_dir(SPRINTS_DIR / "retros"))
    print()

    # 2. Configuration files
    print(f"  {C.BOLD}2. Configuration Files{C.RESET}")
    checks.append(check_file(PROJECT_ROOT / "AGILE_WORKFLOW.md"))
    checks.append(check_file(PROJECT_ROOT / ".github" / "workflows" / "ci.yml"))
    checks.append(
        check_file(PROJECT_ROOT / ".github" / "workflows" / "sprint-board.yml")
    )
    checks.append(
        check_file(PROJECT_ROOT / ".github" / "workflows" / "daily-standup.yml")
    )
    checks.append(
        check_file(PROJECT_ROOT / ".github" / "workflows" / "sprint-review.yml")
    )
    checks.append(check_file(PROJECT_ROOT / ".github" / "pull_request_template.md"))
    checks.append(
        check_file(PROJECT_ROOT / ".github" / "ISSUE_TEMPLATE" / "sprint-task.yml")
    )
    checks.append(
        check_file(PROJECT_ROOT / ".github" / "ISSUE_TEMPLATE" / "user-story.yml")
    )
    checks.append(
        check_file(PROJECT_ROOT / ".github" / "ISSUE_TEMPLATE" / "spike-research.yml")
    )
    checks.append(
        check_file(PROJECT_ROOT / ".github" / "ISSUE_TEMPLATE" / "sprint-bug.yml")
    )
    checks.append(
        check_file(PROJECT_ROOT / ".github" / "ISSUE_TEMPLATE" / "config.yml")
    )
    checks.append(check_file(PROJECT_ROOT / ".pre-commit-config.yaml"))
    checks.append(check_file(PROJECT_ROOT / "docs" / "sprints" / "velocity.md"))
    print()

    # 3. Tools
    print(f"  {C.BOLD}3. Tools & Scripts{C.RESET}")
    checks.append(check_file(PROJECT_ROOT / "scripts" / "agile_cli.py"))
    checks.append(check_file(PROJECT_ROOT / "scripts" / "sprint_validator.py"))

    # Check pre-commit
    if check_command(["pre-commit", "--version"]):
        print(f"  {C.GREEN}✅{C.RESET} pre-commit installed")
        checks.append(True)
    else:
        print(f"  {C.YELLOW}⚠️ pre-commit not installed{C.RESET}")
        print("     Install: pip install pre-commit && pre-commit install")
        checks.append(False)

    # Check ruff
    if check_command(["ruff", "--version"]):
        print(f"  {C.GREEN}✅{C.RESET} ruff installed")
        checks.append(True)
    else:
        print(f"  {C.YELLOW}⚠️ ruff not installed{C.RESET}")
        print("     Install: pip install ruff")
        checks.append(False)
    print()

    # 4. GitHub labels
    print(f"  {C.BOLD}4. GitHub Labels{C.RESET}")
    print(
        f"  {C.DIM}Run 'python scripts/agile_cli.py labels | bash' to create labels{C.RESET}"
    )
    print(f"  {C.DIM}(Requires gh CLI authenticated){C.RESET}")
    print()

    # Summary
    passed = sum(1 for c in checks if c)
    total = len(checks)
    print(f"  {C.BOLD}{'─'*40}{C.RESET}")
    if all(checks):
        print(f"  {C.GREEN}{C.BOLD}✅ All {total} checks passed!{C.RESET}")
    else:
        print(f"  {C.YELLOW}{C.BOLD}⚠️ {passed}/{total} checks passed{C.RESET}")
        print("  Fix the missing items above.")
    print()

    # Next steps
    print(f"  {C.BOLD}Next Steps:{C.RESET}")
    print("    1. pip install pre-commit && pre-commit install")
    print("    2. python scripts/agile_cli.py labels | bash  # Create GitHub labels")
    print(
        "    3. Create GitHub Project board with columns: Backlog, To Do, In Progress, In Review, Done"
    )
    print("    4. Set branch protection rules (see .github/settings.yml)")
    print("    5. Run: make sprint-status")
    print("    6. Start developing: make standup")
    print()


def check_only():
    """Just check, don't create."""
    print(f"\n{C.BOLD}  🏃 Agile Workflow Status Check{C.RESET}\n")
    setup()


if __name__ == "__main__":
    if "--check" in sys.argv:
        check_only()
    elif "--labels" in sys.argv:
        create_labels()
    else:
        setup()
