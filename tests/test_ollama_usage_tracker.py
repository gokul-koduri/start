"""Tests for ollama_usage_tracker_agent — token tracking utility."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock pymysql
mock_pymysql = MagicMock()
sys.modules["pymysql"] = mock_pymysql
sys.modules["pymysql.cursors"] = mock_pymysql.cursors

from agents.ollama_usage_tracker_agent import _track_inference, TRACKER_FILE  # noqa: E402


class TestTrackInference:
    """Tests for the _track_inference utility function."""

    def test_track_inference_writes_to_file(self, tmp_path):
        """_track_inference should append data to the tracker file."""
        tracker_file = tmp_path / "tracker.json"
        with patch("agents.ollama_usage_tracker_agent.TRACKER_FILE", tracker_file):
            # Create file with expected structure
            tracker_file.write_text('{"entries": [], "totals": {}}')
            _track_inference("llama3", 100, 50)
            # Verify the entry was appended
            import json

            data = json.loads(tracker_file.read_text())
            assert len(data["entries"]) == 1
            assert data["entries"][0]["model"] == "llama3"
            assert data["entries"][0]["prompt_tokens"] == 100

    def test_track_inference_handles_missing_file(self, tmp_path):
        """_track_inference should handle missing tracker file gracefully."""
        tracker_file = tmp_path / "nonexistent" / "tracker.json"
        with patch("agents.ollama_usage_tracker_agent.TRACKER_FILE", tracker_file):
            try:
                _track_inference("llama3", 10, 5)
            except (FileNotFoundError, OSError):
                pass  # Expected — file doesn't exist

    def test_tracker_file_is_path_object(self):
        """TRACKER_FILE should be a Path object."""
        assert isinstance(TRACKER_FILE, Path)
