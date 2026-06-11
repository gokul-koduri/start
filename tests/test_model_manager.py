"""Tests for agents/model_manager.py — ModelManager registry and inference."""

import json
import sys
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).parent.parent))


class TestModelManager:
    """Test ModelManager initialization and registry."""

    def test_default_models_loaded(self):
        from agents.model_manager_agent import ModelManager

        mgr = ModelManager({})
        assert mgr.get_model("default") == "llama3"
        assert mgr.get_model("sentiment") == "llama3"
        assert mgr.get_model("ner") == "llama3"

    def test_config_overrides_models(self):
        from agents.model_manager_agent import ModelManager

        config = {
            "ollama": {
                "models": {
                    "sentiment": "custom-sentiment-model",
                    "classification": "custom-classifier",
                }
            }
        }
        mgr = ModelManager(config)
        assert mgr.get_model("sentiment") == "custom-sentiment-model"
        assert mgr.get_model("classification") == "custom-classifier"
        # Default still available
        assert mgr.get_model("default") == "llama3"

    def test_unknown_task_returns_default(self):
        from agents.model_manager_agent import ModelManager

        mgr = ModelManager({})
        assert mgr.get_model("unknown_task_xyz") == "llama3"

    def test_base_url_from_config(self):
        from agents.model_manager_agent import ModelManager

        mgr = ModelManager({"ollama": {"base_url": "http://custom:11434"}})
        assert mgr.base_url == "http://custom:11434"


class TestJSONExtraction:
    """Test _extract_json utility function."""

    def test_plain_json_object(self):
        from agents.model_manager_agent import _extract_json

        result = _extract_json('{"key": "value", "num": 42}')
        assert result == {"key": "value", "num": 42}

    def test_json_with_code_fences(self):
        from agents.model_manager_agent import _extract_json

        result = _extract_json('```json\n{"status": "ok"}\n```')
        assert result == {"status": "ok"}

    def test_json_with_preamble(self):
        from agents.model_manager_agent import _extract_json

        raw = 'Here is the result:\n{"found": true, "count": 5}'
        result = _extract_json(raw)
        assert result == {"found": True, "count": 5}

    def test_json_array(self):
        from agents.model_manager_agent import _extract_json

        result = _extract_json('[{"name": "A"}, {"name": "B"}]')
        assert len(result) == 2
        assert result[0]["name"] == "A"

    def test_invalid_json_returns_none(self):
        from agents.model_manager_agent import _extract_json

        assert _extract_json("not json at all") is None
        assert _extract_json("") is None


class TestTokenTracking:
    """Test token tracking writes to JSON file."""

    def test_track_usage_creates_file(self, tmp_path):
        from agents.model_manager_agent import ModelManager

        # Patch the tracker path
        tracker_path = tmp_path / "tracker.json"
        with patch("agents.model_manager_agent._TOKEN_TRACKER_PATH", tracker_path):
            mgr = ModelManager({})
            mgr._track_usage("llama3", 100, 50)

            assert tracker_path.exists()
            data = json.loads(tracker_path.read_text())
            assert len(data) == 1
            assert data[0]["model"] == "llama3"
            assert data[0]["prompt_tokens"] == 100
            assert data[0]["completion_tokens"] == 50
            assert data[0]["total_tokens"] == 150

    def test_track_usage_appends(self, tmp_path):
        from agents.model_manager_agent import ModelManager

        tracker_path = tmp_path / "tracker.json"
        with patch("agents.model_manager_agent._TOKEN_TRACKER_PATH", tracker_path):
            mgr = ModelManager({})
            mgr._track_usage("llama3", 10, 5)
            mgr._track_usage("llama3", 20, 10)

            data = json.loads(tracker_path.read_text())
            assert len(data) == 2
