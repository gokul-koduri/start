#!/usr/bin/env python3
"""
Sprint Progression Validator

Ensures no sprint can start until the previous sprint is 100% complete.
Checks: tasks, objectives, deliverables, acceptance criteria, metrics, DoD.

Usage:
    python scripts/sprint_validator.py              # Check current sprint status
    python scripts/sprint_validator.py --sprint 1   # Check specific sprint
    python scripts/sprint_validator.py --gate       # Run gate check for next sprint
    python scripts/sprint_validator.py --all        # Show all sprint statuses
"""

import sys
import re
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ANSI colors
class C:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def icon(status: str) -> str:
    """Return status icon."""
    if status in ("DONE", "PASS", "MET", True, "true"):
        return f"{C.GREEN}✅{C.RESET}"
    elif status in ("FAIL", "NOT_MET", "NOT_DONE", False, "false"):
        return f"{C.RED}❌{C.RESET}"
    elif status in ("PARTIAL",):
        return f"{C.YELLOW}⏳{C.RESET}"
    else:
        return f"{C.DIM}🔲{C.RESET}"


def parse_tracker_yaml():
    """Parse the sprint tracker YAML file."""
    tracker_path = PROJECT_ROOT / "docs" / "sprints" / "sprint-tracker.yaml"
    if not tracker_path.exists():
        print(f"{C.RED}ERROR: sprint-tracker.yaml not found at {tracker_path}{C.RESET}")
        sys.exit(1)

    try:
        import yaml
    except ImportError:
        # Fallback: basic parsing without yaml module
        return parse_yaml_fallback(tracker_path)

    with open(tracker_path) as f:
        return yaml.safe_load(f.read())


def parse_yaml_fallback(path):
    """Basic YAML parsing fallback if PyYAML not installed."""
    content = path.read_text()
    # Very minimal parsing - just extract task statuses
    data = {"sprints": {"sprint_1": {"tasks": {}}}}
    for match in re.finditer(r'(T-\d+):\s*\{[^}]*status:\s*"?(\w+)"?', content):
        task_id = match.group(1)
        status = match.group(2)
        data["sprints"]["sprint_1"]["tasks"][task_id] = {"status": status}
    return data


def get_sprint_params_md(sprint_num: int) -> str:
    """Read sprint parameters from the markdown file."""
    params_path = PROJECT_ROOT / "docs" / "sprints" / "sprint-parameters.md"
    if not params_path.exists():
        return ""
    content = params_path.read_text()

    # Extract sprint section
    pattern = rf"## Sprint {sprint_num}:.*?(?=## Sprint \d|## 📊|---\n\*Last)"
    match = re.search(pattern, content, re.DOTALL)
    return match.group(0) if match else ""


def count_checkboxes(text: str) -> tuple:
    """Count checked vs unchecked checkboxes in text."""
    checked = len(re.findall(r"\[x\]", text, re.IGNORECASE))
    unchecked = len(re.findall(r"\[ \]", text))
    return checked, unchecked


def count_statuses(text: str, sprint_num: int) -> dict:
    """Count various status indicators for a sprint."""
    section = get_sprint_params_md(sprint_num)
    if not section:
        return {}

    results = {}

    # Count task statuses
    tasks_done = len(re.findall(r"✅ DONE", section))
    tasks_todo = len(re.findall(r"🔲", section))
    results["tasks_done"] = tasks_done
    results["tasks_total"] = tasks_done + tasks_todo

    # Count objectives (O-N.M format with ✅ or 🔲)
    obj_done = len(re.findall(r"O-\d+\.\d+.*✅", section))
    obj_total_lines = re.findall(r"O-\d+\.\d+", section)
    results["objectives_done"] = obj_done
    results["objectives_total"] = len(obj_total_lines)

    # Count deliverables
    del_done = len(re.findall(r"D-\d+\.\d+.*✅", section))
    del_total_lines = re.findall(r"D-\d+\.\d+", section)
    results["deliverables_done"] = del_done
    results["deliverables_total"] = len(del_total_lines)

    # Count acceptance criteria
    ac_done = len(re.findall(r"AC-\d+\.\d+.*✅", section))
    ac_total_lines = re.findall(r"AC-\d+\.\d+", section)
    results["acceptance_criteria_done"] = ac_done
    results["acceptance_criteria_total"] = len(ac_total_lines)

    # Count checkboxes in DoD
    checked, unchecked = count_checkboxes(section)
    results["dod_checked"] = checked
    results["dod_total"] = checked + unchecked

    return results


