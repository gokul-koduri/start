"""NVIDIA NIM LLM provider implementation.

Provides LLM inference via NVIDIA NIM with OpenAI-compatible API.

Usage:
    from utils.nim_provider import NvidiaNimProvider

    provider = NvidiaNimProvider({
        "base_url": "https://integrate.api.nvidia.com/v1",
        "api_key": "${NVIDIA_NIM_API_KEY}",
        "models": {
            "default": "meta/llama-3.1-405b-instruct",
            "code_gen": "nvidia/nemotron-3-super-120b-a12b",
        }
    })
    result = provider.infer("analysis", "Analyze this failure data...")
"""

import json
import logging
import os
from typing import Optional

from utils.llm_provider import LLMProvider, InferenceResult
from utils.nvidia_nim_client import NvidiaNimClient
from utils.token_tracker import TokenTracker

_logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "meta/llama-3.1-405b-instruct"


class NvidiaNimProvider(LLMProvider):
    """NVIDIA NIM provider using OpenAI-compatible API.

    Features:
    - Task-based model routing
    - JSON extraction from responses
    - Token usage tracking via unified tracker
    - Retry with exponential backoff
    """

    def __init__(self, config: dict | None = None):
        """Initialize NIM provider.

        Args:
            config: Provider configuration with keys:
                - base_url: API base URL (default: NVIDIA NIM endpoint)
                - api_key: API key (from NVIDIA_NIM_API_KEY env if not provided)
                - models: dict mapping task names to model names
        """
        config = config or {}

        self.client = NvidiaNimClient(
            base_url=config.get("base_url", DEFAULT_BASE_URL),
            api_key=config.get("api_key"),  # Will use env var if None
            model=config.get("models", {}).get(
                "default",
                os.getenv("NVIDIA_NIM_MODEL", DEFAULT_MODEL)
            ),
            timeout=config.get("timeout", 120),
            max_retries=config.get("max_retries", 3),
        )

        # Task to model mapping
        model_config = config.get("models", {})
        self.task_models = {
            "sentiment": model_config.get("sentiment"),
            "classification": model_config.get("classification"),
            "ner": model_config.get("ner"),
            "analysis": model_config.get("analysis"),
            "failure_analysis": model_config.get("failure_analysis"),
            "summarization": model_config.get("summarization"),
            "code_gen": model_config.get("code_gen"),
            "default": model_config.get("default"),
        }

        self._token_tracker = TokenTracker()

    @property
    def name(self) -> str:
        """Provider name."""
        return "nvidia_nim"

    def infer(
        self,
        task: str,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        **kwargs
    ) -> InferenceResult:
        """Run task-based inference via NIM.

        Args:
            task: Task type (e.g., 'sentiment', 'analysis', 'code_gen').
            prompt: User message content.
            system_prompt: Optional system message.
            temperature: Generation temperature.
            max_tokens: Max tokens to generate.
            **kwargs: Additional options.

        Returns:
            InferenceResult with text, model, tokens, and status.
        """
        # Route to specific model if task has one configured
        model = self.task_models.get(task) or self.client.model

        # Build message list
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        elif task not in ["default"]:
            messages.append({
                "role": "system",
                "content": f"You are performing a {task} task."
            })
        messages.append({"role": "user", "content": prompt})

        # Make request
        try:
            text = self.client.chat(
                messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            success = text is not None

            # Note: Token counts from NIM aren't easily accessible in current client
            # We track what we can
            prompt_tokens = kwargs.get("prompt_tokens", 0)
            completion_tokens = kwargs.get("completion_tokens", 0)

            if success and (prompt_tokens or completion_tokens):
                self._token_tracker.track(
                    provider=self.name,
                    model=model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    task=task,
                )

            return InferenceResult(
                text=text or "",
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                success=success,
                error=self.client.last_error if not success else None,
            )

        except Exception as e:
            _logger.error("NIM inference failed: %s", e)
            return InferenceResult(
                text="",
                model=model,
                success=False,
                error=str(e),
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
        return self.client.chat(
            messages,
            model=model or self.client.model,
            temperature=temperature,
            **kwargs
        ) or ""

    def infer_json(
        self,
        prompt: str,
        task: str = "default",
        system_prompt: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        **kwargs
    ) -> dict | list | None:
        """Run inference with JSON extraction from response.

        Args:
            prompt: User message content.
            task: Task type.
            system_prompt: Optional system message.
            temperature: Generation temperature (lower for JSON).
            max_tokens: Max tokens to generate.
            **kwargs: Additional options.

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
            max_tokens=max_tokens,
            **kwargs
        )

        if not result.success or not result.text:
            return None

        return _extract_json(result.text)

    def is_available(self) -> bool:
        """Check if NIM endpoint is responsive."""
        return self.client.is_healthy()

    @property
    def last_error(self) -> Optional[str]:
        """Return the last error message."""
        return self.client.last_error


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