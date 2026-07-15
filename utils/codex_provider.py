"""Codex LLM provider implementation.

Provides LLM inference via Codex (or FCC proxy) with task-based model routing.

Usage:
    from utils.codex_provider import CodexProvider

    provider = CodexProvider({
        "base_url": "http://localhost:8082/v1",  # FCC proxy
        "api_key": "fcc-no-auth",
        "models": {
            "default": "nvidia_nim/nvidia/nemotron-3-super-120b-a12b",
            "code_gen": "opencode/gpt-5.3-codex",
            "analysis": "nvidia_nim/z-ai/glm5.1",
        }
    })
    result = provider.infer("analysis", "Analyze this failure data...")
"""

import logging
import os

from utils.llm_provider import LLMProvider, InferenceResult
from utils.codex_client import CodexClient
from utils.token_tracker import TokenTracker

_logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_BASE_URL = "http://localhost:8082/v1"
DEFAULT_MODEL = "nvidia_nim/nvidia/nemotron-3-super-120b-a12b"


class CodexProvider(LLMProvider):
    """Codex provider using FCC proxy or direct API.

    Features:
    - Works with Free Claude Code proxy (localhost:8082)
    - Task-based model routing
    - OpenAI Responses API compatibility
    - JSON extraction from responses
    """

    def __init__(self, config: dict | None = None):
        """Initialize Codex provider.

        Args:
            config: Provider configuration with keys:
                - base_url: API base URL (default: localhost:8082)
                - api_key: API key (from FCC_CODEX_API_KEY env if not provided)
                - models: dict mapping task names to model names
        """
        config = config or {}

        base_url = config.get(
            "base_url",
            os.getenv("CODEX_BASE_URL", os.getenv("FCC_BASE_URL", DEFAULT_BASE_URL))
        )
        api_key = config.get(
            "api_key",
            os.getenv("FCC_CODEX_API_KEY", os.getenv("CODEX_API_KEY", ""))
        )

        # Default model - used when task doesn't have specific model
        default_model = config.get("models", {}).get(
            "default",
            os.getenv("CODEX_MODEL", DEFAULT_MODEL)
        )

        self.client = CodexClient(
            base_url=base_url,
            api_key=api_key or "fcc-no-auth",
            model=default_model,
        )

        # Task to model mapping
        model_config = config.get("models", {})
        self.task_models = {
            # Sentiment/classification tasks
            "sentiment": model_config.get("sentiment"),
            "classification": model_config.get("classification"),
            "ner": model_config.get("ner"),
            # Analysis tasks
            "analysis": model_config.get("analysis"),
            "failure_analysis": model_config.get("failure_analysis"),
            "summarization": model_config.get("summarization"),
            # Code tasks
            "code_gen": model_config.get("code_gen"),
            "default": model_config.get("default"),
        }

        self._token_tracker = TokenTracker()

    @property
    def name(self) -> str:
        """Provider name."""
        return "codex"

    def infer(
        self,
        task: str,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        **kwargs
    ) -> InferenceResult:
        """Run task-based inference via Codex.

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
        model = self.task_models.get(task)

        # Build system prompt if task has default behavior
        if system_prompt is None and task not in ["default"]:
            system_prompt = f"You are performing a {task} task."

        result = self.client.infer(
            prompt=prompt,
            task=task,
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )

        # Track usage from result
        if result.get("prompt_tokens") or result.get("completion_tokens"):
            self._token_tracker.track(
                provider=self.name,
                model=result.get("model", self.client.model),
                prompt_tokens=result.get("prompt_tokens", 0),
                completion_tokens=result.get("completion_tokens", 0),
                task=task,
            )

        return InferenceResult(
            text=result.get("text", ""),
            model=result.get("model", self.client.model),
            prompt_tokens=result.get("prompt_tokens", 0),
            completion_tokens=result.get("completion_tokens", 0),
            total_tokens=result.get("total_tokens", 0),
            success=result.get("success", False),
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
        model = model or self.client.model
        text = self.client.chat(
            messages,
            model=model,
            temperature=temperature,
            **kwargs
        )

        # Track basic usage (may not have token counts without response parsing)
        if text:
            # TODO: Parse token counts from response if available
            pass

        return text or ""

    def infer_json(
        self,
        prompt: str,
        task: str = "default",
        system_prompt: str | None = None,
        **kwargs
    ) -> dict | list | None:
        """Run inference with JSON extraction from response.

        Args:
            prompt: User message content.
            task: Task type.
            system_prompt: Optional system message.
            **kwargs: Additional options.

        Returns:
            Parsed JSON (dict or list) or None on parse failure.
        """
        if system_prompt is None:
            system_prompt = (
                "Respond ONLY with valid JSON. No explanation, no markdown, no code fences. "
                "Output must be parseable by json.loads()."
            )

        return self.client.infer_json(
            prompt=prompt,
            system_prompt=system_prompt,
            model=self.task_models.get(task),
            **kwargs
        )

    def is_available(self) -> bool:
        """Check if Codex endpoint is responsive."""
        return self.client.is_healthy()