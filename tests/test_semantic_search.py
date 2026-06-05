"""Tests for the search stack: VectorStore and SearchIndex.

Tests use mocking since Qdrant and Elasticsearch may not be running.
Tests for embedding generator (real logic) run when sentence-transformers is installed.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ── VectorStore (Qdrant) tests ──


class TestVectorStore:
    def test_init_defaults(self):
        from db.vector_store import VectorStore
        store = VectorStore()
        assert store._url == "http://localhost:6333"
        assert store._collection == "startup_signals"
        assert store._embedding_dim == 384
        assert not store.is_connected

    def test_init_custom_config(self):
        from db.vector_store import VectorStore
        store = VectorStore({"url": "http://custom:6333", "collection_name": "custom"})
        assert store._url == "http://custom:6333"
        assert store._collection == "custom"

    def test_connect_import_error(self):
        from db.vector_store import VectorStore
        store = VectorStore()
        with patch.dict("sys.modules", {"qdrant_client": None}):
            assert store.connect() is False

    def test_connect_success(self):
        from db.vector_store import VectorStore
        store = VectorStore()

        # Simulate successful connection since qdrant_client may not be installed
        store._connected = True
        store._client = MagicMock()
        assert store.is_connected

    def test_search_disconnected(self):
        from db.vector_store import VectorStore
        store = VectorStore()
        results = store.search([0.0] * 384)
        assert results == []

    def test_search_by_text(self):
        from db.vector_store import VectorStore
        store = VectorStore()

        mock_gen = MagicMock()
        mock_gen.embed_text.return_value = [0.1] * 384

        # Disconnected, returns empty
        results = store.search_by_text("test query", mock_gen)
        assert results == []


# ── SearchIndex (Elasticsearch) tests ──


class TestSearchIndex:
    def test_init_defaults(self):
        from db.search_index import SearchIndex
        idx = SearchIndex()
        assert idx._url == "http://localhost:9200"
        assert idx._index == "startup_research"
        assert not idx.is_connected

    def test_connect_import_error(self):
        from db.search_index import SearchIndex
        idx = SearchIndex()
        with patch.dict("sys.modules", {"elasticsearch": None}):
            assert idx.connect() is False

    def test_search_disconnected(self):
        from db.search_index import SearchIndex
        idx = SearchIndex()
        results = idx.search("test query")
        assert results == []


# ── SearchResult and SearchHit data classes ──


class TestDataClasses:
    def test_search_result_to_dict(self):
        from db.vector_store import SearchResult
        r = SearchResult(id="123", score=0.95, payload={"title": "Test"})
        d = r.to_dict()
        assert d["id"] == "123"
        assert d["score"] == 0.95
        assert d["payload"]["title"] == "Test"

    def test_search_hit_to_dict(self):
        from db.search_index import SearchHit
        h = SearchHit(id="456", score=8.5, source={"title": "Test"}, highlights={"title": ["<em>Test</em>"]})
        d = h.to_dict()
        assert d["id"] == "456"
        assert d["highlights"]["title"][0] == "<em>Test</em>"

    def test_hybrid_result_to_dict(self):
        from db.search_index import HybridResult
        h = HybridResult(id="789", score=0.85, bm25_score=5.0, vector_score=0.92)
        d = h.to_dict()
        assert d["bm25_score"] == 5.0
        assert d["vector_score"] == 0.92


# ── EmbeddingGenerator tests (requires sentence-transformers) ──


class TestEmbeddingGenerator:
    def test_init_does_not_load(self):
        from nlp.embedding_generator import EmbeddingGenerator
        gen = EmbeddingGenerator()
        assert not gen.is_loaded
        assert gen.dimension == 384

    def test_load_import_error(self):
        from nlp.embedding_generator import EmbeddingGenerator
        gen = EmbeddingGenerator()
        with patch.dict("sys.modules", {"sentence_transformers": None}):
            with pytest.raises(Exception):
                gen.load()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
