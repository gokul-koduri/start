"""Unified entity extraction: spaCy primary, Ollama fallback.

This is the facade that the rest of the system calls for entity extraction.
It wraps the spaCy NER pipeline and provides Ollama as a fallback when
spaCy is unavailable or returns low-confidence results.

Integration point:
    Replaces _extract_entities_from_text() in knowledge_graph_agent.py.
    Usage:
        extractor = UnifiedEntityExtractor(config)
        entities = extractor.extract("Neuromorphic Labs raised $50M...")
        # entities = [NERResult(name="Neuromorphic Labs", label="startup", ...)]
"""

from __future__ import annotations

import json
import logging
import re
import urllib.request
from typing import Any

from nlp.ner_pipeline import NERResult, StartupNERPipeline

_logger = logging.getLogger(__name__)


class UnifiedEntityExtractor:
    """Unified entity extraction with spaCy primary and Ollama fallback.

    Extraction strategy:
    1. Try spaCy NER (fast, local, deterministic)
    2. If spaCy fails or returns empty results, try Ollama
    3. Merge and deduplicate results (spaCy takes priority)

    Config options:
        primary_engine: "spacy" (default) or "ollama"
        fallback_engine: "ollama" (default) or "none"
        spacy_confidence_threshold: 0.7
        ollama_url: Ollama API endpoint
        ollama_model: model name for NER
        ollama_timeout_seconds: 30
    """

    def __init__(self, config: dict | None = None):
        self._config = config or {}
        self._spacy_pipeline: StartupNERPipeline | None = None
        self._spacy_loaded = False

    def _get_spacy(self) -> StartupNERPipeline | None:
        """Lazy-load the spaCy pipeline."""
        if not self._spacy_loaded:
            try:
                self._spacy_pipeline = StartupNERPipeline(self._config)
                self._spacy_pipeline.load()
                self._spacy_loaded = True
            except Exception as e:
                _logger.warning("UnifiedEntityExtractor: spaCy unavailable: %s", e)
                self._spacy_loaded = True  # Don't retry
                self._spacy_pipeline = None
        return self._spacy_pipeline

    def extract(
        self,
        text: str,
        target_types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Extract entities from text with automatic fallback.

        Args:
            text: Input text (truncated to 500 chars for Ollama).
            target_types: Optional filter for specific KG entity types
                          (e.g., ["startup", "person", "technology"]).

        Returns:
            Deduplicated list of dicts with 'name' and 'type' keys,
            compatible with the existing knowledge_graph_agent.py format.
        """
        if not text or len(text.strip()) < 10:
            return []

        primary = self._config.get("primary_engine", "spacy")
        fallback = self._config.get("fallback_engine", "ollama")

        spacy_results: list[NERResult] = []
        ollama_results: list[dict] = []

        # Step 1: Try primary engine
        if primary == "spacy":
            spacy_results = self._extract_with_spacy(text)
        else:
            ollama_results = self._extract_with_ollama(text)

        # Step 2: Try fallback if primary returned nothing
        if not spacy_results and not ollama_results and fallback != "none":
            if primary == "spacy":
                ollama_results = self._extract_with_ollama(text)
            else:
                spacy_ner = self._get_spacy()
                if spacy_ner:
                    spacy_results = spacy_ner.extract_entities(text)

        # Step 3: Convert and merge
        all_results = []
        for r in spacy_results:
            all_results.append({"name": r.name, "type": r.label})

        # Add Ollama results that don't overlap with spaCy results
        spacy_names = {self._normalize_name(r.name) for r in spacy_results}
        for item in ollama_results:
            norm = self._normalize_name(item.get("name", ""))
            if norm and norm not in spacy_names:
                all_results.append(
                    {"name": item["name"], "type": item.get("type", "startup")}
                )

        # Filter by target types if specified
        if target_types:
            all_results = [r for r in all_results if r.get("type") in target_types]

        return all_results

    def extract_ner_results(
        self,
        text: str,
        confidence_threshold: float = 0.7,
    ) -> list[NERResult]:
        """Extract entities and return full NERResult objects.

        Use this when you need confidence scores and context, not just
        the simple {name, type} dicts.
        """
        if not text or len(text.strip()) < 10:
            return []

        spacy_ner = self._get_spacy()
        if spacy_ner:
            return spacy_ner.extract_entities(text, confidence_threshold)
        return []

    def _extract_with_spacy(self, text: str) -> list[NERResult]:
        """Primary extraction using spaCy."""
        try:
            spacy_ner = self._get_spacy()
            if spacy_ner:
                threshold = self._config.get("spacy_confidence_threshold", 0.7)
                return spacy_ner.extract_entities(text, threshold)
        except Exception as e:
            _logger.warning("UnifiedEntityExtractor: spaCy extraction failed: %s", e)
        return []

    def _extract_with_ollama(self, text: str) -> list[dict]:
        """Fallback extraction using Ollama LLM.

        Reuses the same prompt structure from knowledge_graph_agent.py
        _extract_entities_from_text() for consistency.
        """
        if len(text) < 20:
            return []

        url = self._config.get(
            "ollama_url",
            "http://localhost:11434/api/chat",
        )
        model = self._config.get("ollama_model", "llama3")
        timeout = self._config.get("ollama_timeout_seconds", 30)

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Extract named entities from the text. For each entity, classify as one of: "
                        "startup, investor, technology, industry, location, person, product, market. "
                        "Return ONLY a JSON array of objects with 'name' and 'type' keys. "
                        'Example: [{"name": "Stripe", "type": "startup"}]'
                    ),
                },
                {"role": "user", "content": text[:500]},
            ],
            "stream": False,
            "options": {"temperature": 0.1},
        }

        try:
            data = json.dumps(payload).encode()
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                result = json.loads(resp.read().decode())
            content = result.get("message", {}).get("content", "")
        except Exception as e:
            _logger.debug("UnifiedEntityExtractor: Ollama fallback failed: %s", e)
            return []

        # Parse JSON response (handle markdown code fences)
        try:
            raw = content.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                if raw.endswith("```"):
                    raw = raw[:-3]
                raw = raw.strip()
                if raw.lower().startswith("json"):
                    raw = raw[4:].strip()
            return json.loads(raw)
        except (json.JSONDecodeError, AttributeError):
            _logger.debug("UnifiedEntityExtractor: could not parse Ollama response")
            return []

    @staticmethod
    def _normalize_name(name: str) -> str:
        """Normalize entity name for dedup comparison.

        Matches the existing _normalize_name() in knowledge_graph_agent.py.
        """
        return re.sub(r"[^a-z0-9]", "", name.lower().strip())
