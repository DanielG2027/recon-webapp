# Alembic env - use sync engine and our Base
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

from backend.app.database import Base
from backend.app.models import *  # noqa: F401, F403

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def get_url():
    """Build the sync DB URL from env vars. No hardcoded credentials."""
    explicit = os.environ.get("DATABASE_URL") or os.environ.get("RECON_DATABASE_URL_SYNC")
    if explicit:
        return explicit
    user = os.environ.get("RECON_DB_USER", "recon")
    password = os.environ.get("RECON_DB_PASSWORD", "")
    host = os.environ.get("RECON_DB_HOST", "127.0.0.1")
    port = os.environ.get("RECON_DB_PORT", "5432")
    name = os.environ.get("RECON_DB_NAME", "recon")
    if not password:
        raise RuntimeError(
            "RECON_DB_PASSWORD is not set. "
            "Copy .env.example to .env and set the database password."
        )
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{name}"

def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {}) or {}
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
