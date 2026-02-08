"""Alembic environment configuration for Workflow Service."""

from models import Base
from config import get_settings
import os
import sys
from logging.config import fileConfig

from sqlalchemy import create_engine
from sqlalchemy.engine import Connection

from alembic import context

# Add the service directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import settings and models after adding to path

# Get settings
settings = get_settings()

# Alembic Config object
config = context.config

# Override with actual database URL
database_url = settings.postgres_url
config.set_main_option("sqlalchemy.url", database_url)

# Configure logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = create_engine(database_url)

    with connectable.connect() as connection:
        context.configure(connection=connection,
                          target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
