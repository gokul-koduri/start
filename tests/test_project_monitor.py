"""Tests for the Project Monitor Agent."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

import agents.project_monitor as pm_module
from agents.project_monitor import ProjectMonitorAgent


# ── Fixtures ─────────────────────────────────────────────────────

@pytest.fixture
def minimal_progress():
    """Minimal PROGRESS.yaml content for testing."""
    return {
        "schema_version": 1,
        "last_updated": "2026-06-05T00:00:00Z",
        "last_session_worked": "3.12",
        "project": {
            "name": "Test Platform",
            "schema_version": 13,
            "test_count": 228,
            "python_file_count": 111,
            "target": {"agents": 50, "tests": 400},
        },
        "phases": {
            "phase_1": {"name": "Foundation", "status": "complete",
                        "sessions_total": 8, "sessions_completed": 8},
            "phase_4": {"name": "Deep Collection", "status": "not_started",
                        "sessions_total": 15, "sessions_completed": 0},
        },
        "sessions": {
            "4.1": {
                "title": "GitHub Deep Collector",
                "phase": 4,
                "status": "pending",
                "dependencies": [],
                "files_to_create": ["collectors/github_deep_collector.py"],
                "files_to_modify": ["agents/collection.py"],
                "validation": [
                    {"type": "file_exists", "path": "collectors/github_deep_collector.py"},
                    {"type": "import_clean", "module": "collectors.github_deep_collector"},
                    {"type": "tests_pass"},
                ],
            },
            "4.2": {
                "title": "Reddit Stream Collector",
                "phase": 4,
                "status": "pending",
                "dependencies": ["4.1"],
                "files_to_create": ["collectors/reddit_stream_collector.py"],
                "files_to_modify": [],
                "validation": [
                    {"type": "file_exists", "path": "collectors/reddit_stream_collector.py"},
                ],
            },
            "4.3": {
                "title": "HN Live Collector",
                "phase": 4,
                "status": "complete",
                "dependencies": [],
                "files_to_create": ["collectors/hn_live_collector.py"],
                "files_to_modify": [],
                "validation": [
                    {"type": "file_exists", "path": "agents/orchestrator.py"},
                ],
            },
        },
        "deviations": [],
        "health_history": [],
    }


@pytest.fixture
def monitor():
    """ProjectMonitorAgent instance."""
    return ProjectMonitorAgent()


# ── Loading Tests ─────────────────────────────────────────────────

class TestProgressLoading:
    def test_load_progress_returns_dict(self, monitor, minimal_progress):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(minimal_progress, f)
            tmp_path = Path(f.name)

        try:
            with patch.object(pm_module, "_PROGRESS_FILE", tmp_path):
                result = monitor._load_progress()
            assert result is not None
            assert result["schema_version"] == 1
            assert result["project"]["name"] == "Test Platform"
        finally:
            tmp_path.unlink()

    def test_load_progress_missing_file(self, monitor):
        with patch.object(pm_module, "_PROGRESS_FILE", Path("/nonexistent/path.yaml")):
            result = monitor._load_progress()
        assert result is None

    def test_load_progress_invalid_yaml(self, monitor):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("{{invalid yaml")
            tmp_path = Path(f.name)

        try:
            with patch.object(pm_module, "_PROGRESS_FILE", tmp_path):
                result = monitor._load_progress()
            assert result is None
        finally:
            tmp_path.unlink()


# ── Progress Calculation ──────────────────────────────────────────

class TestProgressCalculation:
    def test_progress_pct(self, monitor, minimal_progress):
        result = monitor._progress_pct(minimal_progress)
        # 8 complete out of 23 total (8 + 15)
        assert result == pytest.approx(34.8, abs=0.1)

    def test_progress_pct_no_sessions(self, monitor):
        progress = {"phases": {
            "phase_1": {"sessions_total": 0, "sessions_completed": 0},
        }}
        result = monitor._progress_pct(progress)
        assert result == 0.0

    def test_progress_pct_all_complete(self, monitor):
        progress = {"phases": {
            "phase_1": {"sessions_total": 5, "sessions_completed": 5},
        }}
        result = monitor._progress_pct(progress)
        assert result == 100.0

    def test_phase_progress(self, monitor, minimal_progress):
        result = monitor._phase_progress(minimal_progress)
        assert result["phase_1"]["pct"] == 100.0
        assert result["phase_1"]["status"] == "complete"
        assert result["phase_4"]["pct"] == 0.0


# ── Next Session Recommendation ───────────────────────────────────

class TestNextSession:
    def test_next_session_no_deps(self, monitor, minimal_progress):
        """Session 4.1 has no deps and is pending — should be recommended."""
        result = monitor._next_session(minimal_progress)
        assert result["id"] == "4.1"
        assert "GitHub Deep" in result["title"]

    def test_next_session_blocked_by_deps(self, monitor, minimal_progress):
        """Session 4.2 depends on 4.1 which is pending — should recommend 4.1."""
        result = monitor._next_session(minimal_progress)
        assert result["id"] != "4.2"

    def test_next_session_deps_met(self, monitor):
        """When 4.1 is complete, 4.2 should be recommended."""
        progress = {
            "sessions": {
                "4.1": {"title": "GitHub", "status": "complete", "dependencies": [], "phase": 4,
                        "files_to_create": [], "files_to_modify": [], "validation": []},
                "4.2": {"title": "Reddit", "status": "pending", "dependencies": ["4.1"], "phase": 4,
                        "files_to_create": [], "files_to_modify": [], "validation": []},
            },
            "phases": {},
        }
        result = monitor._next_session(progress)
        assert result["id"] == "4.2"

    def test_next_session_all_complete(self, monitor):
        progress = {
            "sessions": {
                "4.1": {"title": "GitHub", "status": "complete", "dependencies": [], "phase": 4,
                        "files_to_create": [], "files_to_modify": [], "validation": []},
            },
            "phases": {},
        }
        result = monitor._next_session(progress)
        assert result["id"] is None
        assert "complete" in result["title"].lower()

    def test_next_session_skipped_dep(self, monitor):
        """Skipped sessions should not block dependents."""
        progress = {
            "sessions": {
                "4.1": {"title": "GitHub", "status": "skipped", "dependencies": [], "phase": 4,
                        "files_to_create": [], "files_to_modify": [], "validation": []},
                "4.2": {"title": "Reddit", "status": "pending", "dependencies": ["4.1"], "phase": 4,
                        "files_to_create": [], "files_to_modify": [], "validation": []},
            },
            "phases": {},
        }
        result = monitor._next_session(progress)
        assert result["id"] == "4.2"


# ── Validation Checks ────────────────────────────────────────────

class TestValidationChecks:
    def test_file_exists_pass(self, monitor):
        check = {"type": "file_exists", "path": "agents/__init__.py"}
        result = monitor._run_check(check, pm_module._PROJECT_ROOT)
        assert result["status"] == "pass"

    def test_file_exists_fail(self, monitor):
        check = {"type": "file_exists", "path": "nonexistent_file.py"}
        result = monitor._run_check(check, pm_module._PROJECT_ROOT)
        assert result["status"] == "fail"

    def test_import_clean_pass(self, monitor):
        check = {"type": "import_clean", "module": "agents.base"}
        result = monitor._run_check(check, pm_module._PROJECT_ROOT)
        assert result["status"] == "pass"

    def test_import_clean_fail(self, monitor):
        check = {"type": "import_clean", "module": "nonexistent_module_xyz"}
        result = monitor._run_check(check, pm_module._PROJECT_ROOT)
        assert result["status"] == "fail"

    def test_registered_in_pass(self, monitor):
        check = {"type": "registered_in", "file": "agents/orchestrator.py", "symbol": "AGENT_REGISTRY"}
        result = monitor._run_check(check, pm_module._PROJECT_ROOT)
        assert result["status"] == "pass"

    def test_registered_in_fail(self, monitor):
        check = {"type": "registered_in", "file": "agents/orchestrator.py", "symbol": "NonexistentSymbol123"}
        result = monitor._run_check(check, pm_module._PROJECT_ROOT)
        assert result["status"] == "fail"

    def test_registered_in_missing_file(self, monitor):
        check = {"type": "registered_in", "file": "nonexistent.py", "symbol": "Foo"}
        result = monitor._run_check(check, pm_module._PROJECT_ROOT)
        assert result["status"] == "fail"

    def test_schema_version_ge(self, monitor):
        check = {"type": "schema_version_ge", "version": 1}
        result = monitor._run_check(check, pm_module._PROJECT_ROOT)
        assert result["status"] == "pass"

    def test_validate_session(self, monitor, minimal_progress):
        results = monitor.validate_session(minimal_progress, "4.3")
        # 4.3 validation checks that agents/orchestrator.py exists (which it does)
        assert len(results) > 0
        assert all(r["check"] for r in results)

    def test_validate_nonexistent_session(self, monitor, minimal_progress):
        results = monitor.validate_session(minimal_progress, "99.99")
        assert len(results) == 1
        assert results[0]["status"] == "fail"


# ── Session Completion ────────────────────────────────────────────

class TestSessionCompletion:
    @patch.object(pm_module, "_PROGRESS_FILE", Path("/nonexistent.yaml"))
    def test_complete_session_with_failures(self, monitor):
        """Session 4.1 validation will fail (file doesn't exist)."""
        result = monitor.complete_session("4.1")
        assert result["status"] == "error"  # can't load progress

    @patch.object(pm_module, "_PROGRESS_FILE", Path("/nonexistent.yaml"))
    def test_complete_nonexistent_session(self, monitor):
        result = monitor.complete_session("99.99")
        assert result["status"] == "error"


# ── Deviation Tracking ───────────────────────────────────────────

class TestDeviationTracking:
    def test_log_deviation(self, monitor, minimal_progress):
        """log_deviation returns False when PROGRESS.yaml can't be loaded."""
        with patch.object(pm_module, "_PROGRESS_FILE", Path("/nonexistent.yaml")):
            ok = monitor.log_deviation("4.1", "API deprecated", "skipped")
        assert ok is False  # _load_progress returns None

    def test_log_deviation_with_replace(self, monitor, minimal_progress):
        """log_deviation returns False when PROGRESS.yaml can't be loaded."""
        with patch.object(pm_module, "_PROGRESS_FILE", Path("/nonexistent.yaml")):
            ok = monitor.log_deviation("4.1", "Split into two", "split", replacement="4.1a")
        assert ok is False


# ── Scope Drift Detection ────────────────────────────────────────

class TestScopeDrift:
    def test_drift_empty_progress(self, monitor):
        progress = {"sessions": {}, "project": {}}
        # Should not crash
        drift = monitor._detect_scope_drift(progress)
        assert isinstance(drift, list)

    def test_drift_with_expected_files(self, monitor):
        progress = {
            "sessions": {
                "4.1": {
                    "files_to_create": ["collectors/github_deep_collector.py"],
                    "files_to_modify": ["agents/collection.py"],
                    "validation": [],
                },
            },
            "project": {},
        }
        drift = monitor._detect_scope_drift(progress)
        # github_deep_collector.py doesn't exist yet, so it won't be in drift
        # drift should only contain existing files NOT in the plan
        assert isinstance(drift, list)


# ── Regression Detection ─────────────────────────────────────────

class TestRegressionDetection:
    @patch.object(ProjectMonitorAgent, "_run_tests",
                 return_value={"passing": 100, "total": 100, "status": "all_passing"})
    def test_regression_test_count(self, mock_tests, monitor):
        progress = {"project": {"test_count": 999}}  # Way higher than actual
        regressions = monitor._detect_regressions(progress)
        assert len(regressions) == 1
        assert regressions[0]["type"] == "test_count_decrease"

    @patch.object(ProjectMonitorAgent, "_run_tests",
                 return_value={"passing": 100, "total": 100, "status": "all_passing"})
    def test_no_regression(self, mock_tests, monitor):
        progress = {"project": {"test_count": 1}}  # Lower than actual
        regressions = monitor._detect_regressions(progress)
        assert len(regressions) == 0


# ── Health Assessment ────────────────────────────────────────────

class TestHealthAssessment:
    @patch.object(ProjectMonitorAgent, "_detect_regressions", return_value=[])
    @patch.object(ProjectMonitorAgent, "_detect_scope_drift", return_value=[])
    @patch.object(ProjectMonitorAgent, "_run_tests",
                 return_value={"passing": 228, "total": 228, "status": "all_passing"})
    def test_health_healthy(self, mock_tests, mock_drift, mock_reg, monitor, minimal_progress):
        health = monitor._assess_health(minimal_progress)
        assert health == "healthy"

    def test_health_none_progress(self, monitor):
        health = monitor._assess_health(None)
        assert health == "critical"


# ── Agent Interface ───────────────────────────────────────────────

class TestAgentInterface:
    def test_name_property(self, monitor):
        assert monitor.name == "project_monitor"

    def test_execute_returns_agent_result(self, monitor):
        """execute() returns AgentResult with agent_name set."""
        with patch.object(pm_module, "_PROGRESS_FILE", Path("/nonexistent/path.yaml")):
            result = monitor.execute()
        # Progress file missing → status=failed, but AgentResult is returned
        assert result.agent_name == "project_monitor"
        assert result.status == "failed"
        assert "PROGRESS.yaml" in result.errors[0]
