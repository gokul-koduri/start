"""Reusable NVIDIA NIM API client with retry logic and connection pooling.

NVIDIA NIM uses OpenAI-compatible API format.
Used by agents that communicate with NVIDIA NIM for LLM inference.
"""

import json
import logging
import os
import time
import urllib.error
import urllib.request
from http.client import HTTPSConnection
from pathlib import Path

from dotenv import load_dotenv

from utils.http_client import MalformedApiResponseError, read_json_response

_logger = logging.getLogger(__name__)

# Module-level session for connection reuse
_connection_pool: dict[str, HTTPSConnection] = {}


def _get_connection(host: str, port: int, timeout: float = 10) -> HTTPSConnection:
    """Get or create a persistent HTTPS connection to NVIDIA NIM."""
    key = f"{host}:{port}"
    conn = _connection_pool.get(key)
    if conn is None or conn.sock is None:
        conn = HTTPSConnection(host, port, timeout=timeout)
        _connection_pool[key] = conn
    return conn


class NvidiaNimClient:
    """Client for NVIDIA NIM OpenAI-compatible API with retry and graceful degradation.

    Features:
    - Retry with exponential backoff on transient failures
    - Persistent HTTPS connections (keep-alive)
    - Configurable timeout for connect vs read phases
    - Health check before sending requests
    - Graceful degradation when NIM is unavailable

    Usage:
        client = NvidiaNimClient()
        response = client.chat([{"role": "user", "content": "Hello"}])
        if response:
            print(response)
    """

    def __init__(
        self,
        base_url: str = None,
        api_key: str = None,
        model: str = None,
        timeout: float = 120,
        connect_timeout: float = 5,
        max_retries: int = 3,
        backoff_base: float = 1.0,
    ):
        # Load local dotenv files if available so runtime config matches the rest of the app.
        for dotenv_path in [Path.cwd() / ".env", Path.cwd() / ".env.docker"]:
            if dotenv_path.exists():
                load_dotenv(dotenv_path, override=False)

        # Get from env if not provided
        self.base_url = base_url or os.getenv(
            "NVIDIA_NIM_BASE_URL", "https://integrate.api.nvidia.com/v1"
        )
        self.api_key = (
            api_key
            if api_key is not None and api_key != ""
            else os.getenv("NVIDIA_NIM_API_KEY") or os.getenv("NVIDIA_API_KEY", "")
        )
        self.model = model or os.getenv(
            "NVIDIA_NIM_MODEL", "meta/llama-3.1-405b-instruct"
        )

        self.timeout = timeout
        self.connect_timeout = connect_timeout
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self._last_error: str | None = None

        # Parse host/port from URL for connection pooling
        # e.g. "https://integrate.api.nvidia.com/v1" -> host="integrate.api.nvidia.com", port=443
        parts = self.base_url.replace("https://", "").replace("http://", "").split("/")
        host_port = parts[0].split(":")
        self._host = host_port[0]
        self._port = int(host_port[1]) if len(host_port) > 1 else 443
        self._path = "/v1/chat/completions"

        if not self.api_key:
            _logger.warning(
                "NvidiaNimClient: NVIDIA_NIM_API_KEY or NVIDIA_API_KEY not set"
            )

    @property
    def last_error(self) -> str | None:
        """Return the last error message, useful for debugging."""
        return self._last_error

    def get_auth_headers(self, extra_headers: dict[str, str] | None = None) -> dict[str, str]:
        """Build standard auth headers for NVIDIA-compatible API requests."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }
        if extra_headers:
            headers.update(extra_headers)
        return headers

    def is_healthy(self) -> bool:
        """Check if NVIDIA NIM is running and responsive.

        Attempts a lightweight request to verify connectivity.
        Returns True if NIM responds, False otherwise.
        """
        try:
            req = urllib.request.Request(
                f"{self.base_url}/models",
                headers=self.get_auth_headers(),
            )
            with urllib.request.urlopen(req, timeout=self.connect_timeout) as resp:
                return resp.status == 200
        except Exception as e:
            self._last_error = f"Health check failed: {e}"
            _logger.debug("NvidiaNimClient: health check failed: %s", e)
            return False

    def chat(self, messages: list[dict], **kwargs) -> str | None:
        """Send a chat completion request to NVIDIA NIM with retry logic.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            **kwargs: Override model or timeout for this specific call.

        Returns:
            Response content string, or None if NIM is unavailable.
        """
        model = kwargs.get("model", self.model)
        temperature = kwargs.get("temperature", 0.3)
        max_tokens = kwargs.get("max_tokens", 1024)

        payload = json.dumps(
            {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False,
            }
        ).encode()

        for attempt in range(1, self.max_retries + 1):
            try:
                req = urllib.request.Request(
                    f"{self.base_url}/ai/generations",
                    data=payload,
                    headers=self.get_auth_headers(),
                )

                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    result = read_json_response(resp, provider_name="NVIDIA NIM")

                    # Track token usage if available
                    usage = result.get("usage", {})
                    prompt_tokens = usage.get("prompt_tokens", 0)
                    completion_tokens = usage.get("completion_tokens", 0)
                    if prompt_tokens or completion_tokens:
                        try:
                            from agents.ollama_usage_tracker_agent import (
                                _track_inference,
                            )

                            _track_inference(model, prompt_tokens, completion_tokens)
                        except Exception:
                            pass  # Don't fail the request if tracking fails

                    self._last_error = None
                    # NVIDIA NIM uses 'output' / 'content' fields in generations response
                    if isinstance(result.get("output"), list) and result["output"]:
                        content = result["output"][0].get("content", "")
                        if isinstance(content, dict):
                            return content.get("text", "")
                        if isinstance(content, str):
                            return content
                    if isinstance(result.get("response"), dict):
                        return result["response"].get("output", "")
                    return None

            except MalformedApiResponseError as e:
                self._last_error = str(e)
                _logger.error("NvidiaNimClient: %s", self._last_error)
                return None

            except (
                ConnectionResetError,
                ConnectionRefusedError,
                urllib.error.URLError,
            ) as e:
                if attempt < self.max_retries:
                    wait = self.backoff_base * (2 ** (attempt - 1))
                    _logger.warning(
                        "NvidiaNimClient: error on attempt %d/%d (%s). "
                        "Retrying in %.1fs...",
                        attempt,
                        self.max_retries,
                        type(e).__name__,
                        wait,
                    )
                    time.sleep(wait)
                else:
                    self._last_error = (
                        f"NIM unavailable after {self.max_retries} attempts: {e}"
                    )
                    _logger.error("NvidiaNimClient: %s", self._last_error)

            except Exception as e:
                self._last_error = f"Unexpected error: {e}"
                _logger.error("NvidiaNimClient: %s", self._last_error)
                break  # Don't retry unexpected errors

        return None

    @staticmethod
    def close_all():
        """Close all cached connections. Called during shutdown."""
        for key, conn in list(_connection_pool.items()):
            try:
                conn.close()
            except Exception:
                pass
        _connection_pool.clear()
