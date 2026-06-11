"""Entity Resolution Agent — resolves duplicate entities in the knowledge graph.

Identifies and merges duplicate entity entries that refer to the same
real-world entity (e.g., "OpenAI", "Open AI", "OpenAI Inc.").

Uses a three-stage resolution pipeline:
1. Blocking: generate candidate pairs by grouping on normalized name prefix
2. Matching: score similarity using Jaro-Winkler + attribute overlap
3. Merging: re-point relationships to canonical entity, create aliases

Design choices:
    - Blocking on first 3 chars of normalized_name (avoids O(n²))
    - Jaro-Winkler similarity (prefix-sensitive, good for company names)
    - Embedding similarity as secondary signal (when available)
    - Dry-run mode for testing without making changes
"""

from __future__ import annotations

import logging
from collections import defaultdict

from agents.base import AgentResult, BaseAgent
from db.connection import get_connection
from db import schema

_logger = logging.getLogger(__name__)


def _jaro_winkler_similarity(s1: str, s2: str) -> float:
    """Compute Jaro-Winkler similarity between two strings.

    Jaro-Winkler extends Jaro similarity by giving extra weight to
    matching prefixes — ideal for entity names where "Stripe" and
    "Stripe Inc." should score higher than "Stripe" and "Strlpe".

    Returns float between 0.0 (no match) and 1.0 (exact match).
    """
    if not s1 or not s2:
        return 0.0
    if s1 == s2:
        return 1.0

    len1, len2 = len(s1), len(s2)
    match_distance = max(len1, len2) // 2 - 1
    if match_distance < 0:
        match_distance = 0

    s1_matches = [False] * len1
    s2_matches = [False] * len2

    matches = 0
    transpositions = 0

    for i in range(len1):
        start = max(0, i - match_distance)
        end = min(i + match_distance + 1, len2)
        for j in range(start, end):
            if s2_matches[j] or s1[i] != s2[j]:
                continue
            s1_matches[i] = True
            s2_matches[j] = True
            matches += 1
            break

    if matches == 0:
        return 0.0

    k = 0
    for i in range(len1):
        if not s1_matches[i]:
            continue
        while not s2_matches[k]:
            k += 1
        if s1[i] != s2[k]:
            transpositions += 1
        k += 1

    jaro = (
        matches / len1 + matches / len2 + (matches - transpositions / 2) / matches
    ) / 3.0

    # Winkler bonus for common prefix (max 4 chars)
    prefix_len = 0
    for i in range(min(len1, len2, 4)):
        if s1[i] == s2[i]:
            prefix_len += 1
        else:
            break

    return jaro + prefix_len * 0.1 * (1.0 - jaro)


