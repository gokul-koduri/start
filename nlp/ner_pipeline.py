"""spaCy-based Named Entity Recognition pipeline for startup intelligence.

Replaces Ollama-based NER with deterministic, fast spaCy extraction.
Uses en_core_web_trf (transformer-based) for best accuracy, with a custom
EntityRuler for domain-specific entity types (technology, market, patent).

Design choices:
    - EntityRuler runs BEFORE the transformer NER, seeding domain entities
    - Lazy loading: en_core_web_trf is ~500MB, loaded on first use
    - Custom entity types: TECHNOLOGY, MARKET, PATENT via pattern matching
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

_logger = logging.getLogger(__name__)

# Seed technology terms for EntityRuler patterns
_SEED_TECHNOLOGIES = [
    "Python",
    "JavaScript",
    "TypeScript",
    "Rust",
    "Go",
    "Java",
    "C++",
    "Kubernetes",
    "Docker",
    "Terraform",
    "React",
    "Vue.js",
    "Angular",
    "TensorFlow",
    "PyTorch",
    "scikit-learn",
    "XGBoost",
    "LLM",
    "GPT",
    "BERT",
    "Llama",
    "Stable Diffusion",
    "LangChain",
    "FastAPI",
    "Flask",
    "PostgreSQL",
    "MongoDB",
    "Redis",
    "Kafka",
    "gRPC",
    "GraphQL",
    "AWS",
    "Azure",
    "GCP",
    "Snowflake",
    "Databricks",
    "Spark",
    "Arduino",
    "Raspberry Pi",
    "FPGA",
    "Verilog",
    "3D printing",
    "semiconductor",
    "lithography",
    "photolithography",
    "nanotechnology",
    "machine learning",
    "deep learning",
    "natural language processing",
    "computer vision",
    "reinforcement learning",
    "edge computing",
    "blockchain",
    "smart contracts",
    "zero-knowledge proofs",
    "CRISPR",
    "synthetic biology",
    "genomics",
    "proteomics",
    "autonomous driving",
    "lidar",
    "radar",
    "EV battery",
    "SaaS",
    "PaaS",
    "IaaS",
    "API gateway",
    "microservices",
    "robotics",
    "drone",
    "IoT",
    "5G",
    "Wi-Fi 7",
    "cybersecurity",
    "encryption",
    "zero-trust",
    "identity management",
    "Web3",
    "DeFi",
    "NFT",
    "metaverse",
]

# Market segment patterns
_MARKET_PATTERNS = [
    {
        "label": "MARKET",
        "pattern": [{"LOWER": {"REGEX": r"(?:saas|paas|iaas|b2b|b2c|d2c)"}}],
    },
    {"label": "MARKET", "pattern": [{"LOWER": "market"}, {"IS_TITLE": True}]},
    {
        "label": "MARKET",
        "pattern": [
            {
                "LOWER": {
                    "REGEX": r"(?:fintech|healthtech|edtech|cleantech|agritech|proptech|legaltech|insurtech|regtech|retailtech|foodtech|biotech|medtech)"
                }
            }
        ],
    },
    {
        "label": "MARKET",
        "pattern": [{"LOWER": {"REGEX": r"(?:cybersecurity|ecommerce|e-commerce)"}}],
    },
    {
        "label": "MARKET",
        "pattern": [
            {
                "LOWER": {
                    "REGEX": r"(?:artificial intelligence|machine learning|deep learning|generative ai)"
                }
            }
        ],
    },
]

# Patent number patterns
_PATENT_PATTERNS = [
    {"label": "PATENT", "pattern": [{"LOWER": "patent"}, {"SHAPE": "XXXXXXX"}]},
    {"label": "PATENT", "pattern": [{"TEXT": {"REGEX": r"US\d{6,}A\d?"}}]},
    {
        "label": "PATENT",
        "pattern": [{"LOWER": "patent"}, {"LOWER": "no"}, {"SHAPE": "ddddd"}],
    },
    {"label": "PATENT", "pattern": [{"LOWER": "uspto"}, {"LOWER": "filing"}]},
]


@dataclass
class NERResult:
    """Single named entity extraction result.

    Attributes:
        name: Extracted entity text.
        label: Knowledge graph entity type (startup, person, technology, etc.)
        start_char: Character offset where entity starts in source text.
        end_char: Character offset where entity ends in source text.
        confidence: Detection confidence (0.0-1.0). Rule-based = 1.0, transformer varies.
        source: Which engine produced this result (spacy, rule, ollama_fallback).
        context: Surrounding text snippet for disambiguation.
    """

    name: str
    label: str
    start_char: int = 0
    end_char: int = 0
    confidence: float = 1.0
    source: str = "spacy"
    context: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.label,
            "confidence": self.confidence,
            "source": self.source,
            "context": self.context,
        }


# Map spaCy entity labels to KG entity types
_SPACY_TO_KG_TYPE = {
    "ORG": "startup",
    "PERSON": "person",
    "GPE": "region",
    "LOC": "region",
    "NORP": "industry",
    "PRODUCT": "product",
    "FAC": "industry",
    "EVENT": "industry",
    "LAW": "regulation",
    "LANGUAGE": "technology",
    # Custom types from EntityRuler
    "TECHNOLOGY": "technology",
    "MARKET": "market",
    "PATENT": "patent",
}


class StartupNERPipeline:
    """spaCy-based NER pipeline tuned for startup intelligence domain.

    Uses en_core_web_trf (transformer) with custom EntityRuler for
    domain-specific entities (technology names, market segments, patents).

    Config options:
        model_name: spaCy model (default: en_core_web_trf)
        batch_size: texts per batch for spaCy.pipe()
        confidence_threshold: minimum confidence for results (default: 0.7)
    """

    def __init__(self, config: dict | None = None):
        self._nlp = None
        self._config = config or {}
        self._model_name = self._config.get("model_name", "en_core_web_trf")
        self._batch_size = self._config.get("batch_size", 32)
        self._loaded = False

    def load(self) -> None:
        """Lazy-load the spaCy model and add custom EntityRuler.

        The en_core_web_trf model is ~500MB, so this must be called
        explicitly rather than at import time.
        """
        if self._loaded:
            return

        try:
            import spacy

            self._nlp = spacy.load(self._model_name)
            self._add_custom_entity_ruler()
            self._loaded = True
            _logger.info("StartupNERPipeline: loaded model '%s'", self._model_name)
        except OSError:
            _logger.error(
                "StartupNERPipeline: model '%s' not found. "
                "Run: python -m spacy download %s",
                self._model_name,
                self._model_name,
            )
            raise

    @property
    def is_loaded(self) -> bool:
        return self._loaded and self._nlp is not None

    def extract_entities(
        self,
        text: str,
        confidence_threshold: float = 0.7,
    ) -> list[NERResult]:
        """Extract named entities from text.

        Args:
            text: Input text to process.
            confidence_threshold: Minimum confidence (0-1) to include.

        Returns:
            List of NERResult sorted by confidence descending.
        """
        if not text or len(text.strip()) < 5:
            return []

        self.load()
        threshold = confidence_threshold or self._config.get(
            "confidence_threshold", 0.7
        )

        doc = self._nlp(text[:10_000])  # Truncate to avoid OOM on huge texts
        results = []

        for ent in doc.ents:
            kg_type = _SPACY_TO_KG_TYPE.get(ent.label_)
            if not kg_type:
                continue

            confidence = self._compute_confidence(ent, kg_type)
            if confidence < threshold:
                continue

            # Extract context snippet (surrounding 50 chars)
            start = max(0, ent.start_char - 50)
            end = min(len(text), ent.end_char + 50)
            context = text[start:end].strip()

            results.append(
                NERResult(
                    name=ent.text.strip(),
                    label=kg_type,
                    start_char=ent.start_char,
                    end_char=ent.end_char,
                    confidence=confidence,
                    source="rule"
                    if ent.label_ in ("TECHNOLOGY", "MARKET", "PATENT")
                    else "spacy",
                    context=context,
                )
            )

        results.sort(key=lambda r: r.confidence, reverse=True)
        return results

    def extract_from_batch(
        self,
        texts: list[str],
        confidence_threshold: float = 0.7,
    ) -> list[list[NERResult]]:
        """Extract entities from multiple texts using spaCy.pipe().

        More efficient than calling extract_entities() in a loop.

        Args:
            texts: List of input texts.
            confidence_threshold: Minimum confidence (0-1).

        Returns:
            List of lists (one NERResult list per input text).
        """
        self.load()
        threshold = confidence_threshold or self._config.get(
            "confidence_threshold", 0.7
        )
        all_results = []

        docs = self._nlp.pipe(
            [t[:10_000] for t in texts],
            batch_size=self._batch_size,
            disable=["lemmatizer", "textcat"],
        )

        for doc in docs:
            results = []
            for ent in doc.ents:
                kg_type = _SPACY_TO_KG_TYPE.get(ent.label_)
                if not kg_type:
                    continue
                confidence = self._compute_confidence(ent, kg_type)
                if confidence < threshold:
                    continue
                results.append(
                    NERResult(
                        name=ent.text.strip(),
                        label=kg_type,
                        start_char=ent.start_char,
                        end_char=ent.end_char,
                        confidence=confidence,
                        source="rule"
                        if ent.label_ in ("TECHNOLOGY", "MARKET", "PATENT")
                        else "spacy",
                    )
                )
            results.sort(key=lambda r: r.confidence, reverse=True)
            all_results.append(results)

        return all_results

    def _compute_confidence(self, ent, kg_type: str) -> float:
        """Compute confidence score for an entity.

        Rule-based entities (TECHNOLOGY, MARKET, PATENT) get fixed 0.95
        since they're pattern-matched exactly. Transformer entities get
        their spaCy confidence score, with bonuses for longer names.
        """
        if ent.label_ in ("TECHNOLOGY", "MARKET", "PATENT"):
            return 0.95

        # Base confidence from transformer (spacy provides this via ent._.score
        # for transformer models, but it's not always available)
        confidence = 0.7

        # Bonus for longer, more specific entity names
        if len(ent.text.strip()) > 10:
            confidence += 0.1
        if ent.label_ == "ORG":
            confidence += 0.05  # Companies are generally well-detected
        if ent.label_ == "PERSON":
            confidence += 0.05

        return min(confidence, 1.0)

    def _add_custom_entity_ruler(self) -> None:
        """Add EntityRuler with domain-specific patterns before the transformer.

        The EntityRuler runs as a pipeline component BEFORE the transformer NER.
        This seeds the model with known technology names, market segments, and
        patent patterns that the general-purpose transformer might miss.
        """

        ruler = self._nlp.add_pipe("entity_ruler", before="ner")

        # Technology patterns: exact phrase matches
        tech_patterns = [
            {"label": "TECHNOLOGY", "pattern": [{"LOWER": tech.lower()}]}
            for tech in _SEED_TECHNOLOGIES
        ]

        ruler.add_patterns(tech_patterns)
        ruler.add_patterns(_MARKET_PATTERNS)
        ruler.add_patterns(_PATENT_PATTERNS)

        _logger.info(
            "StartupNERPipeline: EntityRuler added with %d technology, "
            "%d market, %d patent patterns",
            len(tech_patterns),
            len(_MARKET_PATTERNS),
            len(_PATENT_PATTERNS),
        )
