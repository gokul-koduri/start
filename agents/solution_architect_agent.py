"""Solution Architect Agent — system design, tech debt, architecture decisions.

This agent acts as the Solution Architect role in the AI Product Development Team.
It monitors system architecture health, tracks technical debt, manages ADRs,
and ensures the codebase follows clean architecture principles.

Key responsibilities:
    - Monitor architecture health (module coupling, file sizes, function lengths)
    - Track technical debt (TODO/FIXME/HACK comments, known issues)
    - Manage Architecture Decision Records (ADRs)
    - Validate code against design patterns
    - Identify refactoring targets
    - Ensure scalability of current design

Tables used:
    - architecture_health    (module metrics)
    - tech_debt_items        (tracked TODOs/FIXMEs)
    - agent_runs             (agent execution patterns)

Usage:
    architect = SolutionArchitectAgent()
    result = architect.execute()
    # Returns: architecture health, tech debt, ADR status, refactoring priorities
"""

import ast
import re
import logging
from datetime import datetime, timezone
from pathlib import Path

from agents.base import AgentResult, BaseAgent

_logger = logging.getLogger(__name__)


class SolutionArchitectAgent(BaseAgent):
    """Solution Architect — architecture health, tech debt, ADRs.

    Generates:
    - Architecture health metrics (file count, coupling, function lengths)
    - Technical debt inventory (TODOs, FIXMEs, HACKs, deprecated patterns)
    - ADR status (how many, any stale decisions?)
    - Refactoring priority list
    - Design pattern compliance check
    """

    @property
    def name(self) -> str:
        return "solution_architect"

    def execute(self, upstream_results=None) -> AgentResult:
        """Run architecture analysis.

        Steps:
            1. Scan codebase for architecture metrics
            2. Catalog all technical debt (TODO/FIXME/HACK)
            3. Check ADR status and identify undocumented decisions
            4. Identify refactoring targets
            5. Grade overall architecture health
        """
        started = datetime.now(timezone.utc).isoformat()
        errors = []

        try:
            # ── Step 1: Architecture metrics ──
            arch_metrics = self._scan_architecture()

            # ── Step 2: Technical debt ──
            tech_debt = self._scan_tech_debt()

            # ── Step 3: ADR status ──
            adr_status = self._check_adr_status()

            # ── Step 4: Refactoring targets ──
            refactoring = self._identify_refactoring_targets(arch_metrics)

            # ── Step 5: Health grade ──
            grade = self._grade_health(arch_metrics, tech_debt, refactoring)

            result_data = {
                "architecture": arch_metrics,
                "tech_debt": tech_debt,
                "adr_status": adr_status,
                "refactoring": refactoring,
                "health_grade": grade,
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
            _logger.error("SolutionArchitect error: %s", e)
            return AgentResult(
                agent_name=self.name,
                status="failed",
                started_at=started,
                completed_at=datetime.now(timezone.utc).isoformat(),
                errors=errors,
            )

    def _scan_architecture(self) -> dict:
        """Scan codebase for architecture metrics."""
        metrics = {
            "total_py_files": 0,
            "total_lines": 0,
            "by_package": {},
            "files_over_500_lines": [],
            "functions_over_50_lines": [],
            "import_coupling": {},
            "agent_count": 0,
            "collector_count": 0,
        }

        root = Path(".")
        for pyfile in root.rglob("*.py"):
            if ".git" in str(pyfile) or "__pycache__" in str(pyfile):
                continue

            try:
                content = pyfile.read_text()
                lines = content.count("\n") + 1
                metrics["total_py_files"] += 1
                metrics["total_lines"] += lines

                # Package tracking
                parts = str(pyfile).split("/")
                package = parts[0] if len(parts) > 1 else "root"
                if package not in metrics["by_package"]:
                    metrics["by_package"][package] = {"files": 0, "lines": 0}
                metrics["by_package"][package]["files"] += 1
                metrics["by_package"][package]["lines"] += lines

                # Large files
                if lines > 500:
                    metrics["files_over_500_lines"].append(
                        {
                            "file": str(pyfile),
                            "lines": lines,
                        }
                    )

                # Long functions
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            end = getattr(node, "end_lineno", node.lineno)
                            func_len = end - node.lineno + 1
                            if func_len > 50:
                                metrics["functions_over_50_lines"].append(
                                    {
                                        "file": str(pyfile),
                                        "function": node.name,
                                        "lines": func_len,
                                    }
                                )
                except SyntaxError:
                    pass

            except Exception:
                pass

        # Count agents and collectors
        metrics["agent_count"] = len(list(Path("agents").glob("*_agent.py")))
        metrics["agent_count"] += len(list(Path("agents").glob("*_agent_*.py")))
        metrics["collector_count"] = len(
            [
                f
                for f in Path("collectors").glob("*.py")
                if f.name not in ("__init__.py", "base.py") and "_stubs" not in str(f)
            ]
        )

        # Sort for readability
        metrics["files_over_500_lines"].sort(key=lambda x: -x["lines"])
        metrics["functions_over_50_lines"].sort(key=lambda x: -x["lines"])

        return metrics

    def _scan_tech_debt(self) -> dict:
        """Scan for TODO, FIXME, HACK, DEPRECATED, and XXX comments."""
        debt = {"total": 0, "by_type": {}, "by_file": {}, "items": []}
        patterns = {
            "TODO": r"#\s*TODO[\(:]",
            "FIXME": r"#\s*FIXME[\(:]",
            "HACK": r"#\s*HACK[\(:]",
            "DEPRECATED": r"#\s*DEPRECATED[\(:]",
            "XXX": r"#\s*XXX[\(:]",
        }

        root = Path(".")
        for pyfile in root.rglob("*.py"):
            if ".git" in str(pyfile) or "__pycache__" in str(pyfile):
                continue
            try:
                lines = pyfile.read_text().split("\n")
                for i, line in enumerate(lines, 1):
                    for tag, pattern in patterns.items():
                        if re.search(pattern, line, re.IGNORECASE):
                            debt["total"] += 1
                            debt["by_type"][tag] = debt["by_type"].get(tag, 0) + 1
                            debt["by_file"][str(pyfile)] = (
                                debt["by_file"].get(str(pyfile), 0) + 1
                            )
                            debt["items"].append(
                                {
                                    "type": tag,
                                    "file": str(pyfile),
                                    "line": i,
                                    "text": line.strip()[:100],
                                }
                            )
            except Exception:
                pass

        # Top debt files
        debt["top_debt_files"] = sorted(debt["by_file"].items(), key=lambda x: -x[1])[
            :10
        ]

        return debt

    def _check_adr_status(self) -> dict:
        """Check Architecture Decision Records status."""
        status = {"total_adrs": 0, "by_status": {}, "undocumented_decisions": []}

        # Count ADRs from DOCUMENT_DECISIONS.md
        docs_dir = Path("docs/adr")
        if docs_dir.exists():
            adr_files = list(docs_dir.glob("ADR-*.md"))
            status["total_adrs"] = len(adr_files)
        else:
            # Check DOCUMENT_DECISIONS.md
            dd_path = Path("DOCUMENT_DECISIONS.md")
            if dd_path.exists():
                content = dd_path.read_text()
                status["total_adrs"] = content.count("ADR-")
                status["location"] = (
                    "DOCUMENT_DECISIONS.md (should migrate to docs/adr/)"
                )

        # Known decisions that need ADRs
        status["undocumented_decisions"] = [
            "bcrypt for passwords (planned)",
            "slowapi for rate limiting (planned)",
            "Caddy for TLS (planned)",
            "Pydantic for validation (planned)",
            "Stripe for payments (planned)",
        ]

        return status

    def _identify_refactoring_targets(self, metrics: dict) -> list[dict]:
        """Identify files and functions that need refactoring."""
        targets = []

        for f in metrics.get("files_over_500_lines", []):
            targets.append(
                {
                    "type": "large_file",
                    "file": f["file"],
                    "detail": f"{f['lines']} lines (max 500)",
                    "action": "Split into smaller modules",
                    "priority": "P1" if f["lines"] > 1000 else "P2",
                }
            )

        for f in metrics.get("functions_over_50_lines", [])[:20]:
            targets.append(
                {
                    "type": "long_function",
                    "file": f["file"],
                    "detail": f"{f['function']}() = {f['lines']} lines (max 50)",
                    "action": "Extract helper functions",
                    "priority": "P1" if f["lines"] > 100 else "P2",
                }
            )

        return sorted(
            targets,
            key=lambda x: (
                0 if x["priority"] == "P1" else 1,
                -int(re.search(r"(\d+)", x["detail"]).group(1))
                if re.search(r"(\d+)", x["detail"])
                else 0,
            ),
        )

    def _grade_health(self, metrics: dict, debt: dict, refactoring: list) -> dict:
        """Grade overall architecture health (A through F)."""
        score = 100

        # Deductions
        large_files = len(metrics.get("files_over_500_lines", []))
        score -= min(large_files * 2, 20)

        long_functions = len(metrics.get("functions_over_50_lines", []))
        score -= min(long_functions, 20)

        debt_total = debt.get("total", 0)
        score -= min(debt_total, 15)

        p1_targets = sum(1 for t in refactoring if t["priority"] == "P1")
        score -= min(p1_targets * 3, 15)

        # Grade
        if score >= 90:
            grade = "A"
        elif score >= 80:
            grade = "B"
        elif score >= 70:
            grade = "C"
        elif score >= 60:
            grade = "D"
        else:
            grade = "F"

        return {
            "grade": grade,
            "score": score,
            "deductions": {
                "large_files": min(large_files * 2, 20),
                "long_functions": min(long_functions, 20),
                "tech_debt": min(debt_total, 15),
                "refactoring_p1": min(p1_targets * 3, 15),
            },
        }
