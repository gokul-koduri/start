"""SentenceTransformer embedding generator for semantic search.

Uses all-MiniLM-L6-v2 (384-dimensional) for generating text embeddings.
These embeddings power:
    - Qdrant vector search (semantic similarity)
    - Entity resolution (compare entity name embeddings)
    - NLP enrichment (embed raw signals for indexing)

Design choices:
    - all-MiniLM-L6-v2: fast (~80MB), good quality for general semantic tasks
    - L2-normalized embeddings by default (cosine similarity = dot product)
    - Lazy loading: model loads on first use
"""

from __future__ import annotations

import logging

_logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generates 384-dimensional embeddings using all-MiniLM-L6-v2.

    Config options:
        model_name: SentenceTransformer model (default: all-MiniLM-L6-v2)
        device: "cpu" or "cuda"
        batch_size: batch size for encode() calls
    """

    def __init__(self, config: dict | None = None):
        self._model = None
        self._config = config or {}
        self._model_name = self._config.get("model_name", "all-MiniLM-L6-v2")
        self._device = self._config.get("device", "cpu")
        self._batch_size = self._config.get("batch_size", 64)
        self._loaded = False

    def load(self) -> None:
        """Lazy-load the SentenceTransformer model (~80MB)."""
        if self._loaded:
            return

        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(
                self._model_name,
                device=self._device,
            )
            self._loaded = True
            _logger.info(
                "EmbeddingGenerator: loaded model '%s' on %s",
                self._model_name,
                self._device,
            )
        except Exception as e:
            _logger.error("EmbeddingGenerator: failed to load model: %s", e)
            raise

    @property
    def is_loaded(self) -> bool:
        return self._loaded and self._model is not None

    @property
    def dimension(self) -> int:
        """Embedding dimension (384 for all-MiniLM-L6-v2)."""
        return self._config.get("embedding_dim", 384)

    def embed_text(self, text: str) -> list[float]:
        """Generate a 384-dim embedding for a single text.

        Args:
            text: Input text to embed.

        Returns:
            List of 384 floats (L2-normalized).
        """
        self.load()
        embedding = self._model.encode(
            text,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embedding.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts.

        More efficient than calling embed_text() in a loop.

        Args:
            texts: List of input texts.

        Returns:
            List of embedding lists (one 384-dim list per text).
        """
        self.load()
        embeddings = self._model.encode(
            texts,
            normalize_embeddings=True,
            batch_size=self._batch_size,
            show_progress_bar=False,
        )
        return [e.tolist() for e in embeddings]

    def similarity(self, text_a: str, text_b: str) -> float:
        """Compute cosine similarity between two texts.

        Since embeddings are L2-normalized, cosine similarity equals
        the dot product.

        Args:
            text_a: First text.
            text_b: Second text.

        Returns:
            Similarity score between -1.0 and 1.0 (typically 0.0-1.0 for
            similar texts).
        """
        emb_a = self.embed_text(text_a)
        emb_b = self.embed_text(text_b)

        dot = sum(a * b for a, b in zip(emb_a, emb_b))
        return float(dot)
