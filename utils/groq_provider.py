"""Groq LLM provider implementation.

Provides LLM inference via Groq API with task-based model routing.
Free tier supports llama-3.1-8b-instant, qwen/qwen3.6-27b, and llama-3.3-70b-versatile.

Usage:
    from utils.groq_provider import GroqProvider

    provider = GroqProvider({
        "api_key": "gsk_...",  # or set GROQ_API_KEY env var
        "models": {
            "default": "llama-3.1-8b-instant",
            "sentiment": "llama-3.1-8b-instant",
            "analysis": "qwen/qwen3.6-27b",
            "powerful": "llama-3.3-70b-versatile",
        }
    })
    result = provider.infer("sentiment", "Company X failed due to market conditions")

Configuration:
    - Set GROQ_API_KEY in .env or .env.docker
    - Default config uses fast models for efficiency
    - API docs: https://console.groq.com/docs
    - Rate limits: 14,400 requests/minute (free tier)
"""

import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from utils.llm_provider import LLMProvider, InferenceResult
from utils.groq_client import GroqClient
from utils.token_tracker import TokenTracker

_logger = logging.getLogger(__name__)

# Default model configuration (sorted by efficiency for free tier)
DEFAULT_MODELS = {
    "default": "llama-3.1-8b-instant",  # Fastest, cheapest
    "sentiment": "llama-3.1-8b-instant",
    "ner": "llama-3.1-8b-instant",
    "summarization": "llama-3.1-8b-instant",
    "failure_analysis": "qwen/qwen3.6-27b",  # Better for complex analysis (replaces mixtral)
    "classification": "llama-3.1-8b-instant",
    "chat": "llama-3.1-8b-instant",
    "analysis": "qwen/qwen3.6-27b",
    "code": "llama-3.3-70b-versatile",  # Best for code (updated from llama-3.1-70b-versatile)
    "powerful": "llama-3.3-70b-versatile",
}


class GroqProvider(LLMProvider):
    """Groq provider for cloud LLM inference.

    Features:
    - Task-based model routing (fast models by default)
    - Automatic JSON extraction
    - Per-inference token tracking
    - Retry with exponential backoff
    - Free tier friendly (14,400 req/min)

    Models:
    - llama-3.1-8b-instant: Fastest, best for simple tasks
    - mixtral-8x7b-32768: Good balance of speed and quality
    - llama-3.1-70b-versatile: Best quality, slower
    """

    def __init__(self, config: dict | None = None):
        """Initialize Groq provider.

        Args:
            config: Provider configuration with keys:
                - api_key: Groq API key (or set GROQ_API_KEY env var)
                - base_url: API base URL (default: https://api.groq.com/openai/v1)
                - models: dict mapping task names to model names
                - timeout: Request timeout in seconds (default: 60)
        """
        config = config or {}

        # Load env vars from .env files
        for dotenv_path in [Path.cwd() / ".env", Path.cwd() / ".env.docker"]:
            if dotenv_path.exists():
                load_dotenv(dotenv_path, override=False)

        api_key = config.get("api_key") or os.getenv("GROQ_API_KEY", "")
        if not api_key:
            _logger.warning("GroqProvider: GROQ_API_KEY not set")

        self._client = GroqClient(
            api_key=api_key,
            timeout=config.get("timeout", 60),
            max_retries=config.get("max_retries", 3),
        )

        self.models = DEFAULT_MODELS.copy()
        self.models.update(config.get("models", {}))

        self._token_tracker = TokenTracker()

    @property
    def name(self) -> str:
        """Provider name."""
        return "groq"

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
        """Run task-based inference via Groq.

        Args:
            task: Task type for model routing (e.g., 'sentiment', 'ner').
            prompt: User message content.
            system_prompt: Optional system message.
            temperature: Generation temperature (0.0-2.0).
            max_retries: Retry attempts on failure (handled internally).
            timeout: Request timeout in seconds.
            **kwargs: Additional options (model override, etc.)

        Returns:
            InferenceResult with text, model, tokens, and status.
        """
        model = kwargs.get("model") or self.get_model(task)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Update client timeout if specified
        original_timeout = self._client.timeout
        if timeout:
            self._client.timeout = timeout

        try:
            text = self._client.chat(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=kwargs.get("max_tokens", 1024),
            )

            if text is not None:
                # Estimate tokens (Groq doesn't return token counts in free tier)
                # Rough estimate: ~4 chars per token
                prompt_tokens = sum(len(m.get("content", "")) for m in messages) // 4
                completion_tokens = len(text) // 4

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
            else:
                return InferenceResult(
                    text="",
                    model=model,
                    success=False,
                    error=self._client.last_error or "Unknown error",
                )

        finally:
            # Restore timeout
            self._client.timeout = original_timeout

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
            **kwargs: Additional options (timeout, max_tokens, etc.)

        Returns:
            Response content string.
        """
        model = model or self.get_model("default")

        # Update timeout if specified
        if kwargs.get("timeout"):
            original_timeout = self._client.timeout
            self._client.timeout = kwargs["timeout"]

        try:
            text = self._client.chat(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=kwargs.get("max_tokens", 1024),
            )

            # Track usage
            if text is not None:
                prompt_tokens = sum(len(m.get("content", "")) for m in messages) // 4
                completion_tokens = len(text) // 4
                self._token_tracker.track(
                    provider=self.name,
                    model=model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                )

            return text or ""

        except Exception as e:
            _logger.error("Groq chat failed: %s", e)
            return ""

        finally:
            if kwargs.get("timeout"):
                self._client.timeout = original_timeout

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

        Args:
            prompt: User message content.
            task: Task type for model routing.
            system_prompt: Optional system message.
            temperature: Lower temperature for JSON (more deterministic).
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
            **kwargs
        )

        if not result.success or not result.text:
            return None

        return _extract_json(result.text)

    def is_available(self) -> bool:
        """Check if Groq API is reachable and credentials are valid."""
        return self._client.is_healthy()


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