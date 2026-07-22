"""Tests for Groq API client."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from utils.groq_client import GroqClient


def test_client_uses_groq_api_key_env(monkeypatch):
    """Test that client reads GROQ_API_KEY from environment."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test-key")

    client = GroqClient()

    assert client.api_key == "gsk_test-key"


def test_client_prefers_explicit_api_key():
    """Test that explicit api_key takes precedence over env var."""
    client = GroqClient(api_key="explicit-key")

    assert client.api_key == "explicit-key"


def test_client_default_model():
    """Test that default model is set correctly."""
    client = GroqClient()

    assert client.model == "llama-3.1-8b-instant"


def test_client_custom_model():
    """Test that custom model can be specified."""
    client = GroqClient(model="mixtral-8x7b-32768")

    assert client.model == "mixtral-8x7b-32768"


def test_get_headers():
    """Test that auth headers are correctly built."""
    client = GroqClient(api_key="test-key")

    headers = client.get_headers()

    assert headers["Authorization"] == "Bearer test-key"
    assert headers["Content-Type"] == "application/json"


def test_chat_returns_response(monkeypatch):
    """Test successful chat completion."""
    client = GroqClient(api_key="test-key")

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = (
        b'{"choices": [{"message": {"content": "Hello!"}}]}'
    )
    mock_response.__enter__ = Mock(return_value=mock_response)
    mock_response.__exit__ = Mock(return_value=False)

    with patch("utils.groq_client.urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.__enter__ = Mock(return_value=mock_response)
        mock_urlopen.return_value.__exit__ = Mock(return_value=False)

        result = client.chat([{"role": "user", "content": "hello"}])

    assert result == "Hello!"
    assert client.last_error is None


def test_chat_handles_empty_response(monkeypatch):
    """Test that empty choices list returns None."""
    client = GroqClient(api_key="test-key")

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = b'{"choices": []}'
    mock_response.__enter__ = Mock(return_value=mock_response)
    mock_response.__exit__ = Mock(return_value=False)

    with patch("utils.groq_client.urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.__enter__ = Mock(return_value=mock_response)
        mock_urlopen.return_value.__exit__ = Mock(return_value=False)

        result = client.chat([{"role": "user", "content": "hello"}])

    assert result is None


def test_chat_retries_on_connection_error(monkeypatch):
    """Test that client retries on connection errors."""
    client = GroqClient(api_key="test-key", max_retries=3)

    success_response = MagicMock()
    success_response.status = 200
    success_response.read.return_value = (
        b'{"choices": [{"message": {"content": "Success!"}}]}'
    )
    success_response.__enter__ = Mock(return_value=success_response)
    success_response.__exit__ = Mock(return_value=False)

    import urllib.error

    connection_error = urllib.error.URLError("Connection reset")

    with patch("utils.groq_client.urllib.request.urlopen") as mock_urlopen, patch(
        "time.sleep"
    ):
        # Fail twice, succeed on third try
        mock_urlopen.side_effect = [
            connection_error,
            connection_error,
            success_response,
        ]

        result = client.chat([{"role": "user", "content": "hello"}])

    assert result == "Success!"


def test_chat_no_retry_on_auth_error(monkeypatch):
    """Test that auth errors don't trigger retries."""
    client = GroqClient(api_key="bad-key", max_retries=3)

    import urllib.error

    mock_response = MagicMock()
    mock_response.status = 401
    mock_response.read.return_value = b'{"error": {"message": "Invalid API key"}}'
    mock_response.__enter__ = Mock(return_value=mock_response)
    mock_response.__exit__ = Mock(return_value=False)

    with patch("utils.groq_client.urllib.request.urlopen") as mock_urlopen, patch(
        "time.sleep"
    ) as mock_sleep:
        error = urllib.error.HTTPError("url", 401, "Unauthorized", {}, mock_response)
        mock_urlopen.side_effect = error

        result = client.chat([{"role": "user", "content": "hello"}])

    assert result is None
    assert client.last_error is not None
    # Should not have slept for retries on auth error
    assert mock_sleep.call_count == 0


def test_health_check_success(monkeypatch):
    """Test health check when API is reachable."""
    client = GroqClient(api_key="test-key")

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.__enter__ = Mock(return_value=mock_response)
    mock_response.__exit__ = Mock(return_value=False)

    with patch("utils.groq_client.urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.__enter__ = Mock(return_value=mock_response)
        mock_urlopen.return_value.__exit__ = Mock(return_value=False)

        result = client.is_healthy()

    assert result is True


def test_health_check_failure(monkeypatch):
    """Test health check when API is unreachable."""
    client = GroqClient(api_key="test-key")

    import urllib.error

    with patch("utils.groq_client.urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        result = client.is_healthy()

    assert result is False


def test_client_no_api_key_warning(caplog, monkeypatch):
    """Test that warning is logged when no API key is set."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    with caplog.at_level("WARNING"):
        client = GroqClient()

    assert client.api_key == ""
    assert "GROQ_API_KEY not set" in caplog.text
