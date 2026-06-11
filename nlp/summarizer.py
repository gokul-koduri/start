"""Text summarization via Ollama (local LLM).

Provides abstractive summarization for signal text using the existing
Ollama infrastructure. Used by the NLP enrichment agent to create
concise summaries before storing in the knowledge graph.

Design choices:
    - Reuses existing Ollama setup (same model/URL config as other agents)
    - Rate-limited to avoid overwhelming the local LLM
    - Graceful degradation: returns truncated text if Ollama unavailable
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request
import urllib.error

_logger = logging.getLogger(__name__)


class OllamaSummarizer:
    """Text summarization via Ollama.

    Config options:
        ollama_url: Ollama API endpoint (default: http://localhost:11434/api/chat)
        model: model name for summarization
        max_length: max words in summary (default: 200)
        timeout_seconds: request timeout (default: 30)
    """

    def __init__(self, config: dict | None = None):
        self._config = config or {}
        self._url = self._config.get("ollama_url", "http://localhost:11434/api/chat")
        self._model = self._config.get("model", "llama3")
        self._max_length = self._config.get("max_length", 200)
        self._timeout = self._config.get("timeout_seconds", 30)

    def summarize(self, text: str, max_length: int | None = None) -> str:
        """Generate a concise summary of text.

        Args:
            text: Text to summarize.
            max_length: Max words in summary (overrides config).

        Returns:
            Summary string, or truncated original text if Ollama fails.
        """
        if not text or len(text.strip()) < 50:
            return text

        limit = max_length or self._max_length

        # If text is already short enough, return as-is
        if len(text.split()) <= limit:
            return text

        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"Summarize the following text in {limit} words or fewer. "
                        "Focus on key facts: company names, amounts, dates, "
                        "and business significance. Return only the summary."
                    ),
                },
                {"role": "user", "content": text[:3000]},
            ],
            "stream": False,
            "options": {"temperature": 0.3, "num_predict": limit * 3},
        }

        try:
            data = json.dumps(payload).encode()
            req = urllib.request.Request(
                self._url,
                data=data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                result = json.loads(resp.read().decode())
            summary = result.get("message", {}).get("content", "").strip()
            if summary:
                return summary
        except (urllib.error.URLError, OSError) as e:
            _logger.debug("OllamaSummarizer: unavailable (%s), using truncation", e)

        # Fallback: truncate to first N words
        words = text.split()[:limit]
        return " ".join(words) + "..."

    def summarize_batch(
        self,
        texts: list[str],
        delay: float = 1.0,
    ) -> list[str]:
        """Summarize multiple texts with rate limiting.

        Args:
            texts: List of texts to summarize.
            delay: Seconds between Ollama calls.

        Returns:
            List of summaries (one per input text).
        """
        results = []
        for i, text in enumerate(texts):
            results.append(self.summarize(text))
            if delay > 0 and i > 0:
                time.sleep(delay)
        return results
