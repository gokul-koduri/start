from pathlib import Path
import sys
import urllib.error
from unittest.mock import MagicMock, Mock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from utils.nvidia_nim_client import NvidiaNimClient  # noqa: E402


def test_client_uses_nvidia_nim_api_key_env(monkeypatch):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.setenv("NVIDIA_NIM_API_KEY", "nim-key")

    client = NvidiaNimClient(base_url="https://example.com/v1")

    assert client.api_key == "nim-key"


def test_client_falls_back_to_legacy_nvidia_api_key_env(monkeypatch):
    monkeypatch.delenv("NVIDIA_NIM_API_KEY", raising=False)
    monkeypatch.setenv("NVIDIA_API_KEY", "legacy-key")

    client = NvidiaNimClient(base_url="https://example.com/v1")

    assert client.api_key == "legacy-key"


def test_client_prefers_explicit_api_key_argument(monkeypatch):
    monkeypatch.setenv("NVIDIA_NIM_API_KEY", "env-key")

    client = NvidiaNimClient(base_url="https://example.com/v1", api_key="explicit-key")

    assert client.api_key == "explicit-key"


def test_client_loads_api_key_from_dotenv_file(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("NVIDIA_NIM_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    (tmp_path / ".env").write_text("NVIDIA_NIM_API_KEY=dotenv-key\n")

    client = NvidiaNimClient(base_url="https://example.com/v1")

    assert client.api_key == "dotenv-key"


def test_client_auth_headers_work_for_server_endpoint(monkeypatch):
    nvidia_nim_path = ROOT / "nvidia-nim"
    sys.path.insert(0, str(nvidia_nim_path))

    try:
        import importlib

        importlib.import_module("pydantic_settings")
        importlib.import_module("loguru")
    except ModuleNotFoundError:
        pytest.skip(
            "nvidia-nim runtime dependencies are not available in this test environment"
        )

    from fastapi.testclient import TestClient

    from api.app import create_app
    from api.dependencies import get_settings
    from config.settings import Settings

    app = create_app()
    settings = Settings()
    api_key = "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"
    settings.anthropic_auth_token = api_key
    app.dependency_overrides[get_settings] = lambda: settings

    client = NvidiaNimClient(base_url="http://testserver/v1", api_key=api_key)
    payload = {
        "model": "claude-3-sonnet",
        "messages": [{"role": "user", "content": "hello"}],
    }

    try:
        with patch("api.routes.get_token_count", return_value=7):
            with TestClient(app) as test_client:
                response = test_client.post(
                    "/v1/messages/count_tokens",
                    json=payload,
                    headers=client.get_auth_headers(),
                )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["input_tokens"] == 7


def test_client_loads_api_key_from_env_docker_file(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("NVIDIA_NIM_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    (tmp_path / ".env.docker").write_text("NVIDIA_NIM_API_KEY=dotenv-docker-key\n")

    client = NvidiaNimClient(base_url="https://example.com/v1")

    assert client.api_key == "dotenv-docker-key"


def test_client_rejects_empty_200_response(monkeypatch):
    client = NvidiaNimClient(base_url="https://example.com/v1", api_key="test-key")

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = b""

    with patch("utils.nvidia_nim_client.urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.__enter__ = Mock(return_value=mock_response)
        mock_urlopen.return_value.__exit__ = Mock(return_value=False)

        result = client.chat([{"role": "user", "content": "hello"}])

    assert result is None
    assert "empty or malformed response" in (client.last_error or "")


def test_client_retry_on_connection_error(monkeypatch):
    """Test that the client retries on connection errors and succeeds on later attempt."""
    client = NvidiaNimClient(
        base_url="https://example.com/v1",
        api_key="test-key",
        max_retries=3,
    )

    success_response = MagicMock()
    success_response.status = 200
    success_response.read.return_value = (
        b'{"output": [{"content": {"text": "Hello response"}}]}'
    )
    success_response.__enter__ = Mock(return_value=success_response)
    success_response.__exit__ = Mock(return_value=False)

    connection_error = urllib.error.URLError("Connection reset")

    with patch("utils.nvidia_nim_client.urllib.request.urlopen") as mock_urlopen, patch(
        "time.sleep"
    ):
        mock_urlopen.side_effect = [
            connection_error,
            connection_error,
            success_response,
        ]

        result = client.chat([{"role": "user", "content": "hello"}])

    assert result == "Hello response"
