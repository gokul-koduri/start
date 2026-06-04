"""Sentiment Analysis Agent — scores news articles for sentiment polarity.

Two modes:
    1. Fast mode (default): VADER rule-based sentiment — instant, no LLM needed
    2. Deep mode: Ollama LLM via ModelManager for higher quality analysis

Scores are stored in the news_articles table (sentiment_score, sentiment_label,
sentiment_model, sentiment_analyzed_at columns).

Run:
    python run_agent.py --pipeline analysis   (includes sentiment agent)

Config options:
    mode: str — "fast" (VADER) or "deep" (Ollama LLM)
    batch_size: int — articles per batch (default: 100)
"""

import json
import logging
from datetime import datetime, timezone

from agents.base import AgentResult, BaseAgent
from db.connection import get_connection
from db import schema

_logger = logging.getLogger(__name__)


def _vader_sentiment(text: str) -> tuple[float, str]:
    """Score text using VADER sentiment analysis.

    Returns:
        (compound_score, label) where label is positive/negative/neutral.
    """
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        analyzer = SentimentIntensityAnalyzer()
        scores = analyzer.polarity_scores(text)
        compound = scores["compound"]

        if compound >= 0.05:
            label = "positive"
        elif compound <= -0.05:
            label = "negative"
        else:
            label = "neutral"

        return round(compound, 4), label
    except ImportError:
        # Fallback: simple keyword-based sentiment
        return _keyword_sentiment(text)


def _keyword_sentiment(text: str) -> tuple[float, str]:
    """Simple keyword-based sentiment fallback when VADER is not installed."""
    if not text:
        return 0.0, "neutral"

    negative_words = {
        "fail", "failed", "failure", "bankrupt", "bankruptcy", "shutdown", "collapse",
        "crash", "crisis", "loss", "losing", "lost", "decline", "down", "drop",
        "fire", "fired", "layoff", "laid off", "cut", "cuts", "closure", "close",
        "dead", "died", "cease", "liquidat", "insolvent", "fraud", "scandal",
    }
    positive_words = {
        "growth", "grow", "profit", "profitable", "success", "successful", "rise",
        "rising", "gain", "boost", "innovation", "innovative", "fund", "funded",
        "investment", "invest", "launch", "expand", "acquire", "acquisition",
        "partnership", "revenue", "thriving", "milestone", "breakthrough",
    }

    words = text.lower().split()
    neg_count = sum(1 for w in words if w in negative_words)
    pos_count = sum(1 for w in words if w in positive_words)
    total = neg_count + pos_count

    if total == 0:
        return 0.0, "neutral"

    score = (pos_count - neg_count) / total

    if score > 0.2:
        return round(score, 4), "positive"
    elif score < -0.2:
        return round(score, 4), "negative"
    return round(score, 4), "neutral"


def _llm_sentiment(text: str, model_manager) -> tuple[float, str]:
    """Score text using Ollama LLM via ModelManager.

    Returns:
        (compound_score, label).
    """
    prompt = (
        "Analyze the sentiment of this news headline/summary. "
        "Return ONLY a JSON object with two keys:\n"
        '- "score": a float from -1.0 (very negative) to 1.0 (very positive)\n'
        '- "label": one of "positive", "negative", or "neutral"\n\n'
        f"Text: {text[:500]}"
    )

    result = model_manager.infer_json(prompt, task="sentiment", temperature=0.1)

    if result and isinstance(result, dict):
        score = float(result.get("score", 0.0))
        label = result.get("label", "neutral")
        return round(max(-1.0, min(1.0, score)), 4), label

    return 0.0, "neutral"


class SentimentAgent(BaseAgent):
    """Analyzes sentiment of news articles in the database.

    Processes articles that haven't been scored yet (sentiment_score IS NULL).
    """

    @property
    def name(self) -> str:
        return "sentiment"

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        mode = self.config.get("mode", "fast")
        batch_size = self.config.get("batch_size", 100)

        _logger.info("SentimentAgent: Starting (mode=%s, batch_size=%d)", mode, batch_size)

        # Initialize LLM for deep mode
        model_manager = None
        if mode == "deep":
            try:
                from agents.model_manager import ModelManager
                model_manager = ModelManager(self.config)
                _logger.info("SentimentAgent: Using Ollama LLM for deep sentiment analysis")
            except Exception as e:
                _logger.warning("SentimentAgent: Failed to init ModelManager, falling back to fast mode: %s", e)
                mode = "fast"

        try:
            conn = get_connection()
            schema.init_schema(conn)
        except Exception as e:
            return AgentResult(agent_name=self.name, status="failed", errors=[str(e)])

        try:
            cursor = conn.cursor()

            # Count unscored articles
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM news_articles WHERE sentiment_score IS NULL"
            )
            total_unscored = cursor.fetchone()["cnt"]

            if total_unscored == 0:
                _logger.info("SentimentAgent: All articles already scored")
                return AgentResult(
                    agent_name=self.name,
                    status="success",
                    data={"scored": 0, "already_scored": True, "records_affected": 0},
                )

            # Fetch unscored articles
            cursor.execute(
                """SELECT id, title, summary
                   FROM news_articles
                   WHERE sentiment_score IS NULL
                   LIMIT %s""",
                (batch_size,),
            )
            articles = cursor.fetchall()

            scored = 0
            label_counts = {}
            errors = 0

            for article in articles:
                text = article["summary"] or article["title"] or ""

                if not text.strip():
                    cursor.execute(
                        """UPDATE news_articles
                           SET sentiment_score = 0.0, sentiment_label = 'neutral',
                               sentiment_model = 'empty', sentiment_analyzed_at = %s
                           WHERE id = %s""",
                        (datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), article["id"]),
                    )
                    label_counts["neutral"] = label_counts.get("neutral", 0) + 1
                    scored += 1
                    continue

                # Score based on mode
                if mode == "deep" and model_manager:
                    score, label = _llm_sentiment(text, model_manager)
                    model_used = model_manager.get_model("sentiment")
                else:
                    score, label = _vader_sentiment(text)
                    model_used = "vader"

                label_counts[label] = label_counts.get(label, 0) + 1

                if not self.dry_run:
                    cursor.execute(
                        """UPDATE news_articles
                           SET sentiment_score = %s, sentiment_label = %s,
                               sentiment_model = %s, sentiment_analyzed_at = %s
                           WHERE id = %s""",
                        (
                            score,
                            label,
                            model_used,
                            datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                            article["id"],
                        ),
                    )
                scored += 1

            if not self.dry_run:
                conn.commit()

            _logger.info(
                "SentimentAgent: Scored %d/%d articles — %s",
                scored, total_unscored, label_counts,
            )

            return AgentResult(
                agent_name=self.name,
                status="success",
                data={
                    "scored": scored,
                    "remaining": total_unscored - scored,
                    "mode": mode,
                    "model_used": model_used if mode == "deep" else "vader",
                    "label_distribution": label_counts,
                    "records_affected": scored,
                    "errors": errors,
                },
            )

        except Exception as e:
            _logger.error("SentimentAgent: Error: %s", e)
            return AgentResult(agent_name=self.name, status="failed", errors=[str(e)])
        finally:
            conn.close()
