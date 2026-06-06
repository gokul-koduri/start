"""Project Monitor Agent — tracks progress against ROADMAP.md and PROGRESS.yaml.

Validates completed sessions, detects regressions, recommends next steps,
and flags scope drift. Run at the start of every development session.

CLI usage:
    python -m agents.project_monitor                # Session briefing (default)
    python -m agents.project_monitor --next         # Recommend next session
    python -m agents.project_monitor --validate     # Full validation audit
    python -m agents.project_monitor --health       # Quick health check
    python -m agents.project_monitor --complete 4.1 # Mark session complete
    python -m agents.project_monitor --deviate 4.3 "Reason" --replace 4.3a
"""

import argparse
import importlib
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from agents.base import AgentResult, BaseAgent

_logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_PROGRESS_FILE = _PROJECT_ROOT / "PROGRESS.yaml"
_ROADMAP_FILE = _PROJECT_ROOT / "ROADMAP.md"


class ProjectMonitorAgent(BaseAgent):
    """Progress monitoring agent for the Opportunity Intelligence Platform.

    Validates completed sessions, detects regressions, recommends next steps,
    and flags scope drift. Does NOT connect to databases or external services.
    """

    @property
    def name(self) -> str:
        return "project_monitor"

    def execute(self, upstream_results=None) -> AgentResult:
        """Run the monitoring agent — produces a status briefing."""
        progress = self._load_progress()
        if progress is None:
            return AgentResult(
                agent_name=self.name,
                status="failed",
                errors=["Failed to load PROGRESS.yaml"],
            )

        data = {}
        data["project_health"] = self._assess_health(progress)
        data["overall_progress_pct"] = self._progress_pct(progress)
        data["phase_progress"] = self._phase_progress(progress)
        data["next_recommended_session"] = self._next_session(progress)
        data["tests"] = self._run_tests()
        data["regressions"] = self._detect_regressions(progress)
        data["scope_drift"] = self._detect_scope_drift(progress)

        return AgentResult(
            agent_name=self.name,
            status="success",
            data=data,
        )

    # ── YAML Loading ──────────────────────────────────────────────

    def _load_progress(self) -> dict | None:
        """Load and parse PROGRESS.yaml."""
        try:
            with open(_PROGRESS_FILE) as f:
                return yaml.safe_load(f)
        except Exception as e:
            _logger.error("Failed to load PROGRESS.yaml: %s", e)
            return None

    def _save_progress(self, progress: dict) -> bool:
        """Write updated PROGRESS.yaml back to disk."""
        progress["last_updated"] = datetime.now(timezone.utc).isoformat()
        try:
            with open(_PROGRESS_FILE, "w") as f:
                yaml.dump(progress, f, default_flow_style=False, sort_keys=False)
            return True
        except Exception as e:
            _logger.error("Failed to save PROGRESS.yaml: %s", e)
            return False

    # ── Health Assessment ─────────────────────────────────────────

    def _assess_health(self, progress: dict) -> str:
        """Assess overall project health: healthy, degraded, or critical."""
        if progress is None:
            return "critical"
        tests = self._run_tests()
        regressions = self._detect_regressions(progress)
        drift = self._detect_scope_drift(progress)

        if tests.get("status") != "all_passing":
            return "critical"
        if regressions or len(drift) > 5:
            return "degraded"
        return "healthy"

    def _progress_pct(self, progress: dict) -> float:
        """Calculate overall progress percentage."""
        phases = progress.get("phases", {})
        total_done = 0
        total_sessions = 0
        for _phase_key, phase in phases.items():
            total_done += phase.get("sessions_completed", 0)
            total_sessions += phase.get("sessions_total", 0)
        if total_sessions == 0:
            return 0.0
        return round((total_done / total_sessions) * 100, 1)

    def _phase_progress(self, progress: dict) -> dict:
        """Return per-phase progress."""
        result = {}
        for key, phase in progress.get("phases", {}).items():
            done = phase.get("sessions_completed", 0)
            total = phase.get("sessions_total", 0)
            result[key] = {
                "pct": round((done / total) * 100, 1) if total else 0,
                "status": phase.get("status", "unknown"),
            }
        return result

    # ── Next Session Recommendation ───────────────────────────────

    def _next_session(self, progress: dict) -> dict:
        """Recommend the next session to work on.

        Finds the first incomplete session whose dependencies are all met.
        """
        sessions = progress.get("sessions", {})

        # Get completed session IDs
        completed = {sid for sid, s in sessions.items() if s.get("status") == "complete"}
        skipped = {sid for sid, s in sessions.items() if s.get("status") == "skipped"}

        # Sort by phase.session_number
        for sid in sorted(sessions.keys(), key=lambda k: (int(k.split(".")[0]), int(k.split(".")[1]))):
            session = sessions[sid]
            status = session.get("status", "pending")

            if status in ("complete", "skipped", "in_progress"):
                continue

            # Check dependencies
            deps = session.get("dependencies", [])
            unmet = [d for d in deps if d not in completed and d not in skipped]
            if unmet:
                continue

            return {
                "id": sid,
                "title": session.get("title", "Unknown"),
                "reason": f"First incomplete session with all dependencies met."
                          + (f" Dependencies: {', '.join(deps)}" if deps else " No dependencies."),
            }

        return {"id": None, "title": "All sessions complete", "reason": "No remaining work."}

    # ── Validation ───────────────────────────────────────────────

    def validate_session(self, progress: dict, session_id: str) -> list[dict]:
        """Run all validation checks for a specific session.

        Returns list of {"check": str, "status": "pass"|"fail", "detail": str}.
        """
        sessions = progress.get("sessions", {})
        session = sessions.get(session_id)
        if session is None:
            return [{"check": "session_exists", "status": "fail", "detail": f"Session {session_id} not found"}]

        results = []
        for check in session.get("validation", []):
            result = self._run_check(check, _PROJECT_ROOT)
            results.append(result)
        return results

    def _run_check(self, check: dict, project_root: Path) -> dict:
        """Run a single validation check."""
        check_type = check.get("type", "")

        if check_type == "file_exists":
            path = project_root / check["path"]
            status = "pass" if path.exists() else "fail"
            return {"check": f"file_exists:{check['path']}", "status": status,
                    "detail": f"File {'exists' if status == 'pass' else 'missing'}"}

        elif check_type == "tests_pass":
            tests = self._run_tests()
            status = tests.get("status", "fail")
            return {"check": "tests_pass", "status": status,
                    "detail": f"{tests.get('passing', '?')}/{tests.get('total', '?')} passing"}

        elif check_type == "import_clean":
            module = check.get("module", "")
            try:
                importlib.import_module(module)
                return {"check": f"import_clean:{module}", "status": "pass", "detail": "Import OK"}
            except Exception as e:
                return {"check": f"import_clean:{module}", "status": "fail", "detail": str(e)}

        elif check_type == "registered_in":
            target_file = project_root / check["file"]
            symbol = check.get("symbol", "")
            if target_file.exists():
                content = target_file.read_text()
                found = symbol in content
                return {"check": f"registered_in:{symbol}", "status": "pass" if found else "fail",
                        "detail": f"Symbol {'found' if found else 'not found'} in {check['file']}"}
            return {"check": f"registered_in:{symbol}", "status": "fail",
                    "detail": f"File {check['file']} not found"}

        elif check_type == "schema_version_ge":
            min_version = check.get("version", 1)
            try:
                # Use importlib to avoid sys.path manipulation issues in test context
                schema_path = project_root / "db" / "schema.py"
                if schema_path.exists():
                    content = schema_path.read_text()
                    match = re.search(r"_SCHEMA_VERSION\s*=\s*(\d+)", content)
                    if match:
                        current = int(match.group(1))
                        status = "pass" if current >= min_version else "fail"
                        return {"check": f"schema_version_ge:{min_version}", "status": status,
                                "detail": f"Schema v{current} (need >={min_version})"}
                return {"check": f"schema_version_ge:{min_version}", "status": "fail",
                        "detail": "_SCHEMA_VERSION not found in db/schema.py"}
            except Exception as e:
                return {"check": f"schema_version_ge:{min_version}", "status": "fail", "detail": str(e)}

        return {"check": check_type, "status": "pass", "detail": "Unknown check type (skipped)"}

    # ── Regression Detection ──────────────────────────────────────

    def _detect_regressions(self, progress: dict) -> list[dict]:
        """Detect potential regressions."""
        regressions = []
        project = progress.get("project", {})

        # Test count regression
        expected_tests = project.get("test_count", 228)
        tests = self._run_tests()
        actual_tests = tests.get("passing", 0)
        if actual_tests < expected_tests:
            regressions.append({
                "type": "test_count_decrease",
                "expected": expected_tests,
                "actual": actual_tests,
                "detail": f"Tests dropped from {expected_tests} to {actual_tests}",
            })

        return regressions

    # ── Scope Drift Detection ────────────────────────────────────

    def _detect_scope_drift(self, progress: dict) -> list[str]:
        """Detect files not in any session plan."""
        sessions = progress.get("sessions", {})

        # Collect all expected files
        expected_files: set[str] = set()
        for _sid, session in sessions.items():
            for f in session.get("files_to_create", []):
                expected_files.add(f)
            for f in session.get("files_to_modify", []):
                expected_files.add(f)

        # Get current .py files
        current_files = set()
        for p in _PROJECT_ROOT.rglob("*.py"):
            rel = str(p.relative_to(_PROJECT_ROOT))
            current_files.add(rel)

        # Known files not in any session (infrastructure, existing code)
        known_extras = {
            "api_server.py", "run_agent.py", "run_collectors.py", "run_report.py",
            "seed_data.py", "streamlit_app.py",
            "agents/base.py", "agents/__init__.py", "agents/orchestrator.py",
            "agents/collection.py", "agents/report.py", "agents/dashboard.py",
            "agents/git_publisher.py", "agents/alert_dispatcher_agent.py",
            "agents/span_agent.py", "agents/license_agent.py",
            "agents/stripe_webhook.py",
            "agents/opportunity_scorer.py", "agents/risk_scorer.py",
            "collectors/__init__.py", "collectors/base.py",
            "collectors/crunchbase.py", "collectors/failory_scraper.py",
            "collectors/google_news_rss.py", "collectors/techcrunch_rss.py",
            "collectors/bls_survival_rates.py", "collectors/reshoring_pdf.py",
            "db/__init__.py", "db/connection.py", "db/dedup.py", "db/schema.py",
            "ingestion/__init__.py", "ingestion/kafka_producer.py", "ingestion/signal_normalizer.py",
            "config/__init__.py",
            "utils/__init__.py", "utils/http_client.py", "utils/rate_limiter.py",
            "utils/date_parsing.py", "utils/text_normalization.py",
            "scoring/__init__.py", "scoring/composite_scorer.py", "scoring/signal_weights.py",
            "scoring/anomaly_detector.py", "scoring/feature_attribution.py", "scoring/time_decay.py",
            "report/__init__.py", "report/generator.py",
            "tests/__init__.py", "tests/conftest.py",
        }

        drift = []
        for f in sorted(current_files):
            if f not in expected_files and f not in known_extras:
                drift.append(f)
        return drift

    # ── Test Runner ───────────────────────────────────────────────

    def _run_tests(self) -> dict:
        """Run pytest and return results."""
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "tests/", "-q", "--tb=no"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(_PROJECT_ROOT),
            )
            output = result.stdout + result.stderr
            # Parse "X passed, Y failed" pattern
            match = re.search(r"(\d+) passed", output)
            passed = int(match.group(1)) if match else 0
            failed_match = re.search(r"(\d+) failed", output)
            failed = int(failed_match.group(1)) if failed_match else 0
            total = passed + failed
            return {
                "passing": passed,
                "total": total,
                "status": "all_passing" if failed == 0 else "failures",
            }
        except Exception as e:
            return {"passing": 0, "total": 0, "status": "error", "detail": str(e)}

    # ── Session Completion ─────────────────────────────────────────

    def complete_session(self, session_id: str) -> dict:
        """Validate and mark a session as complete.

        Returns {"status": "complete"|"incomplete", "checks": [...], "failures": [...]}.
        """
        progress = self._load_progress()
        if progress is None:
            return {"status": "error", "checks": [], "failures": ["Cannot load PROGRESS.yaml"]}

        checks = self.validate_session(progress, session_id)
        failures = [c for c in checks if c["status"] == "fail"]

        if failures:
            return {"status": "incomplete", "checks": checks, "failures": failures}

        # All checks passed — mark complete
        sessions = progress.get("sessions", {})
        if session_id in sessions:
            sessions[session_id]["status"] = "complete"
            sessions[session_id]["completed_at"] = datetime.now(timezone.utc).isoformat()

            # Get current git SHA
            try:
                sha = subprocess.run(
                    ["git", "rev-parse", "--short", "HEAD"],
                    capture_output=True, text=True, cwd=str(_PROJECT_ROOT),
                )
                if sha.returncode == 0:
                    sessions[session_id]["commit_sha"] = sha.stdout.strip()
            except Exception:
                pass

            # Update phase counters
            phase_key = f"phase_{sessions[session_id].get('phase', '')}"
            phases = progress.get("phases", {})
            if phase_key in phases:
                done = sum(1 for s in sessions.values()
                           if s.get("status") == "complete"
                           and s.get("phase") == sessions[session_id].get("phase"))
                phases[phase_key]["sessions_completed"] = done
                if done >= phases[phase_key].get("sessions_total", 0):
                    phases[phase_key]["status"] = "complete"

            # Update last session worked
            progress["last_session_worked"] = session_id
            progress["project"]["test_count"] = self._run_tests().get("passing", 0)

            self._save_progress(progress)

        return {"status": "complete", "checks": checks, "failures": []}

    # ── Deviation Tracking ───────────────────────────────────────

    def log_deviation(self, session_id: str, reason: str,
                      deviation_type: str = "skipped",
                      replacement: str | None = None) -> bool:
        """Log a deviation from the plan."""
        progress = self._load_progress()
        if progress is None:
            return False

        deviation = {
            "session_id": session_id,
            "type": deviation_type,
            "reason": reason,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        if replacement:
            deviation["replacement"] = replacement

        deviations = progress.setdefault("deviations", [])
        deviations.append(deviation)

        # Mark the original session as skipped
        sessions = progress.get("sessions", {})
        if session_id in sessions:
            sessions[session_id]["status"] = "skipped"

        # Create replacement session if needed
        if replacement and replacement not in sessions:
            original = sessions[session_id]
            sessions[replacement] = {
                **original,
                "title": f"{original.get('title', '')} (replacement)",
                "status": "pending",
                "started_at": None,
                "completed_at": None,
                "commit_sha": None,
                "dependencies": original.get("dependencies", []),
            }
            # Update anything that depended on the original
            for sid, session in sessions.items():
                deps = session.get("dependencies", [])
                if session_id in deps:
                    deps.remove(session_id)
                    if replacement not in deps:
                        deps.append(replacement)

        return self._save_progress(progress)

    # ── CLI Entry Point ───────────────────────────────────────────

    def print_briefing(self):
        """Print a session-start briefing."""
        progress = self._load_progress()
        if progress is None:
            print("ERROR: Cannot load PROGRESS.yaml")
            return

        health = self._assess_health(progress)
        pct = self._progress_pct(progress)
        next_rec = self._next_session(progress)
        tests = self._run_tests()
        regressions = self._detect_regressions(progress)
        last = progress.get("last_session_worked", "none")

        print(f"\n{'='*60}")
        print(f"  OPPORTUNITY INTELLIGENCE PLATFORM — SESSION BRIEFING")
        print(f"{'='*60}")
        print(f"  Health:       {health.upper()}")
        print(f"  Progress:     {pct}% ({last} was last)")
        print(f"  Tests:        {tests.get('passing', '?')}/{tests.get('total', '?')} passing")
        if regressions:
            print(f"  Regressions:  {len(regressions)}")
            for r in regressions:
                print(f"    - {r['detail']}")
        print()
        if next_rec.get("id"):
            print(f"  NEXT SESSION: {next_rec['id']} — {next_rec['title']}")
            print(f"  Reason: {next_rec['reason']}")
        else:
            print("  All sessions complete!")
        print(f"{'='*60}\n")

    def print_next(self):
        """Print just the next session recommendation."""
        progress = self._load_progress()
        if progress is None:
            return
        rec = self._next_session(progress)
        if rec.get("id"):
            print(f"{rec['id']}: {rec['title']}")
            print(f"  Reason: {rec['reason']}")
        else:
            print("All sessions complete!")

    def print_health(self):
        """Print quick health check."""
        health = self._assess_health(self._load_progress() or {})
        tests = self._run_tests()
        drift = self._detect_scope_drift(self._load_progress() or {})
        print(f"Health: {health}")
        print(f"Tests:  {tests.get('passing', '?')}/{tests.get('total', '?')}")
        print(f"Drift:  {len(drift)} unplanned files")

    def print_validate(self):
        """Run full validation and print results."""
        progress = self._load_progress()
        if progress is None:
            return

        sessions = progress.get("sessions", {})
        completed = {sid for sid, s in sessions.items() if s.get("status") == "complete"}
        total_pass = 0
        total_fail = 0

        for sid in sorted(completed):
            checks = self.validate_session(progress, sid)
            for c in checks:
                if c["status"] == "pass":
                    total_pass += 1
                else:
                    total_fail += 1
                    print(f"  FAIL: [{sid}] {c['check']} — {c['detail']}")

        print(f"\nValidation: {total_pass} pass, {total_fail} fail")


# ── Module Entry Point ───────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Project progress monitor")
    parser.add_argument("--next", action="store_true", help="Recommend next session")
    parser.add_argument("--health", action="store_true", help="Quick health check")
    parser.add_argument("--validate", action="store_true", help="Full validation audit")
    parser.add_argument("--complete", metavar="SESSION", help="Mark session as complete")
    parser.add_argument("--deviate", metavar="SESSION", help="Log a deviation")
    parser.add_argument("--reason", help="Reason for deviation")
    parser.add_argument("--replace", metavar="SESSION", help="Replacement session ID")
    parser.add_argument("--briefing", action="store_true", help="Session briefing (default)")
    args = parser.parse_args()

    monitor = ProjectMonitorAgent()

    if args.complete:
        result = monitor.complete_session(args.complete)
        for c in result.get("checks", []):
            marker = "PASS" if c["status"] == "pass" else "FAIL"
            print(f"  [{marker}] {c['check']}")
        print(f"\nSession {args.complete}: {result['status'].upper()}")
        if result.get("failures"):
            for f in result["failures"]:
                print(f"  BLOCKED: {f['detail']}")

    elif args.deviate:
        reason = args.reason or "No reason provided"
        ok = monitor.log_deviation(args.deviate, reason, replacement=args.replace)
        print(f"Deviation logged for {args.deviate}: {'OK' if ok else 'FAILED'}")

    elif args.health:
        monitor.print_health()

    elif args.validate:
        monitor.print_validate()

    elif args.next:
        monitor.print_next()

    else:
        monitor.print_briefing()


if __name__ == "__main__":
    main()
