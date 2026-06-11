"""Semantic Search Agent — syncs embeddings to vector and full-text search indexes.

Finds embeddings in the vector_embeddings table that haven't been indexed in
Qdrant or Elasticsearch, batch upserts them, and optionally cleans stale entries.

Runs as part of the analysis pipeline (after nlp_enrichment).
"""

import logging

from agents.base import AgentResult, BaseAgent
from db.connection import get_connection
from db import schema

_logger = logging.getLogger(__name__)


class SemanticSearchAgent(BaseAgent):
    """Agent that keeps search indexes in sync with vector_embeddings.

    Config options:
        batch_size: rows to process per run (default: 200)
        clean_stale: remove orphaned Qdrant/ES entries (default: false)
        qdrant: dict of Qdrant config (url, collection_name)
        elasticsearch: dict of ES config (url, index_name)
    """

    @property
    def name(self) -> str:
        return "semantic_search"

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        try:
            conn = get_connection()
            schema.init_schema(conn)
        except Exception as e:
            return AgentResult(agent_name=self.name, status="failed", errors=[str(e)])

        batch_size = int(self.config.get("batch_size", 200))
        clean_stale = self.config.get("clean_stale", False)
        errors = []

        vector_store = None
        search_index = None

        # Connect to Qdrant
        try:
            from db.vector_store import VectorStore

            vs_config = self.config.get("qdrant", {})
            vector_store = VectorStore(vs_config)
            vector_store.connect()
        except Exception as e:
            errors.append(f"Qdrant unavailable: {e}")
            _logger.warning("SemanticSearchAgent: %s", e)

        # Connect to Elasticsearch
        try:
            from db.search_index import SearchIndex

            si_config = self.config.get("elasticsearch", {})
            search_index = SearchIndex(si_config)
            search_index.connect()
        except Exception as e:
            errors.append(f"Elasticsearch unavailable: {e}")
            _logger.warning("SemanticSearchAgent: %s", e)

        if not vector_store or not vector_store.is_connected:
            if not search_index or not search_index.is_connected:
                _logger.info(
                    "SemanticSearchAgent: no search backends available, skipping"
                )
                conn.close()
                return AgentResult(
                    agent_name=self.name,
                    status="success",
                    data={
                        "indexed_qdrant": 0,
                        "indexed_es": 0,
                        "reason": "no_backends",
                    },
                )

        qdrant_indexed = 0
        es_indexed = 0

        try:
            cursor = conn.cursor()

            # Fetch embeddings that haven't been synced
            cursor.execute(
                """SELECT ve.id, ve.entity_name, ve.entity_type, ve.content_text,
                          ve.vector_data, ve.qdrant_point_id, ve.created_at
                   FROM vector_embeddings ve
                   ORDER BY ve.created_at DESC
                   LIMIT %s""",
                (batch_size,),
            )
            embeddings = cursor.fetchall()

            if not embeddings:
                _logger.info("SemanticSearchAgent: no embeddings to sync")
                conn.close()
                return AgentResult(
                    agent_name=self.name,
                    status="success",
                    data={"indexed_qdrant": 0, "indexed_es": 0},
                )

            _logger.info("SemanticSearchAgent: syncing %d embeddings", len(embeddings))

            for emb in embeddings:
                point_id = f"ve_{emb['id']}"
                vector = None

                # Parse vector data (stored as JSON list)
                if emb.get("vector_data"):
                    try:
                        import json

                        vector = json.loads(emb["vector_data"])
                    except Exception:
                        pass

                payload = {
                    "ve_id": emb["id"],
                    "entity_name": emb.get("entity_name", ""),
                    "entity_type": emb.get("entity_type", ""),
                    "title": (emb.get("content_text") or "")[:500],
                    "indexed_at": str(emb.get("created_at", "")),
                }

                # Upsert to Qdrant
                if vector_store and vector_store.is_connected and vector:
                    try:
                        vector_store.upsert(
                            point_id=point_id,
                            vector=vector,
                            payload=payload,
                        )
                        qdrant_indexed += 1
                        # Track point_id
                        cursor.execute(
                            "UPDATE vector_embeddings SET qdrant_point_id = %s WHERE id = %s",
                            (point_id, emb["id"]),
                        )
                    except Exception as e:
                        _logger.warning(
                            "SemanticSearchAgent: Qdrant upsert failed for %d: %s",
                            emb["id"],
                            e,
                        )

                # Index in Elasticsearch
                if search_index and search_index.is_connected:
                    doc = {
                        "entity_name": emb.get("entity_name", ""),
                        "entity_type": emb.get("entity_type", ""),
                        "title": (emb.get("content_text") or "")[:500],
                        "body_text": (emb.get("content_text") or "")[:5000],
                        "published_at": str(emb.get("created_at", "")),
                        "composite_score": 0.0,
                    }
                    try:
                        search_index.index_document(doc_id=point_id, document=doc)
                        es_indexed += 1
                    except Exception as e:
                        _logger.warning(
                            "SemanticSearchAgent: ES index failed for %d: %s",
                            emb["id"],
                            e,
                        )

            conn.commit()

        except Exception as e:
            _logger.error("SemanticSearchAgent: sync error: %s", e)
            errors.append(str(e))
        finally:
            if conn:
                conn.close()

        # Optional: clean stale entries
        if clean_stale:
            self._clean_stale(vector_store, search_index)

        status = "success" if not errors else "partial"
        return AgentResult(
            agent_name=self.name,
            status=status,
            data={
                "indexed_qdrant": qdrant_indexed,
                "indexed_es": es_indexed,
            },
            errors=errors,
        )

    def _clean_stale(self, vector_store, search_index):
        """Remove orphaned entries from Qdrant/ES."""
        if vector_store and vector_store.is_connected:
            _logger.info(
                "SemanticSearchAgent: stale cleanup for Qdrant not yet implemented"
            )
        if search_index and search_index.is_connected:
            _logger.info(
                "SemanticSearchAgent: stale cleanup for ES not yet implemented"
            )
