"""Centralized Ollama model manager — maps task types to GGUF models.

Provides a single point for all agents to request LLM inference via Ollama,
with support for HuggingFace GGUF models and automatic token tracking.

Now supports multiple LLM providers:
- Ollama (default, local)
- Codex (via FCC proxy)
- NVIDIA NIM

Usage:
    from agents.model_manager_agent import ModelManager

    # Use default (Ollama)
    mgr = ModelManager(config)
    response = mgr.infer("sentiment", "Analyze: Company X raised $50M then failed")
    # Returns: {"text": "...", "model": "llama3", "tokens": {...}}

    # Or use a different provider
    mgr = ModelManager({"llm": {"provider": "codex", ...}})

Config (settings.yaml):
    llm:
      provider: "ollama"  # or "codex", "nvidia_nim"
    ollama:
      base_url: "http://localhost:11434"
      models:
        default: "llama3"
        sentiment: "llama3"
        ner: "llama3"
        summarization: "llama3"
        failure_analysis: "llama3"
        code_gen: "llama3"
    codex:
      base_url: "http://localhost:8082/v1"  # FCC proxy
      models:
        default: "nvidia_nim/nvidia/nemotron-3-super-120b-a12b"
        analysis: "opencode/gpt-5.3-codex"
"""

import json
import logging
import os
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any

from utils.llm_provider import get_provider, LLMProvider

_logger = logging.getLogger(__name__)

# Default task → model mapping (for Ollama compatibility)
_DEFAULT_MODELS = {
    "default": "llama3",
    "sentiment": "llama3",
    "ner": "llama3",
    "summarization": "llama3",
    "failure_analysis": "llama3",
    "classification": "llama3",
    "chat": "llama3",
}

# Path to local token usage tracker (legacy)
_TOKEN_TRACKER_PATH = Path("data/cache/ollama_token_tracker.json")


