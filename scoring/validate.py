#!/usr/bin/env python3
"""Score validation — measures scoring accuracy against known outcomes.

Validates the CompositeScorer by scoring a curated set of known startups
(10 successes, 10 failures) and comparing predicted outcomes against
actual results. Reports accuracy, precision, recall, and confusion matrix.

Usage:
    python -m scoring.validate                   # Run validation
    python -m scoring.validate --tune            # Suggest weight adjustments
    python -m scoring.validate --verbose         # Detailed per-startup report

The validation set is a "golden dataset" — synthetic signal data modeled
after real startup trajectories. It's used to calibrate scoring weights
and track accuracy over time.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from scoring.composite_scorer import CompositeScorer, ScoreResult
from scoring.signal_weights import SIGNAL_WEIGHTS

_logger = logging.getLogger(__name__)

# ── Validation Dataset ───────────────────────────────────
# 20 known startups: 10 successes, 10 failures
# Signal data is synthetic but reflects real-world patterns.

SUCCESS_THRESHOLD = 70.0  # Score above this → predicted success

VALIDATION_SET: list[dict[str, Any]] = [
    # ── 10 Successful Startups ──
    {
        "entity_name": "Stripe",
        "actual_outcome": "success",
        "description": "Payment infrastructure giant, $95B valuation",
        "signal_scores": {
            "funding_round": {"raw_score": 95, "published_at": "recent"},
            "sec_filing": {"raw_score": 80, "published_at": "recent"},
            "job_posting_spike": {"raw_score": 90, "published_at": "recent"},
            "patent_filed": {"raw_score": 70, "published_at": "semi_recent"},
            "github_trend": {"raw_score": 85, "published_at": "recent"},
            "news_mention": {"raw_score": 90, "published_at": "recent"},
        },
    },
    {
        "entity_name": "Airbnb",
        "actual_outcome": "success",
        "description": "Travel platform, IPO 2020, $75B market cap",
        "signal_scores": {
            "funding_round": {"raw_score": 90, "published_at": "semi_recent"},
            "sec_filing": {"raw_score": 85, "published_at": "recent"},
            "job_posting_spike": {"raw_score": 80, "published_at": "recent"},
            "news_mention": {"raw_score": 85, "published_at": "recent"},
        },
    },
    {
        "entity_name": "SpaceX",
        "actual_outcome": "success",
        "description": "Space exploration, $180B valuation",
        "signal_scores": {
            "funding_round": {"raw_score": 95, "published_at": "recent"},
            "patent_filed": {"raw_score": 85, "published_at": "semi_recent"},
            "job_posting_spike": {"raw_score": 95, "published_at": "recent"},
            "news_mention": {"raw_score": 95, "published_at": "recent"},
        },
    },
    {
        "entity_name": "Notion Labs",
        "actual_outcome": "success",
        "description": "Productivity platform, $10B valuation",
        "signal_scores": {
            "funding_round": {"raw_score": 85, "published_at": "recent"},
            "job_posting_spike": {"raw_score": 75, "published_at": "recent"},
            "github_trend": {"raw_score": 80, "published_at": "recent"},
            "news_mention": {"raw_score": 75, "published_at": "recent"},
        },
    },
    {
        "entity_name": "Databricks",
        "actual_outcome": "success",
        "description": "Data + AI platform, $43B valuation",
        "signal_scores": {
            "funding_round": {"raw_score": 90, "published_at": "recent"},
            "job_posting_spike": {"raw_score": 85, "published_at": "recent"},
            "github_trend": {"raw_score": 90, "published_at": "recent"},
            "sec_filing": {"raw_score": 70, "published_at": "semi_recent"},
            "news_mention": {"raw_score": 80, "published_at": "recent"},
        },
    },
    {
        "entity_name": "Figma",
        "actual_outcome": "success",
        "description": "Design platform, $12.5B valuation",
        "signal_scores": {
            "funding_round": {"raw_score": 85, "published_at": "semi_recent"},
            "job_posting_spike": {"raw_score": 80, "published_at": "recent"},
            "github_trend": {"raw_score": 75, "published_at": "recent"},
            "news_mention": {"raw_score": 85, "published_at": "recent"},
            "website_change": {"raw_score": 70, "published_at": "recent"},
        },
    },
    {
        "entity_name": "Canva",
        "actual_outcome": "success",
        "description": "Design tool, $40B valuation",
        "signal_scores": {
            "funding_round": {"raw_score": 90, "published_at": "recent"},
            "job_posting_spike": {"raw_score": 80, "published_at": "recent"},
            "news_mention": {"raw_score": 80, "published_at": "recent"},
            "social_buzz": {"raw_score": 75, "published_at": "recent"},
        },
    },
    {
        "entity_name": "Anthropic",
        "actual_outcome": "success",
        "description": "AI safety company, $60B valuation",
        "signal_scores": {
            "funding_round": {"raw_score": 95, "published_at": "recent"},
            "job_posting_spike": {"raw_score": 90, "published_at": "recent"},
            "news_mention": {"raw_score": 95, "published_at": "recent"},
            "patent_filed": {"raw_score": 75, "published_at": "semi_recent"},
        },
    },
    {
        "entity_name": "Scale AI",
        "actual_outcome": "success",
        "description": "Data labeling, $14B valuation",
        "signal_scores": {
            "funding_round": {"raw_score": 85, "published_at": "recent"},
            "job_posting_spike": {"raw_score": 80, "published_at": "recent"},
            "github_trend": {"raw_score": 70, "published_at": "recent"},
            "news_mention": {"raw_score": 75, "published_at": "recent"},
        },
    },
    {
        "entity_name": "Anduril",
        "actual_outcome": "success",
        "description": "Defense tech, $14B valuation",
        "signal_scores": {
            "funding_round": {"raw_score": 90, "published_at": "recent"},
            "patent_filed": {"raw_score": 80, "published_at": "recent"},
            "job_posting_spike": {"raw_score": 85, "published_at": "recent"},
            "sec_filing": {"raw_score": 75, "published_at": "semi_recent"},
            "news_mention": {"raw_score": 80, "published_at": "recent"},
        },
    },

    # ── 10 Failed Startups ──
    {
        "entity_name": "Theranos",
        "actual_outcome": "failure",
        "description": "Blood testing fraud, dissolved 2018",
        "signal_scores": {
            "news_mention": {"raw_score": 20, "published_at": "old"},
            "sec_filing": {"raw_score": 10, "published_at": "old"},
        },
    },
    {
        "entity_name": "Quibi",
        "actual_outcome": "failure",
        "description": "Short-form video, shut down after 6 months",
        "signal_scores": {
            "funding_round": {"raw_score": 60, "published_at": "old"},
            "news_mention": {"raw_score": 15, "published_at": "old"},
            "social_buzz": {"raw_score": 10, "published_at": "old"},
        },
    },
    {
        "entity_name": "WeWork",
        "actual_outcome": "failure",
        "description": "Office sharing, failed IPO, massive losses",
        "signal_scores": {
            "funding_round": {"raw_score": 50, "published_at": "old"},
            "news_mention": {"raw_score": 15, "published_at": "semi_recent"},
            "sec_filing": {"raw_score": 25, "published_at": "old"},
            "job_posting_spike": {"raw_score": 10, "published_at": "old"},
        },
    },
    {
        "entity_name": "Juicero",
        "actual_outcome": "failure",
        "description": "$400 juice press, shut down 2017",
        "signal_scores": {
            "funding_round": {"raw_score": 40, "published_at": "old"},
            "news_mention": {"raw_score": 10, "published_at": "old"},
        },
    },
    {
        "entity_name": "Pets.com",
        "actual_outcome": "failure",
        "description": "Dot-com bubble, shut down 2000",
        "signal_scores": {
            "funding_round": {"raw_score": 30, "published_at": "old"},
            "news_mention": {"raw_score": 5, "published_at": "old"},
        },
    },
    {
        "entity_name": "Theranos 2.0 (FakeBio)",
        "actual_outcome": "failure",
        "description": "Hypothetical low-signal biotech",
        "signal_scores": {
            "news_mention": {"raw_score": 15, "published_at": "old"},
            "website_change": {"raw_score": 5, "published_at": "old"},
        },
    },
    {
        "entity_name": "Zenefits",
        "actual_outcome": "failure",
        "description": "HR software, regulatory violations, CEO fired",
        "signal_scores": {
            "funding_round": {"raw_score": 45, "published_at": "old"},
            "news_mention": {"raw_score": 15, "published_at": "old"},
            "sec_filing": {"raw_score": 20, "published_at": "old"},
        },
    },
    {
        "entity_name": "Better.com",
        "actual_outcome": "failure",
        "description": "Digital mortgage, mass layoffs, CEO controversy",
        "signal_scores": {
            "funding_round": {"raw_score": 55, "published_at": "semi_recent"},
            "news_mention": {"raw_score": 20, "published_at": "semi_recent"},
            "job_posting_spike": {"raw_score": 5, "published_at": "old"},
        },
    },
    {
        "entity_name": "Fast (Checkout)",
        "actual_outcome": "failure",
        "description": "One-click checkout, shut down 2022",
        "signal_scores": {
            "funding_round": {"raw_score": 50, "published_at": "old"},
            "news_mention": {"raw_score": 10, "published_at": "old"},
            "social_buzz": {"raw_score": 5, "published_at": "old"},
        },
    },
    {
        "entity_name": "Hopin",
        "actual_outcome": "failure",
        "description": "Virtual events, $7.7B peak → sold for parts",
        "signal_scores": {
            "funding_round": {"raw_score": 55, "published_at": "old"},
            "job_posting_spike": {"raw_score": 10, "published_at": "old"},
            "news_mention": {"raw_score": 15, "published_at": "old"},
        },
    },
]


def _resolve_timestamp(published_at: str) -> datetime:
    """Convert relative timestamp strings to datetime objects."""
    now = datetime.now(timezone.utc)
    mapping = {
        "recent": now - timedelta(hours=12),
        "semi_recent": now - timedelta(days=14),
        "old": now - timedelta(days=180),
    }
    return mapping.get(published_at, now - timedelta(days=30))


@dataclass
class ValidationResult:
    """Result of scoring a single validation startup."""

    entity_name: str
    actual_outcome: str
    predicted_outcome: str
    score: float
    correct: bool
    description: str = ""


@dataclass
class ValidationReport:
    """Full validation report across all startups."""

    total: int = 0
    correct: int = 0
    accuracy: float = 0.0
    threshold: float = SUCCESS_THRESHOLD
    true_positives: int = 0
    false_positives: int = 0
    true_negatives: int = 0
    false_negatives: int = 0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    results: list[ValidationResult] = field(default_factory=list)
    weights_used: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "correct": self.correct,
            "accuracy": round(self.accuracy, 4),
            "threshold": self.threshold,
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "true_negatives": self.true_negatives,
            "false_negatives": self.false_negatives,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1_score": round(self.f1_score, 4),
            "results": [
                {
                    "entity_name": r.entity_name,
                    "actual": r.actual_outcome,
                    "predicted": r.predicted_outcome,
                    "score": round(r.score, 2),
                    "correct": r.correct,
                }
                for r in self.results
            ],
        }


def run_validation(
    weights: dict[str, dict[str, Any]] | None = None,
    threshold: float = SUCCESS_THRESHOLD,
    dataset: list[dict] | None = None,
) -> ValidationReport:
    """Run score validation against the known startup dataset.

    Args:
        weights: Override signal weights. Uses defaults if None.
        threshold: Score threshold for predicting success.
        dataset: Override validation set. Uses built-in set if None.

    Returns:
        ValidationReport with accuracy metrics.
    """
    dataset = dataset or VALIDATION_SET
    scorer = CompositeScorer(weights=weights)
    report = ValidationReport(threshold=threshold)
    report.weights_used = weights or SIGNAL_WEIGHTS

    for entry in dataset:
        entity_name = entry["entity_name"]
        actual = entry["actual_outcome"]

        # Convert signal_scores to CompositeScorer format
        signal_scores = {}
        historical_values = {}
        for sig_type, sig_data in entry.get("signal_scores", {}).items():
            published_at = _resolve_timestamp(sig_data.get("published_at", "old"))
            signal_scores[sig_type] = {
                "raw_score": sig_data["raw_score"],
                "published_at": published_at,
            }
            historical_values[sig_type] = [sig_data["raw_score"]]

        result = scorer.score(
            entity_name=entity_name,
            entity_type="company",
            signal_scores=signal_scores,
            historical_values=historical_values,
        )

        predicted = "success" if result.composite_score >= threshold else "failure"
        correct = predicted == actual

        vr = ValidationResult(
            entity_name=entity_name,
            actual_outcome=actual,
            predicted_outcome=predicted,
            score=result.composite_score,
            correct=correct,
            description=entry.get("description", ""),
        )
        report.results.append(vr)
        report.total += 1
        if correct:
            report.correct += 1

        # Confusion matrix
        if actual == "success" and predicted == "success":
            report.true_positives += 1
        elif actual == "failure" and predicted == "success":
            report.false_positives += 1
        elif actual == "failure" and predicted == "failure":
            report.true_negatives += 1
        elif actual == "success" and predicted == "failure":
            report.false_negatives += 1

    # Calculate metrics
    report.accuracy = report.correct / max(1, report.total) * 100
    predicted_positives = report.true_positives + report.false_positives
    actual_positives = report.true_positives + report.false_negatives
    report.precision = report.true_positives / max(1, predicted_positives) * 100
    report.recall = report.true_positives / max(1, actual_positives) * 100
    if report.precision + report.recall > 0:
        report.f1_score = 2 * report.precision * report.recall / (report.precision + report.recall)
    else:
        report.f1_score = 0.0

    return report


def suggest_weight_tuning(report: ValidationReport) -> list[str]:
    """Analyze validation results and suggest weight adjustments.

    Returns a list of human-readable suggestions.
    """
    suggestions = []
    if report.accuracy >= 80:
        suggestions.append(f"Accuracy is {report.accuracy:.0f}% — no tuning needed.")
        return suggestions

    # Analyze failure patterns
    false_positives = [r for r in report.results if not r.correct and r.predicted_outcome == "success"]
    false_negatives = [r for r in report.results if not r.correct and r.predicted_outcome == "failure"]

    if false_positives:
        names = ", ".join(r.entity_name for r in false_positives)
        suggestions.append(
            f"False positives ({len(false_positives)}): {names}. "
            "Consider lowering secondary/tertiary signal weights or increasing threshold."
        )

    if false_negatives:
        names = ", ".join(r.entity_name for r in false_negatives)
        suggestions.append(
            f"False negatives ({len(false_negatives)}): {names}. "
            "Consider increasing primary signal weights or decreasing threshold."
        )

    if report.false_positives > report.false_negatives:
        suggestions.append(
            f"Try raising SUCCESS_THRESHOLD from {report.threshold:.0f} to "
            f"{report.threshold + 5:.0f} to reduce false positives."
        )
    elif report.false_negatives > report.false_positives:
        suggestions.append(
            f"Try lowering SUCCESS_THRESHOLD from {report.threshold:.0f} to "
            f"{max(50, report.threshold - 5):.0f} to catch more successes."
        )

    return suggestions


def print_report(report: ValidationReport, verbose: bool = False):
    """Print a human-readable validation report."""
    print(f"\n{'=' * 60}")
    print(f"SCORE VALIDATION REPORT")
    print(f"{'=' * 60}")
    print(f"Threshold: {report.threshold:.0f}")
    print(f"Accuracy:  {report.accuracy:.1f}% ({report.correct}/{report.total} correct)")
    print(f"Precision: {report.precision:.1f}%")
    print(f"Recall:    {report.recall:.1f}%")
    print(f"F1 Score:  {report.f1_score:.1f}%")
    print(f"\nConfusion Matrix:")
    print(f"  TP={report.true_positives}  FP={report.false_positives}")
    print(f"  FN={report.false_negatives}  TN={report.true_negatives}")

    if verbose:
        print(f"\n{'─' * 60}")
        for r in sorted(report.results, key=lambda x: (-x.correct, x.score)):
            icon = "✓" if r.correct else "✗"
            print(f"  [{icon}] {r.entity_name:25s} score={r.score:6.1f} "
                  f"actual={r.actual_outcome:7s} predicted={r.predicted_outcome}")

    suggestions = suggest_weight_tuning(report)
    if suggestions:
        print(f"\n{'─' * 60}")
        print("Suggestions:")
        for s in suggestions:
            print(f"  • {s}")

    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Score Validation")
    parser.add_argument("--tune", action="store_true", help="Suggest weight tuning")
    parser.add_argument("--verbose", "-v", action="store_true", help="Detailed output")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    report = run_validation()
    print_report(report, verbose=args.verbose)

    if args.tune:
        print("Weight tuning suggestions:")
        for s in suggest_weight_tuning(report):
            print(f"  → {s}")
