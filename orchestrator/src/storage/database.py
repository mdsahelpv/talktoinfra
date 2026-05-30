"""Database setup and connection management."""

import os
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.config import settings

engine = create_async_engine(settings.database_url, echo=settings.debug)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def create_db_and_tables():
    # Ensure SQLite database directory exists
    parsed = urlparse(settings.database_url)
    if parsed.scheme.startswith("sqlite"):
        db_path = parsed.path.lstrip("/")
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
    async with engine.begin() as conn:
        from src.storage.models import Base
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
