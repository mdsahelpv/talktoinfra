"""
Test fixtures and utilities for all services.

This module provides:
- PostgreSQL testcontainer for database tests
- Redis testcontainer for caching/queue tests
- Test client fixtures with real database sessions
- Transaction-based test isolation
"""

import asyncio
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, AsyncGenerator, Dict, Generator, List, Optional

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from redis import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

# =============================================================================
# Container Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer, None, None]:
    """Start PostgreSQL container for testing."""
    postgres = PostgresContainer(
        image="postgres:16-alpine",
        username="testuser",
        password="testpass",
        dbname="testdb",
        port=5432,
    )
    postgres.start()
    
    # Wait for database to be ready
    import time
    time.sleep(2)
    
    yield postgres
    
    postgres.stop()


@pytest.fixture(scope="session")
def redis_container() -> Generator[RedisContainer, None, None]:
    """Start Redis container for testing."""
    redis = RedisContainer(image="redis:7-alpine", port=6379)
    redis.start()
    
    # Wait for Redis to be ready
    import time
    time.sleep(1)
    
    yield redis
    
    redis.stop()


@pytest.fixture(scope="session")
def postgres_url(postgres_container: PostgresContainer) -> str:
    """Get PostgreSQL connection URL."""
    # Get the connection URL and convert to async format
    url = postgres_container.get_connection_url()
    # Convert to asyncpg format
    async_url = url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
    return async_url


@pytest.fixture(scope="session")
def redis_url(redis_container: RedisContainer) -> str:
    """Get Redis connection URL."""
    return redis_container.get_connection_url()


# =============================================================================
# Database Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def db_engine(postgres_url: str) -> Generator[AsyncEngine, None, None]:
    """Create async database engine for testing."""
    engine = create_async_engine(
        postgres_url,
        echo=False,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )
    
    yield engine
    
    asyncio.run(engine.dispose())


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Test Data Fixtures - Common test data generators
# =============================================================================


@pytest.fixture
def sample_uuid() -> uuid.UUID:
    """Generate a sample UUID for testing."""
    return uuid.uuid4()


@pytest.fixture
def sample_ip_range() -> str:
    """Sample IP range for testing."""
    return "192.168.1.0/24"


@pytest.fixture
def sample_ports() -> List[int]:
    """Sample ports for testing."""
    return [22, 80, 443]


@pytest.fixture
def sample_timestamp() -> datetime:
    """Sample timestamp for testing."""
    return datetime.utcnow()


@pytest.fixture
def future_timestamp() -> datetime:
    """Future timestamp for testing."""
    return datetime.utcnow() + timedelta(hours=1)


@pytest.fixture
def past_timestamp() -> datetime:
    """Past timestamp for testing."""
    return datetime.utcnow() - timedelta(hours=1)


# =============================================================================
# Utility Fixtures
# =============================================================================


@pytest.fixture
def test_user() -> str:
    """Test user identifier."""
    return "test-user"


@pytest.fixture
def test_admin() -> str:
    """Test admin identifier."""
    return "test-admin"