class ModelManager:
    """Manages LLM inference across multiple providers.

    Wraps the LLM provider system with backward-compatible interface:
    - Task-based model routing (sentiment → specific model)
    - Automatic JSON extraction from LLM responses
    - Per-inference token usage logging to JSON file
    - Model pull/ensure before inference (Ollama only)

    Supports multiple backends:
    - Ollama (default, local)
    - Codex (via FCC proxy)
    - NVIDIA NIM
    """

    def __init__(self, config: dict | None = None):
        """Initialize ModelManager with optional provider override.

        Args:
            config: Full config dict or None. Reads from:
                - config["llm"]["provider"] for provider selection
                - config["llm"][provider] for provider-specific config
                - config["ollama"] for legacy Ollama config (backward compat)
        """
        self.config = config or {}

        # Determine which provider to use
        llm_config = self.config.get("llm", {})

        # For backward compatibility, default to Ollama if no provider specified
        # but check if ollama config exists in the old location
        if "provider" not in llm_config:
            # Use legacy ollama config structure if present
            if "ollama" in self.config:
                provider_config = {
                    "llm": {
                        "provider": "ollama",
                        "ollama": self.config.get("ollama", {}),
                    }
                }
                self._provider = get_provider("ollama", provider_config)
            else:
                # Default to ollama
                self._provider = get_provider("ollama", self.config)
        else:
            self._provider = get_provider(llm_config.get("provider", "ollama"), self.config)

        # Legacy attributes for backward compatibility
        ollama_cfg = self.config.get("ollama", {})
        self.base_url = ollama_cfg.get(
            "base_url",
            os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        )
        self.models = _DEFAULT_MODELS.copy()
        user_models = ollama_cfg.get("models", {})
        if user_models:
            self.models.update(user_models)

    @property
    def provider(self) -> LLMProvider:
        """Access the underlying LLM provider."""
        return self._provider

    @property
    def provider_name(self) -> str:
        """Get the current provider name."""
        return self._provider.name

    def get_model(self, task: str) -> str:
        """Return the model name for a given task type.

        Note: Only works for Ollama provider. Other providers
        may route tasks internally.
        """
        if hasattr(self._provider, 'get_model'):
            return self._provider.get_model(task)
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
        """Run inference via the configured LLM provider.

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
        # Use provider's infer method if available
        if hasattr(self._provider, 'infer'):
            result = self._provider.infer(
                task=task,
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_retries=max_retries,
                timeout=timeout,
            )
            # Convert InferenceResult to dict format for backward compat
            return {
                "text": result.text,
                "model": result.model,
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
                "total_tokens": result.total_tokens,
                "success": result.success,
                "error": result.error,
            }

        # Fallback: Ollama direct (for backward compat with old code)
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
                    result_json = json.loads(resp.read().decode())

                text = result_json.get("message", {}).get("content", "")
                token_info = result_json.get("prompt_eval_count"), result_json.get("eval_count")
                prompt_tokens = token_info[0] or 0
                completion_tokens = token_info[1] or 0

                # Track usage (also updates unified tracker)
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
        """Append inference run to token tracker files.

        Writes to both:
        - Legacy Ollama tracker for backward compatibility
        - Unified token tracker for cross-provider tracking

        Uses atomic write pattern to prevent data loss on errors.
        """
        # Write to unified tracker
        try:
            from utils.token_tracker import TokenTracker
            tracker = TokenTracker()
            tracker.track(
                provider=self._provider.name,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )
        except Exception as e:
            _logger.warning("Unified token tracking failed: %s", e)

        # Write to legacy Ollama tracker (for backward compat)
        self._append_to_token_tracker(model, prompt_tokens, completion_tokens)

    def _append_to_token_tracker(
        self, model: str, prompt_tokens: int, completion_tokens: int
    ) -> None:
        """Append a single inference record to the legacy token tracker file.

        Uses atomic write pattern: write to temp file, then rename.
        Falls back to append-only on failure to minimize data loss.
        """
        import tempfile
        import os

        try:
            _TOKEN_TRACKER_PATH.parent.mkdir(parents=True, exist_ok=True)

            # Load existing tracker with proper error handling
            runs = []
            backup_path = None
            if _TOKEN_TRACKER_PATH.exists():
                try:
                    with open(_TOKEN_TRACKER_PATH, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        runs = data if isinstance(data, list) else []
                except json.JSONDecodeError as e:
                    # JSON is corrupt - backup the corrupt file before overwriting
                    _logger.warning(
                        "Token tracker JSON corrupt (len=%d), backing up: %s",
                        _TOKEN_TRACKER_PATH.stat().st_size,
                        e,
                    )
                    backup_path = str(_TOKEN_TRACKER_PATH) + f".backup.{int(time.time())}"
                    try:
                        _TOKEN_TRACKER_PATH.rename(backup_path)
                    except OSError:
                        pass  # Backup failed, will overwrite
                    runs = []

            # Build the new record
            new_record = {
                "model": model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
                "timestamp": time.time(),
            }
            runs.append(new_record)

            # Atomic write: write to temp file, then rename
            try:
                fd, tmp_path = tempfile.mkstemp(
                    suffix=".json", dir=_TOKEN_TRACKER_PATH.parent
                )
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(runs, f, indent=2)
                os.replace(tmp_path, str(_TOKEN_TRACKER_PATH))
                _logger.debug(
                    "Token tracked: model=%s, tokens=%d+%d",
                    model,
                    prompt_tokens,
                    completion_tokens,
                )
            except OSError as e:
                # Atomic write failed (disk full?) - try append-only fallback
                _logger.warning("Token tracker atomic write failed, using append mode: %s", e)
                try:
                    with open(_TOKEN_TRACKER_PATH, "a", encoding="utf-8") as f:
                        f.write(json.dumps(new_record) + "\n")
                except Exception:
                    pass  # Last resort - silently fail to not block inference

        except Exception as e:
            _logger.warning("Legacy token tracking failed: %s", e)

    def is_provider_available(self) -> bool:
        """Check if the current provider is available."""
        if hasattr(self._provider, 'is_available'):
            return self._provider.is_available()
        if hasattr(self._provider, 'is_healthy'):
            return self._provider.is_healthy()
        return True  # Assume available if method not implemented


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
