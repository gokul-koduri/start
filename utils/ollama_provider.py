"""Ollama LLM provider implementation.

Provides LLM inference via local Ollama server with task-based model routing.

Usage:
    from utils.ollama_provider import OllamaProvider

    provider = OllamaProvider({
        "base_url": "http://localhost:11434",
        "models": {
            "default": "llama3",
            "sentiment": "llama3.2:1b",
            "ner": "llama3",
        }
    })
    result = provider.infer("sentiment", "Company X failed due to market conditions")
"""

import json
import logging
import os
import urllib.request
import urllib.error

from utils.llm_provider import LLMProvider, InferenceResult
from utils.http_client import MalformedApiResponseError, read_json_response
from utils.token_tracker import TokenTracker

_logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_MODELS = {
    "default": "llama3",
    "sentiment": "llama3",
    "ner": "llama3",
    "summarization": "llama3",
    "failure_analysis": "llama3",
    "classification": "llama3",
    "chat": "llama3",
}


class OllamaProvider(LLMProvider):
    """Ollama provider for local LLM inference.

    Features:
    - Task-based model routing
    - Automatic JSON extraction
    - Per-inference token tracking
    - Model pull/ensure support
    """

    def __init__(self, config: dict | None = None):
        """Initialize Ollama provider.

        Args:
            config: Provider configuration with keys:
                - base_url: Ollama server URL (default: localhost:11434)
                - models: dict mapping task names to model names
        """
        config = config or {}
        self.base_url = config.get(
            "base_url",
            os.environ.get("OLLAMA_BASE_URL", DEFAULT_BASE_URL)
        )
        self.models = DEFAULT_MODELS.copy()
        self.models.update(config.get("models", {}))

        self._token_tracker = TokenTracker()

    @property
    def name(self) -> str:
        """Provider name."""
        return "ollama"

    def get_model(self, task: str) -> str:
        """Get the model name for a given task type."""
        return self.models.get(task, self.models["default"])

    def infer(
        self,
        task: str,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_retries: int = 2,
        timeout: int = 60,
        **kwargs
    ) -> InferenceResult:
        """Run task-based inference via Ollama.

        Args:
            task: Task type for model routing (e.g., 'sentiment', 'ner').
            prompt: User message content.
            system_prompt: Optional system message.
            temperature: Generation temperature (0.0-1.0).
            max_retries: Retry attempts on connection failure.
            timeout: Request timeout in seconds.
            **kwargs: Additional options.

        Returns:
            InferenceResult with text, model, tokens, and status.
        """
        model = self.get_model(task)
        url = f"{self.base_url}/api/chat"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }

        for attempt in range(max_retries + 1):
            try:
                data = json.dumps(payload).encode()
                req = urllib.request.Request(
                    url,
                    data=data,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    result = read_json_response(resp, provider_name="Ollama")

                text = result.get("message", {}).get("content", "")
                prompt_tokens = result.get("prompt_eval_count", 0) or 0
                completion_tokens = result.get("eval_count", 0) or 0

                # Track usage
                self._token_tracker.track(
                    provider=self.name,
                    model=model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    task=task,
                )

                return InferenceResult(
                    text=text,
                    model=model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                    success=True,
                )

            except MalformedApiResponseError as e:
                _logger.error("Ollama inference failed: %s", e)
                return InferenceResult(
                    text="",
                    model=model,
                    success=False,
                    error=str(e),
                )

            except (urllib.error.URLError, urllib.error.HTTPError,
                    TimeoutError, OSError) as e:
                if attempt < max_retries:
                    wait = 2 * (attempt + 1)
                    _logger.warning(
                        "Ollama inference attempt %d/%d failed (model=%s, task=%s): %s",
                        attempt + 1, max_retries + 1, model, task, e
                    )
                    import time
                    time.sleep(wait)
                else:
                    _logger.error(
                        "Ollama inference failed after %d retries (model=%s, task=%s)",
                        max_retries, model, task
                    )
                    return InferenceResult(
                        text="",
                        model=model,
                        success=False,
                        error=f"Failed after {max_retries} retries: {e}"
                    )

        return InferenceResult(
            text="",
            model=model,
            success=False,
            error="Unknown error"
        )

    def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.3,
        **kwargs
    ) -> str:
        """Send a chat completion request.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            model: Override the default model.
            temperature: Generation temperature.
            **kwargs: Additional options.

        Returns:
            Response content string.
        """
        model = model or self.get_model("default")
        url = f"{self.base_url}/api/chat"

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }

        try:
            data = json.dumps(payload).encode()
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=kwargs.get("timeout", 60)) as resp:
                result = read_json_response(resp, provider_name="Ollama")

            text = result.get("message", {}).get("content", "")

            # Track usage
            prompt_tokens = result.get("prompt_eval_count", 0) or 0
            completion_tokens = result.get("eval_count", 0) or 0
            self._token_tracker.track(
                provider=self.name,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )

            return text

        except MalformedApiResponseError as e:
            _logger.error("Ollama chat failed: %s", e)
            return ""

        except Exception as e:
            _logger.error("Ollama chat failed: %s", e)
            return ""

    def infer_json(
        self,
        prompt: str,
        task: str = "default",
        system_prompt: str | None = None,
        temperature: float = 0.1,
        **kwargs
    ) -> dict | list | None:
        """Run inference and extract JSON from the response.

        Handles common LLM output patterns:
        - Raw JSON: ``{"key": "value"}``
        - Code-fenced: `````json ... ````
        - With preamble text before JSON

        Returns:
            Parsed JSON (dict or list) or None on parse failure.
        """
        if system_prompt is None:
            system_prompt = (
                "Respond ONLY with valid JSON. No explanation, no markdown, no code fences. "
                "Output must be parseable by json.loads()."
            )

        result = self.infer(
            task=task,
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            **kwargs
        )

        if not result.success or not result.text:
            return None

        return _extract_json(result.text)

    def is_available(self) -> bool:
        """Check if Ollama server is responsive."""
        try:
            url = f"{self.base_url}/api/tags"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def list_models(self) -> list[str]:
        """Return list of locally available model names."""
        try:
            url = f"{self.base_url}/api/tags"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = read_json_response(resp, provider_name="Ollama")
            return [m.get("name", "") for m in result.get("models", [])]
        except Exception as e:
            _logger.warning("Failed to list models: %s", e)
            return []

    def pull_model(self, model_name: str, timeout: int = 300) -> bool:
        """Download a model from Ollama registry.

        Args:
            model_name: Model identifier (e.g., "llama3" or "llama3.2:1b").
            timeout: Pull timeout in seconds.

        Returns:
            True if pull succeeded, False otherwise.
        """
        url = f"{self.base_url}/api/pull"
        payload = {"name": model_name, "stream": False}

        try:
            data = json.dumps(payload).encode()
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                result = read_json_response(resp, provider_name="Ollama")
            _logger.info(
                "Model pull completed: %s (status=%s)",
                model_name, result.get("status")
            )
            return True
        except Exception as e:
            _logger.error("Failed to pull model %s: %s", model_name, e)
            return False

    def ensure_model(self, model_name: str) -> bool:
        """Check if model exists locally; pull if not.

        Args:
            model_name: Model identifier.

        Returns:
            True if model is available, False if pull failed.
        """
        local_models = self.list_models()
        normalized = [m.rstrip(":latest") for m in local_models]
        target = model_name.rstrip(":latest")

        if target in normalized or model_name in local_models:
            return True

        _logger.info("Model %s not found locally, pulling...", model_name)
        return self.pull_model(model_name)


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