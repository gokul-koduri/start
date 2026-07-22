"""Unified LLM Provider Interface.

Provides a common abstraction for different LLM backends (Ollama, Codex, NVIDIA NIM).
Usage:
    from utils.llm_provider import get_provider

    # Get default provider (from config)
    provider = get_provider()
    result = provider.infer("sentiment", "Company X failed...")

    # Get specific provider
    ollama = get_provider("ollama")
    codex = get_provider("codex")
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import logging

_logger = logging.getLogger(__name__)


@dataclass
class InferenceResult:
    """Standardized result from LLM inference."""
    text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    success: bool = True
    error: Optional[str] = None


class LLMProvider(ABC):
    """Abstract interface for LLM providers.

    All concrete providers must implement these methods.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g., 'ollama', 'codex', 'nvidia_nim')."""
        pass

    @abstractmethod
    def chat(self, messages: list[dict], **kwargs) -> str:
        """Send a chat completion request.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            **kwargs: Provider-specific options (model, temperature, etc.)

        Returns:
            Response content string.
        """
        pass

    @abstractmethod
    def infer(self, task: str, prompt: str, **kwargs) -> InferenceResult:
        """Task-based inference with standardized output.

        Args:
            task: Task type for model routing (e.g., 'sentiment', 'ner').
            prompt: User message content.
            **kwargs: Additional options (system_prompt, temperature, etc.)

        Returns:
            InferenceResult with text, model, tokens, and status.
        """
        pass

    @abstractmethod
    def infer_json(self, prompt: str, **kwargs) -> dict | list | None:
        """Inference with JSON extraction from response.

        Args:
            prompt: User message content.
            **kwargs: Additional options (task, system_prompt, etc.)

        Returns:
            Parsed JSON (dict or list) or None on parse failure.
        """
        pass

    def is_available(self) -> bool:
        """Check if the provider is available and responsive.

        Returns:
            True if provider can accept requests.
        """
        return True


class LLMProviderFactory:
    """Factory for creating LLM providers."""

    _providers: dict[str, type] = {}
    _instance_cache: dict[str, LLMProvider] = {}

    @classmethod
    def register(cls, name: str, provider_class: type):
        """Register a provider class.

        Args:
            name: Provider name (e.g., 'ollama').
            provider_class: Class inheriting from LLMProvider.
        """
        cls._providers[name] = provider_class
        _logger.debug("Registered LLM provider: %s", name)

    @classmethod
    def get_provider(
        cls,
        provider_name: str | None = None,
        config: dict | None = None,
        force_new: bool = False,
    ) -> LLMProvider:
        """Get an LLM provider instance.

        Args:
            provider_name: Provider name. If None, reads from config.
            config: Full config dict. If provider_name is None, reads provider
                   from config.get("llm", {}).get("provider", "ollama").
            force_new: If True, creates new instance instead of cached.

        Returns:
            LLMProvider instance.
        """
        config = config or {}

        if provider_name is None:
            provider_name = config.get("llm", {}).get("provider", "ollama")

        # Return cached instance if available
        cache_key = f"{provider_name}:{id(config)}"
        if not force_new and cache_key in cls._instance_cache:
            return cls._instance_cache[cache_key]

        if provider_name not in cls._providers:
            # Try to lazy-load common providers
            if provider_name == "ollama":
                from utils.ollama_provider import OllamaProvider
                cls.register("ollama", OllamaProvider)
            elif provider_name == "codex":
                from utils.codex_provider import CodexProvider
                cls.register("codex", CodexProvider)
            elif provider_name == "nvidia_nim":
                from utils.nim_provider import NvidiaNimProvider
                cls.register("nvidia_nim", NvidiaNimProvider)
            elif provider_name == "groq":
                from utils.groq_provider import GroqProvider
                cls.register("groq", GroqProvider)

        if provider_name not in cls._providers:
            raise ValueError(
                f"Unknown provider: {provider_name}. "
                f"Available: {list(cls._providers.keys())}"
            )

        provider_config = config.get("llm", {}).get(provider_name, {})
        provider = cls._providers[provider_name](provider_config)

        # Cache for reuse
        cls._instance_cache[cache_key] = provider

        _logger.info("Created LLM provider: %s", provider_name)
        return provider

    @classmethod
    def list_providers(cls) -> list[str]:
        """List all registered provider names."""
        return list(cls._providers.keys())

    @classmethod
    def clear_cache(cls):
        """Clear the provider instance cache."""
        cls._instance_cache.clear()


def get_provider(provider_name: str | None = None, config: dict | None = None) -> LLMProvider:
    """Convenience function to get an LLM provider.

    Usage:
        ollama = get_provider("ollama")
        codex = get_provider("codex", config)
        default = get_provider()  # From config

    Args:
        provider_name: Provider name or None for default.
        config: Config dict containing 'llm' section.

    Returns:
        LLMProvider instance.
    """
    return LLMProviderFactory.get_provider(provider_name, config)


class NopProvider(LLMProvider):
    """No-operation provider for testing or fallback."""

    @property
    def name(self) -> str:
        return "nop"

    def chat(self, messages: list[dict], **kwargs) -> str:
        return "NOP response"

    def infer(self, task: str, prompt: str, **kwargs) -> InferenceResult:
        return InferenceResult(
            text="NOP response",
            model="nop",
            success=True,
        )

    def infer_json(self, prompt: str, **kwargs) -> dict | None:
        return None


# Auto-register NOP provider
LLMProviderFactory.register("nop", NopProvider)