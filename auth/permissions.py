"""
Permission definitions for AFDAS.
"""

from enum import Enum
from typing import Set


class Permission(str, Enum):
    """Available permissions in the system."""
    ROUTE_REQUEST = "route:request"
    ROUTE_HISTORY = "route:history"
    FLOOD_VIEW = "flood:view"
    FLOOD_MANAGE = "flood:manage"
    ANALYTICS_VIEW = "analytics:view"
    ANALYTICS_EXPORT = "analytics:export"
    ADMIN_PANEL = "admin:panel"
    CACHE_MANAGE = "cache:manage"


# Role-based permission sets
ROLE_PERMISSIONS: dict[str, Set[Permission]] = {
    "user": {
        Permission.ROUTE_REQUEST,
        Permission.FLOOD_VIEW,
    },
    "responder": {
        Permission.ROUTE_REQUEST,
        Permission.ROUTE_HISTORY,
        Permission.FLOOD_VIEW,
        Permission.ANALYTICS_VIEW,
    },
    "admin": {
        Permission.ROUTE_REQUEST,
        Permission.ROUTE_HISTORY,
        Permission.FLOOD_VIEW,
        Permission.FLOOD_MANAGE,
        Permission.ANALYTICS_VIEW,
        Permission.ANALYTICS_EXPORT,
        Permission.ADMIN_PANEL,
        Permission.CACHE_MANAGE,
    },
}


def has_permission(role: str, permission: Permission) -> bool:
    """Check if a role has a specific permission."""
    role_perms = ROLE_PERMISSIONS.get(role, set())
    return permission in role_perms
