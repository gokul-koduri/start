"""Tests for agents/sentiment_agent.py — VADER and keyword sentiment scoring."""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent))


class TestVaderSentiment:
    """Test VADER sentiment analysis function."""

    def test_positive_text(self):
        from agents.sentiment_agent import _vader_sentiment

        score, label = _vader_sentiment(
            "Amazing success! Company raises record $100M in exciting new funding round"
        )
        assert label == "positive"
        assert score > 0

    def test_negative_text(self):
        from agents.sentiment_agent import _vader_sentiment

        score, label = _vader_sentiment(
            "Startup shuts down after failing to raise capital"
        )
        assert label == "negative"
        assert score < 0

    def test_neutral_text(self):
        from agents.sentiment_agent import _vader_sentiment

        score, label = _vader_sentiment(
            "The company was founded in 2020 in Silicon Valley"
        )
        assert label == "neutral"

    def test_empty_text(self):
        from agents.sentiment_agent import _vader_sentiment

        score, label = _vader_sentiment("")
        assert label == "neutral"
        assert score == 0.0

    def test_score_range(self):
        from agents.sentiment_agent import _vader_sentiment

        texts = [
            "Amazing growth and record profits this quarter",
            "Terrible news as company files for bankruptcy",
            "Company opens new office in London",
        ]
        for text in texts:
            score, _ = _vader_sentiment(text)
            assert -1.0 <= score <= 1.0


class TestKeywordSentiment:
    """Test fallback keyword-based sentiment."""

    def test_positive_keywords(self):
        from agents.sentiment_agent import _keyword_sentiment

        score, label = _keyword_sentiment("profit growth investment fund success")
        assert label == "positive"
        assert score > 0

    def test_negative_keywords(self):
        from agents.sentiment_agent import _keyword_sentiment

        score, label = _keyword_sentiment("failure bankrupt shutdown layoff crisis")
        assert label == "negative"
        assert score < 0

    def test_no_keywords(self):
        from agents.sentiment_agent import _keyword_sentiment

        score, label = _keyword_sentiment("the company was established")
        assert label == "neutral"


class TestMLFeatureEngineering:
    """Test ML trainer feature building functions."""

    def test_encode_sector_known(self):
        from agents.ml_trainer_agent import _encode_sector

        assert _encode_sector("Crypto/Blockchain") == 20.0
        assert _encode_sector("Cybersecurity") == 1.0
        assert _encode_sector("SaaS") == 2.0

    def test_encode_sector_unknown(self):
        from agents.ml_trainer_agent import _encode_sector

        assert _encode_sector("UnknownSector") == 10.0
        assert _encode_sector("") == 10.0

    def test_encode_sector_partial_match(self):
        from agents.ml_trainer_agent import _encode_sector

        # "EdTech" should match partially
        result = _encode_sector("EdTech Platform")
        assert result == 15.0

    def test_country_risk_known(self):
        from agents.ml_trainer_agent import _country_risk

        assert _country_risk("US") == 1.0
        assert _country_risk("India") == 1.15
        assert _country_risk("Germany") == 0.9

    def test_country_risk_unknown(self):
        from agents.ml_trainer_agent import _country_risk

        assert _country_risk("") == 1.05
        assert _country_risk("Unknown") == 1.1

    def test_is_manufacturing(self):
        from agents.ml_trainer_agent import _is_manufacturing

        assert _is_manufacturing("Battery Manufacturing") == 1
        assert _is_manufacturing("SaaS Platform") == 0
        assert _is_manufacturing("EV", "Automotive") == 1

    def test_build_features(self):
        from agents.ml_trainer_agent import _build_features

        row = {
            "sector": "Crypto/Blockchain",
            "manufacturing_sub_sector": "",
            "country": "US",
            "region": "US & Global",
            "funding_raised_usd": 50_000_000,
            "year_founded": 2021,
            "year_shutdown": 2024,
            "failure_reason": "",
        }
        features = _build_features(row)

        assert "sector_encoded" in features
        assert "funding_bin" in features
        assert features["sector_encoded"] == 20.0
        assert features["funding_bin"] == 3.0  # $10-100M
        assert features["is_manufacturing"] == 0.0
        assert features["age_at_shutdown"] == 3.0
