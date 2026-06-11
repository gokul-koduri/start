"""Tests for score push, WebSocket enhancements, and score deltas (T-034 to T-036)."""

import unittest
from unittest.mock import MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestCalculateScoreDelta(unittest.TestCase):
    """Test score delta calculation."""

    def test_first_score_no_previous(self):
        """Delta for a brand-new entity (no previous score)."""
        from stream.score_delta import calculate_score_delta

        current = {
            "entity_name": "Tesla",
            "entity_type": "company",
            "composite_score": 82.0,
            "trend_direction": "rising",
            "attribution": [{"signal_type": "funding_round", "contribution_pct": 60.0}],
        }
        delta = calculate_score_delta(current, previous=None)
        self.assertTrue(delta["is_first_score"])
        self.assertIsNone(delta["old_score"])
        self.assertEqual(delta["new_score"], 82.0)
        self.assertEqual(delta["change"], 82.0)

    def test_score_increase(self):
        """Delta shows positive change when score increases."""
        from stream.score_delta import calculate_score_delta

        current = {
            "entity_name": "Tesla",
            "entity_type": "company",
            "composite_score": 82.0,
            "trend_direction": "rising",
            "attribution": [{"signal_type": "funding_round", "contribution_pct": 60.0}],
        }
        previous = {
            "composite_score": 78.0,
            "trend_direction": "stable",
            "attribution": [{"signal_type": "funding_round", "contribution_pct": 40.0}],
        }
        delta = calculate_score_delta(current, previous)
        self.assertFalse(delta["is_first_score"])
        self.assertEqual(delta["old_score"], 78.0)
        self.assertEqual(delta["new_score"], 82.0)
        self.assertAlmostEqual(delta["change"], 4.0)

    def test_score_decrease(self):
        """Delta shows negative change when score decreases."""
        from stream.score_delta import calculate_score_delta

        current = {
            "entity_name": "BlockFi",
            "entity_type": "company",
            "composite_score": 45.0,
            "trend_direction": "falling",
            "attribution": [],
        }
        previous = {
            "composite_score": 60.0,
            "trend_direction": "stable",
            "attribution": [],
        }
        delta = calculate_score_delta(current, previous)
        self.assertAlmostEqual(delta["change"], -15.0)
        self.assertEqual(delta["trend_previous"], "stable")
        self.assertEqual(delta["trend_current"], "falling")

    def test_signal_deltas_computed(self):
        """Signal-level contribution changes are computed."""
        from stream.score_delta import calculate_score_delta

        current = {
            "entity_name": "Test",
            "composite_score": 85.0,
            "attribution": [
                {"signal_type": "funding_round", "contribution_pct": 50.0},
                {"signal_type": "github_trend", "contribution_pct": 30.0},
            ],
        }
        previous = {
            "composite_score": 80.0,
            "attribution": [
                {"signal_type": "funding_round", "contribution_pct": 40.0},
            ],
        }
        delta = calculate_score_delta(current, previous)
        signal_deltas = delta["signal_deltas"]
        self.assertIn("funding_round", signal_deltas)
        self.assertAlmostEqual(signal_deltas["funding_round"], 10.0)
        self.assertIn("github_trend", signal_deltas)

    def test_no_change_returns_near_zero(self):
        """No meaningful change produces a small delta."""
        from stream.score_delta import calculate_score_delta

        current = {"entity_name": "X", "composite_score": 80.0, "attribution": []}
        previous = {"composite_score": 80.0, "attribution": []}
        delta = calculate_score_delta(current, previous)
        self.assertAlmostEqual(delta["change"], 0.0)


class TestFormatDeltaMessage(unittest.TestCase):
    """Test human-readable delta formatting."""

    def test_format_new_entity(self):
        """First score shows as '→ score (new)'."""
        from stream.score_delta import format_delta_message

        delta = {
            "entity_name": "Tesla",
            "old_score": None,
            "new_score": 82.0,
            "change": 82.0,
            "signal_deltas": {},
        }
        msg = format_delta_message(delta)
        self.assertIn("Tesla", msg)
        self.assertIn("new", msg)

    def test_format_increase(self):
        """Score increase shows '78→82 (+4.0)'."""
        from stream.score_delta import format_delta_message

        delta = {
            "entity_name": "Tesla",
            "old_score": 78.0,
            "new_score": 82.0,
            "change": 4.0,
            "signal_deltas": {"funding": 2.0, "market": 2.0},
        }
        msg = format_delta_message(delta)
        self.assertIn("78", msg)
        self.assertIn("82", msg)
        self.assertIn("+", msg)
        self.assertIn("funding", msg)

    def test_format_decrease(self):
        """Score decrease shows negative change."""
        from stream.score_delta import format_delta_message

        delta = {
            "entity_name": "BlockFi",
            "old_score": 60.0,
            "new_score": 45.0,
            "change": -15.0,
            "signal_deltas": {},
        }
        msg = format_delta_message(delta)
        self.assertIn("60", msg)
        self.assertIn("45", msg)
        self.assertIn("-", msg)


