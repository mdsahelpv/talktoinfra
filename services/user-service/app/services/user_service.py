"""User Service - CRUD operations."""

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import (
    ApiKey,
    ClusterAccess,
    Role,
    Team,
    TeamMember,
    User,
    UserRole,
    UserSession,
    UserStatus,
)
from schemas import (
    ApiKeyCreate,
    ChangePasswordRequest,
    ClusterAccessCreate,
    ClusterAccessUpdate,
    RoleCreate,
    RoleUpdate,
    TeamCreate,
    TeamUpdate,
    UserCreate,
    UserUpdate,
)
from app.services.auth_service import AuthService


class UserService:
    """User service for CRUD operations."""

    def __init__(self, db: AsyncSession):
        """Initialize user service."""
        self.db = db
        self.auth_service = AuthService(db)

    # User operations
    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        # Check if email exists
        result = await self.db.execute(
            select(User).where(User.email == user_data.email.lower())
        )
        if result.scalar_one_or_none():
            raise ValueError("Email already registered")

        # Check if username exists
        result = await self.db.execute(
            select(User).where(User.username == user_data.username)
        )
        if result.scalar_one_or_none():
            raise ValueError("Username already taken")

        # Create user
        user = User(
            email=user_data.email.lower(),
            username=user_data.username,
            full_name=user_data.full_name,
            password_hash=self.auth_service.hash_password(user_data.password),
            status=UserStatus.ACTIVE,
        )

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def get_user(self, user_id: uuid.UUID) -> Optional[User]:
        """Get user by ID."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.db.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def list_users(
        self, limit: int = 50, offset: int = 0, status: Optional[UserStatus] = None
    ) -> tuple[int, list[User]]:
        """List users with pagination."""
        query = select(User)

        if status:
            query = query.where(User.status == status)

        # Count total
        count_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar()

        # Get paginated results
        query = query.order_by(User.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        users = result.scalars().all()

        return total, list(users)

    async def update_user(self, user_id: uuid.UUID, user_data: UserUpdate) -> Optional[User]:
        """Update a user."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            return None

        # Update fields
        if user_data.email is not None:
            # Check if email is taken
            existing = await self.get_user_by_email(user_data.email)
            if existing and existing.id != user_id:
                raise ValueError("Email already in use")
            user.email = user_data.email.lower()

        if user_data.username is not None:
            # Check if username is taken
            existing = await self.get_user_by_username(user_data.username)
            if existing and existing.id != user_id:
                raise ValueError("Username already taken")
            user.username = user_data.username

        if user_data.full_name is not None:
            user.full_name = user_data.full_name

        if user_data.avatar_url is not None:
            user.avatar_url = user_data.avatar_url

        if user_data.preferences is not None:
            user.preferences = user_data.preferences

        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def delete_user(self, user_id: uuid.UUID) -> bool:
        """Delete a user."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if user:
            await self.db.delete(user)
            await self.db.commit()
            return True
        return False

    async def change_password(
        self, user_id: uuid.UUID, password_data: ChangePasswordRequest
    ) -> bool:
        """Change user password."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            return False

        # Verify current password
        if not self.auth_service.verify_password(
            password_data.current_password, user.password_hash or ""
        ):
            raise ValueError("Current password is incorrect")

        # Update password
        user.password_hash = self.auth_service.hash_password(password_data.new_password)
        await self.db.commit()

        # Revoke all sessions except current
        await self.auth_service.revoke_all_sessions(user_id)

        return True

    # Team operations
    async def create_team(self, team_data: TeamCreate) -> Team:
        """Create a new team."""
        # Generate slug from name
        slug = team_data.name.lower().replace(" ", "-")
        slug = "".join(c for c in slug if c.isalnum() or c == "-")

        # Check if slug exists
        result = await self.db.execute(select(Team).where(Team.slug == slug))
        if result.scalar_one_or_none():
            # Add random suffix
            import random
            slug = f"{slug}-{random.randint(1000, 9999)}"

        team = Team(
            name=team_data.name,
            slug=slug,
            description=team_data.description,
        )

        self.db.add(team)
        await self.db.commit()
        await self.db.refresh(team)

        return team

    async def get_team(self, team_id: uuid.UUID) -> Optional[Team]:
        """Get team by ID."""
        result = await self.db.execute(select(Team).where(Team.id == team_id))
        return result.scalar_one_or_none()

    async def get_team_by_slug(self, slug: str) -> Optional[Team]:
        """Get team by slug."""
        result = await self.db.execute(select(Team).where(Team.slug == slug))
        return result.scalar_one_or_none()

    async def list_teams(self, limit: int = 50, offset: int = 0) -> tuple[int, list[Team]]:
        """List teams with pagination."""
        query = select(Team).order_by(Team.created_at.desc())

        # Count total
        count_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar()

        # Get paginated results
        query = query.limit(limit).offset(offset)
        result = await self.db.execute(query)
        teams = result.scalars().all()

        return total, list(teams)

    async def update_team(self, team_id: uuid.UUID, team_data: TeamUpdate) -> Optional[Team]:
        """Update a team."""
        result = await self.db.execute(select(Team).where(Team.id == team_id))
        team = result.scalar_one_or_none()

        if not team:
            return None

        if team_data.name is not None:
            team.name = team_data.name
        if team_data.description is not None:
            team.description = team_data.description
        if team_data.avatar_url is not None:
            team.avatar_url = team_data.avatar_url
        if team_data.settings is not None:
            team.settings = team_data.settings

        await self.db.commit()
        await self.db.refresh(team)

        return team

    async def add_team_member(
        self, team_id: uuid.UUID, user_id: uuid.UUID, role: str = "member"
    ) -> Optional[TeamMember]:
        """Add a user to a team."""
        # Check if already a member
        result = await self.db.execute(
            select(TeamMember)
            .where(TeamMember.team_id == team_id)
            .where(TeamMember.user_id == user_id)
        )
        if result.scalar_one_or_none():
            raise ValueError("User is already a team member")

        member = TeamMember(
            team_id=team_id,
            user_id=user_id,
            role=role,
        )

        self.db.add(member)
        await self.db.commit()
        await self.db.refresh(member)

        return member

    async def remove_team_member(self, team_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Remove a user from a team."""
        result = await self.db.execute(
            select(TeamMember)
            .where(TeamMember.team_id == team_id)
            .where(TeamMember.user_id == user_id)
        )
        member = result.scalar_one_or_none()

        if member:
            await self.db.delete(member)
            await self.db.commit()
            return True
        return False

    async def get_user_teams(self, user_id: uuid.UUID) -> list[Team]:
        """Get all teams a user belongs to."""
        result = await self.db.execute(
            select(Team)
            .join(TeamMember)
            .where(TeamMember.user_id == user_id)
        )
        return list(result.scalars().all())

    # Role operations
    async def create_role(self, role_data: RoleCreate) -> Role:
        """Create a new role."""
        role = Role(
            name=role_data.name,
            description=role_data.description,
            role_type=role_data.role_type,
            permissions=role_data.permissions,
        )

        self.db.add(role)
        await self.db.commit()
        await self.db.refresh(role)

        return role

    async def assign_role(self, user_id: uuid.UUID, role_id: uuid.UUID) -> Optional[UserRole]:
        """Assign a role to a user."""
        # Check if already has role
        result = await self.db.execute(
            select(UserRole)
            .where(UserRole.user_id == user_id)
            .where(UserRole.role_id == role_id)
        )
        if result.scalar_one_or_none():
            raise ValueError("User already has this role")

        user_role = UserRole(user_id=user_id, role_id=role_id)

        self.db.add(user_role)
        await self.db.commit()
        await self.db.refresh(user_role)

        return user_role

    async def remove_role(self, user_id: uuid.UUID, role_id: uuid.UUID) -> bool:
        """Remove a role from a user."""
        result = await self.db.execute(
            select(UserRole)
            .where(UserRole.user_id == user_id)
            .where(UserRole.role_id == role_id)
        )
        user_role = result.scalar_one_or_none()

        if user_role:
            await self.db.delete(user_role)
            await self.db.commit()
            return True
        return False

    async def get_user_roles(self, user_id: uuid.UUID) -> list[Role]:
        """Get all roles for a user."""
        result = await self.db.execute(
            select(Role)
            .join(UserRole)
            .where(UserRole.user_id == user_id)
        )
        return list(result.scalars().all())

    # Cluster access operations
    async def create_cluster_access(
        self, team_id: uuid.UUID, access_data: ClusterAccessCreate
    ) -> ClusterAccess:
        """Create cluster access for a team."""
        access = ClusterAccess(
            team_id=team_id,
            cluster_id=access_data.cluster_id,
            permission_level=access_data.permission_level,
            namespace_access=access_data.namespace_access,
            label_selector=access_data.label_selector,
        )

        self.db.add(access)
        await self.db.commit()
        await self.db.refresh(access)

        return access

    async def update_cluster_access(
        self, access_id: uuid.UUID, access_data: ClusterAccessUpdate
    ) -> Optional[ClusterAccess]:
        """Update cluster access."""
        result = await self.db.execute(
            select(ClusterAccess).where(ClusterAccess.id == access_id)
        )
        access = result.scalar_one_or_none()

        if not access:
            return None

        if access_data.permission_level is not None:
            access.permission_level = access_data.permission_level
        if access_data.namespace_access is not None:
            access.namespace_access = access_data.namespace_access
        if access_data.label_selector is not None:
            access.label_selector = access_data.label_selector

        await self.db.commit()
        await self.db.refresh(access)

        return access

    async def delete_cluster_access(self, access_id: uuid.UUID) -> bool:
        """Delete cluster access."""
        result = await self.db.execute(
            select(ClusterAccess).where(ClusterAccess.id == access_id)
        )
        access = result.scalar_one_or_none()

        if access:
            await self.db.delete(access)
            await self.db.commit()
            return True
        return False

    async def get_team_cluster_access(self, team_id: uuid.UUID) -> list[ClusterAccess]:
        """Get all cluster access for a team."""
        result = await self.db.execute(
            select(ClusterAccess).where(ClusterAccess.team_id == team_id)
        )
        return list(result.scalars().all())

    # Session operations
    async def get_user_sessions(self, user_id: uuid.UUID) -> list[UserSession]:
        """Get all sessions for a user."""
        result = await self.db.execute(
            select(UserSession)
            .where(UserSession.user_id == user_id)
            .order_by(UserSession.created_at.desc())
        )
        return list(result.scalars().all())

    # API Key operations
    async def get_user_api_keys(self, user_id: uuid.UUID) -> list[ApiKey]:
        """Get all API keys for a user."""
        result = await self.db.execute(
            select(ApiKey)
            .where(ApiKey.user_id == user_id)
            .order_by(ApiKey.created_at.desc())
        )
        return list(result.scalars().all())
