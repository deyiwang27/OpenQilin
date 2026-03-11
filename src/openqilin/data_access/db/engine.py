"""Database engine and connectivity helpers."""

from __future__ import annotations

import os
from configparser import ConfigParser
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

DEFAULT_DATABASE_URL = "postgresql+psycopg://openqilin:openqilin@localhost:5432/openqilin"


def resolve_database_url(
    *,
    override: str | None = None,
    alembic_ini_path: Path | None = None,
) -> str:
    """Resolve database URL from explicit override, env, alembic config, then default."""

    if override is not None and override.strip():
        return override.strip()

    for env_name in ("OPENQILIN_DATABASE_URL", "POSTGRES_DSN"):
        env_value = os.getenv(env_name)
        if env_value is not None and env_value.strip():
            return env_value.strip()

    ini_path = alembic_ini_path or Path("alembic.ini")
    if ini_path.exists():
        parser = ConfigParser()
        parser.read(ini_path)
        configured = parser.get("alembic", "sqlalchemy.url", fallback="").strip()
        if configured:
            return configured

    return DEFAULT_DATABASE_URL


def create_sqlalchemy_engine(database_url: str) -> Engine:
    """Create SQLAlchemy engine with pre-ping enabled."""

    return create_engine(database_url, future=True, pool_pre_ping=True)


def ping_database(database_url: str) -> tuple[bool, str]:
    """Run a lightweight `SELECT 1` connectivity probe."""

    engine: Engine | None = None
    try:
        engine = create_sqlalchemy_engine(database_url)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True, "database connectivity check passed"
    except Exception as error:
        return False, f"database connectivity check failed: {error}"
    finally:
        if engine is not None:
            engine.dispose()


def check_pgvector_extension(database_url: str) -> tuple[bool, str]:
    """Verify pgvector extension availability in target PostgreSQL database."""

    engine: Engine | None = None
    try:
        engine = create_sqlalchemy_engine(database_url)
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
            ).scalar()
        if result == "vector":
            return True, "pgvector extension is available"
        return False, "pgvector extension is not installed in target database"
    except Exception as error:
        return False, f"pgvector extension check failed: {error}"
    finally:
        if engine is not None:
            engine.dispose()
