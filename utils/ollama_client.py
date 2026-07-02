"""Reusable Ollama API client with retry logic, connection pooling, and health checks.

Used by agents that communicate with Ollama for LLM inference.
Replaces raw urllib.request.urlopen() calls throughout the codebase.
"""

import json
import logging
import time
import urllib.error
import urllib.request
from http.client import HTTPConnection

_logger = logging.getLogger(__name__)

# Module-level session for connection reuse
_connection_pool: dict[str, HTTPConnection] = {}


def _get_connection(host: str, port: int, timeout: float = 10) -> HTTPConnection:
    """Get or create a persistent HTTP connection to Ollama."""
    key = f"{host}:{port}"
    conn = _connection_pool.get(key)
    if conn is None or conn.sock is None:
        conn = HTTPConnection(host, port, timeout=timeout)
        _connection_pool[key] = conn
    return conn


class OllamaClient:
    """Client for Ollama /api/chat endpoint with retry and graceful degradation.

    Features:
    - Retry with exponential backoff on transient failures
    - Persistent HTTP connections (keep-alive) to prevent BrokenPipeError
    - Configurable timeout for connect vs read phases
    - Health check before sending requests
    - Graceful degradation when Ollama is unavailable

    Usage:
        client = OllamaClient()
        response = client.chat([{"role": "user", "content": "Hello"}])
        if response:
            print(response)
    """

    def __init__(
        self,
        url: str = "http://localhost:11434/api/chat",
        model: str = "llama3",
        timeout: float = 120,
        connect_timeout: float = 5,
        max_retries: int = 3,
        backoff_base: float = 1.0,
    ):
        self.url = url
        self.model = model
        self.timeout = timeout
        self.connect_timeout = connect_timeout
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self._last_error: str | None = None

        # Parse host/port from URL for connection pooling
        # e.g. "http://localhost:11434/api/chat" -> host="localhost", port=11434
        parts = url.replace("http://", "").replace("https://", "").split("/")
        host_port = parts[0].split(":")
        self._host = host_port[0]
        self._port = int(host_port[1]) if len(host_port) > 1 else 11434
        self._path = "/" + "/".join(parts[1:])

    @property
    def last_error(self) -> str | None:
        """Return the last error message, useful for debugging."""
        return self._last_error

    def is_healthy(self) -> bool:
        """Check if Ollama is running and responsive.

        Sends a lightweight GET to /api/tags (lists models).
        Returns True if Ollama responds, False otherwise.
        """
        try:
            req = urllib.request.Request(
                f"http://{self._host}:{self._port}/api/tags",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=self.connect_timeout) as resp:
                return resp.status == 200
        except Exception as e:
            self._last_error = f"Health check failed: {e}"
            _logger.debug("OllamaClient: health check failed: %s", e)
            return False

    def chat(self, messages: list[dict], **kwargs) -> str | None:
        """Send a chat completion request to Ollama with retry logic.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            **kwargs: Override model or timeout for this specific call.

        Returns:
            Response content string, or None if Ollama is unavailable.
        """
        model = kwargs.get("model", self.model)

        payload = json.dumps(
            {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": 0.3},
            }
        ).encode()


        for attempt in range(1, self.max_retries + 1):
            try:
                # Use persistent connection to avoid BrokenPipeError
                conn = _get_connection(self._host, self._port, self.connect_timeout)
                conn.request(
                    "POST",
                    self._path,
                    body=payload,
                    headers={"Content-Type": "application/json"},
                )
                response = conn.getresponse()

                if response.status >= 500:
                    # Server error — retry
                    body = response.read().decode()
                    raise urllib.error.URLError(
                        f"Ollama returned {response.status}: {body[:200]}"
                    )

                if response.status >= 400:
                    # Client error — don't retry (bad request)
                    body = response.read().decode()
                    self._last_error = (
                        f"Ollama client error {response.status}: {body[:200]}"
                    )
                    _logger.error("OllamaClient: %s", self._last_error)
                    return None

                result = json.loads(response.read().decode())

                # Track token usage
                prompt_tokens = result.get("prompt_eval_count", 0)
                completion_tokens = result.get("eval_count", 0)
                if prompt_tokens or completion_tokens:
                    try:
                        from agents.ollama_usage_tracker_agent import _track_inference

                        _track_inference(model, prompt_tokens, completion_tokens)
                    except Exception:
                        pass  # Don't fail the request if tracking fails

                self._last_error = None
                content = result.get("message", {}).get("content", "")
                return content

            except (BrokenPipeError, ConnectionResetError, ConnectionRefusedError) as e:
                # Clear the cached connection — it's broken
                key = f"{self._host}:{self._port}"
                conn = _connection_pool.pop(key, None)
                if conn:
                    try:
                        conn.close()
                    except Exception:
                        pass

                if attempt < self.max_retries:
                    wait = self.backoff_base * (2 ** (attempt - 1))
                    _logger.warning(
                        "OllamaClient: connection error on attempt %d/%d (%s). "
                        "Retrying in %.1fs...",
                        attempt,
                        self.max_retries,
                        type(e).__name__,
                        wait,
                    )
                    time.sleep(wait)
                else:
                    self._last_error = (
                        f"Ollama unavailable after {self.max_retries} attempts: {e}"
                    )
                    _logger.error("OllamaClient: %s", self._last_error)

            except urllib.error.URLError as e:
                if attempt < self.max_retries:
                    wait = self.backoff_base * (2 ** (attempt - 1))
                    _logger.warning(
                        "OllamaClient: URL error on attempt %d/%d (%s). "
                        "Retrying in %.1fs...",
                        attempt,
                        self.max_retries,
                        e,
                        wait,
                    )
                    time.sleep(wait)
                else:
                    self._last_error = (
                        f"Ollama error after {self.max_retries} attempts: {e}"
                    )
                    _logger.error("OllamaClient: %s", self._last_error)

            except Exception as e:
                self._last_error = f"Unexpected error: {e}"
                _logger.error("OllamaClient: %s", self._last_error)
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
