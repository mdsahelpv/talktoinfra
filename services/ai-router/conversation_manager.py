"""
Conversation manager for handling chat history.
Uses Redis for caching and PostgreSQL for persistence.
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import redis.asyncio as redis
import structlog
from sqlalchemy import (
    Column,
    DateTime,
    String,
    select,
    update,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config import get_settings

logger = structlog.get_logger()

Base = declarative_base()


class ConversationORM(Base):
    """SQLAlchemy model for conversations."""

    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(255), nullable=False, index=True)
    title = Column(String(255))
    messages = Column(JSONB, default=list)
    meta_data = Column(
        JSONB, default=dict
    )  # Renamed from 'metadata' (reserved by SQLAlchemy)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ConversationManager:
    """Manage conversation history with Redis cache and PostgreSQL persistence."""

    def __init__(self, redis_url: str, postgres_url: str):
        """Initialize conversation manager.

        Args:
            redis_url: Redis connection URL
            postgres_url: PostgreSQL connection URL
        """
        self.redis_url = redis_url
        self.postgres_url = postgres_url
        self.redis: Optional[redis.Redis] = None
        self.engine = None
        self.async_session = None

        # Convert postgres URL to async version
        async_postgres_url = postgres_url.replace(
            "postgresql://", "postgresql+asyncpg://"
        )

        self.engine = create_async_engine(async_postgres_url, echo=False)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def _get_redis(self) -> redis.Redis:
        """Get or create Redis connection."""
        if self.redis is None:
            self.redis = await redis.from_url(
                self.redis_url, encoding="utf-8", decode_responses=True
            )
        return self.redis

    async def create_conversation(
        self, user_id: str, title: Optional[str] = None, metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create a new conversation.

        Args:
            user_id: User identifier
            title: Optional conversation title
            metadata: Optional metadata dict

        Returns:
            Created conversation dict
        """
        conversation_id = str(uuid.uuid4())
        now = datetime.utcnow()

        conversation = {
            "id": conversation_id,
            "user_id": user_id,
            "title": title or "New Conversation",
            "messages": [],
            "metadata": metadata or {},
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        # Store in PostgreSQL
        async with self.async_session() as session:
            orm_conv = ConversationORM(
                id=conversation_id,
                user_id=user_id,
                title=conversation["title"],
                messages=[],
                meta_data=metadata or {},  # Updated column name
                created_at=now,
                updated_at=now,
            )
            session.add(orm_conv)
            await session.commit()

        # Cache in Redis with TTL
        settings = get_settings()
        redis_client = await self._get_redis()
        ttl_seconds = settings.conversation_ttl_hours * 3600

        await redis_client.setex(
            f"conversation:{conversation_id}",
            ttl_seconds,
            json.dumps(conversation),
        )

        logger.info(
            "conversation_created", conversation_id=conversation_id, user_id=user_id
        )

        return conversation

    async def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a conversation by ID.

        Args:
            conversation_id: Conversation unique identifier

        Returns:
            Conversation dict or None if not found
        """
        # Try Redis cache first
        redis_client = await self._get_redis()
        cached = await redis_client.get(f"conversation:{conversation_id}")

        if cached:
            return json.loads(cached)

        # Fallback to PostgreSQL
        async with self.async_session() as session:
            result = await session.execute(
                select(ConversationORM).where(ConversationORM.id == conversation_id)
            )
            orm_conv = result.scalar_one_or_none()

            if orm_conv is None:
                return None

            conversation = {
                "id": orm_conv.id,
                "user_id": orm_conv.user_id,
                "title": orm_conv.title,
                "messages": orm_conv.messages or [],
                "metadata": orm_conv.meta_data or {},  # Updated column name
                "created_at": (
                    orm_conv.created_at.isoformat() if orm_conv.created_at else None
                ),
                "updated_at": (
                    orm_conv.updated_at.isoformat() if orm_conv.updated_at else None
                ),
            }

            # Cache in Redis
            settings = get_settings()
            ttl_seconds = settings.conversation_ttl_hours * 3600
            await redis_client.setex(
                f"conversation:{conversation_id}",
                ttl_seconds,
                json.dumps(conversation),
            )

            return conversation

    async def get_or_create(
        self, conversation_id: Optional[str], user_id: str
    ) -> Dict[str, Any]:
        """Get existing conversation or create new one.

        Args:
            conversation_id: Existing conversation ID or None
            user_id: User identifier

        Returns:
            Conversation dict
        """
        if conversation_id:
            conversation = await self.get_conversation(conversation_id)
            if conversation:
                return conversation

        return await self.create_conversation(user_id)

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Add a message to conversation.

        Args:
            conversation_id: Conversation identifier
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Optional metadata

        Returns:
            Updated conversation dict
        """
        conversation = await self.get_conversation(conversation_id)
        if conversation is None:
            raise ValueError(f"Conversation {conversation_id} not found")

        # Create message
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }

        # Add to conversation
        conversation["messages"].append(message)
        conversation["updated_at"] = datetime.utcnow().isoformat()

        # Enforce max history limit
        settings = get_settings()
        max_messages = settings.max_conversation_history * 2  # User + assistant pairs
        if len(conversation["messages"]) > max_messages:
            conversation["messages"] = conversation["messages"][-max_messages:]

        # Update PostgreSQL
        async with self.async_session() as session:
            await session.execute(
                update(ConversationORM)
                .where(ConversationORM.id == conversation_id)
                .values(
                    messages=conversation["messages"],
                    updated_at=datetime.utcnow(),
                )
            )
            await session.commit()

        # Update Redis cache
        redis_client = await self._get_redis()
        ttl_seconds = settings.conversation_ttl_hours * 3600
        await redis_client.setex(
            f"conversation:{conversation_id}",
            ttl_seconds,
            json.dumps(conversation),
        )

        logger.info(
            "message_added",
            conversation_id=conversation_id,
            role=role,
            message_length=len(content),
        )

        return conversation

    async def list_conversations(
        self, user_id: str, limit: int = 20, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List conversations for a user.

        Args:
            user_id: User identifier
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of conversation dicts
        """
        async with self.async_session() as session:
            result = await session.execute(
                select(ConversationORM)
                .where(ConversationORM.user_id == user_id)
                .order_by(ConversationORM.updated_at.desc())
                .limit(limit)
                .offset(offset)
            )
            orm_convs = result.scalars().all()

            return [
                {
                    "id": conv.id,
                    "user_id": conv.user_id,
                    "title": conv.title,
                    "message_count": len(conv.messages) if conv.messages else 0,
                    "created_at": (
                        conv.created_at.isoformat() if conv.created_at else None
                    ),
                    "updated_at": (
                        conv.updated_at.isoformat() if conv.updated_at else None
                    ),
                }
                for conv in orm_convs
            ]

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation.

        Args:
            conversation_id: Conversation identifier

        Returns:
            True if deleted, False if not found
        """
        async with self.async_session() as session:
            result = await session.execute(
                select(ConversationORM).where(ConversationORM.id == conversation_id)
            )
            orm_conv = result.scalar_one_or_none()

            if orm_conv is None:
                return False

            await session.delete(orm_conv)
            await session.commit()

        # Remove from Redis
        redis_client = await self._get_redis()
        await redis_client.delete(f"conversation:{conversation_id}")

        logger.info("conversation_deleted", conversation_id=conversation_id)
        return True

    async def close(self):
        """Close database connections."""
        if self.redis:
            await self.redis.close()
        if self.engine:
            await self.engine.dispose()
