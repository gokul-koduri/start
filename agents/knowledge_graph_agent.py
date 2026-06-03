"""Knowledge Graph Agent — extracts entities and relationships from existing data.

Builds an adjacency-list knowledge graph in MySQL by:
1. Extracting entities from failed_startups, news_articles, revival_industries, geographic_hotspots
2. Using Ollama for entity extraction from free-text fields
3. Resolving entity aliases via normalized names
4. Building typed relationships between entities
5. Storing in kg_entity_types, kg_entities, kg_relationships tables

Runs as part of the analysis and weekly pipelines.
"""

import json
import logging
import re
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

from agents.base import AgentResult, BaseAgent
from db.connection import get_connection
from db import schema

_logger = logging.getLogger(__name__)

# Seed entity types
_SEED_ENTITY_TYPES = [
    ("startup", "Failed or analyzed startup companies", "1F4BC"),
    ("industry", "Industry sectors and sub-sectors", "1F3ED"),
    ("investor", "Investment firms and individual investors", "1F4B0"),
    ("region", "Geographic regions and countries", "1F30D"),
    ("sector", "Business sectors (technology, healthcare, etc.)", "1F4CA"),
    ("failure_reason", "Categorized failure reasons", "26A0"),
    ("technology", "Technologies mentioned in startup descriptions", "1F527"),
]


def _normalize_name(name: str) -> str:
    """Normalize entity name for deduplication."""
    return re.sub(r"[^a-z0-9]", "", name.lower().strip())


