"""Tests for score validation (scoring/validate.py) and accuracy tracking (T-037 to T-039)."""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestValidationDataset(unittest.TestCase):
    """Test the validation dataset structure."""

    def test_validation_set_has_20_startups(self):
        """Validation set contains exactly 20 startups."""
        from scoring.validate import VALIDATION_SET

        self.assertEqual(len(VALIDATION_SET), 20)

    def test_10_successes_and_10_failures(self):
        """Validation set has 10 successes and 10 failures."""
        from scoring.validate import VALIDATION_SET

        successes = [s for s in VALIDATION_SET if s["actual_outcome"] == "success"]
        failures = [s for s in VALIDATION_SET if s["actual_outcome"] == "failure"]
        self.assertEqual(len(successes), 10)
        self.assertEqual(len(failures), 10)

    def test_all_entries_have_required_fields(self):
        """Each entry has entity_name, actual_outcome, signal_scores."""
        from scoring.validate import VALIDATION_SET

        for entry in VALIDATION_SET:
            self.assertIn("entity_name", entry)
            self.assertIn("actual_outcome", entry)
            self.assertIn("signal_scores", entry)
            self.assertIn(entry["actual_outcome"], ("success", "failure"))

    def test_all_signal_scores_have_raw_score(self):
        """Each signal score has a raw_score value."""
        from scoring.validate import VALIDATION_SET

        for entry in VALIDATION_SET:
            for sig_type, sig_data in entry["signal_scores"].items():
                self.assertIn("raw_score", sig_data)
                self.assertGreaterEqual(sig_data["raw_score"], 0)
                self.assertLessEqual(sig_data["raw_score"], 100)


class TestRunValidation(unittest.TestCase):
    """Test the validation runner."""

    def test_run_validation_returns_report(self):
        """run_validation returns a ValidationReport."""
        from scoring.validate import run_validation, ValidationReport

        report = run_validation()
        self.assertIsInstance(report, ValidationReport)

    def test_validation_report_has_20_results(self):
        """Report contains results for all 20 startups."""
        from scoring.validate import run_validation

        report = run_validation()
        self.assertEqual(report.total, 20)
        self.assertEqual(len(report.results), 20)

    def test_confusion_matrix_sums_to_total(self):
        """Confusion matrix entries sum to total."""
        from scoring.validate import run_validation

        report = run_validation()
        total_cm = (
            report.true_positives
            + report.false_positives
            + report.true_negatives
            + report.false_negatives
        )
        self.assertEqual(total_cm, report.total)

    def test_accuracy_calculated_correctly(self):
        """Accuracy matches correct/total."""
        from scoring.validate import run_validation

        report = run_validation()
        expected = report.correct / report.total * 100
        self.assertAlmostEqual(report.accuracy, expected, places=1)

    def test_accuracy_at_least_50_percent(self):
        """Validation achieves at least 50% accuracy with default weights."""
        from scoring.validate import run_validation

        report = run_validation()
        self.assertGreaterEqual(
            report.accuracy,
            50.0,
            f"Accuracy {report.accuracy:.1f}% is below 50% target",
        )

    def test_report_to_dict(self):
        """Report serializes to dict correctly."""
        from scoring.validate import run_validation

        report = run_validation()
        d = report.to_dict()
        self.assertIn("accuracy", d)
        self.assertIn("total", d)
        self.assertIn("precision", d)
        self.assertIn("recall", d)
        self.assertIn("results", d)
        self.assertEqual(len(d["results"]), 20)

    def test_custom_threshold(self):
        """Custom threshold changes predictions."""
        from scoring.validate import run_validation

        report_low = run_validation(threshold=50.0)
        report_high = run_validation(threshold=90.0)
        # Higher threshold should predict fewer successes
        self.assertGreaterEqual(
            report_low.true_positives + report_low.false_positives,
            report_high.true_positives + report_high.false_positives,
        )


