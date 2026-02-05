"""Database connection and session management for monitoring service."""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

# Get settings
settings = get_settings()

# Create engine
engine: Engine = create_engine(
    settings.database.url,
    pool_size=settings.database.pool_size,
    max_overflow=settings.database.max_overflow,
    pool_timeout=settings.database.pool_timeout,
    echo=settings.debug,
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db_session() -> Session:
    """Get a database session.

    Returns:
        SQLAlchemy Session
    """
    db = SessionLocal()
    try:
        return db
    except Exception:
        db.close()
        raise


@contextmanager
def get_db_session_context() -> Generator[Session, None, None]:
    """Get a database session as a context manager.

    Yields:
        SQLAlchemy Session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_engine() -> Engine:
    """Get the database engine.

    Returns:
        SQLAlchemy Engine
    """
    return engine


def init_db() -> None:
    """Initialize database tables."""
    from app.models import Base
    from app.models_alerts import AlertRule, EscalationPolicy, NotificationChannel

    # Import all models
    from app.models import BaselineMetric, CustomMetric, Metric, ServiceHealth
    from app.models_alerts import Alert, AlertHistory, AlertNotification

    # Create all tables
    Base.metadata.create_all(bind=engine)


def check_db_connection() -> bool:
    """Check if database connection is healthy.

    Returns:
        True if connection is healthy
    """
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False