def show_sprint_status(sprint_num: int, detailed: bool = False):
    """Display status for a specific sprint."""
    data = parse_tracker_yaml()
    sprint_key = f"sprint_{sprint_num}"
    params = count_statuses("", sprint_num)

    # Get sprint info from yaml
    sprint_info = data.get("sprints", {}).get(sprint_key, {})

    print(f"\n{C.BOLD}{'='*70}{C.RESET}")
    print(
        f"{C.BOLD}  SPRINT {sprint_num}: {sprint_info.get('name', 'Unknown')}{C.RESET}"
    )
    print(f"  Theme: {sprint_info.get('theme', 'N/A')}")
    print(f"  Status: {sprint_info.get('status', 'Unknown')}")
    print(f"{'='*70}{C.RESET}\n")

    if sprint_info.get("status") == "BLOCKED":
        blocker = sprint_info.get("blocker", "Previous sprint incomplete")
        print(f"  {C.RED}🔒 BLOCKED: {blocker}{C.RESET}\n")
        return False

    # Read from tracker yaml
    sprint_data = data.get("sprints", {}).get(sprint_key, {})
    tasks = sprint_data.get("tasks", {})

    if tasks:
        done_count = sum(1 for t in tasks.values() if t.get("status") == "DONE")
        total_count = len(tasks)
        pct = int((done_count / total_count * 100) if total_count > 0 else 0)
    else:
        done_count = params.get("tasks_done", 0)
        total_count = params.get("tasks_total", 0)
        pct = sprint_info.get("completion_pct", 0)

    # Task status
    print(f"  {C.BOLD}TASKS:{C.RESET} {done_count}/{total_count} complete ({pct}%)")

    # Progress bar
    bar_len = 40
    filled = int(bar_len * pct / 100)
    bar = f"{C.GREEN}{'█' * filled}{C.DIM}{'░' * (bar_len - filled)}{C.RESET}"
    print(f"  [{bar}] {pct}%")
    print()

    if detailed and tasks:
        print(f"  {C.BOLD}Task Breakdown:{C.RESET}")
        for task_id in sorted(tasks.keys(), key=lambda x: int(x.split("-")[1])):
            task = tasks[task_id]
            status = task.get("status", "TODO")
            desc = task.get("description", "")
            effort = task.get("effort", "")
            s_icon = icon(status)
            print(f"    {s_icon} {task_id}: {desc} ({effort})")
        print()

    # Objectives
    obj_data = sprint_data.get("objectives", {})
    if obj_data:
        obj_done = sum(1 for o in obj_data.values() if o.get("status") == "MET")
        obj_total = len(obj_data)
        print(f"  {C.BOLD}OBJECTIVES:{C.RESET} {obj_done}/{obj_total} met")
        if detailed:
            for obj_id in sorted(obj_data.keys()):
                obj = obj_data[obj_id]
                s = icon(obj.get("status", "NOT_STARTED"))
                print(f"    {s} {obj_id}: {obj.get('description', '')}")
        print()

    # Deliverables
    del_data = sprint_data.get("deliverables", {})
    if del_data:
        del_done = sum(1 for d in del_data.values() if d.get("status") == "DONE")
        del_total = len(del_data)
        print(f"  {C.BOLD}DELIVERABLES:{C.RESET} {del_done}/{del_total} produced")
        print()

    # Acceptance Criteria
    ac_data = sprint_data.get("acceptance_criteria", {})
    if ac_data:
        ac_done = sum(1 for a in ac_data.values() if a.get("status") == "PASS")
        ac_total = len(ac_data)
        print(f"  {C.BOLD}ACCEPTANCE CRITERIA:{C.RESET} {ac_done}/{ac_total} verified")
        print()

    # Metrics
    met_data = sprint_data.get("metrics", {})
    if met_data:
        met_done = sum(1 for m in met_data.values() if m.get("met", False))
        met_total = len(met_data)
        print(f"  {C.BOLD}METRICS:{C.RESET} {met_done}/{met_total} at target")
        print()

    # Definition of Done
    dod = sprint_data.get("definition_of_done", {})
    if dod:
        dod_done = sum(1 for v in dod.values() if v is True)
        dod_total = len(dod)
        print(f"  {C.BOLD}DEFINITION OF DONE:{C.RESET} {dod_done}/{dod_total} checked")
        if detailed:
            for key, val in dod.items():
                s = icon(val)
                label = key.replace("_", " ").title()
                print(f"    {s} {label}")
        print()

    # Overall completion
    is_complete = (
        pct == 100
        and (not obj_data or all(o.get("status") == "MET" for o in obj_data.values()))
        and (not del_data or all(d.get("status") == "DONE" for d in del_data.values()))
        and (not ac_data or all(a.get("status") == "PASS" for a in ac_data.values()))
        and (not met_data or all(m.get("met", False) for m in met_data.values()))
        and (not dod or all(dod.values()))
    )

    if is_complete:
        print(f"  {C.GREEN}{C.BOLD}🎉 SPRINT {sprint_num} IS 100% COMPLETE{C.RESET}")
        print(
            f"  {C.GREEN}✅ Gate passed — Sprint {sprint_num + 1} may begin.{C.RESET}"
        )
    else:
        print(f"  {C.RED}{C.BOLD}🚫 SPRINT {sprint_num} IS NOT COMPLETE{C.RESET}")
        print(f"  {C.RED}🔒 Sprint {sprint_num + 1} remains BLOCKED.{C.RESET}")

    print()
    return is_complete