class TestSuggestWeightTuning(unittest.TestCase):
    """Test weight tuning suggestions."""

    def test_high_accuracy_no_tuning(self):
        """No tuning suggested when accuracy is high."""
        from scoring.validate import suggest_weight_tuning, ValidationReport

        report = ValidationReport(accuracy=90.0, total=20, correct=18)
        suggestions = suggest_weight_tuning(report)
        self.assertTrue(any("no tuning needed" in s.lower() for s in suggestions))

    def test_low_accuracy_gives_suggestions(self):
        """Suggestions provided when accuracy is low."""
        from scoring.validate import (
            suggest_weight_tuning,
            ValidationReport,
            ValidationResult,
        )

        report = ValidationReport(accuracy=30.0, total=20, correct=6)
        report.false_positives = 5
        report.false_negatives = 9
        report.results = [
            ValidationResult("X", "failure", "success", 75, False),
            ValidationResult("Y", "success", "failure", 65, False),
        ]
        suggestions = suggest_weight_tuning(report)
        self.assertGreater(len(suggestions), 0)


class TestValidationResult(unittest.TestCase):
    """Test individual validation result."""

    def test_correct_prediction(self):
        """Correct prediction sets correct=True."""
        from scoring.validate import ValidationResult

        result = ValidationResult(
            entity_name="Stripe",
            actual_outcome="success",
            predicted_outcome="success",
            score=85.0,
            correct=True,
        )
        self.assertTrue(result.correct)

    def test_incorrect_prediction(self):
        """Incorrect prediction sets correct=False."""
        from scoring.validate import ValidationResult

        result = ValidationResult(
            entity_name="Theranos",
            actual_outcome="failure",
            predicted_outcome="success",
            score=75.0,
            correct=False,
        )
        self.assertFalse(result.correct)


class TestScoreAccuracySchema(unittest.TestCase):
    """Test score_accuracy_runs table in schema."""

    def test_accuracy_table_in_schema(self):
        """score_accuracy_runs table is defined in schema."""
        schema_path = Path(__file__).parent.parent / "db" / "schema.py"
        content = schema_path.read_text()
        self.assertIn("score_accuracy_runs", content)
        self.assertIn("accuracy_pct", content)
        self.assertIn("f1_score", content)
        self.assertIn("threshold_used", content)

    def test_validate_module_exists(self):
        """scoring/validate.py exists."""
        path = Path(__file__).parent.parent / "scoring" / "validate.py"
        self.assertTrue(path.exists())


class TestResolveTimestamp(unittest.TestCase):
    """Test timestamp resolution."""

    def test_recent_timestamp(self):
        """'recent' resolves to ~12 hours ago."""
        from scoring.validate import _resolve_timestamp
        from datetime import datetime, timezone

        ts = _resolve_timestamp("recent")
        now = datetime.now(timezone.utc)
        delta = (now - ts).total_seconds()
        # Should be roughly 12 hours (43200 seconds), allow some tolerance
        self.assertAlmostEqual(delta, 43200, delta=60)

    def test_old_timestamp(self):
        """'old' resolves to ~180 days ago."""
        from scoring.validate import _resolve_timestamp
        from datetime import datetime, timezone

        ts = _resolve_timestamp("old")
        now = datetime.now(timezone.utc)
        delta_days = (now - ts).days
        self.assertGreater(delta_days, 100)


class TestValidationWithCustomDataset(unittest.TestCase):
    """Test validation with custom datasets."""

    def test_single_entity_success(self):
        """Single high-scoring success is predicted correctly."""
        from scoring.validate import run_validation

        dataset = [
            {
                "entity_name": "TestSuccess",
                "actual_outcome": "success",
                "signal_scores": {
                    "funding_round": {"raw_score": 95, "published_at": "recent"},
                    "sec_filing": {"raw_score": 85, "published_at": "recent"},
                    "job_posting_spike": {"raw_score": 90, "published_at": "recent"},
                    "github_trend": {"raw_score": 85, "published_at": "recent"},
                    "news_mention": {"raw_score": 80, "published_at": "recent"},
                },
            }
        ]
        report = run_validation(dataset=dataset)
        self.assertEqual(report.total, 1)
        self.assertEqual(report.results[0].predicted_outcome, "success")

    def test_single_entity_failure(self):
        """Single low-scoring failure is predicted correctly."""
        from scoring.validate import run_validation

        dataset = [
            {
                "entity_name": "TestFailure",
                "actual_outcome": "failure",
                "signal_scores": {
                    "news_mention": {"raw_score": 10, "published_at": "old"},
                },
            }
        ]
        report = run_validation(dataset=dataset)
        self.assertEqual(report.total, 1)
        self.assertEqual(report.results[0].predicted_outcome, "failure")


if __name__ == "__main__":
    unittest.main()
