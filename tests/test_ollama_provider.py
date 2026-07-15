from pathlib import Path
import sys
from unittest.mock import MagicMock, Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from utils.ollama_provider import OllamaProvider  # noqa: E402


def test_infer_rejects_empty_200_response():
    provider = OllamaProvider({"base_url": "http://localhost:11434"})

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = b""

    with patch("utils.ollama_provider.urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.__enter__ = Mock(return_value=mock_response)
        mock_urlopen.return_value.__exit__ = Mock(return_value=False)

        result = provider.infer("default", "hello")

    assert result.success is False
    assert "empty or malformed response" in (result.error or "")
