"""Graph queries for knowledge graph traversal and analysis."""

from typing import List, Dict, Any, Optional
from db.connection import get_connection
from db import schema
import logging

_logger = logging.getLogger(__name__)


def get_entity_connections(entity_name: str, max_depth: int = 2) -> List[Dict[str, Any]]:
    """Get connections for an entity from the knowledge graph.

    Args:
        entity_name: Name of the entity to query
        max_depth: Maximum depth of traversal

    Returns:
        List of connected entities with relationship info
    """
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    # Get entity ID
    cursor.execute(
        """SELECT id FROM kg_entities WHERE normalized_name = %s LIMIT 1""",
        (entity_name.lower(),)
    )
    entity_row = cursor.fetchone()
    if not entity_row:
        cursor.close()
        conn.close()
        return []

    entity_id = entity_row["id"]

    # Get direct connections
    cursor.execute(
        """SELECT r.target_entity_id, r.relationship_type, r.weight,
                  e.name as target_name, e.entity_type_id
           FROM kg_relationships r
           JOIN kg_entities e ON r.target_entity_id = e.id
           WHERE r.source_entity_id = %s
           LIMIT 100""",
        (entity_id,)
    )

    connections = []
    for row in cursor.fetchall():
        connections.append({
            "target_entity": row.get("target_name", ""),
            "relationship_type": row.get("relationship_type", ""),
            "weight": row.get("weight", 0.0),
            "entity_type_id": row.get("entity_type_id", 0)
        })

    cursor.close()
    conn.close()

    return connections


def get_community_members(limit: int = 50) -> List[Dict[str, Any]]:
    """Get entities grouped by community (based on relationship density).

    Args:
        limit: Maximum number of entities to return

    Returns:
        List of entities with community info
    """
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    cursor.execute(
        """SELECT e.id, e.name, e.entity_type_id, e.mention_count,
                  COUNT(r.id) as connection_count
           FROM kg_entities e
           LEFT JOIN kg_relationships r ON (
               r.source_entity_id = e.id OR r.target_entity_id = e.id
           )
           GROUP BY e.id
           ORDER BY connection_count DESC
           LIMIT %s""",
        (limit,)
    )

    entities = []
    for row in cursor.fetchall():
        entities.append({
            "id": row.get("id", 0),
            "name": row.get("name", ""),
            "entity_type_id": row.get("entity_type_id", 0),
            "mention_count": row.get("mention_count", 0),
            "connection_count": row.get("connection_count", 0)
        })

    cursor.close()
    conn.close()

    return entities


def get_entity_centrality(entity_name: str) -> Optional[float]:
    """Calculate centrality score for an entity.

    Args:
        entity_name: Name of the entity

    Returns:
        Centrality score or None if entity not found
    """
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    cursor.execute(
        """SELECT COUNT(*) as connection_count
           FROM kg_relationships
           WHERE source_entity_id = (SELECT id FROM kg_entities WHERE normalized_name = %s)
              OR target_entity_id = (SELECT id FROM kg_entities WHERE normalized_name = %s)""",
        (entity_name.lower(), entity_name.lower())
    )

    row = cursor.fetchone()
    centrality = row.get("connection_count", 0) if row else 0

    cursor.close()
    conn.close()

    return float(centrality) if centrality > 0 else None
