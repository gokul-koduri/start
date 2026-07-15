"""Unit tests for Codex client and provider.

Tests the Codex API client and provider implementation.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from utils.codex_client import CodexClient, _extract_json
from utils.codex_provider import CodexProvider


class TestCodexClient:
    """Tests for CodexClient."""

    def test_init_with_defaults(self):
        """Test client initialization with defaults."""
        client = CodexClient()
        assert client.base_url == "http://localhost:8082/v1"
        assert client.model == "nvidia_nim/nvidia/nemotron-3-super-120b-a12b"
        assert client.timeout == 120
        assert client.max_retries == 3

    def test_init_with_config(self):
        """Test client initialization with custom config."""
        client = CodexClient(
            base_url="http://custom:9000/v1",
            api_key="test-key",
            model="custom/model",
            timeout=60,
        )
        assert client.base_url == "http://custom:9000/v1"
        assert client.api_key == "test-key"
        assert client.model == "custom/model"
        assert client.timeout == 60

    def test_get_headers(self):
        """Test header generation."""
        client = CodexClient(api_key="test-key")
        headers = client._get_headers()
        assert headers["Authorization"] == "Bearer test-key"
        assert headers["Content-Type"] == "application/json"

    def test_build_payload(self):
        """Test payload building for OpenAI Responses API."""
        client = CodexClient(model="test-model")
        payload = client._build_payload(
            [{"role": "user", "content": "Hello"}],
            model="override-model",
            temperature=0.5,
        )
        assert payload["model"] == "override-model"
        assert payload["input"] == [{"role": "user", "content": "Hello"}]
        assert payload["temperature"] == 0.5
        assert payload["max_tokens"] == 4096

    @patch("utils.codex_client.urllib.request.urlopen")
    def test_chat_success(self, mock_urlopen):
        """Test successful chat request."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({
            "output": [
                {
                    "type": "message",
                    "content": [
                        {"type": "output_text", "text": "Hello, world!"}
                    ]
                }
            ],
            "usage": {"input_tokens": 10, "output_tokens": 20}
        }).encode()
        mock_urlopen.return_value.__enter__ = Mock(return_value=mock_response)
        mock_urlopen.return_value.__exit__ = Mock(return_value=False)

        client = CodexClient()
        result = client.chat([{"role": "user", "content": "Hello"}])

        assert result == "Hello, world!"

    @patch("utils.codex_client.urllib.request.urlopen")
    def test_infer_success(self, mock_urlopen):
        """Test task-based inference."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({
            "output": [
                {
                    "type": "message",
                    "content": [
                        {"type": "output_text", "text": "Analysis complete."}
                    ]
                }
            ]
        }).encode()
        mock_urlopen.return_value.__enter__ = Mock(return_value=mock_response)
        mock_urlopen.return_value.__exit__ = Mock(return_value=False)

        client = CodexClient()
        result = client.infer("analysis", "Analyze this data")

        assert result["text"] == "Analysis complete."
        assert result["model"] == "nvidia_nim/nvidia/nemotron-3-super-120b-a12b"
        assert result["success"] is True

    @patch("utils.codex_client.urllib.request.urlopen")
    def test_infer_json_success(self, mock_urlopen):
        """Test JSON extraction from response."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({
            "output": [
                {
                    "type": "message",
                    "content": [
                        {"type": "output_text", "text": '{"key": "value"}'}
                    ]
                }
            ]
        }).encode()
        mock_urlopen.return_value.__enter__ = Mock(return_value=mock_response)
        mock_urlopen.return_value.__exit__ = Mock(return_value=False)

        client = CodexClient()
        result = client.infer_json("Return JSON")

        assert result == {"key": "value"}

    @patch("utils.codex_client.urllib.request.urlopen")
    def test_chat_with_retry(self, mock_urlopen):
        """Test retry on failure."""
        import urllib.error

        # First call fails, second succeeds
        mock_response_fail = MagicMock()
        mock_response_fail.status = 500

        mock_response_success = MagicMock()
        mock_response_success.status = 200
        mock_response_success.read.return_value = json.dumps({
            "output": [
                {"type": "message", "content": [{"type": "output_text", "text": "OK"}]}
            ]
        }).encode()
        mock_response_success.__enter__ = Mock(return_value=mock_response_success)
        mock_response_success.__exit__ = Mock(return_value=False)

        mock_urlopen.side_effect = [
            urllib.error.URLError("Server error"),
            mock_response_success
        ]

        client = CodexClient(max_retries=2)
        result = client.chat([{"role": "user", "content": "Hello"}])

        assert result == "OK"
        assert mock_urlopen.call_count == 2

    @patch("utils.codex_client.urllib.request.urlopen")
    def test_chat_rejects_empty_200_response(self, mock_urlopen):
        """Test that an empty 200 response is treated as a proxy/gateway issue."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b""
        mock_urlopen.return_value.__enter__ = Mock(return_value=mock_response)
        mock_urlopen.return_value.__exit__ = Mock(return_value=False)

        client = CodexClient()
        result = client.chat([{"role": "user", "content": "Hello"}])

        assert result is None
        assert "empty or malformed response" in (client.last_error or "")


class TestExtractJson:
    """Tests for JSON extraction helper."""

    def test_extract_raw_json(self):
        """Test extraction of raw JSON."""
        result = _extract_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_extract_code_fenced_json(self):
        """Test extraction of code-fenced JSON."""
        result = _extract_json('```json\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_extract_json_with_preamble(self):
        """Test extraction of JSON with text before it."""
        result = _extract_json('Here is the result: {"key": "value"}')
        assert result == {"key": "value"}

    def test_extract_json_array(self):
        """Test extraction of JSON array."""
        result = _extract_json('[{"a": 1}, {"b": 2}]')
        assert result == [{"a": 1}, {"b": 2}]

    def test_extract_invalid_json(self):
        """Test that invalid JSON returns None."""
        result = _extract_json("Not JSON at all")
        assert result is None


class TestCodexProvider:
    """Tests for CodexProvider."""

    def test_init(self):
        """Test provider initialization."""
        provider = CodexProvider({
            "api_key": "test-key",
            "models": {
                "default": "model/default",
                "analysis": "model/analysis",
            }
        })
        assert provider.name == "codex"
        assert provider.client.api_key == "test-key"

    def test_infer_uses_task_model(self):
        """Test that infer uses task-specific model when configured."""
        provider = CodexProvider({
            "models": {
                "default": "default-model",
                "analysis": "analysis-model",
            }
        })

        with patch.object(provider, 'client') as mock_client:
            mock_client.infer.return_value = {
                "text": "result",
                "model": "analysis-model",
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30,
                "success": True,
            }

            result = provider.infer("analysis", "Analyze this")

            assert result.model == "analysis-model"

    def test_is_available(self):
        """Test availability check."""
        provider = CodexProvider({})
        with patch.object(provider.client, 'is_healthy', return_value=True):
            assert provider.is_available() is True


class TestIntegration:
    """Integration-style tests (mocked external calls)."""

    def test_full_infer_flow(self):
        """Test complete inference flow with mocked API."""
        client = CodexClient()

        with patch("utils.codex_client.urllib.request.urlopen") as mock:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.read.return_value = json.dumps({
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {"type": "output_text", "text": '```json\n{"sentiment": "positive", "confidence": 0.95}\n```'}
                        ]
                    }
                ],
                "usage": {"input_tokens": 50, "output_tokens": 30}
            }).encode()
            mock.return_value.__enter__ = Mock(return_value=mock_response)
            mock.return_value.__exit__ = Mock(return_value=False)

            # Test inference
            result = client.infer("sentiment", "This company raised $100M!")
            assert result["success"] is True
            assert result["text"] == '```json\n{"sentiment": "positive", "confidence": 0.95}\n```'

            # Test JSON extraction
            json_result = client.infer_json("Give me JSON", system_prompt="Respond with JSON only")
            assert json_result == {"sentiment": "positive", "confidence": 0.95}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])