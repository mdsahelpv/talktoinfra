"""Authentication Service."""

import secrets
import string
import uuid
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from models import (
    ApiKey,
    User,
    UserSession,
    UserStatus,
)

settings = get_settings()


class AuthService:
    """Authentication service for user management."""

    def __init__(self, db: AsyncSession):
        """Initialize auth service."""
        self.db = db

    # Password hashing
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode(), salt).decode()

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify a password against its hash."""
        try:
            return bcrypt.checkpw(password.encode(), password_hash.encode())
        except Exception:
            return False

    # JWT tokens
    def create_access_token(self, user_id: uuid.UUID) -> str:
        """Create a JWT access token."""
        expire = datetime.utcnow() + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )
        payload = {
            "sub": str(user_id),
            "type": "access",
            "exp": expire,
            "iat": datetime.utcnow(),
        }
        return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    def create_refresh_token(self, user_id: uuid.UUID) -> str:
        """Create a JWT refresh token."""
        expire = datetime.utcnow() + timedelta(days=settings.jwt_refresh_token_expire_days)
        payload = {
            "sub": str(user_id),
            "type": "refresh",
            "exp": expire,
            "iat": datetime.utcnow(),
        }
        return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    def verify_token(self, token: str) -> Optional[dict]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(
                token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    # User authentication
    async def authenticate_user(
        self, email: str, password: str
    ) -> Optional[tuple[User, str, str]]:
        """Authenticate a user with email and password."""
        result = await self.db.execute(
            select(User).where(User.email == email.lower())
        )
        user = result.scalar_one_or_none()

        if not user:
            return None

        if user.status != UserStatus.ACTIVE:
            return None

        if not user.password_hash:
            return None

        if not self.verify_password(password, user.password_hash):
            return None

        # Update last login
        user.last_login_at = datetime.utcnow()
        await self.db.commit()

        # Create tokens
        access_token = self.create_access_token(user.id)
        refresh_token = self.create_refresh_token(user.id)

        return user, access_token, refresh_token

    async def create_session(
        self,
        user: User,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> UserSession:
        """Create a new user session."""
        # Generate unique token
        token = secrets.token_urlsafe(32)
        refresh_token = secrets.token_urlsafe(32)

        expires_at = datetime.utcnow() + timedelta(hours=settings.session_expire_hours)

        session = UserSession(
            user_id=user.id,
            token=token,
            refresh_token=refresh_token,
            device_info=device_info,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at,
        )

        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)

        return session

    async def get_session_by_token(self, token: str) -> Optional[UserSession]:
        """Get session by token."""
        result = await self.db.execute(
            select(UserSession)
            .where(UserSession.token == token)
            .where(UserSession.is_active == True)
            .where(UserSession.expires_at > datetime.utcnow())
        )
        return result.scalar_one_or_none()

    async def refresh_session(
        self, refresh_token: str
    ) -> Optional[tuple[User, str, str]]:
        """Refresh a session using refresh token."""
        payload = self.verify_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            return None

        user_id = uuid.UUID(payload.get("sub"))
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user or user.status != UserStatus.ACTIVE:
            return None

        # Update last login
        user.last_login_at = datetime.utcnow()
        await self.db.commit()

        # Create new tokens
        access_token = self.create_access_token(user.id)
        new_refresh_token = self.create_refresh_token(user.id)

        return user, access_token, new_refresh_token

    async def revoke_session(self, session_id: uuid.UUID) -> bool:
        """Revoke a session."""
        result = await self.db.execute(
            select(UserSession).where(UserSession.id == session_id)
        )
        session = result.scalar_one_or_none()

        if session:
            session.is_active = False
            await self.db.commit()
            return True
        return False

    async def revoke_all_sessions(self, user_id: uuid.UUID) -> int:
        """Revoke all sessions for a user."""
        result = await self.db.execute(
            select(UserSession)
            .where(UserSession.user_id == user_id)
            .where(UserSession.is_active == True)
        )
        sessions = result.scalars().all()

        count = 0
        for session in sessions:
            session.is_active = False
            count += 1

        await self.db.commit()
        return count

    # API Keys
    async def create_api_key(
        self,
        user: User,
        name: str,
        permissions: Optional[dict] = None,
        expires_at: Optional[datetime] = None,
    ) -> tuple[ApiKey, str]:
        """Create an API key for a user."""
        # Generate API key
        prefix = "sk_" + "".join(secrets.choice(string.ascii_lowercase) for _ in range(8))
        full_key = prefix + "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
        key_hash = self.hash_password(full_key)

        api_key = ApiKey(
            user_id=user.id,
            name=name,
            key_hash=key_hash,
            prefix=prefix,
            permissions=permissions,
            expires_at=expires_at,
        )

        self.db.add(api_key)
        await self.db.commit()
        await self.db.refresh(api_key)

        return api_key, full_key

    async def verify_api_key(self, api_key: str) -> Optional[User]:
        """Verify an API key and return the user."""
        if len(api_key) < 12:
            return None

        prefix = api_key[:12]

        result = await self.db.execute(
            select(ApiKey)
            .where(ApiKey.prefix == prefix)
            .where(ApiKey.is_active == True)
        )
        api_key_obj = result.scalar_one_or_none()

        if not api_key_obj:
            return None

        if api_key_obj.expires_at and api_key_obj.expires_at < datetime.utcnow():
            return None

        if not self.verify_password(api_key, api_key_obj.key_hash):
            return None

        # Update last used
        api_key_obj.last_used_at = datetime.utcnow()
        await self.db.commit()

        # Get user
        result = await self.db.execute(
            select(User).where(User.id == api_key_obj.user_id)
        )
        return result.scalar_one_or_none()

    async def revoke_api_key(self, api_key_id: uuid.UUID) -> bool:
        """Revoke an API key."""
        result = await self.db.execute(
            select(ApiKey).where(ApiKey.id == api_key_id)
        )
        api_key = result.scalar_one_or_none()

        if api_key:
            api_key.is_active = False
            await self.db.commit()
            return True
        return False
