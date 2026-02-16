"""Permission Service - Access Control."""

import fnmatch
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import (
    ClusterAccess,
    PermissionLevel,
    Team,
    TeamMember,
    User,
)


class PermissionService:
    """Permission service for access control."""

    def __init__(self, db: AsyncSession):
        """Initialize permission service."""
        self.db = db

    async def get_user_teams(self, user_id: uuid.UUID) -> list[Team]:
        """Get all teams a user belongs to."""
        result = await self.db.execute(
            select(Team)
            .join(TeamMember)
            .where(TeamMember.user_id == user_id)
        )
        return list(result.scalars().all())

    async def check_cluster_access(
        self,
        user_id: uuid.UUID,
        cluster_id: uuid.UUID,
        required_permission: PermissionLevel = PermissionLevel.READ,
    ) -> tuple[bool, Optional[str]]:
        """Check if user has access to a cluster.
        
        Returns:
            Tuple of (allowed, reason)
        """
        # Get user's teams
        teams = await self.get_user_teams(user_id)
        
        if not teams:
            return False, "User is not a member of any team"

        # Check each team's access to the cluster
        for team in teams:
            result = await self.db.execute(
                select(ClusterAccess)
                .where(ClusterAccess.team_id == team.id)
                .where(ClusterAccess.cluster_id == cluster_id)
            )
            access = result.scalar_one_or_none()

            if access:
                # Check permission level
                if self._has_permission(access.permission_level, required_permission):
                    return True, None

        return False, f"No team has {required_permission.value} access to this cluster"

    async def check_namespace_access(
        self,
        user_id: uuid.UUID,
        cluster_id: uuid.UUID,
        namespace: str,
        required_permission: PermissionLevel = PermissionLevel.READ,
    ) -> tuple[bool, Optional[str]]:
        """Check if user has access to a specific namespace.
        
        Returns:
            Tuple of (allowed, reason)
        """
        # First check cluster access
        allowed, reason = await self.check_cluster_access(
            user_id, cluster_id, required_permission
        )
        
        if not allowed:
            return False, reason

        # Get user's teams
        teams = await self.get_user_teams(user_id)

        # Check namespace-level access for each team
        for team in teams:
            result = await self.db.execute(
                select(ClusterAccess)
                .where(ClusterAccess.team_id == team.id)
                .where(ClusterAccess.cluster_id == cluster_id)
            )
            access = result.scalar_one_or_none()

            if access and access.namespace_access:
                allowed_namespaces = access.namespace_access.get("allowed", [])
                denied_namespaces = access.namespace_access.get("denied", [])

                # Check denied first
                for pattern in denied_namespaces:
                    if fnmatch.fnmatch(namespace, pattern):
                        return False, f"Namespace '{namespace}' is explicitly denied"

                # Check allowed
                if not allowed_namespaces:
                    # No restrictions, allow all
                    return True, None

                for pattern in allowed_namespaces:
                    if fnmatch.fnmatch(namespace, pattern):
                        return True, None

                return False, f"Namespace '{namespace}' is not in allowed list"

        return True, None

    async def check_resource_access(
        self,
        user_id: uuid.UUID,
        cluster_id: uuid.UUID,
        namespace: Optional[str],
        resource_kind: str,
        action: str,
    ) -> tuple[bool, Optional[str]]:
        """Check if user can perform action on a resource.
        
        Args:
            user_id: The user ID
            cluster_id: The cluster ID
            namespace: The namespace (optional)
            resource_kind: The resource kind (pod, deployment, etc.)
            action: The action (read, write, dry_run, admin)
            
        Returns:
            Tuple of (allowed, reason)
        """
        # Map action to permission level
        action_to_permission = {
            "read": PermissionLevel.READ,
            "get": PermissionLevel.READ,
            "list": PermissionLevel.READ,
            "watch": PermissionLevel.READ,
            "write": PermissionLevel.WRITE,
            "create": PermissionLevel.WRITE,
            "update": PermissionLevel.WRITE,
            "patch": PermissionLevel.WRITE,
            "delete": PermissionLevel.WRITE,
            "dry_run": PermissionLevel.DRY_RUN,
            "admin": PermissionLevel.ADMIN,
        }

        required_permission = action_to_permission.get(
            action.lower(), PermissionLevel.READ
        )

        # Check namespace access if provided
        if namespace:
            return await self.check_namespace_access(
                user_id, cluster_id, namespace, required_permission
            )

        # Otherwise check cluster access
        return await self.check_cluster_access(
            user_id, cluster_id, required_permission
        )

    async def get_accessible_clusters(
        self, user_id: uuid.UUID
    ) -> list[dict]:
        """Get all clusters a user has access to.
        
        Returns:
            List of cluster access info
        """
        teams = await self.get_user_teams(user_id)
        
        if not teams:
            return []

        cluster_access = []
        for team in teams:
            result = await self.db.execute(
                select(ClusterAccess).where(ClusterAccess.team_id == team.id)
            )
            accesses = result.scalars().all()

            for access in accesses:
                cluster_access.append({
                    "cluster_id": str(access.cluster_id),
                    "team_id": str(team.id),
                    "team_name": team.name,
                    "permission_level": access.permission_level.value,
                    "namespace_access": access.namespace_access,
                    "label_selector": access.label_selector,
                })

        return cluster_access

    async def is_superuser(self, user_id: uuid.UUID) -> bool:
        """Check if user is a superuser."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return False
            
        return user.is_superuser

    @staticmethod
    def _has_permission(
        granted: PermissionLevel, required: PermissionLevel
    ) -> bool:
        """Check if granted permission satisfies required permission."""
        permission_order = [
            PermissionLevel.NONE,
            PermissionLevel.READ,
            PermissionLevel.DRY_RUN,
            PermissionLevel.WRITE,
            PermissionLevel.ADMIN,
        ]
        
        try:
            granted_index = permission_order.index(granted)
            required_index = permission_order.index(required)
            return granted_index >= required_index
        except ValueError:
            return False
