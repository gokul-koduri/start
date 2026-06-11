"""Centralized Ollama model manager — maps task types to GGUF models.

Provides a single point for all agents to request LLM inference via Ollama,
with support for HuggingFace GGUF models and automatic token tracking.

Usage:
    from agents.model_manager_agent import ModelManager

    mgr = ModelManager(config)
    response = mgr.infer("sentiment", "Analyze: Company X raised $50M then failed")
    # Returns: {"text": "...", "model": "lm-kit/lm-kit-sentiment-analysis-2.0-1b", "tokens": {...}}

Config (settings.yaml):
    ollama:
      base_url: "http://localhost:11434"
      models:
        default: "llama3"
        sentiment: "llama3"
        ner: "llama3"
        summarization: "llama3"
        failure_analysis: "llama3"
"""

import json
import logging
import os
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any

_logger = logging.getLogger(__name__)

# Default task → model mapping
_DEFAULT_MODELS = {
    "default": "llama3",
    "sentiment": "llama3",
    "ner": "llama3",
    "summarization": "llama3",
    "failure_analysis": "llama3",
    "classification": "llama3",
    "chat": "llama3",
}

# Path to local token usage tracker
_TOKEN_TRACKER_PATH = Path("data/cache/ollama_token_tracker.json")


class ModelManager:
    """Manages Ollama model inference, registry, and token tracking.

    Wraps the Ollama REST API (/api/chat) with:
    - Task-based model routing (sentiment → specific model)
    - Automatic JSON extraction from LLM responses
    - Per-inference token usage logging to JSON file
    - Model pull/ensure before inference
    """

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        ollama_cfg = self.config.get("ollama", {})
        self.base_url = ollama_cfg.get(
            "base_url",
            os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        )
        self.models = _DEFAULT_MODELS.copy()
        # Merge user-configured model overrides
        user_models = ollama_cfg.get("models", {})
        if user_models:
            self.models.update(user_models)

    def get_model(self, task: str) -> str:
        """Return the model name for a given task type."""
        return self.models.get(task, self.models["default"])

    def infer(
        self,
        prompt: str,
        task: str = "default",
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_retries: int = 2,
        timeout: int = 60,
    ) -> dict[str, Any]:
        """Run inference via Ollama /api/chat endpoint.

        Args:
            prompt: User message content.
            task: Task type for model routing (e.g., "sentiment", "ner").
            system_prompt: Optional system message.
            temperature: Generation temperature (0.0-1.0).
            max_retries: Retry attempts on connection failure.
            timeout: Request timeout in seconds.

        Returns:
            dict with keys: text, model, prompt_tokens, completion_tokens, total_tokens
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
                    url, data=data, headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    result = json.loads(resp.read().decode())

                text = result.get("message", {}).get("content", "")
                token_info = result.get("prompt_eval_count"), result.get("eval_count")
                prompt_tokens = token_info[0] or 0
                completion_tokens = token_info[1] or 0

                # Track usage
                self._track_usage(model, prompt_tokens, completion_tokens)

                return {
                    "text": text,
                    "model": model,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                }

            except (
                urllib.error.URLError,
                urllib.error.HTTPError,
                TimeoutError,
                OSError,
            ) as e:
                _logger.warning(
                    "Ollama inference attempt %d/%d failed for model=%s task=%s: %s",
                    attempt + 1,
                    max_retries + 1,
                    model,
                    task,
                    e,
                )
                if attempt < max_retries:
                    time.sleep(2 * (attempt + 1))

        _logger.error(
            "Ollama inference failed after %d retries (model=%s, task=%s)",
            max_retries,
            model,
            task,
        )
        return {
            "text": "",
            "model": model,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

    def infer_json(
        self,
        prompt: str,
        task: str = "default",
        system_prompt: str | None = None,
        temperature: float = 0.1,
        **kwargs,
    ) -> dict | list | None:
        """Run inference and extract JSON from the response.

        Handles common LLM output patterns:
        - Raw JSON: ``{"key": "value"}``
        - Code-fenced: `````json ... ````
        - With preamble text before JSON

        Returns parsed JSON (dict or list) or None on parse failure.
        """
        if system_prompt is None:
            system_prompt = (
                "Respond ONLY with valid JSON. No explanation, no markdown, no code fences. "
                "Output must be parseable by json.loads()."
            )

        result = self.infer(
            prompt,
            task=task,
            system_prompt=system_prompt,
            temperature=temperature,
            **kwargs,
        )
        raw = result["text"].strip()

        return _extract_json(raw)

    def pull_model(self, model_name: str, timeout: int = 300) -> bool:
        """Download a GGUF model from HuggingFace via Ollama.

        Args:
            model_name: Ollama model identifier (e.g., "llama3" or HF model reference).
            timeout: Pull timeout in seconds.

        Returns:
            True if pull succeeded, False otherwise.
        """
        url = f"{self.base_url}/api/pull"
        payload = {"name": model_name, "stream": False}

        try:
            data = json.dumps(payload).encode()
            req = urllib.request.Request(
                url, data=data, headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                result = json.loads(resp.read().decode())
            _logger.info(
                "Model pull completed: %s (status=%s)", model_name, result.get("status")
            )
            return True
        except Exception as e:
            _logger.error("Failed to pull model %s: %s", model_name, e)
            return False

    def ensure_model(self, model_name: str) -> bool:
        """Check if model exists locally; pull if not."""
        try:
            url = f"{self.base_url}/api/tags"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode())
            local_models = [m.get("name", "") for m in result.get("models", [])]
            # Ollama tags can include ":latest" — normalize
            normalized = [m.rstrip(":latest") for m in local_models]
            target = model_name.rstrip(":latest")
            if target in normalized or model_name in local_models:
                return True
        except Exception:
            pass

        _logger.info("Model %s not found locally, pulling...", model_name)
        return self.pull_model(model_name)

    def list_local_models(self) -> list[str]:
        """Return list of locally available Ollama model names."""
        try:
            url = f"{self.base_url}/api/tags"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode())
            return [m.get("name", "") for m in result.get("models", [])]
        except Exception as e:
            _logger.warning("Failed to list local models: %s", e)
            return []

    def _track_usage(
        self, model: str, prompt_tokens: int, completion_tokens: int
    ) -> None:
        """Append inference run to local token tracker JSON file."""
        try:
            _TOKEN_TRACKER_PATH.parent.mkdir(parents=True, exist_ok=True)

            # Load existing tracker
            runs = []
            if _TOKEN_TRACKER_PATH.exists():
                with open(_TOKEN_TRACKER_PATH, "r") as f:
                    data = json.load(f)
                    runs = data if isinstance(data, list) else []

            runs.append(
                {
                    "model": model,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                    "timestamp": time.time(),
                }
            )

            with open(_TOKEN_TRACKER_PATH, "w") as f:
                json.dump(runs, f, indent=2)

        except Exception as e:
            _logger.debug("Token tracking failed: %s", e)


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
