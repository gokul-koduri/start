"""Groq API client - Free cloud LLM inference with rate limits.

Groq provides free tier access to:
- llama-3.1-8b-instant (fastest, cheapest)
- llama-3.1-70b-versatile
- mixtral-8x7b-32768

Rate limits: 14,400 requests/minute (free tier)
API docs: https://console.groq.com/docs
"""

import json
import logging
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

_logger = logging.getLogger(__name__)


class GroqClient:
    """Client for Groq API - OpenAI-compatible with free tier.

    Usage:
        client = GroqClient()
        response = client.chat([{"role": "user", "content": "Hello"}])
        print(response)
    """

    BASE_URL = "https://api.groq.com/openai/v1"

    # Available models (sorted by preference for free tier)
    MODELS = {
        "fast": "llama-3.1-8b-instant",  # Fastest, cheapest
        "balanced": "mixtral-8x7b-32768",  # Good balance
        "powerful": "llama-3.1-70b-versatile",  # Best quality
        "default": "llama-3.1-8b-instant",
    }

    def __init__(
        self,
        api_key: str = None,
        model: str = None,
        timeout: float = 60,
        max_retries: int = 3,
    ):
        """Initialize Groq client.

        Args:
            api_key: Groq API key (or set GROQ_API_KEY env var)
            model: Model to use (default: llama-3.1-8b-instant)
            timeout: Request timeout in seconds
            max_retries: Number of retries on failure
        """
        # Load dotenv files
        for dotenv_path in [Path.cwd() / ".env", Path.cwd() / ".env.docker"]:
            if dotenv_path.exists():
                load_dotenv(dotenv_path, override=False)

        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.model = model or self.MODELS["default"]
        self.timeout = timeout
        self.max_retries = max_retries
        self._last_error: str | None = None

        if not self.api_key:
            _logger.warning("GroqClient: GROQ_API_KEY not set")

    @property
    def last_error(self) -> str | None:
        """Return the last error message."""
        return self._last_error

    def get_headers(self) -> dict:
        """Build request headers with auth."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            # User-Agent prevents Cloudflare 403 errors (bot protection)
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        }

    def chat(
        self,
        messages: list[dict],
        model: str = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> str | None:
        """Send a chat completion request to Groq.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Override default model
            temperature: Randomness (0-2)
            max_tokens: Max response length

        Returns:
            Response content string, or None on failure
        """
        model = model or self.model
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        for attempt in range(1, self.max_retries + 1):
            try:
                req = urllib.request.Request(
                    f"{self.BASE_URL}/chat/completions",
                    data=json.dumps(payload).encode(),
                    headers=self.get_headers(),
                    method="POST",
                )

                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    result = json.loads(resp.read().decode())
                    self._last_error = None

                    if choices := result.get("choices"):
                        return choices[0]["message"]["content"]
                    return None

            except urllib.error.HTTPError as e:
                error_body = e.read().decode() if e.fp else ""
                self._last_error = f"HTTP {e.code}: {error_body}"

                # Don't retry on auth errors
                if e.code in (401, 403):
                    _logger.error("GroqClient: Auth error - check GROQ_API_KEY")
                    return None

                if attempt < self.max_retries:
                    wait = 2**attempt  # Exponential backoff
                    _logger.warning(
                        "GroqClient: Error on attempt %d/%d. Retrying in %ds...",
                        attempt,
                        self.max_retries,
                        wait,
                    )
                    time.sleep(wait)

            except urllib.error.URLError as e:
                self._last_error = f"Connection error: {e.reason}"
                _logger.warning("GroqClient: Connection error: %s", e.reason)

                if attempt < self.max_retries:
                    wait = 2**attempt
                    time.sleep(wait)

            except Exception as e:
                self._last_error = f"Unexpected error: {e}"
                _logger.error("GroqClient: %s", e)
                break

        _logger.error(
            "GroqClient: Failed after %d attempts: %s",
            self.max_retries,
            self._last_error,
        )
        return None

    def is_healthy(self) -> bool:
        """Check if Groq API is reachable.

        Returns:
            True if API responds, False otherwise
        """
        try:
            req = urllib.request.Request(
                f"{self.BASE_URL}/models",
                headers=self.get_headers(),
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception as e:
            self._last_error = f"Health check failed: {e}"
            return False


if __name__ == "__main__":
    # Quick test
    client = GroqClient()
    if client.api_key:
        print("Testing Groq client...")
        result = client.chat(
            [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'Hello from Groq!' in one sentence."},
            ]
        )
        print(f"Response: {result}")
        print(f"Healthy: {client.is_healthy()}")
    else:
        print("GROQ_API_KEY not set. Get one at https://console.groq.com/keys")
