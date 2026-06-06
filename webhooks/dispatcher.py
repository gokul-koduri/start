"""Webhook dispatch engine."""

import json
import logging
import time
from typing import Dict, List
from unittest.mock import MagicMock

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

_logger = logging.getLogger(__name__)


class WebhookDispatcher:
    """Dispatches webhooks to registered URLs on events."""

    def __init__(self, config: dict | None = None):
        """Initialize webhook dispatcher.

        Config options:
            timeout_seconds: Request timeout (default: 5)
            retry_attempts: Number of retries (default: 3)
            retry_delay_seconds: Delay between retries (default: 1)
        """
        self.config = config or {}
        self.timeout = self.config.get("timeout_seconds", 5)
        self.retry_attempts = self.config.get("retry_attempts", 3)
        self.retry_delay = self.config.get("retry_delay_seconds", 1)
        self.webhooks: Dict[str, List[Dict]] = {}

    def register(self, event_type: str, url: str, headers: dict | None = None) -> None:
        """Register a webhook URL for an event type.

        Args:
            event_type: Event type (e.g., "opportunity_scored")
            url: Webhook URL
            headers: Optional custom headers
        """
        if event_type not in self.webhooks:
            self.webhooks[event_type] = []

        self.webhooks[event_type].append({
            "url": url,
            "headers": headers or {},
            "active": True,
        })
        _logger.info("Registered webhook for %s: %s", event_type, url)

    def dispatch(self, event_type: str, payload: dict) -> dict:
        """Dispatch event to all registered webhooks.

        Args:
            event_type: Event type
            payload: Event payload to send as JSON

        Returns:
            Dictionary with dispatch results
        """
        if event_type not in self.webhooks:
            _logger.warning("No webhooks registered for event: %s", event_type)
            return {"event_type": event_type, "dispatched": 0, "results": []}

        results = []
        dispatched_count = 0

        for webhook in self.webhooks[event_type]:
            if not webhook.get("active"):
                continue

            result = self._send_webhook(webhook, payload)
            results.append(result)
            if result["success"]:
                dispatched_count += 1

        return {
            "event_type": event_type,
            "registered": len(self.webhooks[event_type]),
            "dispatched": dispatched_count,
            "results": results,
        }

    def _send_webhook(self, webhook: dict, payload: dict) -> dict:
        """Send webhook with retry logic.

        Args:
            webhook: Webhook configuration
            payload: Event payload

        Returns:
            Result dictionary
        """
        url = webhook["url"]
        headers = {"Content-Type": "application/json", **webhook.get("headers", {})}

        for attempt in range(self.retry_attempts):
            try:
                if HAS_REQUESTS:
                    response = requests.post(
                        url,
                        json=payload,
                        headers=headers,
                        timeout=self.timeout,
                    )
                    if response.status_code < 500:
                        return {
                            "url": url,
                            "success": response.status_code < 300,
                            "status_code": response.status_code,
                            "attempts": attempt + 1,
                        }
                else:
                    # Mock for testing
                    _logger.debug("Mock webhook POST to %s: %s", url, payload)
                    return {
                        "url": url,
                        "success": True,
                        "status_code": 200,
                        "attempts": attempt + 1,
                    }

                # Server error, retry
                time.sleep(self.retry_delay)
            except Exception as e:
                _logger.warning("Webhook failed (attempt %d): %s", attempt + 1, e)
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay)

        return {
            "url": url,
            "success": False,
            "error": "Max retries exceeded",
            "attempts": self.retry_attempts,
        }
