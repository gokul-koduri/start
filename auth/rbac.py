"""Role-based access control (RBAC) permissions."""

import logging
from typing import Dict, List, Set

_logger = logging.getLogger(__name__)


# Role hierarchy (higher number = higher privilege)
ROLE_HIERARCHY = {
    "viewer": 1,
    "analyst": 2,
    "admin": 3,
}

# Resource permissions
PERMISSIONS = {
    # Startup data
    "startups:read": ["viewer", "analyst", "admin"],
    "startups:write": ["analyst", "admin"],
    "startups:delete": ["admin"],

    # News and signals
    "news:read": ["viewer", "analyst", "admin"],
    "news:write": ["analyst", "admin"],
    "signals:read": ["viewer", "analyst", "admin"],
    "signals:write": ["analyst", "admin"],

    # Analysis and reports
    "analysis:read": ["viewer", "analyst", "admin"],
    "analysis:run": ["analyst", "admin"],
    "reports:read": ["viewer", "analyst", "admin"],
    "reports:generate": ["analyst", "admin"],

    # Knowledge graph
    "knowledge_graph:read": ["viewer", "analyst", "admin"],
    "knowledge_graph:write": ["analyst", "admin"],

    # ML models
    "ml:read": ["viewer", "analyst", "admin"],
    "ml:train": ["analyst", "admin"],

    # Users and licenses
    "users:read": ["admin"],
    "users:write": ["admin"],
    "licenses:read": ["viewer", "analyst", "admin"],
    "licenses:write": ["admin"],

    # Pipelines and agents
    "pipelines:read": ["viewer", "analyst", "admin"],
    "pipelines:run": ["analyst", "admin"],
    "agents:read": ["viewer", "analyst", "admin"],
    "agents:run": ["analyst", "admin"],

    # Webhooks and integrations
    "webhooks:read": ["viewer", "analyst", "admin"],
    "webhooks:write": ["analyst", "admin"],
    "integrations:read": ["viewer", "analyst", "admin"],
    "integrations:write": ["admin"],

    # System administration
    "system:read": ["viewer", "analyst", "admin"],
    "system:write": ["admin"],
    "system:metrics": ["analyst", "admin"],
}


class RBAC:
    """Role-based access control manager."""

    def __init__(self, config: dict | None = None):
        """Initialize RBAC with configuration.

        Config options:
            roles: Custom role definitions (optional, extends defaults)
            permissions: Custom permission mappings (optional, extends defaults)
        """
        self.config = config or {}
        self.role_hierarchy = {**ROLE_HIERARCHY, **self.config.get("roles", {})}
        self.permissions = {**PERMISSIONS, **self.config.get("permissions", {})}

    def check_permission(self, role: str, permission: str) -> bool:
        """Check if a role has permission for a resource action.

        Args:
            role: User role (viewer, analyst, admin)
            permission: Permission string (e.g., "startups:read")

        Returns:
            True if role has permission, False otherwise
        """
        if role not in self.role_hierarchy:
            _logger.warning("Unknown role: %s", role)
            return False

        if permission not in self.permissions:
            _logger.warning("Unknown permission: %s", permission)
            return False

        allowed_roles = self.permissions[permission]
        return role in allowed_roles

    def get_permissions(self, role: str) -> List[str]:
        """Get all permissions for a given role.

        Args:
            role: User role

        Returns:
            List of permission strings
        """
        if role not in self.role_hierarchy:
            _logger.warning("Unknown role: %s", role)
            return []

        permissions = []
        for perm, allowed_roles in self.permissions.items():
            if role in allowed_roles:
                permissions.append(perm)
        return sorted(permissions)

    def get_role_level(self, role: str) -> int:
        """Get the hierarchy level for a role.

        Args:
            role: User role

        Returns:
            Integer level (higher = more privileged)
        """
        return self.role_hierarchy.get(role, 0)

    def is_higher_role(self, role_a: str, role_b: str) -> bool:
        """Check if role_a is higher privilege than role_b.

        Args:
            role_a: First role
            role_b: Second role

        Returns:
            True if role_a > role_b in hierarchy
        """
        return self.get_role_level(role_a) > self.get_role_level(role_b)

    def filter_roles_by_level(self, min_level: int | None = None) -> List[str]:
        """Get roles at or above a minimum hierarchy level.

        Args:
            min_level: Minimum level (if None, returns all roles)

        Returns:
            List of role names
        """
        if min_level is None:
            return list(self.role_hierarchy.keys())

        return [
            role for role, level in self.role_hierarchy.items()
            if level >= min_level
        ]

    def add_permission(self, permission: str, roles: List[str]) -> None:
        """Add a new permission or update existing permission's allowed roles.

        Args:
            permission: Permission string (e.g., "resource:action")
            roles: List of roles that can perform this action
        """
        self.permissions[permission] = roles
        _logger.info("Added permission: %s -> %s", permission, roles)

    def add_role(self, role: str, level: int) -> None:
        """Add a new role to the hierarchy.

        Args:
            role: Role name
            level: Hierarchy level (1-100, higher = more privilege)
        """
        self.role_hierarchy[role] = level
        _logger.info("Added role: %s at level %d", role, level)
