"""Tests for the OllamaClient — retry logic, connection pooling, health checks."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock pymysql before importing anything that uses it
mock_pymysql = MagicMock()
sys.modules["pymysql"] = mock_pymysql
sys.modules["pymysql.cursors"] = mock_pymysql.cursors

from utils.ollama_client import OllamaClient, _connection_pool, _get_connection  # noqa: E402


def _mock_response(status: int = 200, body: dict | None = None):
    """Create a mock HTTP response."""
    resp = MagicMock()
    resp.status = status
    resp.read.return_value = json.dumps(body or {}).encode()
    return resp


class TestOllamaClientInit:
    """Test client initialization and URL parsing."""

    def test_default_config(self):
        client = OllamaClient()
        assert client._host == "localhost"
        assert client._port == 11434
        assert client._path == "/api/chat"
        assert client.model == "llama3"
        assert client.max_retries == 3

    def test_custom_url(self):
        client = OllamaClient(url="http://myhost:8080/v1/chat/completions")
        assert client._host == "myhost"
        assert client._port == 8080
        assert client._path == "/v1/chat/completions"

    def test_url_without_port(self):
        client = OllamaClient(url="http://myhost/api/chat")
        assert client._host == "myhost"
        assert client._port == 11434  # default

    def test_https_url(self):
        client = OllamaClient(url="https://ollama.example.com:443/api/chat")
        assert client._host == "ollama.example.com"
        assert client._port == 443


class TestHealthCheck:
    """Test the is_healthy() method."""

    def test_healthy_when_ollama_responds(self):
        client = OllamaClient()
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            assert client.is_healthy() is True

    def test_unhealthy_when_connection_refused(self):
        client = OllamaClient()
        with patch("urllib.request.urlopen", side_effect=ConnectionRefusedError):
            assert client.is_healthy() is False
            assert "Health check failed" in (client.last_error or "")

    def test_unhealthy_when_timeout(self):
        client = OllamaClient()
        with patch("urllib.request.urlopen", side_effect=TimeoutError):
            assert client.is_healthy() is False


class TestChatSuccess:
    """Test successful chat completion."""

    def test_returns_content_on_success(self):
        client = OllamaClient()
        mock_conn = MagicMock()
        mock_conn.getresponse.return_value = _mock_response(
            200,
            {
                "message": {"content": "Hello from Ollama!"},
                "prompt_eval_count": 10,
                "eval_count": 5,
            },
        )

        with patch("utils.ollama_client._get_connection", return_value=mock_conn):
            result = client.chat([{"role": "user", "content": "Hi"}])

        assert result == "Hello from Ollama!"
        assert client.last_error is None

    def test_tracks_inference_tokens(self):
        client = OllamaClient()
        mock_conn = MagicMock()
        mock_conn.getresponse.return_value = _mock_response(
            200,
            {
                "message": {"content": "test"},
                "prompt_eval_count": 100,
                "eval_count": 50,
            },
        )

        mock_track = MagicMock()
        mock_module = MagicMock(_track_inference=mock_track)

        with patch(
            "utils.ollama_client._get_connection", return_value=mock_conn
        ), patch.dict(sys.modules, {"agents.ollama_usage_tracker_agent": mock_module}):
            client.chat([{"role": "user", "content": "test"}])
            mock_track.assert_called_once_with("llama3", 100, 50)

    def test_empty_content_returns_empty_string(self):
        client = OllamaClient()
        mock_conn = MagicMock()
        mock_conn.getresponse.return_value = _mock_response(200, {"message": {}})

        with patch("utils.ollama_client._get_connection", return_value=mock_conn):
            result = client.chat([{"role": "user", "content": "Hi"}])

        assert result == ""

    def test_missing_message_key_returns_empty_string(self):
        client = OllamaClient()
        mock_conn = MagicMock()
        mock_conn.getresponse.return_value = _mock_response(200, {})

        with patch("utils.ollama_client._get_connection", return_value=mock_conn):
            result = client.chat([{"role": "user", "content": "Hi"}])

        assert result == ""


class TestChatRetry:
    """Test retry logic on transient failures."""

    def test_retries_on_broken_pipe(self):
        """BrokenPipeError should clear connection and retry."""
        client = OllamaClient(max_retries=3, backoff_base=0.01)
        mock_conn = MagicMock()
        mock_conn.sock = MagicMock()  # pretend connected

        # First attempt: BrokenPipeError, second: success
        mock_conn.getresponse.side_effect = [
            BrokenPipeError("Connection broken"),
            _mock_response(200, {"message": {"content": "Success on retry"}}),
        ]

        with patch(
            "utils.ollama_client._get_connection", return_value=mock_conn
        ), patch("time.sleep"):
            result = client.chat([{"role": "user", "content": "Hi"}])

        assert result == "Success on retry"

    def test_retries_on_connection_refused(self):
        """ConnectionRefusedError should retry."""
        client = OllamaClient(max_retries=2, backoff_base=0.01)

        call_count = 0

        def get_conn(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_conn = MagicMock()
            if call_count == 1:
                mock_conn.request.side_effect = ConnectionRefusedError("No one home")
            else:
                mock_conn.getresponse.return_value = _mock_response(
                    200, {"message": {"content": "Connected!"}}
                )
            return mock_conn

        with patch("utils.ollama_client._get_connection", side_effect=get_conn), patch(
            "time.sleep"
        ):
            result = client.chat([{"role": "user", "content": "Hi"}])

        assert result == "Connected!"

    def test_retries_on_server_error_500(self):
        """500 errors should trigger retry."""
        client = OllamaClient(max_retries=2, backoff_base=0.01)
        mock_conn = MagicMock()

        mock_conn.getresponse.side_effect = [
            _mock_response(500, {"error": "internal"}),
            _mock_response(200, {"message": {"content": "Recovered"}}),
        ]

        with patch(
            "utils.ollama_client._get_connection", return_value=mock_conn
        ), patch("time.sleep"):
            result = client.chat([{"role": "user", "content": "Hi"}])

        assert result == "Recovered"

    def test_returns_none_after_max_retries(self):
        """Should return None after exhausting all retries."""
        client = OllamaClient(max_retries=2, backoff_base=0.01)
        mock_conn = MagicMock()
        mock_conn.request.side_effect = ConnectionRefusedError("Down")

        with patch(
            "utils.ollama_client._get_connection", return_value=mock_conn
        ), patch("time.sleep"):
            result = client.chat([{"role": "user", "content": "Hi"}])

        assert result is None
        assert "unavailable after 2 attempts" in (client.last_error or "")


class TestChatClientErrors:
    """Test non-retryable errors (4xx)."""

    def test_returns_none_on_400_error(self):
        """400 Bad Request should NOT retry."""
        client = OllamaClient(max_retries=3)
        mock_conn = MagicMock()
        mock_conn.getresponse.return_value = _mock_response(
            400, {"error": "bad request"}
        )

        with patch("utils.ollama_client._get_connection", return_value=mock_conn):
            result = client.chat([{"role": "user", "content": "Hi"}])

        assert result is None
        assert "client error 400" in (client.last_error or "")
        # Should only have called request once (no retry)
        assert mock_conn.request.call_count == 1

    def test_returns_none_on_404_error(self):
        """404 Not Found should NOT retry."""
        client = OllamaClient()
        mock_conn = MagicMock()
        mock_conn.getresponse.return_value = _mock_response(
            404, {"error": "model not found"}
        )

        with patch("utils.ollama_client._get_connection", return_value=mock_conn):
            result = client.chat([{"role": "user", "content": "Hi"}])

        assert result is None
        assert "client error 404" in (client.last_error or "")

    def test_returns_none_on_empty_200_response(self):
        """200 responses without JSON should be treated as malformed."""
        client = OllamaClient()
        mock_conn = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b""
        mock_conn.getresponse.return_value = mock_response

        with patch("utils.ollama_client._get_connection", return_value=mock_conn):
            result = client.chat([{"role": "user", "content": "Hi"}])

        assert result is None
        assert "empty or malformed response" in (client.last_error or "")


class TestConnectionPooling:
    """Test the module-level connection pool."""

    def test_get_connection_creates_new(self):
        _connection_pool.clear()
        conn = _get_connection("localhost", 11434)
        assert conn is not None
        assert "localhost:11434" in _connection_pool

    def test_get_connection_reuses_existing(self):
        _connection_pool.clear()
        # Create a real connection and simulate it having an active socket
        conn1 = _get_connection("localhost", 11434)
        conn1.sock = MagicMock()  # pretend socket is alive
        conn2 = _get_connection("localhost", 11434)
        assert conn1 is conn2

    def test_get_connection_creates_new_when_socket_dead(self):
        _connection_pool.clear()
        conn1 = _get_connection("localhost", 11434)
        conn1.sock = None  # simulate dead socket
        conn2 = _get_connection("localhost", 11434)
        assert conn1 is not conn2

    def test_close_all_clears_pool(self):
        _connection_pool.clear()
        _get_connection("host1", 1234)
        _get_connection("host2", 5678)
        assert len(_connection_pool) == 2

        OllamaClient.close_all()
        assert len(_connection_pool) == 0


class TestBrokenPipeRecovery:
    """Test the specific BrokenPipeError scenario from the bug report."""

    def test_clears_stale_connection_on_broken_pipe(self):
        """When a BrokenPipeError occurs, the stale connection should be evicted."""
        client = OllamaClient(max_retries=2, backoff_base=0.01)
        _connection_pool.clear()

        mock_conn = MagicMock()
        mock_conn.request.side_effect = BrokenPipeError("Broken pipe")

        with patch(
            "utils.ollama_client._get_connection", return_value=mock_conn
        ), patch("time.sleep"):
            result = client.chat([{"role": "user", "content": "Hi"}])

        assert result is None
        assert "unavailable" in (client.last_error or "")

    def test_connection_pool_eviction_on_error(self):
        """BrokenPipeError should pop the connection from the pool."""
        client = OllamaClient(max_retries=1, backoff_base=0.01)
        _connection_pool.clear()
        _connection_pool["localhost:11434"] = MagicMock()

        mock_conn = MagicMock()
        mock_conn.request.side_effect = BrokenPipeError("Broken")

        with patch(
            "utils.ollama_client._get_connection", return_value=mock_conn
        ), patch("time.sleep"):
            client.chat([{"role": "user", "content": "Hi"}])

        # The old connection should have been evicted from the pool
        assert "localhost:11434" not in _connection_pool


class TestGracefulDegradation:
    """Test behavior when Ollama is completely unavailable."""

    def test_returns_none_when_ollama_down(self):
        client = OllamaClient(max_retries=1, backoff_base=0.01)
        mock_conn = MagicMock()
        mock_conn.request.side_effect = ConnectionRefusedError("Connection refused")

        with patch(
            "utils.ollama_client._get_connection", return_value=mock_conn
        ), patch("time.sleep"):
            result = client.chat([{"role": "user", "content": "Hi"}])

        assert result is None
        assert client.last_error is not None

    def test_last_error_cleared_on_success(self):
        client = OllamaClient()
        mock_conn = MagicMock()
        mock_conn.getresponse.return_value = _mock_response(
            200, {"message": {"content": "OK"}}
        )

        client._last_error = "Previous error"
        with patch("utils.ollama_client._get_connection", return_value=mock_conn):
            client.chat([{"role": "user", "content": "Hi"}])

        assert client.last_error is None
