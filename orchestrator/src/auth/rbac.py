"""Role-based access control — defines roles, permissions, and enforcement."""

from dataclasses import dataclass, field
from enum import Enum


class Permission(Enum):
    SESSION_READ = "session:read"
    SESSION_CREATE = "session:create"
    SESSION_DELETE = "session:delete"
    TOOL_READ = "tool:read"
    TOOL_EXECUTE = "tool:execute"
    AGENT_READ = "agent:read"
    AGENT_MANAGE = "agent:manage"
    AUDIT_READ = "audit:read"
    AUDIT_EXPORT = "audit:export"
    USER_READ = "user:read"
    USER_MANAGE = "user:manage"
    SETTINGS_READ = "settings:read"
    SETTINGS_WRITE = "settings:write"
    APPROVE_MUTATE = "approve:mutate"
    APPROVE_DESTRUCTIVE = "approve:destructive"
    ADMIN = "admin:*"


@dataclass
class Role:
    name: str
    permissions: set[Permission] = field(default_factory=set)
    parents: set[str] = field(default_factory=set)


ROLES: dict[str, Role] = {
    "viewer": Role(
        name="viewer",
        permissions={
            Permission.SESSION_READ,
            Permission.TOOL_READ,
            Permission.AGENT_READ,
            Permission.AUDIT_READ,
        },
    ),
    "operator": Role(
        name="operator",
        permissions={
            Permission.SESSION_READ,
            Permission.SESSION_CREATE,
            Permission.TOOL_READ,
            Permission.TOOL_EXECUTE,
            Permission.AGENT_READ,
            Permission.AUDIT_READ,
            Permission.APPROVE_MUTATE,
        },
        parents={"viewer"},
    ),
    "admin": Role(
        name="admin",
        permissions={
            Permission.SESSION_READ,
            Permission.SESSION_CREATE,
            Permission.SESSION_DELETE,
            Permission.TOOL_READ,
            Permission.TOOL_EXECUTE,
            Permission.AGENT_READ,
            Permission.AGENT_MANAGE,
            Permission.AUDIT_READ,
            Permission.AUDIT_EXPORT,
            Permission.USER_READ,
            Permission.USER_MANAGE,
            Permission.SETTINGS_READ,
            Permission.SETTINGS_WRITE,
            Permission.APPROVE_MUTATE,
            Permission.APPROVE_DESTRUCTIVE,
            Permission.ADMIN,
        },
        parents={"operator"},
    ),
    "auditor": Role(
        name="auditor",
        permissions={
            Permission.SESSION_READ,
            Permission.AGENT_READ,
            Permission.AUDIT_READ,
            Permission.AUDIT_EXPORT,
        },
    ),
}


def get_role(name: str) -> Role | None:
    return ROLES.get(name)


def resolve_permissions(role_names: list[str]) -> set[Permission]:
    resolved: set[Permission] = set()
    visited: set[str] = set()
    queue = list(role_names)
    while queue:
        name = queue.pop(0)
        if name in visited:
            continue
        visited.add(name)
        role = ROLES.get(name)
        if role:
            resolved.update(role.permissions)
            queue.extend(role.parents)
    return resolved


def has_permission(user_roles: list[str], required: Permission) -> bool:
    perms = resolve_permissions(user_roles)
    return required in perms or Permission.ADMIN in perms