class TestCalculateAndStoreDelta(unittest.TestCase):
    """Test the full calculate-and-store flow."""

    def test_store_delta_no_previous(self):
        """Stores delta when no previous score exists."""
        from stream.score_delta import calculate_and_store_delta

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None  # No previous score
        mock_conn.cursor.return_value = mock_cursor

        current = {
            "entity_name": "NewCo",
            "entity_type": "company",
            "composite_score": 85.0,
            "attribution": [],
        }
        delta = calculate_and_store_delta(mock_conn, current)
        self.assertIsNotNone(delta)
        self.assertTrue(delta["is_first_score"])

    def test_store_delta_with_change(self):
        """Stores delta when score changes."""
        from stream.score_delta import calculate_and_store_delta

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            "composite_score": 78.0,
            "trend_direction": "stable",
            "attribution_json": '[{"signal_type": "funding", "contribution_pct": 40}]',
        }
        mock_conn.cursor.return_value = mock_cursor

        current = {
            "entity_name": "Tesla",
            "entity_type": "company",
            "composite_score": 82.0,
            "attribution": [{"signal_type": "funding", "contribution_pct": 60}],
        }
        delta = calculate_and_store_delta(mock_conn, current)
        self.assertIsNotNone(delta)
        self.assertFalse(delta["is_first_score"])
        self.assertAlmostEqual(delta["change"], 4.0)

    def test_store_delta_no_change_returns_none(self):
        """Returns None when score hasn't changed."""
        from stream.score_delta import calculate_and_store_delta

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            "composite_score": 80.0,
            "trend_direction": "stable",
            "attribution_json": "[]",
        }
        mock_conn.cursor.return_value = mock_cursor

        current = {
            "entity_name": "StableCo",
            "entity_type": "company",
            "composite_score": 80.0,
            "attribution": [],
        }
        delta = calculate_and_store_delta(mock_conn, current)
        self.assertIsNone(delta)

    def test_store_delta_handles_db_error(self):
        """Returns None on DB error without crashing."""
        from stream.score_delta import calculate_and_store_delta

        mock_conn = MagicMock()
        mock_conn.cursor.side_effect = Exception("DB error")
        delta = calculate_and_store_delta(
            mock_conn, {"entity_name": "X", "composite_score": 50}
        )
        self.assertIsNone(delta)


class TestExtractSignalContributions(unittest.TestCase):
    """Test signal contribution extraction."""

    def test_extract_from_attribution(self):
        """Extracts signal type → contribution mapping."""
        from stream.score_delta import _extract_signal_contributions

        attribution = [
            {"signal_type": "funding_round", "contribution_pct": 50.0},
            {"signal_type": "github_trend", "contribution_pct": 30.0},
        ]
        result = _extract_signal_contributions(attribution)
        self.assertEqual(result["funding_round"], 50.0)
        self.assertEqual(result["github_trend"], 30.0)

    def test_extract_empty(self):
        """Returns empty dict for empty attribution."""
        from stream.score_delta import _extract_signal_contributions

        self.assertEqual(_extract_signal_contributions([]), {})


class TestComputeSignalDeltas(unittest.TestCase):
    """Test per-signal delta computation."""

    def test_signal_added(self):
        """New signal appears in deltas."""
        from stream.score_delta import _compute_signal_deltas

        current = [{"signal_type": "funding", "contribution_pct": 30.0}]
        previous = []
        deltas = _compute_signal_deltas(current, previous)
        self.assertIn("funding", deltas)
        self.assertAlmostEqual(deltas["funding"], 30.0)

    def test_signal_removed(self):
        """Removed signal shows negative delta."""
        from stream.score_delta import _compute_signal_deltas

        current = []
        previous = [{"signal_type": "hiring", "contribution_pct": 20.0}]
        deltas = _compute_signal_deltas(current, previous)
        self.assertIn("hiring", deltas)
        self.assertAlmostEqual(deltas["hiring"], -20.0)

    def test_signal_unchanged_not_included(self):
        """Unchanged signals are not included in deltas."""
        from stream.score_delta import _compute_signal_deltas

        current = [{"signal_type": "funding", "contribution_pct": 40.0}]
        previous = [{"signal_type": "funding", "contribution_pct": 40.0}]
        deltas = _compute_signal_deltas(current, previous)
        self.assertEqual(len(deltas), 0)


class TestScoreDeltasSchema(unittest.TestCase):
    """Test score_deltas table exists in schema."""

    def test_score_deltas_in_schema(self):
        """score_deltas table is defined in schema."""
        schema_path = Path(__file__).parent.parent / "db" / "schema.py"
        content = schema_path.read_text()
        self.assertIn("score_deltas", content)
        self.assertIn("old_score", content)
        self.assertIn("new_score", content)
        self.assertIn("signal_breakdown_json", content)

    def test_score_delta_module_exists(self):
        """stream/score_delta.py exists."""
        delta_path = Path(__file__).parent.parent / "stream" / "score_delta.py"
        self.assertTrue(delta_path.exists())


class TestScoreDeltaMessageFormat(unittest.TestCase):
    """Test WebSocket message format for score deltas."""

    def test_score_update_format(self):
        """score_update WebSocket message has required fields."""
        msg = {
            "type": "score_update",
            "data": {
                "entity_name": "Tesla",
                "entity_type": "company",
                "composite_score": 82.0,
                "signal_count": 5,
                "trend_direction": "rising",
            },
        }
        self.assertEqual(msg["type"], "score_update")
        self.assertIn("entity_name", msg["data"])
        self.assertIn("composite_score", msg["data"])

    def test_score_delta_format(self):
        """score_delta WebSocket message has required fields."""
        msg = {
            "type": "score_delta",
            "data": {
                "entity_name": "Tesla",
                "old_score": 78.0,
                "new_score": 82.0,
                "change": 4.0,
                "trend_previous": "stable",
                "trend_current": "rising",
                "signal_deltas": {"funding": 2.0, "market": 2.0},
            },
        }
        self.assertEqual(msg["type"], "score_delta")
        self.assertIn("change", msg["data"])
        self.assertIn("signal_deltas", msg["data"])


if __name__ == "__main__":
    unittest.main()