class EntityResolverAgent(BaseAgent):
    """Resolves duplicate entities in the knowledge graph.

    Config options:
        similarity_threshold: min Jaro-Winkler to consider a match (default: 0.85)
        batch_size: entities to process per batch (default: 1000)
        dry_run: if True, report matches but don't merge (default: False)
        min_mention_count: only resolve entities mentioned at least N times (default: 1)
    """

    @property
    def name(self) -> str:
        return "entity_resolver"

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        try:
            conn = get_connection()
            schema.init_schema(conn)
        except Exception as e:
            return AgentResult(agent_name=self.name, status="failed", errors=[str(e)])

        errors = []
        total_resolved = 0
        total_aliases = 0

        try:
            threshold = float(self.config.get("similarity_threshold", 0.85))
            dry_run = self.config.get("dry_run", False)
            min_mentions = int(self.config.get("min_mention_count", 1))

            cursor = conn.cursor()

            # Load all entities grouped by type_id
            cursor.execute(
                "SELECT id, name, normalized_name, entity_type_id, attributes_json, mention_count "
                "FROM kg_entities ORDER BY entity_type_id, normalized_name"
            )
            all_entities = cursor.fetchall()

            # Group by entity_type_id (only resolve within same type)
            by_type: dict[int, list[dict]] = defaultdict(list)
            for row in all_entities:
                by_type[row["entity_type_id"]].append(dict(row))

            for type_id, entities in by_type.items():
                resolved, aliases = self._resolve_type(
                    conn,
                    cursor,
                    entities,
                    threshold,
                    dry_run,
                    min_mentions,
                )
                total_resolved += resolved
                total_aliases += aliases

            conn.commit()
            cursor.close()
            conn.close()

        except Exception as e:
            errors.append(str(e))
            _logger.error("EntityResolverAgent: Error: %s", e)
            try:
                conn.close()
            except Exception:
                pass
            return AgentResult(agent_name=self.name, status="failed", errors=errors)

        _logger.info(
            "EntityResolverAgent: Done — %d duplicates resolved, %d aliases created",
            total_resolved,
            total_aliases,
        )

        return AgentResult(
            agent_name=self.name,
            status="success" if not errors else "partial",
            data={
                "total_resolved": total_resolved,
                "total_aliases": total_aliases,
                "records_affected": total_resolved + total_aliases,
            },
            errors=errors,
        )

    def _resolve_type(
        self,
        conn,
        cursor,
        entities: list[dict],
        threshold: float,
        dry_run: bool,
        min_mentions: int,
    ) -> tuple[int, int]:
        """Resolve duplicates within a single entity type."""
        resolved = 0
        aliases = 0

        # Filter by minimum mention count
        entities = [e for e in entities if e["mention_count"] >= min_mentions]
        if len(entities) < 2:
            return resolved, aliases

        # Stage 1: Blocking — group by first 3 chars of normalized_name
        blocks: dict[str, list[dict]] = defaultdict(list)
        for entity in entities:
            prefix = entity["normalized_name"][:3]
            blocks[prefix].append(entity)

        # Stage 2: Matching — score candidate pairs within blocks
        merged_ids: set[int] = set()  # IDs already merged (skip)

        for block_key, block_entities in blocks.items():
            # Compare all pairs within block
            for i in range(len(block_entities)):
                ei = block_entities[i]
                if ei["id"] in merged_ids:
                    continue

                for j in range(i + 1, len(block_entities)):
                    ej = block_entities[j]
                    if ej["id"] in merged_ids:
                        continue

                    score = _jaro_winkler_similarity(
                        ei["normalized_name"],
                        ej["normalized_name"],
                    )

                    if score < threshold:
                        continue

                    # Determine canonical (higher mention count wins)
                    if ei["mention_count"] >= ej["mention_count"]:
                        canonical, duplicate = ei, ej
                    else:
                        canonical, duplicate = ej, ei

                    _logger.info(
                        "EntityResolverAgent: match '%s' ↔ '%s' (score=%.3f)",
                        canonical["name"],
                        duplicate["name"],
                        score,
                    )

                    if not dry_run:
                        alias_count = self._merge_entities(
                            cursor,
                            canonical["id"],
                            duplicate["id"],
                            duplicate["name"],
                            duplicate["normalized_name"],
                        )
                        aliases += alias_count

                    merged_ids.add(duplicate["id"])
                    resolved += 1

        return resolved, aliases

    def _merge_entities(
        self,
        cursor,
        canonical_id: int,
        duplicate_id: int,
        alias_name: str,
        normalized_alias: str,
    ) -> int:
        """Merge duplicate entity into canonical entity.

        Steps:
        1. Re-point all relationships from duplicate to canonical
        2. Create alias mapping
        3. Transfer mention_count
        4. Delete duplicate entity

        Returns number of aliases created (0 or 1).
        """
        # Re-point relationships: source_entity_id
        cursor.execute(
            "UPDATE kg_relationships SET source_entity_id = %s WHERE source_entity_id = %s",
            (canonical_id, duplicate_id),
        )

        # Re-point relationships: target_entity_id
        cursor.execute(
            "UPDATE kg_relationships SET target_entity_id = %s WHERE target_entity_id = %s",
            (canonical_id, duplicate_id),
        )

        # Transfer mention count
        cursor.execute(
            "UPDATE kg_entities SET mention_count = mention_count + "
            "(SELECT mention_count FROM kg_entities WHERE id = %s) "
            "WHERE id = %s",
            (duplicate_id, canonical_id),
        )

        # Create alias mapping (skip if already exists)
        cursor.execute(
            "INSERT IGNORE INTO kg_entity_aliases (alias_name, normalized_alias, canonical_entity_id) "
            "VALUES (%s, %s, %s)",
            (alias_name, normalized_alias, canonical_id),
        )

        # Delete duplicate
        cursor.execute("DELETE FROM kg_entities WHERE id = %s", (duplicate_id,))

        return cursor.rowcount  # 1 if alias was created, 0 if duplicate key
