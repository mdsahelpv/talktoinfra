"""PostgreSQL checkpointing — LangGraph BaseCheckpointSaver using SQLAlchemy."""

import json
from datetime import datetime, timezone
from typing import Any, AsyncIterator

from sqlalchemy import Column, String, Text, DateTime, JSON
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.config import settings
from src.storage.models import Base


class CheckpointModel(Base):
    __tablename__ = "checkpoints"

    thread_id = Column(String, primary_key=True)
    checkpoint_ns = Column(String, default="")
    checkpoint_id = Column(String, primary_key=True)
    parent_id = Column(String, default="")
    state = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class PostgresCheckpointer:
    def __init__(self) -> None:
        db_url = settings.checkpoint_db_url or settings.database_url
        self._engine = create_async_engine(db_url, echo=settings.debug)
        self._async_session = async_sessionmaker(self._engine, expire_on_commit=False)

    async def setup(self) -> None:
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def save_checkpoint(self, thread_id: str, checkpoint_id: str, state: dict, parent_id: str = "", checkpoint_ns: str = "") -> None:
        async with self._async_session() as session:
            existing = await session.get(CheckpointModel, (thread_id, checkpoint_id))
            if existing:
                existing.state = state
                existing.parent_id = parent_id
            else:
                session.add(CheckpointModel(
                    thread_id=thread_id,
                    checkpoint_ns=checkpoint_ns,
                    checkpoint_id=checkpoint_id,
                    parent_id=parent_id,
                    state=state,
                ))
            await session.commit()

    async def load_checkpoint(self, thread_id: str, checkpoint_id: str) -> dict | None:
        async with self._async_session() as session:
            cp = await session.get(CheckpointModel, (thread_id, checkpoint_id))
            if cp is None:
                return None
            return {
                "thread_id": cp.thread_id,
                "checkpoint_ns": cp.checkpoint_ns,
                "checkpoint_id": cp.checkpoint_id,
                "parent_id": cp.parent_id,
                "state": cp.state,
                "created_at": cp.created_at.isoformat() if cp.created_at else "",
            }

    async def list_checkpoints(self, thread_id: str, limit: int = 10) -> list[dict]:
        from sqlalchemy import select
        async with self._async_session() as session:
            stmt = (
                select(CheckpointModel)
                .where(CheckpointModel.thread_id == thread_id)
                .order_by(CheckpointModel.created_at.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            checkpoints = result.scalars().all()
            return [
                {
                    "thread_id": cp.thread_id,
                    "checkpoint_id": cp.checkpoint_id,
                    "parent_id": cp.parent_id,
                    "state": cp.state,
                    "created_at": cp.created_at.isoformat() if cp.created_at else "",
                }
                for cp in checkpoints
            ]
