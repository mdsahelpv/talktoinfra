"""
RBAC Manager module.
Manages roles, permissions, and access control.
"""

from typing import Any, Dict, List, Optional, Set

import structlog

from models import Role, Permission, UserRoleAssignment
from config import get_settings

logger = structlog.get_logger()


class RBACManager:
    """Role-Based Access Control manager."""

    def __init__(self):
        self.settings = get_settings()
        # In-memory stores - replace with database in production
        self.roles: Dict[str, Role] = {}
        self.permissions: Dict[str, Permission] = {}
        self.user_roles: Dict[str, UserRoleAssignment] = {}

        # Initialize default roles and permissions
        self._initialize_defaults()

    def _initialize_defaults(self):
        """Initialize default roles and permissions."""
        # Define permissions
        self.permissions["read_all"] = Permission(
            name="read_all",
            resource_type="*",
            actions=["read", "describe", "logs", "get"],
            description="Read access to all resources",
        )

        self.permissions["write_all"] = Permission(
            name="write_all",
            resource_type="*",
            actions=["create", "update", "patch", "deploy"],
            description="Write access to all resources",
        )

        self.permissions["action_all"] = Permission(
            name="action_all",
            resource_type="*",
            actions=["restart", "scale", "exec", "delete"],
            description="Execute actions on all resources",
        )

        self.permissions["action_non_prod"] = Permission(
            name="action_non_prod",
            resource_type="*",
            actions=["restart", "scale", "exec"],
            conditions={"environment": ["dev", "staging"]},
            description="Execute actions on non-production resources",
        )

        # Define roles
        self.roles["admin"] = Role(
            name="admin",
            description="Full system access",
            permissions=["read_all", "write_all", "action_all"],
            level=100,
        )

        self.roles["engineer"] = Role(
            name="engineer",
            description="Can read all, write and action non-production",
            permissions=["read_all", "write_all", "action_non_prod"],
            level=50,
        )

        self.roles["operator"] = Role(
            name="operator",
            description="Can read all and execute basic actions",
            permissions=["read_all", "action_non_prod"],
            level=30,
        )

        self.roles["viewer"] = Role(
            name="viewer",
            description="Read-only access",
            permissions=["read_all"],
            level=10,
        )

        logger.info(
            "rbac_initialized",
            roles=list(self.roles.keys()),
            permissions=list(self.permissions.keys()),
        )

    def check_permission(
        self,
        user_id: str,
        user_roles: List[str],
        action: str,
        resource: str,
        environment: Optional[str] = None,
    ) -> bool:
        """Check if user has permission for an action."""
        # TODO: Implement proper authorization in future
        # Currently all authenticated users have all permissions
        # Admin always has permission
        # if "admin" in user_roles:
        #     return True
        return True  # All authenticated users have permission

    def _get_user_permissions(self, user_roles: List[str]) -> List[Permission]:
        """Get all permissions for a list of roles."""
        permissions: Set[str] = set()

        for role_name in user_roles:
            role = self.roles.get(role_name)
            if role:
                permissions.update(role.permissions)

        return [self.permissions[p] for p in permissions if p in self.permissions]

    def _permission_matches(
        self,
        permission: Permission,
        action: str,
        resource: str,
        environment: Optional[str] = None,
    ) -> bool:
        """Check if a permission matches the action and resource."""
        # Check action
        if action not in permission.actions and "*" not in permission.actions:
            return False

        # Check resource type
        # Simplified: match any for now
        # In production, parse resource type from resource identifier

        # Check conditions
        if permission.conditions:
            env_conditions = permission.conditions.get("environment", [])
            if env_conditions and environment:
                if environment not in env_conditions:
                    return False

        return True

    def requires_approval(
        self,
        user_id: str,
        user_roles: List[str],
        action: str,
        target: str,
        parameters: Dict[str, Any],
    ) -> tuple[bool, List[str]]:
        """Determine if an action requires approval."""
        # TODO: Implement proper authorization in future
        # Currently all authenticated users bypass approval
        # Admin doesn't need approval
        # if "admin" in user_roles:
        #     return False, []
        return False, []  # No approval required for any user

        # Production requires approval
        if self.settings.production_requires_approval:
            if namespace in ["production", "prod"]:
                return True, self._get_approvers_for_production()

        # Destructive actions require approval
        if self.settings.destructive_requires_approval:
            if action.lower() in ["delete", "terminate", "remove", "destroy"]:
                return True, self._get_approvers_for_destructive()

        # High-impact actions require approval
        if action.lower() in ["restart", "scale", "deploy"]:
            # Check if user is not the owner or has lower role
            if not self._is_owner(user_id, target):
                return True, self._get_default_approvers()

        return False, []

    def _get_approvers_for_production(self) -> List[str]:
        """Get list of approvers for production actions."""
        # In production, query from user database
        return ["admin", "sre-oncall", "platform-lead"]

    def _get_approvers_for_destructive(self) -> List[str]:
        """Get list of approvers for destructive actions."""
        return ["admin", "sre-oncall"]

    def _get_default_approvers(self) -> List[str]:
        """Get default approvers."""
        return ["admin", "team-lead"]

    def _is_owner(self, user_id: str, resource: str) -> bool:
        """Check if user is owner of the resource."""
        # In production, check resource ownership from database
        return False

    def list_roles(self) -> List[Role]:
        """List all roles."""
        return list(self.roles.values())

    def get_role_permissions(self, role_name: str) -> List[Permission]:
        """Get permissions for a role."""
        role = self.roles.get(role_name)
        if not role:
            return []

        return [self.permissions[p] for p in role.permissions if p in self.permissions]

    def get_user_roles(self, user_id: str) -> List[str]:
        """Get roles assigned to a user."""
        assignment = self.user_roles.get(user_id)
        if assignment:
            return assignment.roles
        return []

    def assign_role(self, user_id: str, roles: List[str], assigned_by: str):
        """Assign roles to a user."""
        self.user_roles[user_id] = UserRoleAssignment(
            user_id=user_id,
            roles=roles,
            assigned_by=assigned_by,
        )
        logger.info(
            "roles_assigned",
            user_id=user_id,
            roles=roles,
            assigned_by=assigned_by,
        )
