"""Git publisher agent — commits and pushes changes to a GitHub repository."""

import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from agents.base import AgentResult, BaseAgent
from config import get_project_root

_logger = logging.getLogger(__name__)


class GitPublisherAgent(BaseAgent):
    """Agent that publishes the report and dashboard to a GitHub repository.

    Uses GitPython for git operations with subprocess fallback.

    Config options:
        repo_url: GitHub repository URL (or env var GITHUB_REPO)
        branch: main branch name (default: main)
        pages_branch: GitHub Pages branch (default: gh-pages)
        commit_message_template: Template with {timestamp} placeholder
        files_to_commit: list of file patterns to stage
    """

    @property
    def name(self) -> str:
        return "git_publisher"

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        project_root = get_project_root()

        # Check if git is available
        if not self._git_available():
            return AgentResult(
                agent_name=self.name,
                status="failed",
                errors=["git is not available on this system"],
            )

        # Check if we're in a git repo
        if not (project_root / ".git").exists():
            return AgentResult(
                agent_name=self.name,
                status="failed",
                errors=["Not a git repository. Run: git init"],
            )

        # Determine what to commit
        files_to_commit = self.config.get(
            "files_to_commit",
            [
                "Failed_Startups_Manufacturing_Revival_Report.md",
                "site/",
            ],
        )

        # Check for changes
        changed_files = self._get_changed_files(project_root)
        if not changed_files:
            _logger.info("GitPublisherAgent: No changes to commit")
            return AgentResult(
                agent_name=self.name,
                status="success",
                data={"skipped": True, "reason": "no_changes"},
            )

        _logger.info("GitPublisherAgent: %d files changed", len(changed_files))

        # Check if remote is configured
        has_remote = self._has_remote(project_root)

        # Stage and commit
        commit_hash = self._commit_changes(project_root, files_to_commit)
        if not commit_hash:
            return AgentResult(
                agent_name=self.name,
                status="failed",
                errors=["Failed to commit changes"],
            )

        # Push if remote exists
        pushed = False
        deployed_url = ""
        if has_remote:
            pushed = self._push(project_root)
            if pushed:
                repo_url = self.config.get("repo_url", "") or os.environ.get(
                    "GITHUB_REPO", ""
                )
                if repo_url:
                    # Convert git URL to GitHub Pages URL
                    deployed_url = self._get_pages_url(repo_url)

        return AgentResult(
            agent_name=self.name,
            status="success"
            if (commit_hash and (not has_remote or pushed))
            else "partial",
            data={
                "commit_hash": commit_hash,
                "files_changed": len(changed_files),
                "pushed": pushed,
                "deployed_url": deployed_url,
                "records_affected": 1,
            },
        )

    def _git_available(self) -> bool:
        try:
            result = subprocess.run(
                ["git", "--version"], capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _get_changed_files(self, project_root: Path) -> list[str]:
        """Get list of modified/new files matching our patterns."""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                return []

            changed = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                # Status format: XY filename
                filepath = line[3:].strip()
                changed.append(filepath)
            return changed
        except Exception as e:
            _logger.error("GitPublisherAgent: git status failed: %s", e)
            return []

    def _has_remote(self, project_root: Path) -> bool:
        try:
            result = subprocess.run(
                ["git", "remote"],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=5,
            )
            return bool(result.stdout.strip())
        except Exception:
            return False

    def _commit_changes(self, project_root: Path, files_to_commit: list[str]) -> str:
        """Stage files and commit. Returns commit hash or empty string."""
        try:
            # Stage specific files
            for pattern in files_to_commit:
                subprocess.run(
                    ["git", "add", pattern],
                    cwd=str(project_root),
                    capture_output=True,
                    timeout=30,
                )

            # Check if there's anything staged
            result = subprocess.run(
                ["git", "diff", "--cached", "--quiet"],
                cwd=str(project_root),
                capture_output=True,
                timeout=10,
            )
            if result.returncode == 0:
                _logger.info("GitPublisherAgent: Nothing staged after git add")
                return ""

            # Commit
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
            msg_template = self.config.get(
                "commit_message_template",
                "Automated report update - {timestamp}",
            )
            message = msg_template.format(timestamp=timestamp)

            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                _logger.error("GitPublisherAgent: git commit failed: %s", result.stderr)
                return ""

            # Get commit hash
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=5,
            )
            commit_hash = result.stdout.strip()
            _logger.info("GitPublisherAgent: Committed as %s", commit_hash)
            return commit_hash

        except Exception as e:
            _logger.error("GitPublisherAgent: commit failed: %s", e)
            return ""

    def _push(self, project_root: Path) -> bool:
        """Push to remote. Returns True on success."""
        branch = self.config.get("branch", "main")
        try:
            result = subprocess.run(
                ["git", "push", "origin", branch],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                _logger.info("GitPublisherAgent: Pushed to origin/%s", branch)
                return True
            else:
                _logger.error("GitPublisherAgent: push failed: %s", result.stderr)
                return False
        except Exception as e:
            _logger.error("GitPublisherAgent: push failed: %s", e)
            return False

    def _get_pages_url(self, repo_url: str) -> str:
        """Convert a GitHub repo URL to the GitHub Pages URL."""
        # Handle various formats: git@github.com:user/repo.git, https://github.com/user/repo.git
        import re

        match = re.search(r"github\.com[:/]([^/]+)/([^/.]+)", repo_url)
        if match:
            user, repo = match.group(1), match.group(2)
            return f"https://{user}.github.io/{repo}/"
        return ""
