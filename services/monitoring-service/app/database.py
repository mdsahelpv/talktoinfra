"""
Monitoring Service Database.

Database connection and session management.
"""

from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings

# Global engine and session factory
_engine = None
_session_factory = None


def get_engine():
    """Get or create the async engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        # Convert postgresql:// to postgresql+asyncpg://
        db_url = settings.database.url
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace(
                "postgresql://", "postgresql+asyncpg://", 1)

        _engine = create_async_engine(
            db_url,
            pool_size=settings.database.pool_size,
            max_overflow=settings.database.max_overflow,
            pool_timeout=settings.database.pool_timeout,
            echo=settings.debug,
        )
    return _engine


def get_session_factory():
    """Get or create the session factory."""
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        _session_factory = sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """Initialize database tables."""
    from app.models import Base
    from app.models_alerts import Base as AlertsBase

    engine = get_engine()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(AlertsBase.metadata.create_all)

    # Import and create self-healing tables
    try:
        from app.models_self_healing import Base as SelfHealingBase
        async with engine.begin() as conn:
            await conn.run_sync(SelfHealingBase.metadata.create_all)
    except ImportError:
        pass


async def close_db():
    """Close database connections."""
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
    _session_factory = None
