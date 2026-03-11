from pathlib import Path

from openqilin.data_access.db.engine import DEFAULT_DATABASE_URL, resolve_database_url


def test_resolve_database_url_prefers_override(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OPENQILIN_DATABASE_URL", "postgresql+psycopg://env-primary")
    monkeypatch.setenv("POSTGRES_DSN", "postgresql+psycopg://env-legacy")
    ini = tmp_path / "alembic.ini"
    ini.write_text("[alembic]\nsqlalchemy.url = postgresql+psycopg://ini\n", encoding="utf-8")

    resolved = resolve_database_url(
        override="postgresql+psycopg://override",
        alembic_ini_path=ini,
    )

    assert resolved == "postgresql+psycopg://override"


def test_resolve_database_url_uses_openqilin_env_before_legacy(monkeypatch) -> None:
    monkeypatch.setenv("OPENQILIN_DATABASE_URL", "postgresql+psycopg://env-primary")
    monkeypatch.setenv("POSTGRES_DSN", "postgresql+psycopg://env-legacy")

    resolved = resolve_database_url()

    assert resolved == "postgresql+psycopg://env-primary"


def test_resolve_database_url_uses_legacy_env_when_primary_missing(monkeypatch) -> None:
    monkeypatch.delenv("OPENQILIN_DATABASE_URL", raising=False)
    monkeypatch.setenv("POSTGRES_DSN", "postgresql+psycopg://env-legacy")

    resolved = resolve_database_url()

    assert resolved == "postgresql+psycopg://env-legacy"


def test_resolve_database_url_uses_alembic_ini_then_default(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("OPENQILIN_DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_DSN", raising=False)

    ini = tmp_path / "alembic.ini"
    ini.write_text("[alembic]\nsqlalchemy.url = postgresql+psycopg://ini\n", encoding="utf-8")
    resolved_from_ini = resolve_database_url(alembic_ini_path=ini)
    assert resolved_from_ini == "postgresql+psycopg://ini"

    missing_ini = tmp_path / "missing.ini"
    resolved_default = resolve_database_url(alembic_ini_path=missing_ini)
    assert resolved_default == DEFAULT_DATABASE_URL
