"""Software Engineer Agent — code quality, implementation, technical standards.

This agent acts as the Software Engineer role in the AI Product Development Team.
It monitors code quality, tracks implementation progress, identifies code smells,
and ensures the codebase follows coding standards and best practices.

Key responsibilities:
    - Monitor code quality metrics (type coverage, docstring coverage)
    - Track implementation progress against sprint plan
    - Identify code smells and anti-patterns
    - Validate coding standards compliance (PEP 8, naming, structure)
    - Track test coverage
    - Ensure reusable components are used

Usage:
    engineer = SoftwareEngineerAgent()
    result = engineer.execute()
    # Returns: code quality report, implementation status, standards compliance
"""

import ast
import re
import logging
from datetime import datetime, timezone
from pathlib import Path

from agents.base import AgentResult, BaseAgent

_logger = logging.getLogger(__name__)


class SoftwareEngineerAgent(BaseAgent):
    """Software Engineer — code quality, standards, implementation tracking.

    Generates:
    - Code quality metrics (type hints, docstrings, function lengths)
    - Standards compliance (naming, imports, structure)
    - Test coverage overview
    - Reusable component usage
    - Anti-pattern detection
    - Sprint implementation progress
    """

    @property
    def name(self) -> str:
        return "software_engineer"

    def execute(self, upstream_results=None) -> AgentResult:
        """Run code quality analysis."""
        started = datetime.now(timezone.utc).isoformat()
        errors = []

        try:
            # ── Step 1: Code quality metrics ──
            quality = self._measure_code_quality()

            # ── Step 2: Standards compliance ──
            standards = self._check_standards()

            # ── Step 3: Anti-pattern detection ──
            anti_patterns = self._detect_anti_patterns()

            # ── Step 4: Test coverage ──
            test_coverage = self._check_test_coverage()

            # ── Step 5: Reusable component usage ──
            reuse = self._check_reuse()

            # ── Step 6: Recommendations ──
            recommendations = self._generate_recommendations(
                quality, standards, anti_patterns, test_coverage, reuse
            )

            result_data = {
                "quality": quality,
                "standards": standards,
                "anti_patterns": anti_patterns,
                "test_coverage": test_coverage,
                "reuse": reuse,
                "recommendations": recommendations,
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
            }

            return AgentResult(
                agent_name=self.name,
                status="success",
                started_at=started,
                completed_at=datetime.now(timezone.utc).isoformat(),
                data=result_data,
                errors=errors,
            )

        except Exception as e:
            errors.append(str(e))
            _logger.error("SoftwareEngineer error: %s", e)
            return AgentResult(
                agent_name=self.name,
                status="failed",
                started_at=started,
                completed_at=datetime.now(timezone.utc).isoformat(),
                errors=errors,
            )

    def _measure_code_quality(self) -> dict:
        """Measure code quality metrics across the codebase."""
        quality = {
            "total_functions": 0,
            "functions_with_type_hints": 0,
            "functions_with_docstrings": 0,
            "type_coverage_pct": 0,
            "docstring_coverage_pct": 0,
            "avg_function_length": 0,
            "functions_over_50_lines": 0,
        }

        total_length = 0

        for pyfile in Path(".").rglob("*.py"):
            if ".git" in str(pyfile) or "__pycache__" in str(pyfile):
                continue
            try:
                tree = ast.parse(pyfile.read_text())
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if node.name.startswith("__") and node.name.endswith("__"):
                            continue
                        quality["total_functions"] += 1

                        # Type hints
                        has_return = node.returns is not None
                        has_args = all(
                            a.annotation is not None
                            for a in node.args.args
                            if a.arg != "self"
                        )
                        if has_return and has_args:
                            quality["functions_with_type_hints"] += 1

                        # Docstrings
                        docstring = ast.get_docstring(node)
                        if docstring:
                            quality["functions_with_docstrings"] += 1

                        # Length
                        end = getattr(node, "end_lineno", node.lineno)
                        func_len = end - node.lineno + 1
                        total_length += func_len
                        if func_len > 50:
                            quality["functions_over_50_lines"] += 1

            except (SyntaxError, Exception):
                pass

        total = quality["total_functions"]
        if total > 0:
            quality["type_coverage_pct"] = round(
                quality["functions_with_type_hints"] / total * 100, 1
            )
            quality["docstring_coverage_pct"] = round(
                quality["functions_with_docstrings"] / total * 100, 1
            )
            quality["avg_function_length"] = round(total_length / total, 1)

        return quality

    def _check_standards(self) -> dict:
        """Check coding standards compliance."""
        standards = {
            "naming_issues": [],
            "import_issues": [],
            "missing_module_docstrings": [],
        }

        for pyfile in Path(".").rglob("*.py"):
            if ".git" in str(pyfile) or "__pycache__" in str(pyfile):
                continue
            if "test" in str(pyfile):
                continue
            try:
                content = pyfile.read_text()
                tree = ast.parse(content)

                # Module docstring
                if not ast.get_docstring(tree) and pyfile.name != "__init__.py":
                    # Only flag non-trivial files
                    if content.count("\n") > 20:
                        standards["missing_module_docstrings"].append(str(pyfile))

                # Naming: check for camelCase functions
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if not node.name.startswith("_") and re.match(r'^[a-z]+[A-Z]', node.name):
                            if node.name not in ("setUp", "tearDown"):
                                standards["naming_issues"].append({
                                    "file": str(pyfile),
                                    "function": node.name,
                                    "issue": "camelCase (use snake_case)",
                                })

            except Exception:
                pass

        return standards

    def _detect_anti_patterns(self) -> list[dict]:
        """Detect common anti-patterns."""
        patterns = []

        for pyfile in Path(".").rglob("*.py"):
            if ".git" in str(pyfile) or "__pycache__" in str(pyfile) or "test" in str(pyfile):
                continue
            try:
                content = pyfile.read_text()

                # Bare except Exception
                bare_excepts = content.count("except Exception")
                if bare_excepts > 3:
                    patterns.append({
                        "file": str(pyfile),
                        "pattern": "too_many_bare_excepts",
                        "count": bare_excepts,
                        "recommendation": "Use specific exception types",
                    })

                # datetime.utcnow() (deprecated in 3.12)
                if "datetime.utcnow()" in content:
                    patterns.append({
                        "file": str(pyfile),
                        "pattern": "deprecated_utcnow",
                        "recommendation": "Use datetime.now(timezone.utc)",
                    })

                # import * (wildcard)
                if re.search(r'from\s+\w+\s+import\s+\*', content):
                    patterns.append({
                        "file": str(pyfile),
                        "pattern": "wildcard_import",
                        "recommendation": "Import specific names",
                    })

            except Exception:
                pass

        return patterns

    def _check_test_coverage(self) -> dict:
        """Check test file coverage."""
        coverage = {
            "source_files": 0,
            "test_files": 0,
            "tested_modules": set(),
            "untested_modules": [],
        }

        source_files = set()
        test_files = []

        for pyfile in Path(".").rglob("*.py"):
            if ".git" in str(pyfile) or "__pycache__" in str(pyfile):
                continue
            if "test" in str(pyfile) and "test" in pyfile.name:
                test_files.append(str(pyfile))
            elif pyfile.name not in ("__init__.py", "conftest.py"):
                source_files.add(str(pyfile))

        coverage["source_files"] = len(source_files)
        coverage["test_files"] = len(test_files)

        # Map test files to source modules
        for tf in test_files:
            module_name = Path(tf).stem.replace("test_", "")
            coverage["tested_modules"].add(module_name)

        # Find untested source modules
        for sf in sorted(source_files):
            module = Path(sf).stem
            if module not in coverage["tested_modules"] and module != "__init__":
                coverage["untested_modules"].append(sf)

        coverage["tested_modules"] = list(coverage["tested_modules"])
        coverage["coverage_pct"] = round(
            len(coverage["tested_modules"]) / max(1, coverage["source_files"]) * 100, 1
        )

        return coverage

    def _check_reuse(self) -> dict:
        """Check for reusable component usage (db helpers, etc.)."""
        reuse = {
            "db_boilerplate_count": 0,
            "should_use_db_helpers": [],
        }

        for pyfile in Path(".").rglob("*.py"):
            if ".git" in str(pyfile) or "__pycache__" in str(pyfile) or "test" in str(pyfile):
                continue
            if str(pyfile) in ("db/helpers.py", "db/connection.py"):
                continue
            try:
                content = pyfile.read_text()
                # Count raw DB boilerplate
                count = content.count("schema.init_schema(conn)")
                if count > 0:
                    reuse["db_boilerplate_count"] += count
                    reuse["should_use_db_helpers"].append({
                        "file": str(pyfile),
                        "count": count,
                    })
            except Exception:
                pass

        return reuse

    def _generate_recommendations(self, quality, standards, anti_patterns, coverage, reuse) -> list[str]:
        """Generate engineering recommendations."""
        recs = []

        if quality["type_coverage_pct"] < 90:
            recs.append(
                f"Type coverage is {quality['type_coverage_pct']}%. "
                "Add type hints to reach 90%."
            )

        if quality["docstring_coverage_pct"] < 80:
            recs.append(
                f"Docstring coverage is {quality['docstring_coverage_pct']}%. "
                "Add docstrings to public functions."
            )

        if reuse["db_boilerplate_count"] > 20:
            recs.append(
                f"{reuse['db_boilerplate_count']} DB boilerplate blocks found. "
                "Use db/helpers.py (db_execute, db_connection)."
            )

        if coverage["coverage_pct"] < 50:
            recs.append(
                f"Test module coverage is {coverage['coverage_pct']}%. "
                "Add tests for core modules."
            )

        if anti_patterns:
            recs.append(
                f"Found {len(anti_patterns)} anti-patterns. "
                "Address high-priority ones first."
            )

        return recs
