"""Tests for the startup failure risk scorer."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock pymysql
mock_pymysql = MagicMock()
sys.modules["pymysql"] = mock_pymysql
sys.modules["pymysql.cursors"] = mock_pymysql.cursors

from agents.risk_scorer import score_startup


class TestRiskScorer:
    def test_ev_startup_high_risk(self):
        """EV startups should score high risk due to sector + capital intensity."""
        result = score_startup(
            sector="EV/Automotive",
            funding_usd=50_000_000,
            country="US",
            region="US & Global",
            year_founded=2022,
        )
        assert result["risk_score"] >= 0.5
        assert result["risk_level"] in ("high", "critical", "moderate")
        assert len(result["factors"]) > 0

    def test_saas_low_risk(self):
        """Established SaaS company should have lower risk."""
        result = score_startup(
            sector="SaaS",
            funding_usd=100_000_000,
            country="US",
            region="US & Global",
            year_founded=2010,
        )
        assert result["risk_score"] < 0.7
        assert result["risk_level"] in ("low", "moderate")

    def test_crypto_critical_risk(self):
        """Crypto startup with high-risk failure reason should score critical."""
        result = score_startup(
            sector="Crypto/Blockchain",
            funding_usd=5_000_000,
            country="US",
            region="US & Global",
            year_founded=2023,
            failure_reason="ran out of cash, no market need",
        )
        assert result["risk_score"] >= 0.6
        assert result["risk_level"] in ("high", "critical")

    def test_no_inputs_defaults(self):
        """With no inputs, should return a baseline score."""
        result = score_startup()
        assert 0.0 <= result["risk_score"] <= 1.0
        assert result["risk_level"] in ("low", "moderate", "high", "critical")
        assert result["recommendation"] is not None

    def test_manufacturing_bonus(self):
        """Manufacturing startups should get a capital intensity risk bonus."""
        normal = score_startup(sector="SaaS", funding_usd=50_000_000, year_founded=2018)
        mfg = score_startup(sector="Battery Manufacturing", funding_usd=50_000_000, year_founded=2018)
        assert mfg["risk_score"] >= normal["risk_score"]

    def test_funding_underfunded(self):
        """Underfunded startups should score higher risk."""
        underfunded = score_startup(sector="EV/Automotive", funding_usd=500_000, year_founded=2022)
        well_funded = score_startup(sector="EV/Automotive", funding_usd=200_000_000, year_founded=2022)
        assert underfunded["risk_score"] > well_funded["risk_score"]

    def test_age_risk_young(self):
        """Very young startups should score higher risk."""
        young = score_startup(sector="Fintech", funding_usd=10_000_000, year_founded=2024)
        old = score_startup(sector="Fintech", funding_usd=10_000_000, year_founded=2010)
        assert young["risk_score"] > old["risk_score"]

    def test_output_structure(self):
        """Verify the output structure is correct."""
        result = score_startup(sector="Robotics", funding_usd=30_000_000)
        assert "risk_score" in result
        assert "risk_level" in result
        assert "factors" in result
        assert "recommendation" in result
        assert isinstance(result["factors"], list)
        assert isinstance(result["risk_score"], float)
        assert 0.0 <= result["risk_score"] <= 1.0

    def test_partial_sector_match(self):
        """Should match sector by partial text."""
        result = score_startup(sector="3D Printing and Additive")
        factors = {f["factor"]: f for f in result["factors"]}
        assert "sector" in factors
