"""Multi-tenant database isolation manager."""

import logging
from contextlib import contextmanager

from db.connection import get_connection
from db import schema

_logger = logging.getLogger(__name__)


class TenantManager:
    """Manages multi-tenant database isolation using tenant_id context.

    In a real multi-tenant deployment, each tenant gets:
    - Separate tenant_id in config
    - Schema prefix (e.g., tenant123_.failed_startups)
    - Row-level security filters

    For this implementation, we use a simpler approach:
    - tenant_id from config
    - WHERE tenant_id = X filters on queries
    - Context manager for tenant switching
    """

    def __init__(self, config: dict | None = None):
        """Initialize tenant manager.

        Config options:
            tenant_id: Current tenant ID (default: "default")
            isolation_level: "schema" or "row" (default: "row")
        """
        self.config = config or {}
        self.tenant_id = self.config.get("tenant_id", "default")
        self.isolation_level = self.config.get("isolation_level", "row")
        self._current_tenant = self.tenant_id

    @property
    def current_tenant(self) -> str:
        """Get the current active tenant ID."""
        return self._current_tenant

    @contextmanager
    def switch_tenant(self, tenant_id: str):
        """Context manager to temporarily switch tenant context.

        Args:
            tenant_id: Tenant ID to switch to

        Example:
            with tenant_manager.switch_tenant("acme-corp"):
                # All queries here filter to acme-corp
                results = query_startups()
        """
        old_tenant = self._current_tenant
        self._current_tenant = tenant_id
        _logger.debug("Switched tenant context: %s -> %s", old_tenant, tenant_id)
        try:
            yield
        finally:
            self._current_tenant = old_tenant
            _logger.debug("Restored tenant context: %s", old_tenant)

    def get_tenant_filter(self, table_name: str) -> str:
        """Generate SQL WHERE clause for tenant filtering.

        Args:
            table_name: Table to filter (must have tenant_id column)

        Returns:
            SQL WHERE clause fragment (e.g., "tenant_id = 'acme'")
        """
        if self.isolation_level == "schema":
            # Schema-based isolation uses table prefixes
            schema_prefix = f"{self._current_tenant}_"
            return f"-- Schema isolation: table {schema_prefix}{table_name}"
        else:
            # Row-based isolation uses WHERE clause
            return f"tenant_id = '{self._current_tenant}'"

    def apply_tenant_filter(self, query: str, table_name: str) -> str:
        """Apply tenant filtering to a SQL query.

        Args:
            query: SQL query string
            table_name: Primary table being queried

        Returns:
            Modified query with tenant filter applied
        """
        if self.isolation_level == "schema":
            # For schema isolation, would need to rewrite table names
            # Not implemented in this simple version
            return query
        else:
            # Add WHERE clause for row-level filtering
            filter_clause = self.get_tenant_filter(table_name)

            # Simple heuristic: add WHERE if not present
            if " WHERE " in query.upper():
                return f"{query} AND {filter_clause}"
            elif "GROUP BY" in query.upper():
                # Insert before GROUP BY
                parts = query.split("GROUP BY")
                return f"{parts[0]} WHERE {filter_clause} GROUP BY{parts[1]}"
            else:
                return f"{query} WHERE {filter_clause}"

    def check_table_access(self, table_name: str) -> bool:
        """Check if current tenant has access to a table.

        Args:
            table_name: Table to check

        Returns:
            True if access is allowed
        """
        # In a real implementation, would check tenant permissions
        # For now, all tenants have access to all tables
        return True

    def get_tenant_config(self, tenant_id: str | None = None) -> dict:
        """Get configuration for a specific tenant.

        Args:
            tenant_id: Tenant ID (uses current if None)

        Returns:
            Dictionary with tenant configuration
        """
        tid = tenant_id or self._current_tenant
        # In a real implementation, would load from DB or config file
        # For now, return basic config
        return {
            "tenant_id": tid,
            "isolation_level": self.isolation_level,
            "features": ["basic_analytics"],
        }

    def list_tenants(self) -> list[dict]:
        """List all available tenants.

        Returns:
            List of tenant info dictionaries
        """
        try:
            conn = get_connection()
            schema.init_schema(conn)
            cursor = conn.cursor()

            cursor.execute("SELECT id, name, slug, is_active FROM tenants")
            rows = cursor.fetchall()

            tenants = [dict(r) for r in rows]

            cursor.close()
            conn.close()

            return tenants
        except Exception as e:
            _logger.error("Failed to list tenants: %s", e)
            return []

    def create_tenant(
        self, name: str, slug: str, config: dict | None = None
    ) -> int | None:
        """Create a new tenant.

        Args:
            name: Tenant display name
            slug: URL-safe tenant identifier
            config: Optional tenant configuration JSON

        Returns:
            New tenant ID or None if failed
        """
        try:
            import json

            conn = get_connection()
            schema.init_schema(conn)
            cursor = conn.cursor()

            cursor.execute(
                """INSERT INTO tenants (name, slug, config, is_active)
                   VALUES (%s, %s, %s, 1)""",
                (name, slug, json.dumps(config) if config else None),
            )
            tenant_id = cursor.lastrowid
            conn.commit()
            cursor.close()
            conn.close()

            _logger.info("Created tenant: %s (ID: %d)", name, tenant_id)
            return tenant_id
        except Exception as e:
            _logger.error("Failed to create tenant: %s", e)
            return None

    def activate_tenant(self, tenant_id: int) -> bool:
        """Activate a tenant.

        Args:
            tenant_id: Tenant ID to activate

        Returns:
            True if successful
        """
        try:
            conn = get_connection()
            schema.init_schema(conn)
            cursor = conn.cursor()

            cursor.execute(
                "UPDATE tenants SET is_active = 1 WHERE id = %s", (tenant_id,)
            )
            conn.commit()
            cursor.close()
            conn.close()

            _logger.info("Activated tenant ID: %d", tenant_id)
            return True
        except Exception as e:
            _logger.error("Failed to activate tenant: %s", e)
            return False
