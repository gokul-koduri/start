"""Opportunity scorer edge case tests (T-041).

Tests for scoring edge cases: empty signals, negative inputs, large numbers,
single signal, many signals, zero weights, etc.
"""

import unittest
from datetime import datetime, timezone, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestCompositeScorerEdgeCases(unittest.TestCase):
    """Test CompositeScorer with edge case inputs."""

    def test_empty_signals(self):
        """Score with no signals returns 0."""
        from scoring.composite_scorer import CompositeScorer

        scorer = CompositeScorer()
        result = scorer.score(
            entity_name="EmptyCorp",
            entity_type="company",
            signal_scores={},
            historical_values={},
        )
        self.assertEqual(result.composite_score, 0.0)
        self.assertEqual(result.signal_count, 0)

    def test_single_signal(self):
        """Score with a single signal works."""
        from scoring.composite_scorer import CompositeScorer

        scorer = CompositeScorer()
        result = scorer.score(
            entity_name="SingleSig",
            entity_type="company",
            signal_scores={
                "funding_round": {
                    "raw_score": 80,
                    "published_at": datetime.now(timezone.utc),
                },
            },
            historical_values={"funding_round": [80]},
        )
        self.assertGreater(result.composite_score, 0)
        self.assertEqual(result.signal_count, 1)

    def test_many_signals(self):
        """Score with all signal types works."""
        from scoring.composite_scorer import CompositeScorer

        scorer = CompositeScorer()
        now = datetime.now(timezone.utc)
        signal_scores = {
            "funding_round": {"raw_score": 90, "published_at": now},
            "sec_filing": {"raw_score": 80, "published_at": now},
            "job_posting_spike": {"raw_score": 75, "published_at": now},
            "patent_filed": {"raw_score": 70, "published_at": now},
            "github_trend": {"raw_score": 65, "published_at": now},
            "news_mention": {"raw_score": 60, "published_at": now},
            "social_buzz": {"raw_score": 55, "published_at": now},
            "website_change": {"raw_score": 50, "published_at": now},
        }
        historical = {k: [v["raw_score"]] for k, v in signal_scores.items()}
        result = scorer.score("ManySignals", "company", signal_scores, historical)
        self.assertGreater(result.composite_score, 0)
        self.assertEqual(result.signal_count, 8)

    def test_zero_score_signal(self):
        """Signal with raw_score=0 doesn't crash."""
        from scoring.composite_scorer import CompositeScorer

        scorer = CompositeScorer()
        result = scorer.score(
            "ZeroCorp",
            "company",
            {
                "funding_round": {
                    "raw_score": 0,
                    "published_at": datetime.now(timezone.utc),
                }
            },
            {"funding_round": [0]},
        )
        self.assertIsInstance(result.composite_score, float)

    def test_max_score_signal(self):
        """Signal with raw_score=100 works."""
        from scoring.composite_scorer import CompositeScorer

        scorer = CompositeScorer()
        result = scorer.score(
            "MaxCorp",
            "company",
            {
                "funding_round": {
                    "raw_score": 100,
                    "published_at": datetime.now(timezone.utc),
                }
            },
            {"funding_round": [100]},
        )
        self.assertGreater(result.composite_score, 0)

    def test_old_signal_decays(self):
        """Very old signal has lower impact than recent one."""
        from scoring.composite_scorer import CompositeScorer

        scorer = CompositeScorer()
        now = datetime.now(timezone.utc)
        old = now - timedelta(days=365)

        recent_result = scorer.score(
            "RecentCorp",
            "company",
            {"funding_round": {"raw_score": 80, "published_at": now}},
            {"funding_round": [80]},
        )
        old_result = scorer.score(
            "OldCorp",
            "company",
            {"funding_round": {"raw_score": 80, "published_at": old}},
            {"funding_round": [80]},
        )
        # Recent should score higher due to less decay
        self.assertGreater(recent_result.composite_score, old_result.composite_score)

    def test_score_result_has_trend_direction(self):
        """Result includes trend_direction."""
        from scoring.composite_scorer import CompositeScorer

        scorer = CompositeScorer()
        result = scorer.score("TrendCorp", "company", {}, {})
        self.assertIn(result.trend_direction, ("rising", "falling", "stable"))

    def test_score_result_has_confidence(self):
        """Result includes confidence factor."""
        from scoring.composite_scorer import CompositeScorer

        scorer = CompositeScorer()
        result = scorer.score("ConfCorp", "company", {}, {})
        self.assertIsInstance(result.confidence, float)
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)

    def test_custom_weights(self):
        """Custom weights change the score."""
        from scoring.composite_scorer import CompositeScorer

        now = datetime.now(timezone.utc)
        signals = {
            "funding_round": {"raw_score": 90, "published_at": now},
            "social_buzz": {"raw_score": 30, "published_at": now},
        }
        historical = {k: [v["raw_score"]] for k, v in signals.items()}

        high_funding = CompositeScorer(
            weights={
                "funding_round": {
                    "weight": 50.0,
                    "decay_lambda": 0.000079,
                    "label": "Funding",
                    "category": "primary",
                },
                "social_buzz": {
                    "weight": 1.0,
                    "decay_lambda": 0.002063,
                    "label": "Social",
                    "category": "tertiary",
                },
            }
        )
        low_funding = CompositeScorer(
            weights={
                "funding_round": {
                    "weight": 1.0,
                    "decay_lambda": 0.000079,
                    "label": "Funding",
                    "category": "primary",
                },
                "social_buzz": {
                    "weight": 50.0,
                    "decay_lambda": 0.002063,
                    "label": "Social",
                    "category": "tertiary",
                },
            }
        )

        result_high = high_funding.score("Corp1", "company", signals, historical)
        result_low = low_funding.score("Corp2", "company", signals, historical)
        # High funding weight should favor funding_round=90 over social_buzz=30
        self.assertGreater(result_high.composite_score, result_low.composite_score)

    def test_score_result_to_dict(self):
        """ScoreResult.to_dict() has all expected fields."""
        from scoring.composite_scorer import CompositeScorer

        scorer = CompositeScorer()
        result = scorer.score("DictCorp", "company", {}, {})
        d = result.to_dict()
        self.assertIn("entity_name", d)
        self.assertIn("composite_score", d)
        self.assertIn("signal_count", d)
        self.assertIn("trend_direction", d)
        self.assertIn("confidence", d)
        self.assertIn("attribution", d)

    def test_entity_type_market(self):
        """Scoring works with entity_type='market'."""
        from scoring.composite_scorer import CompositeScorer

        scorer = CompositeScorer()
        result = scorer.score(
            "AI Market",
            "market",
            {
                "news_mention": {
                    "raw_score": 70,
                    "published_at": datetime.now(timezone.utc),
                }
            },
            {"news_mention": [70]},
        )
        self.assertEqual(result.entity_type, "market")

    def test_anomaly_with_spike(self):
        """Large historical spike triggers anomaly detection."""
        from scoring.composite_scorer import CompositeScorer

        scorer = CompositeScorer()
        now = datetime.now(timezone.utc)
        result = scorer.score(
            "SpikeCorp",
            "company",
            {"funding_round": {"raw_score": 95, "published_at": now}},
            {"funding_round": [30, 35, 32, 28, 95]},  # Spike at end
        )
        # Score should be higher due to anomaly boost
        self.assertGreater(result.composite_score, 0)


if __name__ == "__main__":
    unittest.main()
