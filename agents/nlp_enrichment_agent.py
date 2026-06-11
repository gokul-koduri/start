"""NLP Enrichment Agent — enriches raw signals with NLP-derived data.

Processes unprocessed raw_signals through:
1. Entity extraction (spaCy NER, fallback Ollama)
2. Signal classification (type + sentiment)
3. Embedding generation (all-MiniLM-L6-v2, 384-dim)
4. Storage in vector_embeddings table
5. Indexing in Qdrant (vector) + Elasticsearch (full-text)

Runs as part of the analysis pipeline.
"""

import json
import logging

from agents.base import AgentResult, BaseAgent
from db.connection import get_connection
from db import schema

_logger = logging.getLogger(__name__)


class NLPEnrichmentAgent(BaseAgent):
    """Agent that enriches raw signals with NLP-derived metadata.

    Config options:
        batch_size: signals per batch (default: 50)
        embedding_batch_size: embeddings to generate at once (default: 32)
        skip_text_shorter_than: minimum text length for NLP (default: 10)
        store_embeddings: whether to generate/store embeddings (default: true)
        index_search: whether to index in Qdrant/ES (default: true)
    """

    @property
    def name(self) -> str:
        return "nlp_enrichment"

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        try:
            conn = get_connection()
            schema.init_schema(conn)
        except Exception as e:
            return AgentResult(agent_name=self.name, status="failed", errors=[str(e)])

        batch_size = int(self.config.get("batch_size", 50))
        int(self.config.get("embedding_batch_size", 32))
        min_text_len = int(self.config.get("skip_text_shorter_than", 10))
        do_embeddings = self.config.get("store_embeddings", True)
        do_search_index = self.config.get("index_search", True)

        total_processed = 0
        total_entities = 0
        total_embeddings = 0
        total_indexed = 0
        errors = []

        # Lazy-load NLP components
        extractor = None
        classifier = None
        embedder = None
        vector_store = None
        search_index = None

        try:
            from nlp.entity_extractor import UnifiedEntityExtractor

            extractor = UnifiedEntityExtractor()
            _logger.info("NLPEnrichmentAgent: entity extractor ready")
        except Exception as e:
            errors.append(f"Entity extractor unavailable: {e}")
            _logger.warning("NLPEnrichmentAgent: %s", e)

        try:
            from nlp.text_classifier import SignalTextClassifier

            classifier = SignalTextClassifier()
        except Exception as e:
            errors.append(f"Text classifier unavailable: {e}")
            _logger.warning("NLPEnrichmentAgent: %s", e)

        if do_embeddings:
            try:
                from nlp.embedding_generator import EmbeddingGenerator

                embedder = EmbeddingGenerator()
                embedder.load()
                _logger.info(
                    "NLPEnrichmentAgent: embedding generator loaded (dim=%d)",
                    embedder.dimension,
                )
            except Exception as e:
                errors.append(f"Embedding generator unavailable: {e}")
                _logger.warning("NLPEnrichmentAgent: %s", e)

        if do_search_index:
            try:
                from db.vector_store import VectorStore

                vs_config = self.config.get("qdrant", {})
                vector_store = VectorStore(vs_config)
                vector_store.connect()
                _logger.info(
                    "NLPEnrichmentAgent: vector store %s",
                    "connected" if vector_store.is_connected else "unavailable",
                )
            except Exception as e:
                _logger.warning("NLPEnrichmentAgent: vector store unavailable: %s", e)

            try:
                from db.search_index import SearchIndex

                si_config = self.config.get("elasticsearch", {})
                search_index = SearchIndex(si_config)
                search_index.connect()
                _logger.info(
                    "NLPEnrichmentAgent: search index %s",
                    "connected" if search_index.is_connected else "unavailable",
                )
            except Exception as e:
                _logger.warning("NLPEnrichmentAgent: search index unavailable: %s", e)

        try:
            cursor = conn.cursor()

            # Fetch unprocessed raw_signals
            cursor.execute(
                """SELECT id, signal_type, title, body_text, source_name, collected_at
                   FROM raw_signals
                   WHERE processed = 0
                   ORDER BY collected_at DESC
                   LIMIT %s""",
                (batch_size,),
            )
            signals = cursor.fetchall()

            if not signals:
                _logger.info("NLPEnrichmentAgent: no unprocessed signals")
                conn.close()
                return AgentResult(
                    agent_name=self.name,
                    status="success",
                    data={
                        "processed": 0,
                        "entities_extracted": 0,
                        "embeddings_stored": 0,
                    },
                )

            _logger.info("NLPEnrichmentAgent: processing %d signals", len(signals))

            for sig in signals:
                sig_id = sig["id"]
                text_parts = []
                if sig.get("title"):
                    text_parts.append(sig["title"])
                if sig.get("body_text"):
                    text_parts.append(sig["body_text"])
                full_text = " ".join(text_parts).strip()

                if len(full_text) < min_text_len:
                    # Mark processed even if too short
                    self._mark_processed(cursor, sig_id, {})
                    total_processed += 1
                    continue

                enrichment = {}

                # 1. Entity extraction
                if extractor:
                    try:
                        entities = extractor.extract(full_text)
                        enrichment["entities"] = entities
                        total_entities += len(entities)
                    except Exception as e:
                        _logger.warning(
                            "NLPEnrichmentAgent: entity extraction failed for signal %d: %s",
                            sig_id,
                            e,
                        )

                # 2. Classification
                if classifier:
                    try:
                        sig_type, sig_conf = classifier.classify_signal_type(full_text)
                        sent_label, sent_score = classifier.classify_sentiment(
                            full_text
                        )
                        enrichment["signal_type_nlp"] = sig_type
                        enrichment["signal_type_confidence"] = round(sig_conf, 3)
                        enrichment["sentiment_label"] = sent_label
                        enrichment["sentiment_score"] = round(sent_score, 3)
                    except Exception as e:
                        _logger.warning(
                            "NLPEnrichmentAgent: classification failed for signal %d: %s",
                            sig_id,
                            e,
                        )

                # 3. Embedding
                if embedder:
                    try:
                        vector = embedder.embed_text(full_text)
                        enrichment["embedding_dim"] = len(vector)

                        # Store in vector_embeddings table
                        cursor.execute(
                            """INSERT INTO vector_embeddings
                               (entity_name, entity_type, content_text, vector_data, created_at)
                               VALUES (%s, %s, %s, %s, NOW())""",
                            (
                                sig.get("source_name", ""),
                                sig.get("signal_type", ""),
                                full_text[:2000],
                                json.dumps(vector),
                            ),
                        )
                        ve_id = cursor.lastrowid
                        enrichment["vector_embedding_id"] = ve_id
                        total_embeddings += 1

                        # Index in Qdrant
                        if vector_store and vector_store.is_connected:
                            payload = {
                                "signal_id": sig_id,
                                "signal_type": sig.get("signal_type", ""),
                                "source_name": sig.get("source_name", ""),
                                "title": sig.get("title", "")[:500],
                                "collected_at": str(sig.get("collected_at", "")),
                            }
                            vector_store.upsert(
                                point_id=f"signal_{sig_id}",
                                vector=vector,
                                payload=payload,
                            )

                        # Index in Elasticsearch
                        if search_index and search_index.is_connected:
                            doc = {
                                "signal_id": sig_id,
                                "signal_type": sig.get("signal_type", ""),
                                "entity_name": sig.get("source_name", ""),
                                "title": sig.get("title", ""),
                                "body_text": full_text[:5000],
                                "published_at": str(sig.get("collected_at", "")),
                            }
                            search_index.index_document(
                                doc_id=f"signal_{sig_id}", document=doc
                            )
                            total_indexed += 1

                    except Exception as e:
                        _logger.warning(
                            "NLPEnrichmentAgent: embedding failed for signal %d: %s",
                            sig_id,
                            e,
                        )

                # Mark signal as processed
                self._mark_processed(cursor, sig_id, enrichment)
                total_processed += 1

            conn.commit()

        except Exception as e:
            _logger.error("NLPEnrichmentAgent: processing error: %s", e)
            errors.append(str(e))
        finally:
            if conn:
                conn.close()

        status = "success" if not errors else "partial"
        return AgentResult(
            agent_name=self.name,
            status=status,
            data={
                "processed": total_processed,
                "entities_extracted": total_entities,
                "embeddings_stored": total_embeddings,
                "indexed_search": total_indexed,
            },
            errors=errors,
        )

    def _mark_processed(self, cursor, sig_id: int, enrichment: dict):
        """Mark a signal as processed and store enrichment metadata."""
        result_data = json.dumps(enrichment, default=str)[:2000] if enrichment else None
        cursor.execute(
            """UPDATE raw_signals SET processed = 1, result_data = %s WHERE id = %s""",
            (result_data, sig_id),
        )
