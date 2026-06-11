"""Knowledge Graph Agent — extracts entities and relationships from existing data.

Builds an adjacency-list knowledge graph in MySQL by:
1. Extracting entities from failed_startups, news_articles, revival_industries,
   geographic_hotspots, funding_events, sec_filings, job_postings, github_trends,
   patent_filings
2. Using spaCy for entity extraction from free-text fields (Phase 2)
3. Resolving entity aliases via kg_entity_aliases table
4. Building typed relationships between entities (20 relationship types)
5. Storing in kg_entity_types, kg_entities, kg_relationships tables

Runs as part of the analysis and weekly pipelines.
"""

import json
import logging
import re
import time
import urllib.request
import urllib.error

from agents.base import AgentResult, BaseAgent
from db.connection import get_connection
from db import schema

_logger = logging.getLogger(__name__)

# Seed entity types (7 existing + 5 new in Phase 2)
_SEED_ENTITY_TYPES = [
    # Existing 7
    ("startup", "Failed or analyzed startup companies", "1F4BC"),
    ("industry", "Industry sectors and sub-sectors", "1F3ED"),
    ("investor", "Investment firms and individual investors", "1F4B0"),
    ("region", "Geographic regions and countries", "1F30D"),
    ("sector", "Business sectors (technology, healthcare, etc.)", "1F4CA"),
    ("failure_reason", "Categorized failure reasons", "26A0"),
    ("technology", "Technologies mentioned in startup descriptions", "1F527"),
    # Phase 2: 5 new types
    ("person", "Founders, CEOs, executives, board members", "1F464"),
    ("product", "Products and services offered by companies", "1F4E6"),
    ("market", "Target markets and market segments", "1F4C8"),
    ("patent", "Patent filings and IP documents", "1F4DC"),
    ("regulation", "Regulatory frameworks and compliance requirements", "2696"),
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
            _logger.info(
                "KnowledgeGraphAgent: failed_startups → %d relationships", rels
            )

            # Step 3: Extract from revival_industries (structured, no Ollama)
            rels = self._extract_from_revival_industries(conn, type_map)
            total_relationships += rels
            _logger.info(
                "KnowledgeGraphAgent: revival_industries → %d relationships", rels
            )

            # Step 4: Extract from geographic_hotspots (structured, no Ollama)
            rels = self._extract_from_geographic_hotspots(conn, type_map)
            total_relationships += rels
            _logger.info(
                "KnowledgeGraphAgent: geographic_hotspots → %d relationships", rels
            )

            # Step 5: Extract from news_articles (Ollama-assisted for text)
            delay = float(self.config.get("delay_seconds", 1.0))
            batch_size = int(self.config.get("batch_size", 50))
            rels = self._extract_from_news_articles(conn, type_map, delay, batch_size)
            total_relationships += rels
            _logger.info("KnowledgeGraphAgent: news_articles → %d relationships", rels)

            # Step 5a: Extract from funding_events (structured)
            rels = self._extract_from_funding_events(conn, type_map)
            total_relationships += rels
            _logger.info("KnowledgeGraphAgent: funding_events → %d relationships", rels)

            # Step 5b: Extract from sec_filings (structured + NER)
            rels = self._extract_from_sec_filings(conn, type_map)
            total_relationships += rels
            _logger.info("KnowledgeGraphAgent: sec_filings → %d relationships", rels)

            # Step 5c: Extract from job_postings (structured)
            rels = self._extract_from_job_postings(conn, type_map)
            total_relationships += rels
            _logger.info("KnowledgeGraphAgent: job_postings → %d relationships", rels)

            # Step 5d: Extract from github_trends (structured)
            rels = self._extract_from_github_trends(conn, type_map)
            total_relationships += rels
            _logger.info("KnowledgeGraphAgent: github_trends → %d relationships", rels)

            # Step 5e: Extract from patent_filings (structured)
            rels = self._extract_from_patent_filings(conn, type_map)
            total_relationships += rels
            _logger.info("KnowledgeGraphAgent: patent_filings → %d relationships", rels)

            # Step 6: Build cross-entity relationships
            rels = self._build_cross_relationships(conn, type_map)
            total_relationships += rels
            _logger.info(
                "KnowledgeGraphAgent: cross-relationships → %d relationships", rels
            )

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
            total_entities,
            total_relationships,
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
            cursor.execute(
                "SELECT id FROM kg_entity_types WHERE type_name = %s", (type_name,)
            )
            type_map[type_name] = cursor.fetchone()["id"]
        conn.commit()
        cursor.close()
        return type_map

    # ── Entity and relationship upserts ──

    def _upsert_entity(
        self,
        cursor,
        name: str,
        normalized: str,
        type_id: int,
        attributes: dict | None = None,
    ) -> int:
        """Upsert an entity and return its ID.

        Phase 2 enhancement: checks kg_entity_aliases first. If an alias
        exists for this normalized name, returns the canonical entity ID
        instead of creating a duplicate.
        """
        # Phase 2: check alias table before inserting
        try:
            cursor.execute(
                "SELECT canonical_entity_id FROM kg_entity_aliases WHERE normalized_alias = %s",
                (normalized,),
            )
            alias_row = cursor.fetchone()
            if alias_row:
                canonical_id = alias_row["canonical_entity_id"]
                cursor.execute(
                    "UPDATE kg_entities SET mention_count = mention_count + 1 WHERE id = %s",
                    (canonical_id,),
                )
                return canonical_id
        except Exception:
            pass  # kg_entity_aliases table may not exist in older schemas

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

    def _upsert_relationship(
        self,
        cursor,
        source_id: int,
        target_id: int,
        rel_type: str,
        weight: float = 1.0,
        source_table: str | None = None,
        source_record_id: int | None = None,
    ) -> None:
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
                cursor,
                startup_name,
                _normalize_name(startup_name),
                type_map["startup"],
                {"funding_raised_usd": r["funding_raised_usd"], "source_id": r["id"]},
            )

            # operates_in_sector
            if r["sector"]:
                sector_id = self._upsert_entity(
                    cursor,
                    r["sector"],
                    _normalize_name(r["sector"]),
                    type_map["sector"],
                )
                self._upsert_relationship(
                    cursor,
                    startup_id,
                    sector_id,
                    "operates_in_sector",
                    source_table="failed_startups",
                    source_record_id=r["id"],
                )
                relationships += 1

            # located_in
            location = r["region"] or r["country"]
            if location:
                loc_id = self._upsert_entity(
                    cursor,
                    location,
                    _normalize_name(location),
                    type_map["region"],
                )
                self._upsert_relationship(
                    cursor,
                    startup_id,
                    loc_id,
                    "located_in",
                    source_table="failed_startups",
                    source_record_id=r["id"],
                )
                relationships += 1

            # failed_with_reason
            if r["failure_category"]:
                reason_id = self._upsert_entity(
                    cursor,
                    r["failure_category"],
                    _normalize_name(r["failure_category"]),
                    type_map["failure_reason"],
                )
                self._upsert_relationship(
                    cursor,
                    startup_id,
                    reason_id,
                    "failed_with_reason",
                    source_table="failed_startups",
                    source_record_id=r["id"],
                )
                relationships += 1

            # operates_in (industry sub-sector)
            if r["manufacturing_sub_sector"]:
                industry_id = self._upsert_entity(
                    cursor,
                    r["manufacturing_sub_sector"],
                    _normalize_name(r["manufacturing_sub_sector"]),
                    type_map["industry"],
                )
                self._upsert_relationship(
                    cursor,
                    startup_id,
                    industry_id,
                    "operates_in",
                    source_table="failed_startups",
                    source_record_id=r["id"],
                )
                relationships += 1

        conn.commit()
        cursor.close()
        return relationships

    # ── Structured extraction: revival_industries ──

    def _extract_from_revival_industries(self, conn, type_map: dict[str, int]) -> int:
        """Extract entities and relationships from revival_industries table."""
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, industry, why_returning, market_fit, market_size_2030, key_investors FROM revival_industries"
        )
        rows = cursor.fetchall()
        relationships = 0

        for row in rows:
            r = dict(row)
            industry_name = r["industry"]
            if not industry_name:
                continue

            industry_id = self._upsert_entity(
                cursor,
                industry_name,
                _normalize_name(industry_name),
                type_map["industry"],
                {
                    "why_returning": r["why_returning"],
                    "market_fit": r["market_fit"],
                    "market_size_2030": r["market_size_2030"],
                    "source_id": r["id"],
                },
            )

            # Extract investors as entities
            investors = r.get("key_investors", "")
            if investors:
                for inv_name in re.split(r"[,;]", investors):
                    inv_name = inv_name.strip()
                    if len(inv_name) < 2:
                        continue
                    inv_id = self._upsert_entity(
                        cursor,
                        inv_name,
                        _normalize_name(inv_name),
                        type_map["investor"],
                    )
                    self._upsert_relationship(
                        cursor,
                        inv_id,
                        industry_id,
                        "invested_in",
                        source_table="revival_industries",
                        source_record_id=r["id"],
                    )
                    relationships += 1

        conn.commit()
        cursor.close()
        return relationships

    # ── Structured extraction: geographic_hotspots ──

    def _extract_from_geographic_hotspots(self, conn, type_map: dict[str, int]) -> int:
        """Extract entities and relationships from geographic_hotspots table."""
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, region, closed_facility_types, revival_potential FROM geographic_hotspots"
        )
        rows = cursor.fetchall()
        relationships = 0

        for row in rows:
            r = dict(row)
            region_name = r["region"]
            if not region_name:
                continue

            region_id = self._upsert_entity(
                cursor,
                region_name,
                _normalize_name(region_name),
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
                        cursor,
                        fac,
                        _normalize_name(fac),
                        type_map["industry"],
                    )
                    self._upsert_relationship(
                        cursor,
                        region_id,
                        fac_id,
                        "hotspot_region",
                        source_table="geographic_hotspots",
                        source_record_id=r["id"],
                    )
                    relationships += 1

        conn.commit()
        cursor.close()
        return relationships

    # ── Ollama-assisted extraction: news_articles ──

    def _extract_from_news_articles(
        self, conn, type_map: dict[str, int], delay: float, batch_size: int
    ) -> int:
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
                    cursor,
                    r["startup_name_extracted"],
                    _normalize_name(r["startup_name_extracted"]),
                    type_map["startup"],
                    {"source_id": r["id"]},
                )
                self._upsert_relationship(
                    cursor,
                    startup_id,
                    startup_id,
                    "mentioned_in_news",
                    source_table="news_articles",
                    source_record_id=r["id"],
                )
                relationships += 1

            # Then, use NER to extract additional entities from summary
            if i % batch_size == 0 and i > 0:
                conn.commit()
                _logger.info("KnowledgeGraphAgent: news batch %d/%d", i, len(rows))

            entities = self._extract_entities_from_text(r.get("summary", ""))
            for ent in entities:
                ent_name = ent.get("name", "")
                ent_type = ent.get("type", "")
                kg_type = self._map_ner_type_to_kg_type(ent_type)
                if not kg_type or kg_type not in type_map or len(ent_name) < 2:
                    continue
                ent_id = self._upsert_entity(
                    cursor,
                    ent_name,
                    _normalize_name(ent_name),
                    type_map[kg_type],
                )
                # Link the entity to the news mention
                self._upsert_relationship(
                    cursor,
                    ent_id,
                    ent_id,
                    "mentioned_in_news",
                    source_table="news_articles",
                    source_record_id=r["id"],
                )
                relationships += 1

            if delay > 0 and i > 0 and i % 10 == 0:
                time.sleep(delay)

        conn.commit()
        cursor.close()
        return relationships

    def _map_ner_type_to_kg_type(self, ner_type: str) -> str | None:
        """Map NER type to knowledge graph entity type."""
        mapping = {
            # Existing
            "startup": "startup",
            "company": "startup",
            "investor": "investor",
            "technology": "technology",
            "industry": "industry",
            "location": "region",
            "region": "region",
            # Phase 2: 5 new types
            "person": "person",
            "product": "product",
            "market": "market",
            "patent": "patent",
            "regulation": "regulation",
        }
        return mapping.get(ner_type.lower())

    def _extract_entities_from_text(self, text: str) -> list[dict]:
        """Extract named entities from text using spaCy (primary) with Ollama fallback.

        Phase 2: Replaced direct Ollama calls with UnifiedEntityExtractor.
        The facade tries spaCy first (fast, local, deterministic), falls back
        to Ollama if spaCy is unavailable.
        """
        if not text or len(text) < 20:
            return []

        try:
            from nlp.entity_extractor import UnifiedEntityExtractor

            extractor = UnifiedEntityExtractor(self.config)
            return extractor.extract(text)
        except ImportError:
            _logger.debug(
                "KnowledgeGraphAgent: NLP package unavailable, using Ollama directly"
            )
            return self._extract_with_ollama(text)

    def _extract_with_ollama(self, text: str) -> list[dict]:
        """Direct Ollama fallback for entity extraction."""
        url = self.config.get("ollama_url", "http://localhost:11434/api/chat")
        model = self.config.get("ollama_model", "llama3")
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Extract named entities from the text. For each entity, classify as one of: "
                        "startup, investor, technology, industry, location, person. "
                        "Return ONLY a JSON array of objects with 'name' and 'type' keys."
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
                url, data=data, headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode())
            content = result.get("message", {}).get("content", "")
            raw = content.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                if raw.endswith("```"):
                    raw = raw[:-3]
                raw = raw.strip()
            return json.loads(raw)
        except Exception:
            return []

    # ── Phase 2: Structured extraction from new data sources ──

    def _extract_from_funding_events(self, conn, type_map: dict[str, int]) -> int:
        """Extract entities and relationships from funding_events table.

        Structured extraction: company→startup, investors_json→investor,
        funded_by relationship.
        """
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, company_name, round_type, amount_usd, investors_json, announced_date FROM funding_events"
        )
        rows = cursor.fetchall()
        relationships = 0

        for row in rows:
            r = dict(row)
            company = r.get("company_name")
            if not company:
                continue

            startup_id = self._upsert_entity(
                cursor,
                company,
                _normalize_name(company),
                type_map["startup"],
                {
                    "round_type": r["round_type"],
                    "amount_usd": r["amount_usd"],
                    "source_id": r["id"],
                },
            )

            investors_json = r.get("investors_json")
            if investors_json:
                try:
                    investors = (
                        json.loads(investors_json)
                        if isinstance(investors_json, str)
                        else investors_json
                    )
                    if isinstance(investors, str):
                        investors = [
                            inv.strip()
                            for inv in re.split(r"[,;]", investors)
                            if inv.strip()
                        ]
                except (json.JSONDecodeError, TypeError):
                    investors = [
                        inv.strip()
                        for inv in re.split(r"[,;]", str(investors_json))
                        if inv.strip()
                    ]

                for inv_name in investors:
                    if len(inv_name) < 2:
                        continue
                    inv_id = self._upsert_entity(
                        cursor,
                        inv_name,
                        _normalize_name(inv_name),
                        type_map["investor"],
                    )
                    weight = 1.0 + (r["amount_usd"] or 0) / 50_000_000
                    self._upsert_relationship(
                        cursor,
                        startup_id,
                        inv_id,
                        "funded_by",
                        weight=min(weight, 5.0),
                        source_table="funding_events",
                        source_record_id=r["id"],
                    )
                    relationships += 1

        conn.commit()
        cursor.close()
        return relationships

    def _extract_from_sec_filings(self, conn, type_map: dict[str, int]) -> int:
        """Extract entities from sec_filings table.

        Structured (company_name) + NER on summary_text for additional entities.
        """
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, company_name, filing_type, summary_text FROM sec_filings"
        )
        rows = cursor.fetchall()
        relationships = 0

        for row in rows:
            r = dict(row)
            company = r.get("company_name")
            if not company:
                continue

            startup_id = self._upsert_entity(
                cursor,
                company,
                _normalize_name(company),
                type_map["startup"],
                {"filing_type": r["filing_type"], "source_id": r["id"]},
            )

            # NER on summary for additional entities
            summary = r.get("summary_text", "")
            if summary and len(summary) > 20:
                entities = self._extract_entities_from_text(summary)
                for ent in entities:
                    ent_name = ent.get("name", "")
                    ent_type = ent.get("type", "")
                    kg_type = self._map_ner_type_to_kg_type(ent_type)
                    if not kg_type or kg_type not in type_map or len(ent_name) < 2:
                        continue
                    if _normalize_name(ent_name) == _normalize_name(company):
                        continue  # Skip self-reference
                    ent_id = self._upsert_entity(
                        cursor, ent_name, _normalize_name(ent_name), type_map[kg_type]
                    )
                    self._upsert_relationship(
                        cursor,
                        startup_id,
                        ent_id,
                        "mentioned_in_news",
                        source_table="sec_filings",
                        source_record_id=r["id"],
                    )
                    relationships += 1

        conn.commit()
        cursor.close()
        return relationships

    def _extract_from_job_postings(self, conn, type_map: dict[str, int]) -> int:
        """Extract entities from job_postings table.

        Structured: company→startup, skills_json→technology,
        uses_tech/hiring_for relationships.
        """
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, company_name, job_title, skills_json FROM job_postings"
        )
        rows = cursor.fetchall()
        relationships = 0

        for row in rows:
            r = dict(row)
            company = r.get("company_name")
            if not company:
                continue

            startup_id = self._upsert_entity(
                cursor,
                company,
                _normalize_name(company),
                type_map["startup"],
                {"source_id": r["id"]},
            )

            skills_json = r.get("skills_json")
            if skills_json:
                try:
                    skills = (
                        json.loads(skills_json)
                        if isinstance(skills_json, str)
                        else skills_json
                    )
                    if isinstance(skills, str):
                        skills = [
                            s.strip() for s in re.split(r"[,;]", skills) if s.strip()
                        ]
                except (json.JSONDecodeError, TypeError):
                    skills = [
                        s.strip()
                        for s in re.split(r"[,;]", str(skills_json))
                        if s.strip()
                    ]

                for skill in skills:
                    if len(skill) < 2:
                        continue
                    tech_id = self._upsert_entity(
                        cursor, skill, _normalize_name(skill), type_map["technology"]
                    )
                    self._upsert_relationship(
                        cursor,
                        startup_id,
                        tech_id,
                        "uses_tech",
                        source_table="job_postings",
                        source_record_id=r["id"],
                    )
                    relationships += 1

        conn.commit()
        cursor.close()
        return relationships

    def _extract_from_github_trends(self, conn, type_map: dict[str, int]) -> int:
        """Extract entities from github_trends table.

        Structured: language→technology, topic_tags→technology/market.
        """
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, repo_name, language, description, topic_tags FROM github_trends"
        )
        rows = cursor.fetchall()
        relationships = 0

        for row in rows:
            r = dict(row)
            repo = r.get("repo_name")
            language = r.get("language")

            # Language as technology entity
            if language and len(language) >= 2:
                tech_id = self._upsert_entity(
                    cursor, language, _normalize_name(language), type_map["technology"]
                )
                repo_id = self._upsert_entity(
                    cursor,
                    repo,
                    _normalize_name(repo),
                    type_map["technology"],
                    {"source_id": r["id"], "weekly_stars_delta": ""},
                )
                self._upsert_relationship(
                    cursor,
                    repo_id,
                    tech_id,
                    "uses_tech",
                    source_table="github_trends",
                    source_record_id=r["id"],
                )
                relationships += 1

            # Topic tags as technology or market entities
            topic_tags = r.get("topic_tags")
            if topic_tags:
                try:
                    tags = (
                        json.loads(topic_tags)
                        if isinstance(topic_tags, str)
                        else topic_tags
                    )
                    if isinstance(tags, str):
                        tags = [t.strip() for t in re.split(r"[,;]", tags) if t.strip()]
                except (json.JSONDecodeError, TypeError):
                    tags = [
                        t.strip()
                        for t in re.split(r"[,;]", str(topic_tags))
                        if t.strip()
                    ]

                for tag in tags:
                    if len(tag) < 2:
                        continue
                    tag_type = (
                        "market"
                        if any(
                            m in tag.lower() for m in ("market", "industry", "sector")
                        )
                        else "technology"
                    )
                    if tag_type not in type_map:
                        tag_type = "technology"
                    self._upsert_entity(
                        cursor, tag, _normalize_name(tag), type_map[tag_type]
                    )
                    relationships += 1

        conn.commit()
        cursor.close()
        return relationships

    def _extract_from_patent_filings(self, conn, type_map: dict[str, int]) -> int:
        """Extract entities from patent_filings table.

        Structured: title→patent, assignee→startup, patent_held_by relationship.
        """
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, patent_number, title, assignee, classification FROM patent_filings"
        )
        rows = cursor.fetchall()
        relationships = 0

        for row in rows:
            r = dict(row)
            title = r.get("title")
            assignee = r.get("assignee")

            if not title:
                continue

            patent_id = self._upsert_entity(
                cursor,
                title[:100],
                _normalize_name(title[:100]),
                type_map["patent"],
                {
                    "patent_number": r["patent_number"],
                    "classification": r["classification"],
                    "source_id": r["id"],
                },
            )

            if assignee and len(assignee) >= 2:
                assignee_id = self._upsert_entity(
                    cursor,
                    assignee,
                    _normalize_name(assignee),
                    type_map["startup"],
                )
                self._upsert_relationship(
                    cursor,
                    patent_id,
                    assignee_id,
                    "patent_held_by",
                    source_table="patent_filings",
                    source_record_id=r["id"],
                )
                relationships += 1

        conn.commit()
        cursor.close()
        return relationships

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
                cursor,
                sp["sector"],
                _normalize_name(sp["sector"]),
                type_map["sector"],
            )
            cat_id = self._upsert_entity(
                cursor,
                sp["failure_category"],
                _normalize_name(sp["failure_category"]),
                type_map["failure_reason"],
            )
            self._upsert_relationship(
                cursor,
                sector_id,
                cat_id,
                "shares_failure_pattern",
                weight=float(sp["cnt"]),
            )
            relationships += 1

        conn.commit()
        cursor.close()
        return relationships
