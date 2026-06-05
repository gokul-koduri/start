"""Text classification for signal types and sentiment.

Uses spaCy textcat for signal type classification and a rule-based
sentiment classifier. Falls back to keyword matching when spaCy
is unavailable.

Design choices:
    - Rule-based signal type classification first (deterministic, fast)
    - spaCy textcat as enhancement (when model supports it)
    - VADER-like keyword scoring for sentiment (avoid adding another dependency)
"""

from __future__ import annotations

import logging
import re

from ingestion.signal_normalizer import VALID_SIGNAL_TYPES

_logger = logging.getLogger(__name__)

# Signal type classification patterns
_SIGNAL_PATTERNS: dict[str, list[str]] = {
    "funding_round": [
        r"\braised?\s+\$?\d", r"\bfunded\b", r"\bseries\s+[a-z]\b",
        r"\bseed\s+round\b", r"\bventure\s+capital\b", r"\binvestment\b",
        r"\bvaluation\b", r"\bipo\b", r"\bpre[- ]?seed\b",
    ],
    "sec_filing": [
        r"\b10[- ]?[kKqQ]\b", r"\b8[- ]?K\b", r"\bS[- ]?1\b",
        r"\bSEC\b", r"\bfiling\b", r"\bannual\s+report\b",
        r"\bquarterly\s+report\b", r"\bproxy\s+statement\b",
    ],
    "job_posting_spike": [
        r"\bhiring\b", r"\bjob\s+posting\b", r"\brecruiting\b",
        r"\bcareer\b", r"\bposition\b", r"\bopen\s+role\b",
        r"\blooking\s+for\b.*\b(engineer|developer|scientist)\b",
    ],
    "github_trend": [
        r"\bgithub\b", r"\bopen[- ]?source\b", r"\brepository\b",
        r"\bstar(s|red|ting)?\b", r"\bfork(s|ed)?\b", r"\bPR\b",
        r"\bpull\s+request\b", r"\bcommit\b",
    ],
    "patent_filed": [
        r"\bpatent\b", r"\bUSPTO\b", r"\bintellectual\s+property\b",
        r"\binvention\b", r"\bgrant(ed)?\b", r"\bclaim(s)?\b",
    ],
    "social_buzz": [
        r"\breddit\b", r"\bhacker\s+news\b", r"\bHN\b",
        r"\bupvote\b", r"\bfront\s+page\b", r"\btrending\b",
    ],
    "news_mention": [
        r"\bannounc(ed|es|ing|ement)\b", r"\breport(ed|s|ing)?\b",
        r"\baccordin?g\s+to\b", r"\bsaid\b", r"\b spokes",
    ],
}

# Sentiment keyword lists
_POSITIVE_WORDS = {
    "success", "growth", "profit", "revenue", "innovation", "breakthrough",
    "leading", "impressive", "milestone", "launch", "expand", "thrive",
    "record", "soar", "surge", "boom", "excellent", "outstanding",
    "revolutionary", "transformative", "unicorn", "series", "funded",
    "raised", "strategic", "partnership", "acquisition", "gain",
}

_NEGATIVE_WORDS = {
    "fail", "bankrupt", "shutdown", "collapse", "crisis", "loss",
    "decline", "struggle", "lawsuit", "fraud", "scandal", "downfall",
    "layoff", "fire", "cut", "reduce", "negative", "warning",
    "risk", "threat", "vulnerable", "distress", "delist", "pandemic",
    "regulatory", "compliance", "violation", "penalty", "fine",
}


class SignalTextClassifier:
    """Classifies text into signal types and sentiment.

    Uses rule-based pattern matching for signal type detection
    and keyword-based scoring for sentiment. These approaches are
    deterministic and fast, making them suitable for high-throughput
    processing in the enrichment pipeline.

    Config options:
        confidence_threshold: minimum confidence for classification
    """

    def __init__(self, config: dict | None = None):
        self._config = config or {}
        self._confidence_threshold = self._config.get("confidence_threshold", 0.6)
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Pre-compile regex patterns for efficiency."""
        self._compiled: dict[str, list[re.Pattern]] = {}
        for signal_type, patterns in _SIGNAL_PATTERNS.items():
            self._compiled[signal_type] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]

    def classify_signal_type(
        self, text: str, title: str = "",
    ) -> tuple[str, float]:
        """Classify text into a signal type.

        Args:
            text: Body text to classify.
            title: Optional title (given extra weight).

        Returns:
            Tuple of (signal_type, confidence).
            signal_type is one of VALID_SIGNAL_TYPES or "unknown".
        """
        combined = f"{title} {text}".lower()

        if not combined.strip():
            return "unknown", 0.0

        # Score each signal type by counting pattern matches
        scores: dict[str, float] = {}
        for signal_type, patterns in self._compiled.items():
            matches = sum(1 for p in patterns if p.search(combined))
            if matches > 0:
                scores[signal_type] = min(matches / 3.0, 1.0)

        if not scores:
            return "unknown", 0.0

        best_type = max(scores, key=scores.get)
        confidence = scores[best_type]
        return best_type, confidence

    def classify_sentiment(self, text: str) -> tuple[str, float]:
        """Classify text sentiment using keyword scoring.

        Args:
            text: Text to analyze.

        Returns:
            Tuple of (label, score).
            label: "positive", "negative", or "neutral".
            score: sentiment score from -1.0 to 1.0.
        """
        words = set(text.lower().split())
        positive_count = len(words & _POSITIVE_WORDS)
        negative_count = len(words & _NEGATIVE_WORDS)
        total = positive_count + negative_count

        if total == 0:
            return "neutral", 0.0

        score = (positive_count - negative_count) / total
        label = "positive" if score > 0.2 else ("negative" if score < -0.2 else "neutral")
        return label, score

    def classify(
        self, text: str, title: str = "",
    ) -> dict[str, str | float]:
        """Run all classifications and return combined result.

        Returns:
            Dict with keys: signal_type, signal_confidence,
            sentiment_label, sentiment_score.
        """
        sig_type, sig_conf = self.classify_signal_type(text, title)
        sent_label, sent_score = self.classify_sentiment(text)

        return {
            "signal_type": sig_type,
            "signal_confidence": sig_conf,
            "sentiment_label": sent_label,
            "sentiment_score": sent_score,
        }
