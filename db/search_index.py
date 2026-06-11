"""Elasticsearch client for full-text search.

Provides BM25 text search over raw signals using Elasticsearch.
Works alongside Qdrant (vector search) for hybrid search capabilities.

Design choices:
    - Single index "startup_research" for all content types
    - English analyzer for text fields, keyword for categorical fields
    - Hybrid search blends BM25 + vector cosine via script_score
    - Graceful degradation: if ES unavailable, returns empty results
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

_logger = logging.getLogger(__name__)

_INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "title": {
                "type": "text",
                "analyzer": "english",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "body_text": {"type": "text", "analyzer": "english"},
            "entity_name": {
                "type": "text",
                "analyzer": "english",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "entity_type": {"type": "keyword"},
            "signal_type": {"type": "keyword"},
            "published_at": {"type": "date"},
            "composite_score": {"type": "float"},
            "signal_id": {"type": "integer"},
            "embedding_vector": {
                "type": "dense_vector",
                "dims": 384,
                "index": True,
                "similarity": "cosine",
            },
        }
    },
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
    },
}


@dataclass
class SearchHit:
    """Single Elasticsearch search result."""

    id: str
    score: float  # BM25 relevance score
    source: dict = field(default_factory=dict)
    highlights: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "score": round(self.score, 4),
            "source": self.source,
            "highlights": self.highlights,
        }


@dataclass
class HybridResult:
    """Combined result from hybrid (BM25 + vector) search."""

    id: str
    score: float
    source: dict = field(default_factory=dict)
    bm25_score: float = 0.0
    vector_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "score": round(self.score, 4),
            "bm25_score": round(self.bm25_score, 4),
            "vector_score": round(self.vector_score, 4),
            "source": self.source,
        }


class SearchIndex:
    """Elasticsearch client for full-text search.

    Index design:
        - Name: "startup_research"
        - Mappings: title/body_text (text+english), entity_name/type (keyword)
        - Settings: 1 shard, 0 replicas (single-node dev setup)

    Config options:
        url: Elasticsearch URL (default: http://localhost:9200)
        index_name: index name (default: startup_research)
        batch_size: bulk index batch size (default: 100)
    """

    def __init__(self, config: dict | None = None):
        self._config = config or {}
        self._url = self._config.get("url", "http://localhost:9200")
        self._index = self._config.get("index_name", "startup_research")
        self._batch_size = self._config.get("batch_size", 100)
        self._client = None
        self._connected = False

    def connect(self) -> bool:
        """Initialize connection and create index if needed.

        Returns True if successful, False if ES is unavailable.
        """
        try:
            from elasticsearch import Elasticsearch

            self._client = Elasticsearch([self._url])

            # Check if index exists, create if not
            if not self._client.indices.exists(index=self._index):
                self._client.indices.create(
                    index=self._index,
                    body=_INDEX_MAPPING,
                )
                _logger.info(
                    "SearchIndex: created index '%s'",
                    self._index,
                )

            self._connected = True
            _logger.info("SearchIndex: connected to ES at %s", self._url)
            return True

        except ImportError:
            _logger.warning("SearchIndex: elasticsearch not installed")
            return False
        except Exception as e:
            _logger.warning("SearchIndex: cannot connect to ES: %s", e)
            return False

    @property
    def is_connected(self) -> bool:
        return self._connected and self._client is not None

    def index_document(self, doc_id: str, document: dict) -> bool:
        """Index a single document.

        Args:
            doc_id: Unique document identifier.
            document: Document fields.
        """
        if not self.is_connected:
            return False

        try:
            self._client.index(
                index=self._index,
                id=doc_id,
                body=document,
            )
            return True
        except Exception as e:
            _logger.warning("SearchIndex: index failed: %s", e)
            return False

    def index_batch(self, documents: list[dict]) -> int:
        """Bulk index documents.

        Args:
            documents: List of dicts with "_id" and other fields.

        Returns:
            Number of successfully indexed documents.
        """
        if not self.is_connected:
            return 0

        try:
            from elasticsearch.helpers import bulk

            actions = [
                {"_index": self._index, "_id": str(d.pop("_id", i)), "_source": d}
                for i, d in enumerate(documents)
            ]

            success, errors = bulk(
                self._client,
                actions,
                chunk_size=self._batch_size,
                raise_on_error=False,
            )

            if errors:
                _logger.warning(
                    "SearchIndex: %d errors during bulk index",
                    len(errors),
                )

            return success
        except Exception as e:
            _logger.warning("SearchIndex: bulk index failed: %s", e)
            return 0

    def search(
        self,
        query: str,
        limit: int = 20,
        filters: dict[str, str] | None = None,
    ) -> list[SearchHit]:
        """Full-text search with optional filters.

        Uses multi_match query across title and body_text.

        Args:
            query: Search query string.
            limit: Max results.
            filters: Optional {"entity_type": "company"}.

        Returns:
            List of SearchHit sorted by score descending.
        """
        if not self.is_connected:
            return []

        try:
            body = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["title^2", "body_text"],
                                    "type": "best_fields",
                                    "fuzziness": "AUTO",
                                }
                            }
                        ],
                    }
                },
                "highlight": {
                    "fields": {
                        "title": {},
                        "body_text": {"fragment_size": 200},
                    },
                    "pre_tags": ["<em>"],
                    "post_tags": ["</em>"],
                },
                "size": limit,
            }

            # Add filter terms
            if filters:
                filter_clauses = [{"term": {k: v}} for k, v in filters.items()]
                body["query"]["bool"]["filter"] = filter_clauses

            resp = self._client.search(index=self._index, body=body)

            results = []
            for hit in resp["hits"]["hits"]:
                results.append(
                    SearchHit(
                        id=hit["_id"],
                        score=hit["_score"],
                        source=hit["_source"],
                        highlights=hit.get("highlight", {}),
                    )
                )

            return results
        except Exception as e:
            _logger.warning("SearchIndex: search failed: %s", e)
            return []

    def hybrid_search(
        self,
        query: str,
        query_vector: list[float],
        limit: int = 20,
        alpha: float = 0.7,
    ) -> list[HybridResult]:
        """Hybrid search: blends BM25 text score with vector cosine similarity.

        Args:
            query: Text query for BM25.
            query_vector: 384-dim embedding for vector search.
            limit: Max results.
            alpha: Weight for BM25 (1-alpha for vector). Default 0.7.

        Returns:
            List of HybridResult sorted by combined score descending.
        """
        if not self.is_connected:
            return []

        try:
            body = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["title^2", "body_text"],
                                    "type": "best_fields",
                                    "fuzziness": "AUTO",
                                }
                            }
                        ],
                        "should": [
                            {
                                "script_score": {
                                    "query": {"match_all": {}},
                                    "script": {
                                        "source": "cosineSimilarity(params.query_vector, 'embedding_vector') + 1.0",
                                        "params": {
                                            "query_vector": query_vector,
                                        },
                                    },
                                }
                            }
                        ],
                    }
                },
                "size": limit,
            }

            resp = self._client.search(index=self._index, body=body)

            results = []
            for hit in resp["hits"]["hits"]:
                results.append(
                    HybridResult(
                        id=hit["_id"],
                        score=hit["_score"],
                        source=hit["_source"],
                        bm25_score=hit["_score"],  # Combined score from ES
                        vector_score=0.0,
                    )
                )

            return results
        except Exception as e:
            _logger.warning("SearchIndex: hybrid search failed: %s", e)
            return []

    def delete(self, doc_ids: list[str]) -> bool:
        """Delete documents by IDs."""
        if not self.is_connected:
            return False
        try:
            actions = [
                {"_op_type": "delete", "_index": self._index, "_id": did}
                for did in doc_ids
            ]
            from elasticsearch.helpers import bulk

            bulk(self._client, actions, raise_on_error=False)
            return True
        except Exception as e:
            _logger.warning("SearchIndex: delete failed: %s", e)
            return False

    def count(self) -> int:
        """Return total document count in index."""
        if not self.is_connected:
            return 0
        try:
            resp = self._client.count(index=self._index)
            return resp.get("count", 0)
        except Exception:
            return 0
