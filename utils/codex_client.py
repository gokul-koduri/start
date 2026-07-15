"""Codex API client using OpenAI Responses API.

Supports:
- Free Claude Code (FCC) proxy at localhost:8082
- Direct Codex API
- Any OpenAI Responses API-compatible endpoint

Usage:
    from utils.codex_client import CodexClient

    client = CodexClient(
        base_url="http://localhost:8082/v1",  # FCC proxy
        api_key="fcc-no-auth",
        model="nvidia_nim/nvidia/nemotron-3-super-120b-a12b"
    )
    response = client.chat([{"role": "user", "content": "Hello"}])
"""

import json
import logging
import os
import time
from typing import Any, Optional

import urllib.request
import urllib.error

from utils.http_client import MalformedApiResponseError, read_json_response

_logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_BASE_URL = "http://localhost:8082/v1"
DEFAULT_MODEL = "nvidia_nim/nvidia/nemotron-3-super-120b-a12b"
DEFAULT_TIMEOUT = 120


class CodexClient:
    """Client for Codex API using OpenAI Responses format.

    Features:
    - OpenAI Responses API compatibility
    - Retry with exponential backoff
    - JSON extraction from responses
    - Token usage tracking
    - Works with FCC proxy or direct Codex API
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = 3,
        backoff_base: float = 1.0,
    ):
        """Initialize Codex client.

        Args:
            base_url: API base URL. Defaults to FCC proxy at localhost:8082.
            api_key: API key. Defaults to FCC_CODEX_API_KEY env var.
            model: Default model ID.
            timeout: Request timeout in seconds.
            max_retries: Max retry attempts on failure.
            backoff_base: Base for exponential backoff calculation.
        """
        self.base_url = (base_url or
                        os.getenv("CODEX_BASE_URL", "") or
                        os.getenv("FCC_BASE_URL", "") or
                        DEFAULT_BASE_URL)
        self.api_key = (api_key or
                       os.getenv("FCC_CODEX_API_KEY", "") or
                       os.getenv("CODEX_API_KEY", "") or
                       "fcc-no-auth")
        self.model = model or os.getenv("CODEX_MODEL", DEFAULT_MODEL)
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_base = backoff_base

        self._last_error: Optional[str] = None

    @property
    def last_error(self) -> Optional[str]:
        """Return the last error message."""
        return self._last_error

    def _get_headers(self) -> dict[str, str]:
        """Build request headers."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_payload(
        self,
        messages: list[dict],
        model: str | None = None,
        **kwargs
    ) -> dict[str, Any]:
        """Build request payload for OpenAI Responses API.

        The Responses API uses a different format than Chat Completions.
        """
        return {
            "model": model or self.model,
            "input": messages,
            "max_tokens": kwargs.get("max_tokens", 4096),
            "temperature": kwargs.get("temperature", 0.3),
        }

    def is_healthy(self) -> bool:
        """Check if Codex endpoint is responsive."""
        try:
            req = urllib.request.Request(
                f"{self.base_url.rstrip('/v1')}/models",
                headers=self._get_headers(),
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception as e:
            self._last_error = f"Health check failed: {e}"
            _logger.debug("CodexClient health check failed: %s", e)
            return False

    def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        **kwargs
    ) -> str | None:
        """Send a chat completion request.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            model: Override the default model.
            **kwargs: Additional options (temperature, max_tokens, etc.)

        Returns:
            Response content string, or None on failure.
        """
        model = model or self.model
        payload = self._build_payload(messages, model, **kwargs)

        for attempt in range(1, self.max_retries + 1):
            try:
                data = json.dumps(payload).encode()
                url = f"{self.base_url.rstrip('/')}/responses"
                req = urllib.request.Request(
                    url,
                    data=data,
                    headers=self._get_headers(),
                )

                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    result = read_json_response(resp, provider_name="Codex")

                # Parse OpenAI Responses API format
                # Response output can be in 'output' or 'content'
                output_items = result.get("output", [])
                if isinstance(output_items, list):
                    for item in output_items:
                        if item.get("type") == "message":
                            content = item.get("content", [])
                            for c in content:
                                if c.get("type") == "output_text":
                                    text = c.get("text", "")
                                    self._track_usage_from_result(result)
                                    self._last_error = None
                                    return text

                # Fallback: try 'content' field directly
                if isinstance(result.get("content"), str):
                    self._track_usage_from_result(result)
                    return result["content"]

                # Fallback: try first output item
                if output_items and isinstance(output_items[0], dict):
                    content = output_items[0].get("content", [])
                    for c in content:
                        if isinstance(c, dict) and c.get("type") == "text":
                            self._track_usage_from_result(result)
                            return c.get("text", "")

                self._last_error = "No valid response content found"
                return None

            except MalformedApiResponseError as e:
                self._last_error = str(e)
                _logger.error("CodexClient: %s", self._last_error)
                return None

            except (urllib.error.URLError, ConnectionResetError,
                    ConnectionRefusedError, TimeoutError, OSError) as e:
                if attempt < self.max_retries:
                    wait = self.backoff_base * (2 ** (attempt - 1))
                    _logger.warning(
                        "CodexClient: attempt %d/%d failed (%s). Retrying in %.1fs...",
                        attempt, self.max_retries, type(e).__name__, wait
                    )
                    time.sleep(wait)
                else:
                    self._last_error = f"Failed after {self.max_retries} attempts: {e}"
                    _logger.error("CodexClient: %s", self._last_error)

            except Exception as e:
                self._last_error = f"Unexpected error: {e}"
                _logger.error("CodexClient: %s", self._last_error)
                break

        return None

    def infer(
        self,
        prompt: str,
        task: str | None = None,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        **kwargs
    ) -> dict[str, Any]:
        """Task-based inference with standardized output.

        Args:
            prompt: User message content.
            task: Task type (for model routing in provider).
            system_prompt: Optional system message.
            model: Override the default model.
            temperature: Generation temperature.
            max_tokens: Max tokens to generate.
            **kwargs: Additional options.

        Returns:
            dict with keys: text, model, prompt_tokens, completion_tokens,
                          total_tokens, success
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if task:
            if not system_prompt:
                messages.append({
                    "role": "system",
                    "content": f"You are performing a {task or 'general'} task."
                })
        messages.append({"role": "user", "content": prompt})

        text = self.chat(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )

        return {
            "text": text or "",
            "model": model or self.model,
            "prompt_tokens": kwargs.get("prompt_tokens", 0),
            "completion_tokens": kwargs.get("completion_tokens", 0),
            "total_tokens": kwargs.get("total_tokens", 0),
            "success": text is not None,
        }

    def infer_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        **kwargs
    ) -> dict | list | None:
        """Inference with JSON extraction from response.

        Args:
            prompt: User message content.
            system_prompt: Optional system message.
            model: Override the default model.
            **kwargs: Additional options.

        Returns:
            Parsed JSON (dict or list) or None on parse failure.
        """
        if system_prompt is None:
            system_prompt = (
                "Respond ONLY with valid JSON. No explanation, no markdown, "
                "no code fences. Output must be parseable by json.loads()."
            )

        # Add JSON instruction to prompt
        enhanced_prompt = f"{prompt}\n\nRespond with valid JSON only."

        result = self.infer(
            prompt=enhanced_prompt,
            system_prompt=system_prompt,
            model=model,
            **kwargs
        )

        # infer() returns a dict with 'text' key
        if isinstance(result, dict):
            text = result.get("text", "")
        else:
            text = result

        if not text:
            return None

        return _extract_json(text)

    def _track_usage_from_result(self, result: dict) -> None:
        """Track token usage from API response."""
        try:
            usage = result.get("usage", {})
            prompt_tokens = usage.get("input_tokens", 0)
            completion_tokens = usage.get("output_tokens", 0)

            if prompt_tokens or completion_tokens:
                from utils.token_tracker import TokenTracker
                tracker = TokenTracker()
                tracker.track(
                    provider=self.name,
                    model=self.model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                )
        except Exception:
            pass  # Don't fail on tracking errors

    @property
    def name(self) -> str:
        """Provider name for tracking."""
        return "codex"


def _extract_json(raw: str) -> dict | list | None:
    """Extract JSON from raw LLM output, handling code fences and preamble."""
    text = raw.strip()

    # Strip code fences
    if text.startswith("```"):
        lines = text.split("\n", 1)
        if len(lines) > 1:
            text = lines[1]
        else:
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()

    # Try to find JSON in the text (handle preamble)
    for opener in ["{", "["]:
        idx = text.find(opener)
        if idx >= 0:
            candidate = text[idx:]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue

    # Final attempt
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None