def gate_check():
    """Run gate check: verify current sprint is complete before allowing next."""
    data = parse_tracker_yaml()
    current = data.get("current_sprint", 1)

    print(f"\n{C.BOLD}{'='*70}{C.RESET}")
    print(f"{C.BOLD}  🚧 SPRINT GATE CHECK{C.RESET}")
    print(f"  Checking if Sprint {current} is complete...")
    print(f"{'='*70}{C.RESET}\n")

    is_complete = show_sprint_status(current, detailed=True)

    print(f"\n{C.BOLD}{'='*70}{C.RESET}")
    if is_complete:
        print(f"  {C.GREEN}{C.BOLD}✅ GATE PASSED{C.RESET}")
        print(f"  Sprint {current} is 100% complete.")
        print(f"  {C.GREEN}Sprint {current + 1} is now UNBLOCKED.{C.RESET}")
    else:
        print(f"  {C.RED}{C.BOLD}❌ GATE BLOCKED{C.RESET}")
        print(f"  Sprint {current} is NOT complete.")
        print(f"  {C.RED}Sprint {current + 1} remains BLOCKED.{C.RESET}")
        print(f"\n  {C.YELLOW}Resolve all incomplete items before proceeding.{C.RESET}")
    print(f"{C.BOLD}{'='*70}{C.RESET}\n")

    return is_complete


def show_all():
    """Show status of all sprints."""
    print(f"\n{C.BOLD}{'='*70}{C.RESET}")
    print(f"{C.BOLD}  📊 MASTER SPRINT DASHBOARD{C.RESET}")
    print("  Project: Opportunity Intelligence Platform")
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*70}{C.RESET}\n")

    data = parse_tracker_yaml()
    sprints = data.get("sprints", {})
    current = data.get("current_sprint", 1)

    print(f"  {'SPRINT':<8} {'THEME':<25} {'STATUS':<15} {'COMPLETION':<12}")
    print(f"  {'─'*8} {'─'*25} {'─'*15} {'─'*12}")

    for i in range(1, 9):
        sprint_key = f"sprint_{i}"
        sprint = sprints.get(sprint_key, {})
        name = sprint.get("name", "Unknown")
        status = sprint.get("status", "Unknown")
        pct = sprint.get("completion_pct", 0)

        # Status indicator
        if status == "BLOCKED":
            status_str = f"{C.RED}🔒 BLOCKED{C.RESET}"
        elif pct == 100:
            status_str = f"{C.GREEN}✅ COMPLETE{C.RESET}"
        elif pct > 0:
            status_str = f"{C.YELLOW}⏳ IN PROGRESS{C.RESET}"
        else:
            status_str = f"{C.DIM}🔲 NOT STARTED{C.RESET}"

        # Completion bar
        bar_len = 10
        filled = int(bar_len * pct / 100)
        bar = f"{'█' * filled}{'░' * (bar_len - filled)}"

        # Current sprint indicator
        current_marker = " ◀" if i == current else ""

        print(f"  {i:<8} {name:<25} {status_str} {bar} {pct}%{current_marker}")

    print()
    print(f"  {C.BOLD}Current Sprint: {current}{C.RESET}")
    print(
        f"  Next Sprint: {'UNBLOCKED' if sprints.get(f'sprint_{current}', {}).get('completion_pct', 0) == 100 else '🔒 BLOCKED'}"
    )
    print()


def main():
    args = sys.argv[1:]

    if "--gate" in args:
        success = gate_check()
        sys.exit(0 if success else 1)

    elif "--all" in args:
        show_all()

    elif "--sprint" in args:
        try:
            idx = args.index("--sprint")
            sprint_num = int(args[idx + 1])
        except (IndexError, ValueError):
            print(f"{C.RED}Error: --sprint requires a number (1-8){C.RESET}")
            sys.exit(1)
        detailed = "--detail" in args or "-d" in args
        show_sprint_status(sprint_num, detailed=detailed)

    elif "--help" in args or "-h" in args:
        print(f"""
{C.BOLD}Sprint Progression Validator{C.RESET}

Usage:
  python scripts/sprint_validator.py              Show current sprint status
  python scripts/sprint_validator.py --sprint N    Show sprint N status
  python scripts/sprint_validator.py --sprint N -d Show sprint N with details
  python scripts/sprint_validator.py --gate        Run gate check (exit code: 0=pass, 1=fail)
  python scripts/sprint_validator.py --all         Show all sprint statuses

Exit codes (with --gate):
  0  Gate passed — next sprint may begin
  1  Gate blocked — current sprint incomplete
""")
    else:
        # Default: show current sprint
        data = parse_tracker_yaml()
        current = data.get("current_sprint", 1)
        show_sprint_status(current, detailed=True)


if __name__ == "__main__":
    main()