class KnowledgeGraphAgent(BaseAgent):
    """Agent that extracts entities and relationships into a knowledge graph.

    Config options:
        ollama_url: Ollama API endpoint (default: http://localhost:11434/api/chat)
        ollama_model: model name (default: llama3)
        delay_seconds: delay between Ollama calls for news extraction (default: 1.0)
        batch_size: number of news articles to process per batch (default: 50)
    """

    @property
    def name(self) -> str:
        return "knowledge_graph"

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        try:
            conn = get_connection()
            schema.init_schema(conn)
        except Exception as e:
            return AgentResult(agent_name=self.name, status="failed", errors=[str(e)])

        total_entities = 0
        total_relationships = 0
        errors = []

        try:
            # Step 1: Seed entity types
            type_map = self._seed_entity_types(conn)

            # Step 2: Extract from failed_startups (structured, no Ollama)
            rels = self._extract_from_failed_startups(conn, type_map)
            total_relationships += rels
            _logger.info("KnowledgeGraphAgent: failed_startups → %d relationships", rels)

            # Step 3: Extract from revival_industries (structured, no Ollama)
            rels = self._extract_from_revival_industries(conn, type_map)
            total_relationships += rels
            _logger.info("KnowledgeGraphAgent: revival_industries → %d relationships", rels)

            # Step 4: Extract from geographic_hotspots (structured, no Ollama)
            rels = self._extract_from_geographic_hotspots(conn, type_map)
            total_relationships += rels
            _logger.info("KnowledgeGraphAgent: geographic_hotspots → %d relationships", rels)

            # Step 5: Extract from news_articles (Ollama-assisted for text)
            delay = float(self.config.get("delay_seconds", 1.0))
            batch_size = int(self.config.get("batch_size", 50))
            rels = self._extract_from_news_articles(conn, type_map, delay, batch_size)
            total_relationships += rels
            _logger.info("KnowledgeGraphAgent: news_articles → %d relationships", rels)

            # Step 6: Build cross-entity relationships
            rels = self._build_cross_relationships(conn, type_map)
            total_relationships += rels
            _logger.info("KnowledgeGraphAgent: cross-relationships → %d relationships", rels)

            # Count totals
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as cnt FROM kg_entities")
            total_entities = cursor.fetchone()["cnt"]
            cursor.execute("SELECT COUNT(*) as cnt FROM kg_relationships")
            total_relationships_final = cursor.fetchone()["cnt"]
            cursor.close()
            total_relationships = total_relationships_final

            conn.close()

        except Exception as e:
            errors.append(str(e))
            _logger.error("KnowledgeGraphAgent: Error: %s", e)
            try:
                conn.close()
            except Exception:
                pass
            return AgentResult(agent_name=self.name, status="failed", errors=errors)

        _logger.info(
            "KnowledgeGraphAgent: Done — %d entities, %d relationships",
            total_entities, total_relationships,
        )

        return AgentResult(
            agent_name=self.name,
            status="success" if not errors else "partial",
            data={
                "total_entities": total_entities,
                "total_relationships": total_relationships,
                "records_affected": total_entities + total_relationships,
            },
            errors=errors,
        )

    # ── Entity type seeding ──

    def _seed_entity_types(self, conn) -> dict[str, int]:
        """Ensure entity type rows exist. Returns {type_name: id} mapping."""
        cursor = conn.cursor()
        type_map = {}
        for type_name, description, icon in _SEED_ENTITY_TYPES:
            cursor.execute(
                """INSERT INTO kg_entity_types (type_name, description, icon)
                   VALUES (%s, %s, %s)
                   ON DUPLICATE KEY UPDATE description = VALUES(description)""",
                (type_name, description, icon),
            )
            cursor.execute("SELECT id FROM kg_entity_types WHERE type_name = %s", (type_name,))
            type_map[type_name] = cursor.fetchone()["id"]
        conn.commit()
        cursor.close()
        return type_map

    # ── Entity and relationship upserts ──

    def _upsert_entity(self, cursor, name: str, normalized: str, type_id: int,
                        attributes: dict | None = None) -> int:
        """Upsert an entity and return its ID."""
        attrs_json = json.dumps(attributes, default=str) if attributes else None
        cursor.execute(
            """INSERT INTO kg_entities (name, normalized_name, entity_type_id, attributes_json, mention_count)
               VALUES (%s, %s, %s, %s, 1)
               ON DUPLICATE KEY UPDATE
                 mention_count = mention_count + 1,
                 attributes_json = COALESCE(kg_entities.attributes_json, VALUES(attributes_json))""",
            (name, normalized, type_id, attrs_json),
        )
        cursor.execute(
            "SELECT id FROM kg_entities WHERE entity_type_id = %s AND normalized_name = %s",
            (type_id, normalized),
        )
        return cursor.fetchone()["id"]

    def _upsert_relationship(self, cursor, source_id: int, target_id: int,
                              rel_type: str, weight: float = 1.0,
                              source_table: str | None = None,
                              source_record_id: int | None = None) -> None:
        """Upsert a relationship between two entities."""
        cursor.execute(
            """INSERT INTO kg_relationships
               (source_entity_id, target_entity_id, relationship_type, weight, source_table, source_record_id)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE weight = VALUES(weight)""",
            (source_id, target_id, rel_type, weight, source_table, source_record_id),
        )

    # ── Structured extraction: failed_startups ──

    def _extract_from_failed_startups(self, conn, type_map: dict[str, int]) -> int:
        """Extract entities and relationships from failed_startups table."""
        cursor = conn.cursor()
        cursor.execute(
            """SELECT id, name, sector, manufacturing_sub_sector, country, region,
                      failure_category, funding_raised_usd
               FROM failed_startups"""
        )
        rows = cursor.fetchall()
        relationships = 0

        for row in rows:
            r = dict(row)
            startup_name = r["name"]
            if not startup_name:
                continue

            startup_id = self._upsert_entity(
                cursor, startup_name, _normalize_name(startup_name),
                type_map["startup"],
                {"funding_raised_usd": r["funding_raised_usd"], "source_id": r["id"]},
            )

            # operates_in_sector
            if r["sector"]:
                sector_id = self._upsert_entity(
                    cursor, r["sector"], _normalize_name(r["sector"]),
                    type_map["sector"],
                )
                self._upsert_relationship(cursor, startup_id, sector_id, "operates_in_sector",
                                           source_table="failed_startups", source_record_id=r["id"])
                relationships += 1

            # located_in
            location = r["region"] or r["country"]
            if location:
                loc_id = self._upsert_entity(
                    cursor, location, _normalize_name(location),
                    type_map["region"],
                )
                self._upsert_relationship(cursor, startup_id, loc_id, "located_in",
                                           source_table="failed_startups", source_record_id=r["id"])
                relationships += 1

            # failed_with_reason
            if r["failure_category"]:
                reason_id = self._upsert_entity(
                    cursor, r["failure_category"], _normalize_name(r["failure_category"]),
                    type_map["failure_reason"],
                )
                self._upsert_relationship(cursor, startup_id, reason_id, "failed_with_reason",
                                           source_table="failed_startups", source_record_id=r["id"])
                relationships += 1

            # operates_in (industry sub-sector)
            if r["manufacturing_sub_sector"]:
                industry_id = self._upsert_entity(
                    cursor, r["manufacturing_sub_sector"],
                    _normalize_name(r["manufacturing_sub_sector"]),
                    type_map["industry"],
                )
                self._upsert_relationship(cursor, startup_id, industry_id, "operates_in",
                                           source_table="failed_startups", source_record_id=r["id"])
                relationships += 1

        conn.commit()
        cursor.close()
        return relationships

    # ── Structured extraction: revival_industries ──

    def _extract_from_revival_industries(self, conn, type_map: dict[str, int]) -> int:
        """Extract entities and relationships from revival_industries table."""
        cursor = conn.cursor()
        cursor.execute("SELECT id, industry, why_returning, market_fit, market_size_2030, key_investors FROM revival_industries")
        rows = cursor.fetchall()
        relationships = 0

        for row in rows:
            r = dict(row)
            industry_name = r["industry"]
            if not industry_name:
                continue

            industry_id = self._upsert_entity(
                cursor, industry_name, _normalize_name(industry_name),
                type_map["industry"],
                {"why_returning": r["why_returning"], "market_fit": r["market_fit"],
                 "market_size_2030": r["market_size_2030"], "source_id": r["id"]},
            )

            # Extract investors as entities
            investors = r.get("key_investors", "")
            if investors:
                for inv_name in re.split(r"[,;]", investors):
                    inv_name = inv_name.strip()
                    if len(inv_name) < 2:
                        continue
                    inv_id = self._upsert_entity(
                        cursor, inv_name, _normalize_name(inv_name),
                        type_map["investor"],
                    )
                    self._upsert_relationship(cursor, inv_id, industry_id, "invested_in",
                                               source_table="revival_industries", source_record_id=r["id"])
                    relationships += 1

        conn.commit()
        cursor.close()
        return relationships

    # ── Structured extraction: geographic_hotspots ──

    def _extract_from_geographic_hotspots(self, conn, type_map: dict[str, int]) -> int:
        """Extract entities and relationships from geographic_hotspots table."""
        cursor = conn.cursor()
        cursor.execute("SELECT id, region, closed_facility_types, revival_potential FROM geographic_hotspots")
        rows = cursor.fetchall()
        relationships = 0

        for row in rows:
            r = dict(row)
            region_name = r["region"]
            if not region_name:
                continue

            region_id = self._upsert_entity(
                cursor, region_name, _normalize_name(region_name),
                type_map["region"],
                {"revival_potential": r["revival_potential"], "source_id": r["id"]},
            )

            # Extract facility types as industry entities
            facilities = r.get("closed_facility_types", "")
            if facilities:
                for fac in re.split(r"[,;]", facilities):
                    fac = fac.strip()
                    if len(fac) < 2:
                        continue
                    fac_id = self._upsert_entity(
                        cursor, fac, _normalize_name(fac),
                        type_map["industry"],
                    )
                    self._upsert_relationship(cursor, region_id, fac_id, "hotspot_region",
                                               source_table="geographic_hotspots", source_record_id=r["id"])
                    relationships += 1

        conn.commit()
        cursor.close()
        return relationships

    # ── Ollama-assisted extraction: news_articles ──

    def _extract_from_news_articles(self, conn, type_map: dict[str, int],
                                      delay: float, batch_size: int) -> int:
        """Extract entities from news_articles using Ollama NER on summary text."""
        cursor = conn.cursor()
        cursor.execute(
            """SELECT id, title, summary, startup_name_extracted
               FROM news_articles
               WHERE summary IS NOT NULL AND LENGTH(summary) > 20"""
        )
        rows = cursor.fetchall()
        relationships = 0

        for i, row in enumerate(rows):
            r = dict(row)

            # First, use already-extracted startup name (structured)
            if r.get("startup_name_extracted"):
                startup_id = self._upsert_entity(
                    cursor, r["startup_name_extracted"],
                    _normalize_name(r["startup_name_extracted"]),
                    type_map["startup"],
                    {"source_id": r["id"]},
                )
                self._upsert_relationship(cursor, startup_id, startup_id, "mentioned_in_news",
                                           source_table="news_articles", source_record_id=r["id"])
                relationships += 1

            # Then, use Ollama to extract additional entities from summary
            if i % batch_size == 0 and i > 0:
                conn.commit()
                _logger.info("KnowledgeGraphAgent: news batch %d/%d", i, len(rows))

            entities = self._extract_entities_from_text(r.get("summary", ""))
            for ent in entities:
                ent_name = ent.get("name", "")
                ent_type = ent.get("type", "")
                kg_type = self._map_ner_type_to_kg_type(ent_type)
                if not kg_type or len(ent_name) < 2:
                    continue
                ent_id = self._upsert_entity(
                    cursor, ent_name, _normalize_name(ent_name),
                    type_map[kg_type],
                )
                # Link the entity to the news mention
                self._upsert_relationship(cursor, ent_id, ent_id, "mentioned_in_news",
                                           source_table="news_articles", source_record_id=r["id"])
                relationships += 1

            if delay > 0 and i > 0 and i % 10 == 0:
                time.sleep(delay)

        conn.commit()
        cursor.close()
        return relationships

    def _map_ner_type_to_kg_type(self, ner_type: str) -> str | None:
        """Map NER type from Ollama to knowledge graph entity type."""
        mapping = {
            "startup": "startup",
            "company": "startup",
            "investor": "investor",
            "technology": "technology",
            "industry": "industry",
            "location": "region",
            "region": "region",
        }
        return mapping.get(ner_type.lower())

    def _extract_entities_from_text(self, text: str) -> list[dict]:
        """Use Ollama to extract named entities from text."""
        if not text or len(text) < 20:
            return []

        url = self.config.get("ollama_url", "http://localhost:11434/api/chat")
        model = self.config.get("ollama_model", "llama3")
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Extract named entities from the text. For each entity, classify as one of: "
                        "startup, investor, technology, industry, location. "
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
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode())
            content = result.get("message", {}).get("content", "")
        except Exception:
            return []

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
            return []

    # ── Cross-entity relationships ──

    def _build_cross_relationships(self, conn, type_map: dict[str, int]) -> int:
        """Build derived relationships between existing entities."""
        cursor = conn.cursor()
        relationships = 0

        # Sectors that share failure categories (competing_sectors)
        cursor.execute(
            """SELECT fs.sector, fs.failure_category, COUNT(*) as cnt
               FROM failed_startups fs
               WHERE fs.sector IS NOT NULL AND fs.failure_category IS NOT NULL
               GROUP BY fs.sector, fs.failure_category
               HAVING cnt >= 2
               ORDER BY cnt DESC"""
        )
        sector_pairs = cursor.fetchall()
        for sp in sector_pairs:
            sector_id = self._upsert_entity(
                cursor, sp["sector"], _normalize_name(sp["sector"]),
                type_map["sector"],
            )
            cat_id = self._upsert_entity(
                cursor, sp["failure_category"], _normalize_name(sp["failure_category"]),
                type_map["failure_reason"],
            )
            self._upsert_relationship(cursor, sector_id, cat_id, "shares_failure_pattern",
                                       weight=float(sp["cnt"]))
            relationships += 1

        conn.commit()
        cursor.close()
        return relationships
