"""Slack integration agent — posts alerts to Slack."""

import logging
from typing import Dict
from agents.base import BaseAgent, AgentResult

_logger = logging.getLogger(__name__)


class SlackIntegrationAgent(BaseAgent):
    """Posts alerts to Slack via webhook."""

    def __init__(self, config: Dict | None = None, dry_run: bool = False):
        super().__init__(config, dry_run)
        self.webhook_url = self.config.get("webhook_url", "")

    @property
    def name(self) -> str:
        return "slack_integration"

    def execute(self, upstream_results) -> AgentResult:
        """Post alerts to Slack."""
        if not self.webhook_url:
            return AgentResult(
                agent_name=self.name,
                status="success",
                data={"skipped": True, "reason": "no webhook_url configured"},
            )

        try:
            import requests

            message = self.config.get(
                "message", "Startup Research Alert: Pipeline completed successfully"
            )

            if self.dry_run:
                _logger.info("Dry run: Would post to Slack: %s", message)
                return AgentResult(
                    agent_name=self.name,
                    status="success",
                    data={"dry_run": True, "message": message},
                )

            response = requests.post(
                self.webhook_url,
                json={"text": message},
                timeout=10,
            )

            if response.status_code == 200:
                return AgentResult(
                    agent_name=self.name,
                    status="success",
                    data={"posted": True, "message": message},
                )
            else:
                return AgentResult(
                    agent_name=self.name,
                    status="failed",
                    errors=[f"Slack returned {response.status_code}"],
                )
        except Exception as e:
            return AgentResult(
                agent_name=self.name,
                status="failed",
                errors=[str(e)],
            )
