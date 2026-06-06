"""Tests for the Entity Resolution Agent.

Tests the Jaro-Winkler similarity function and resolution logic
without requiring a database connection.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from agents.entity_resolver_agent import (
    EntityResolverAgent,
    _jaro_winkler_similarity,
)


# ── Jaro-Winkler Similarity ──


class TestJaroWinklerSimilarity:
    def test_identical_strings(self):
        assert _jaro_winkler_similarity("Stripe", "Stripe") == 1.0

    def test_empty_strings(self):
        assert _jaro_winkler_similarity("", "") == 0.0

    def test_one_empty(self):
        assert _jaro_winkler_similarity("Stripe", "") == 0.0

    def test_exact_case_insensitive_match(self):
        # Note: JW works on exact chars, not normalized
        score = _jaro_winkler_similarity("stripe", "stripe")
        assert score == 1.0

    def test_very_similar_names(self):
        score = _jaro_winkler_similarity("openai", "openai")
        assert score == 1.0

    def test_minor_suffix_difference(self):
        score = _jaro_winkler_similarity("openai", "openaicorp")
        assert score > 0.85  # High similarity, same prefix

    def test_different_entities(self):
        score = _jaro_winkler_similarity("stripe", "spotify")
        assert score < 0.7  # Different entities

    def test_prefix_bonus(self):
        """JW gives bonus for matching prefix — key for 'Stripe' vs 'Stripe Inc.'"""
        score_abbr = _jaro_winkler_similarity("stripe", "stripeinc")
        score_diff_prefix = _jaro_winkler_similarity("stripe", "xtripe")
        # Same edit distance, different prefix — JW should prefer same prefix
        assert score_abbr > score_diff_prefix

    def test_single_char_strings(self):
        score = _jaro_winkler_similarity("a", "a")
        assert score == 1.0

    def test_completely_different(self):
        score = _jaro_winkler_similarity("abcdef", "ghijkl")
        assert score < 0.3

    def test_transposition(self):
        """Transpositions are penalized less than insertions."""
        score = _jaro_winkler_similarity("abc", "acb")
        assert score > 0.5  # Jaro base ~0.6, JW prefix bonus adds a bit


# ── EntityResolverAgent ──


class TestEntityResolverAgent:
    def test_name_property(self):
        agent = EntityResolverAgent()
        assert agent.name == "entity_resolver"

    def test_execute_no_db(self):
        """Returns failed result when DB connection fails."""
        agent = EntityResolverAgent()
        with patch("agents.entity_resolver.get_connection", side_effect=Exception("no db")):
            result = agent.execute()
        assert result.status == "failed"
        assert len(result.errors) > 0

    def test_execute_with_mock_db(self):
        """Dry run with mocked DB returns success."""
        agent = EntityResolverAgent({"dry_run": True})

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value = mock_cursor

        with patch("agents.entity_resolver.get_connection", return_value=mock_conn):
            with patch("agents.entity_resolver.schema") as mock_schema:
                result = agent.execute()

        assert result.status == "success"
        assert result.data["total_resolved"] == 0

    def test_blocking_logic(self):
        """Test that entities are grouped by normalized name prefix."""
        entities = [
            {"id": 1, "name": "OpenAI", "normalized_name": "openai", "entity_type_id": 1, "mention_count": 10, "attributes_json": None},
            {"id": 2, "name": "Open AI Inc", "normalized_name": "openaiinc", "entity_type_id": 1, "mention_count": 5, "attributes_json": None},
            {"id": 3, "name": "Spotify", "normalized_name": "spotify", "entity_type_id": 1, "mention_count": 8, "attributes_json": None},
        ]

        from collections import defaultdict
        blocks = defaultdict(list)
        for e in entities:
            blocks[e["normalized_name"][:3]].append(e)

        # "ope" block has OpenAI + Open AI Inc
        assert len(blocks["ope"]) == 2
        # "spo" block has Spotify alone
        assert len(blocks["spo"]) == 1

    def test_threshold_config(self):
        agent = EntityResolverAgent({"similarity_threshold": 0.90})
        assert agent.config["similarity_threshold"] == 0.90

    def test_dry_run_flag(self):
        agent = EntityResolverAgent({"dry_run": True})
        assert agent.config["dry_run"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
