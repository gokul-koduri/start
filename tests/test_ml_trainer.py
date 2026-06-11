"""Tests for agents/ml_trainer.py — feature engineering and CSV loading."""

import csv
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent))


class TestMLTrainer:
    """Test ML trainer utility functions."""

    def test_parse_funding_dollars(self):
        from agents.ml_trainer_agent import _parse_funding

        assert _parse_funding("$50M") == 50_000_000
        assert _parse_funding("$1.2B") == 1_200_000_000
        assert _parse_funding("$500K") == 500_000
        assert _parse_funding("10000000") == 10_000_000
        assert _parse_funding("") == 0.0
        assert _parse_funding("unknown") == 0.0

    def test_parse_int(self):
        from agents.ml_trainer_agent import _parse_int

        assert _parse_int("2020") == 2020
        assert _parse_int("2023.5") == 2023
        assert _parse_int("invalid") == 2020  # fallback

    def test_load_training_data_from_csv(self, tmp_path):
        from agents.ml_trainer_agent import load_training_data_from_csv

        csv_path = tmp_path / "test_data.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["sector", "country", "funding", "founded", "status"])
            writer.writerow(["SaaS", "US", "$10M", "2020", "1"])  # failed
            writer.writerow(["Fintech", "UK", "$5M", "2019", "0"])  # operating
            writer.writerow(["Crypto/Blockchain", "US", "$50M", "2021", "1"])  # failed

        features, labels = load_training_data_from_csv(str(csv_path))
        assert len(features) == 3
        assert labels == [1, 0, 1]
        assert features[0]["sector_encoded"] > 0

    def test_load_training_data_from_csv_empty(self, tmp_path):
        from agents.ml_trainer_agent import load_training_data_from_csv

        csv_path = tmp_path / "empty.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["sector", "country", "funding", "status"])

        features, labels = load_training_data_from_csv(str(csv_path))
        assert len(features) == 0


class TestMLPredictor:
    """Test ML predictor agent (no real DB or model)."""

    def test_ml_predictor_name(self):
        from agents.ml_predictor_agent import MLPredictorAgent

        agent = MLPredictorAgent({})
        assert agent.name == "ml_predictor"

    def test_ml_predictor_skips_without_model(self, tmp_path):
        """MLPredictorAgent should return skip result when no model exists."""
        from agents.ml_predictor_agent import MLPredictorAgent

        # Point to empty directory so no model files are found
        agent = MLPredictorAgent({"model_output_dir": str(tmp_path)})
        result = agent.execute()
        assert result.status == "success"
        assert result.data.get("skipped") is True
