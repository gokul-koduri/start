"""QA Engineer Agent — test quality, coverage, regression detection, test strategy.

This agent acts as the QA Engineer role in the AI Product Development Team.
It monitors test health, tracks coverage, detects regressions, validates acceptance
criteria, and ensures every feature meets the Definition of Done.

Key responsibilities:
    - Run and track test suite health (pass/fail/skip counts)
    - Monitor test coverage trends
    - Detect regressions (previously passing tests now failing)
    - Validate acceptance criteria against test cases
    - Generate test case suggestions for untested code
    - Track Definition of Done compliance

Usage:
    qa = QAEngineerAgent()
    result = qa.execute()
    # Returns: test health, coverage, regressions, DoD compliance
"""

import logging
import subprocess
import re
from datetime import datetime, timezone
from pathlib import Path

from agents.base import AgentResult, BaseAgent

_logger = logging.getLogger(__name__)


class QAEngineerAgent(BaseAgent):
    """QA Engineer — test quality, coverage, regression detection.

    Generates:
    - Test suite health (pass/fail/skip/error counts)
    - Coverage metrics (by module, trends)
    - Regression detection (tests that changed status)
    - Acceptance criteria validation
    - Definition of Done checklist status
    - Test case suggestions
    """

    @property
    def name(self) -> str:
        return "qa_engineer"

    def execute(self, upstream_results=None) -> AgentResult:
        """Run QA analysis."""
        started = datetime.now(timezone.utc).isoformat()
        errors = []

        try:
            # ── Step 1: Run test suite ──
            test_health = self._run_tests()

            # ── Step 2: Analyze coverage ──
            coverage = self._analyze_coverage()

            # ── Step 3: Detect regressions ──
            regressions = self._detect_regressions(test_health)

            # ── Step 4: Validate acceptance criteria ──
            acceptance = self._validate_acceptance_criteria()

            # ── Step 5: Definition of Done ──
            dod = self._check_definition_of_done(test_health, coverage)

            # ── Step 6: Test suggestions ──
            suggestions = self._suggest_tests()

            result_data = {
                "test_health": test_health,
                "coverage": coverage,
                "regressions": regressions,
                "acceptance": acceptance,
                "definition_of_done": dod,
                "suggestions": suggestions,
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
            }

            return AgentResult(
                agent_name=self.name,
                status="success" if test_health.get("failed", 0) == 0 else "partial",
                started_at=started,
                completed_at=datetime.now(timezone.utc).isoformat(),
                data=result_data,
                errors=errors,
            )

        except Exception as e:
            errors.append(str(e))
            _logger.error("QAEngineer error: %s", e)
            return AgentResult(
                agent_name=self.name,
                status="failed",
                started_at=started,
                completed_at=datetime.now(timezone.utc).isoformat(),
                errors=errors,
            )

    def _run_tests(self) -> dict:
        """Run pytest and collect results."""
        health = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0,
            "duration_seconds": 0,
            "failed_tests": [],
        }

        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "tests/", "-v", "--tb=no", "-q"],
                capture_output=True,
                text=True,
                timeout=300,
            )

            output = result.stdout + result.stderr

            # Parse pytest summary line: "X passed, Y failed, Z skipped in Ts"
            summary_match = re.search(
                r"(\d+) passed(?:, (\d+) failed)?(?:, (\d+) skipped)?(?:, (\d+) errors?)? in ([\d.]+)s",
                output,
            )
            if summary_match:
                health["passed"] = int(summary_match.group(1))
                health["failed"] = int(summary_match.group(2) or 0)
                health["skipped"] = int(summary_match.group(3) or 0)
                health["errors"] = int(summary_match.group(4) or 0)
                health["total"] = (
                    health["passed"]
                    + health["failed"]
                    + health["skipped"]
                    + health["errors"]
                )
                health["duration_seconds"] = float(summary_match.group(5))

            # Parse failed test names
            for line in output.split("\n"):
                if "FAILED" in line:
                    test_name = line.strip().split("FAILED")[0].strip()
                    health["failed_tests"].append(test_name)

        except subprocess.TimeoutExpired:
            health["error"] = "Test suite timed out (>300s)"
        except FileNotFoundError:
            health["error"] = "pytest not found — install with: pip install pytest"
        except Exception as e:
            health["error"] = str(e)

        return health

    def _analyze_coverage(self) -> dict:
        """Analyze test coverage by module."""
        coverage = {
            "test_files": [],
            "source_modules": [],
            "modules_with_tests": 0,
            "modules_without_tests": 0,
        }

        # Find test files
        for tf in Path("tests").glob("test_*.py"):
            # Map test file to source module
            module = tf.stem.replace("test_", "")
            coverage["test_files"].append(
                {
                    "test_file": str(tf),
                    "module": module,
                }
            )

        # Find source modules
        tested = {tf["module"] for tf in coverage["test_files"]}

        for source_dir in [
            "agents",
            "collectors",
            "scoring",
            "stream",
            "db",
            "auth",
            "nlp",
            "ingestion",
            "monitoring",
            "webhooks",
        ]:
            for sf in Path(source_dir).glob("*.py"):
                if sf.name in ("__init__.py", "base.py"):
                    continue
                module = sf.stem
                has_test = module in tested
                coverage["source_modules"].append(
                    {
                        "module": str(sf),
                        "has_test": has_test,
                    }
                )
                if has_test:
                    coverage["modules_with_tests"] += 1
                else:
                    coverage["modules_without_tests"] += 1

        return coverage

    def _detect_regressions(self, test_health: dict) -> list[dict]:
        """Detect test regressions."""
        regressions = []

        # Currently just report failed tests as potential regressions
        for failed_test in test_health.get("failed_tests", []):
            regressions.append(
                {
                    "test": failed_test,
                    "status": "FAILED",
                    "action": "Investigate and fix before merge",
                }
            )

        return regressions

    def _validate_acceptance_criteria(self) -> dict:
        """Validate that acceptance criteria have corresponding tests."""
        return {
            "criteria_with_tests": 0,
            "criteria_without_tests": 0,
            "note": "Full AC validation requires backlog_items table with acceptance_criteria field",
        }

    def _check_definition_of_done(self, test_health: dict, coverage: dict) -> dict:
        """Check Definition of Done compliance."""
        dod = {
            "checks": [
                {
                    "item": "Code implemented",
                    "status": "N/A",
                    "note": "Check per-feature",
                },
                {
                    "item": "Tests passing",
                    "status": "FAIL" if test_health.get("failed", 0) > 0 else "PASS",
                    "detail": f"{test_health.get('failed', 0)} tests failing",
                },
                {
                    "item": "Documentation updated",
                    "status": "N/A",
                    "note": "Check per-feature",
                },
                {
                    "item": "Code reviewed",
                    "status": "N/A",
                    "note": "Requires PR workflow",
                },
                {
                    "item": "Merged to develop",
                    "status": "N/A",
                    "note": "Requires branch strategy",
                },
                {
                    "item": "Deployment verified",
                    "status": "N/A",
                    "note": "Requires CI/CD",
                },
            ],
            "pass_count": 0,
            "total_checks": 6,
        }

        for check in dod["checks"]:
            if check["status"] == "PASS":
                dod["pass_count"] += 1

        return dod

    def _suggest_tests(self) -> list[dict]:
        """Suggest test cases for untested modules."""
        suggestions = []

        high_priority = [
            "api_server",  # 0 test files
            "composite_scorer",  # Critical path
            "signal_normalizer",  # Critical path
            "kafka_producer",  # Critical path
        ]

        for module in high_priority:
            test_path = f"tests/test_{module}.py"
            if not Path(test_path).exists():
                suggestions.append(
                    {
                        "module": module,
                        "suggested_test_file": test_path,
                        "priority": "P0",
                        "reason": "Critical path, no tests",
                    }
                )

        return suggestions
