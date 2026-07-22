"""Tests for GroqProvider LLM interface."""

import pytest
from unittest.mock import patch, MagicMock

from utils.groq_provider import GroqProvider, _extract_json
from utils.llm_provider import get_provider, LLMProviderFactory


class TestGroqProvider:
    """Tests for GroqProvider class."""

    def test_provider_name(self):
        """Provider name should be 'groq'."""
        provider = GroqProvider()
        assert provider.name == "groq"

    def test_default_model_routing(self):
        """Default models should be assigned to different tasks."""
        provider = GroqProvider()
        assert provider.get_model("default") == "llama-3.1-8b-instant"
        assert provider.get_model("sentiment") == "llama-3.1-8b-instant"
        assert provider.get_model("analysis") == "qwen/qwen3.6-27b"
        assert provider.get_model("powerful") == "llama-3.3-70b-versatile"

    def test_custom_model_override(self):
        """Custom models should override defaults."""
        provider = GroqProvider({
            "models": {
                "sentiment": "qwen/qwen3.6-27b",
            }
        })
        assert provider.get_model("sentiment") == "qwen/qwen3.6-27b"
        # Other defaults should still work
        assert provider.get_model("default") == "llama-3.1-8b-instant"

    def test_infer_success(self):
        """infer() should return InferenceResult with text."""
        provider = GroqProvider({"api_key": "test-key"})

        with patch.object(provider._client, "chat") as mock_chat:
            mock_chat.return_value = "This is positive sentiment."

            result = provider.infer(
                task="sentiment",
                prompt="Company X had a great quarter!"
            )

            assert result.success is True
            assert result.text == "This is positive sentiment."
            assert result.model == "llama-3.1-8b-instant"
            assert result.prompt_tokens > 0
            mock_chat.assert_called_once()

    def test_infer_failure(self):
        """infer() should return failed InferenceResult on error."""
        provider = GroqProvider({"api_key": "bad-key"})

        with patch.object(provider._client, "chat") as mock_chat:
            mock_chat.return_value = None
            provider._client._last_error = "Invalid API key"

            result = provider.infer(task="sentiment", prompt="test")

            assert result.success is False
            assert result.error is not None

    def test_infer_with_system_prompt(self):
        """infer() should include system prompt in messages."""
        provider = GroqProvider({"api_key": "test-key"})

        with patch.object(provider._client, "chat") as mock_chat:
            mock_chat.return_value = "Analysis complete."

            provider.infer(
                task="analysis",
                prompt="What went wrong?",
                system_prompt="You are a financial analyst."
            )

            # Check that messages include system and user
            call_args = mock_chat.call_args
            messages = call_args[1]["messages"]
            assert len(messages) == 2
            assert messages[0]["role"] == "system"
            assert messages[0]["content"] == "You are a financial analyst."
            assert messages[1]["role"] == "user"

    def test_chat_returns_text(self):
        """chat() should return text response."""
        provider = GroqProvider({"api_key": "test-key"})

        with patch.object(provider._client, "chat") as mock_chat:
            mock_chat.return_value = "Hello from Groq!"

            result = provider.chat([
                {"role": "user", "content": "Say hello"}
            ])

            assert result == "Hello from Groq!"

    def test_infer_json(self):
        """infer_json() should parse JSON from response."""
        provider = GroqProvider({"api_key": "test-key"})

        with patch.object(provider._client, "chat") as mock_chat:
            mock_chat.return_value = '{"sentiment": "positive", "confidence": 0.95}'

            result = provider.infer_json(
                prompt="Analyze sentiment",
                task="sentiment"
            )

            assert result is not None
            assert result["sentiment"] == "positive"
            assert result["confidence"] == 0.95

    def test_infer_json_handles_code_fence(self):
        """infer_json() should handle code-fenced JSON."""
        provider = GroqProvider({"api_key": "test-key"})

        with patch.object(provider._client, "chat") as mock_chat:
            mock_chat.return_value = '```json\n{"result": "ok"}\n```'

            result = provider.infer_json(
                prompt="Return JSON",
                task="default"
            )

            assert result is not None
            assert result["result"] == "ok"

    def test_is_available_health_check(self):
        """is_available() should check client health."""
        provider = GroqProvider({"api_key": "test-key"})

        with patch.object(provider._client, "is_healthy") as mock_health:
            mock_health.return_value = True
            assert provider.is_available() is True

            mock_health.return_value = False
            assert provider.is_available() is False


class TestGroqProviderFactory:
    """Tests for factory integration."""

    def test_get_provider_groq(self):
        """Factory should create GroqProvider."""
        LLMProviderFactory.clear_cache()
        provider = get_provider("groq", {"llm": {"provider": "groq", "groq": {"api_key": "test"}}})
        assert provider.name == "groq"

    def test_get_provider_from_config(self):
        """Factory should read provider from config."""
        LLMProviderFactory.clear_cache()
        config = {
            "llm": {
                "provider": "groq",
                "groq": {"api_key": "test-key"}
            }
        }
        provider = get_provider(config=config)
        assert provider.name == "groq"


class TestExtractJson:
    """Tests for JSON extraction helper."""

    def test_raw_json_object(self):
        """Should parse raw JSON object."""
        result = _extract_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_raw_json_array(self):
        """Should parse raw JSON array."""
        result = _extract_json('["a", "b", "c"]')
        assert result == ["a", "b", "c"]

    def test_code_fenced_json(self):
        """Should strip code fences and parse."""
        result = _extract_json('```json\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_code_fence_with_language(self):
        """Should handle code fence with language tag."""
        result = _extract_json('```json\n{"result": "ok"}\n```')
        assert result == {"result": "ok"}

    def test_preamble_before_json(self):
        """Should find JSON after preamble text."""
        result = _extract_json("Here is the result:\n{\"value\": 42}")
        assert result == {"value": 42}

    def test_invalid_json_returns_none(self):
        """Should return None for invalid JSON."""
        result = _extract_json("Not valid JSON at all")
        assert result is None