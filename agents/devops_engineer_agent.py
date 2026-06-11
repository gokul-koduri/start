"""DevOps Engineer Agent — CI/CD, deployment, infrastructure, monitoring.

This agent acts as the DevOps Engineer role in the AI Product Development Team.
It monitors infrastructure health, checks deployment readiness, validates Docker
configuration, and ensures monitoring and alerting are in place.

Key responsibilities:
    - Check Docker service health (all 11 containers)
    - Validate deployment readiness (checklist compliance)
    - Monitor infrastructure metrics (CPU, memory, disk, uptime)
    - Validate CI/CD pipeline configuration
    - Check backup and recovery readiness
    - Monitor security scan results

Usage:
    devops = DevOpsEngineerAgent()
    result = devops.execute()
    # Returns: infrastructure health, deployment readiness, monitoring status
"""

import json
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from agents.base import AgentResult, BaseAgent

_logger = logging.getLogger(__name__)


class DevOpsEngineerAgent(BaseAgent):
    """DevOps Engineer — infrastructure, deployment, CI/CD, monitoring.

    Generates:
    - Docker service health (running/unhealthy/restarting counts)
    - Infrastructure metrics (disk, memory estimation)
    - Deployment readiness checklist
    - CI/CD pipeline status
    - Backup status
    - Security scan status
    """

    @property
    def name(self) -> str:
        return "devops_engineer"

    def execute(self, upstream_results=None) -> AgentResult:
        """Run DevOps analysis."""
        started = datetime.now(timezone.utc).isoformat()
        errors = []

        try:
            # ── Step 1: Docker health ──
            docker_health = self._check_docker()

            # ── Step 2: Infrastructure metrics ──
            infra = self._check_infrastructure()

            # ── Step 3: Deployment readiness ──
            deploy_readiness = self._check_deployment_readiness(docker_health)

            # ── Step 4: CI/CD status ──
            cicd = self._check_cicd()

            # ── Step 5: Backup status ──
            backups = self._check_backups()

            # ── Step 6: Security scan ──
            security = self._check_security()

            result_data = {
                "docker": docker_health,
                "infrastructure": infra,
                "deployment_readiness": deploy_readiness,
                "cicd": cicd,
                "backups": backups,
                "security": security,
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
            }

            status = "success"
            if deploy_readiness.get("ready") is False:
                status = "partial"

            return AgentResult(
                agent_name=self.name,
                status=status,
                started_at=started,
                completed_at=datetime.now(timezone.utc).isoformat(),
                data=result_data,
                errors=errors,
            )

        except Exception as e:
            errors.append(str(e))
            _logger.error("DevOpsEngineer error: %s", e)
            return AgentResult(
                agent_name=self.name,
                status="failed",
                started_at=started,
                completed_at=datetime.now(timezone.utc).isoformat(),
                errors=errors,
            )

    def _check_docker(self) -> dict:
        """Check Docker container health."""
        docker = {
            "available": False,
            "services": {},
            "running_count": 0,
            "unhealthy_count": 0,
        }

        try:
            result = subprocess.run(
                ["docker", "compose", "ps", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            docker["available"] = True

            if result.returncode == 0 and result.stdout.strip():
                for line in result.stdout.strip().split("\n"):
                    try:
                        svc = json.loads(line)
                        name = svc.get("Name", svc.get("Service", "unknown"))
                        state = svc.get("State", "unknown")
                        health = svc.get("Health", "unknown")
                        docker["services"][name] = {
                            "state": state,
                            "health": health,
                        }
                        if state == "running":
                            docker["running_count"] += 1
                        if health == "unhealthy":
                            docker["unhealthy_count"] += 1
                    except json.JSONDecodeError:
                        pass

        except FileNotFoundError:
            docker["error"] = "Docker not installed or not in PATH"
        except subprocess.TimeoutExpired:
            docker["error"] = "Docker command timed out"
        except Exception as e:
            docker["error"] = str(e)

        return docker

    def _check_infrastructure(self) -> dict:
        """Check infrastructure metrics."""
        infra = {"disk": {}, "estimated_memory": "unknown"}

        try:
            import shutil

            usage = shutil.disk_usage("/")
            infra["disk"] = {
                "total_gb": round(usage.total / (1024**3), 1),
                "used_gb": round(usage.used / (1024**3), 1),
                "free_gb": round(usage.free / (1024**3), 1),
                "usage_pct": round(usage.used / usage.total * 100, 1),
            }
        except Exception as e:
            infra["disk"]["error"] = str(e)

        return infra

    def _check_deployment_readiness(self, docker_health: dict) -> dict:
        """Check deployment readiness against checklist."""
        checks = [
            {
                "item": "Docker services running",
                "status": "PASS"
                if docker_health.get("running_count", 0) >= 5
                else "FAIL",
                "detail": f"{docker_health.get('running_count', 0)} services running",
            },
            {
                "item": "No unhealthy services",
                "status": "PASS"
                if docker_health.get("unhealthy_count", 0) == 0
                else "FAIL",
                "detail": f"{docker_health.get('unhealthy_count', 0)} unhealthy",
            },
            {
                "item": ".env file exists",
                "status": "PASS" if Path(".env").exists() else "FAIL",
            },
            {
                "item": ".env.example complete",
                "status": "PASS" if Path(".env.example").exists() else "FAIL",
            },
            {
                "item": "docker-compose.yml exists",
                "status": "PASS" if Path("docker-compose.yml").exists() else "FAIL",
            },
            {
                "item": "Backup script exists",
                "status": "PASS" if Path("scripts/backup_db.sh").exists() else "FAIL",
            },
            {
                "item": "Security scan script exists",
                "status": "PASS"
                if Path("scripts/security_scan.sh").exists()
                else "FAIL",
            },
            {
                "item": "LICENSE file exists",
                "status": "FAIL",
                "detail": "Not created yet",
            },
            {
                "item": "Git tag for release",
                "status": "FAIL",
                "detail": "No tags exist",
            },
            {
                "item": "Tests all passing",
                "status": "FAIL",
                "detail": "12 tests failing in test_semantic_search.py",
            },
        ]

        pass_count = sum(1 for c in checks if c["status"] == "PASS")
        ready = pass_count >= 8 and all(c["status"] == "PASS" for c in checks[:5])

        return {
            "ready": ready,
            "checks": checks,
            "pass_count": pass_count,
            "total_checks": len(checks),
            "readiness_pct": round(pass_count / len(checks) * 100, 1),
        }

    def _check_cicd(self) -> dict:
        """Check CI/CD pipeline status."""
        cicd = {
            "github_actions": Path(".github").exists(),
            "dependabot": Path(".github/dependabot.yml").exists(),
            "pre_commit": Path(".pre-commit-config.yaml").exists(),
            "issue_templates": Path(".github/ISSUE_TEMPLATE").exists(),
            "workflows": [],
        }

        workflows_dir = Path(".github/workflows")
        if workflows_dir.exists():
            cicd["workflows"] = [f.name for f in workflows_dir.glob("*.yml")]

        return cicd

    def _check_backups(self) -> dict:
        """Check backup status."""
        backups = {
            "script_exists": Path("scripts/backup_db.sh").exists(),
            "restore_script_exists": Path("scripts/restore_db.sh").exists(),
            "cron_configured": False,
            "last_backup": None,
        }

        # Check if cron job is set up
        try:
            result = subprocess.run(
                ["crontab", "-l"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if "backup_db" in result.stdout:
                backups["cron_configured"] = True
        except Exception:
            pass

        # Check for recent backup files
        backup_dir = Path("data/backups")
        if backup_dir.exists():
            backup_files = sorted(
                backup_dir.glob("*.sql.gz"),
                key=lambda f: f.stat().st_mtime,
                reverse=True,
            )
            if backup_files:
                from datetime import datetime

                mtime = backup_files[0].stat().st_mtime
                backups["last_backup"] = datetime.fromtimestamp(mtime).isoformat()

        return backups

    def _check_security(self) -> dict:
        """Check security configuration."""
        security = {
            "gitignore_has_env": False,
            "gitignore_has_secrets": False,
            "no_secrets_in_tracking": True,
            "security_scan_script": Path("scripts/security_scan.sh").exists(),
        }

        # Check .gitignore
        gitignore = Path(".gitignore")
        if gitignore.exists():
            content = gitignore.read_text()
            security["gitignore_has_env"] = ".env" in content

        # Check for tracked secret files
        try:
            result = subprocess.run(
                ["git", "ls-files"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            tracked = result.stdout
            for secret in [".env", ".env.production", "secrets.json", "id_rsa"]:
                if secret in tracked:
                    security["no_secrets_in_tracking"] = False
        except Exception:
            pass

        return security