# =============================================================================
# Environment Setup Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def setup_test_env(
    postgres_url: str,
    redis_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Set up test environment variables."""
    # Set database URL
    monkeypatch.setenv("DATABASE_URL", postgres_url.replace("postgresql+asyncpg://", "postgresql://"))
    monkeypatch.setenv("DB_URL", postgres_url.replace("postgresql+asyncpg://", "postgresql://"))
    
    # Set Redis URL
    monkeypatch.setenv("REDIS_URL", redis_url)
    
    # Set test-specific configurations
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("SERVICE_PORT", "8000")
    monkeypatch.setenv("JWT_SECRET", "test-secret-key-for-testing-only")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    
    # Scanner paths (use system defaults for tests)
    monkeypatch.setenv("MASSCAN_PATH", "/usr/bin/masscan")
    monkeypatch.setenv("NMAP_PATH", "/usr/bin/nmap")
    
    # Test-specific rate limits (higher for faster tests)
    monkeypatch.setenv("SCAN_RATE_LIMIT_PER_MINUTE", "100")
    monkeypatch.setenv("API_RATE_LIMIT_PER_MINUTE", "1000")


# =============================================================================
# Clean Database Fixture
# =============================================================================


@pytest_asyncio.fixture
async def clean_database(db_engine: AsyncEngine) -> AsyncGenerator[None, None]:
    """
    Clean database tables before each test.
    
    This fixture truncates all tables to ensure test isolation.
    """
    async with db_engine.begin() as conn:
        # Get all table names
        result = await conn.execute(text("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename NOT LIKE 'pg_%' 
            AND tablename NOT LIKE 'sql_%'
        """))
        tables = [row[0] for row in result.fetchall()]
        
        if tables:
            # Truncate all tables
            truncate_stmt = "TRUNCATE TABLE {} CASCADE".format(
                ", ".join(f'"{table}"' for table in tables)
            )
            await conn.execute(text(truncate_stmt))
    
    yield
    
    # Cleanup after test
    async with db_engine.begin() as conn:
        if tables:
            truncate_stmt = "TRUNCATE TABLE {} CASCADE".format(
                ", ".join(f'"{table}"' for table in tables)
            )
            await conn.execute(text(truncate_stmt))


# =============================================================================
# Async Database Session Fixture
# =============================================================================


@pytest_asyncio.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create a database session for testing.
    
    This fixture provides a session that rolls back after each test
    to ensure test isolation.
    """
    connection = await db_engine.connect()
    transaction = await connection.begin()
    
    session = AsyncSession(
        bind=connection,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    yield session
    
    await session.close()
    await transaction.rollback()
    await connection.close()


# =============================================================================
# Redis Client Fixture
# =============================================================================


@pytest.fixture
def redis_client(redis_url: str) -> Generator[Redis, None, None]:
    """Create Redis client for testing."""
    # Parse the URL to get host and port
    # redis://localhost:6379/0 format
    client = Redis.from_url(redis_url, decode_responses=True)
    
    # Clear all data
    client.flushall()
    
    yield client
    
    # Cleanup
    client.flushall()
    client.close()


# =============================================================================
# Service-Specific Fixtures
# =============================================================================


@pytest.fixture
def mock_external_api():
    """
    Fixture for mocking external API calls only.
    
    Use this to mock calls to external services like:
    - Third-party APIs
    - Cloud provider APIs
    - External authentication services
    
    Do NOT use this for internal service logic.
    """
    from unittest.mock import AsyncMock, patch
    
    class ExternalAPIMock:
        def __init__(self):
            self.mocks = {}
        
        def mock(self, target: str, return_value: Any = None):
            """Mock an external API call."""
            mock_obj = AsyncMock(return_value=return_value)
            self.mocks[target] = mock_obj
            return patch(target, mock_obj)
        
        def cleanup(self):
            """Clean up all mocks."""
            for mock in self.mocks.values():
                if hasattr(mock, 'stop'):
                    mock.stop()
    
    api_mock = ExternalAPIMock()
    yield api_mock
    api_mock.cleanup()


# =============================================================================
# Test Configuration
# =============================================================================


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "external_api: mark test as using external APIs")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers."""
    for item in items:
        # Add integration marker to tests using containers
        if "container" in item.fixturenames or "postgres" in item.nodeid:
            item.add_marker(pytest.mark.integration)


# =============================================================================
# Test Helpers
# =============================================================================


async def create_test_tables(engine: AsyncEngine, base) -> None:
    """Create all tables from SQLAlchemy models."""
    async with engine.begin() as conn:
        await conn.run_sync(base.metadata.create_all)


async def drop_test_tables(engine: AsyncEngine, base) -> None:
    """Drop all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(base.metadata.drop_all)
