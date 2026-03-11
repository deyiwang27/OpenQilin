from pathlib import Path

from openqilin.data_access.db import engine as db_engine


class _FakeResult:
    def __init__(self, value: str | None) -> None:
        self._value = value

    def scalar(self) -> str | None:
        return self._value


class _FakeConnection:
    def __init__(self, extension_name: str | None) -> None:
        self._extension_name = extension_name

    def __enter__(self) -> "_FakeConnection":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, statement):  # noqa: ANN001
        del statement
        return _FakeResult(self._extension_name)


class _FakeEngine:
    def __init__(self, extension_name: str | None) -> None:
        self._extension_name = extension_name
        self.disposed = False

    def connect(self) -> _FakeConnection:
        return _FakeConnection(self._extension_name)

    def dispose(self) -> None:
        self.disposed = True


def test_check_pgvector_extension_reports_available(monkeypatch) -> None:
    fake_engine = _FakeEngine("vector")
    monkeypatch.setattr(db_engine, "create_sqlalchemy_engine", lambda _: fake_engine)

    ok, message = db_engine.check_pgvector_extension("postgresql+psycopg://stub")

    assert ok is True
    assert message == "pgvector extension is available"
    assert fake_engine.disposed is True


def test_check_pgvector_extension_reports_missing(monkeypatch) -> None:
    fake_engine = _FakeEngine(None)
    monkeypatch.setattr(db_engine, "create_sqlalchemy_engine", lambda _: fake_engine)

    ok, message = db_engine.check_pgvector_extension("postgresql+psycopg://stub")

    assert ok is False
    assert message == "pgvector extension is not installed in target database"
    assert fake_engine.disposed is True


def test_pgvector_migration_contract_file_contains_extension_and_vector_schema() -> None:
    project_root = Path(__file__).resolve().parents[2]
    migration_file = (
        project_root / "migrations" / "versions" / "20260311_0001_pgvector_baseline_contract.py"
    )
    content = migration_file.read_text(encoding="utf-8")

    assert "CREATE EXTENSION IF NOT EXISTS vector" in content
    assert "knowledge_embedding" in content
    assert "embedding vector(1536)" in content


def test_compose_uses_pgvector_enabled_postgres_image() -> None:
    project_root = Path(__file__).resolve().parents[2]
    compose_file = project_root / "compose.yml"
    content = compose_file.read_text(encoding="utf-8")

    assert "image: pgvector/pgvector:pg16" in content
