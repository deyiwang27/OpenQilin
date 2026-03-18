from pathlib import Path

from typer.testing import CliRunner

from openqilin.apps import admin_cli

RUNNER = CliRunner()


def test_smoke_command_succeeds() -> None:
    result = RUNNER.invoke(admin_cli.app, ["smoke", "--in-process"])

    assert result.exit_code == 0
    assert "[OK] smoke_owner_command_ingress_in_process: accepted task_id=" in result.stdout


def test_smoke_command_uses_live_probe_by_default(monkeypatch) -> None:
    called: dict[str, str] = {}

    def fake_live_smoke(
        *, api_base_url: str, timeout_seconds: float = 5.0
    ) -> admin_cli.CheckResult:
        called["url"] = api_base_url
        called["timeout"] = str(timeout_seconds)
        return admin_cli.CheckResult("smoke_owner_command_ingress_live", True, "ok")

    monkeypatch.setattr(admin_cli, "run_smoke_check", fake_live_smoke)
    result = RUNNER.invoke(
        admin_cli.app,
        ["smoke", "--api-base-url", "http://localhost:18000"],
    )

    assert result.exit_code == 0
    assert called["url"] == "http://localhost:18000"
    assert "[OK] smoke_owner_command_ingress_live: ok" in result.stdout


def test_smoke_command_uses_default_base_url_when_flag_missing(monkeypatch) -> None:
    called: dict[str, str] = {}

    def fake_live_smoke(
        *, api_base_url: str, timeout_seconds: float = 5.0
    ) -> admin_cli.CheckResult:
        called["url"] = api_base_url
        return admin_cli.CheckResult("smoke_owner_command_ingress_live", True, "ok")

    monkeypatch.setattr(admin_cli, "run_smoke_check", fake_live_smoke)
    result = RUNNER.invoke(admin_cli.app, ["smoke"])

    assert result.exit_code == 0
    assert called["url"] == admin_cli.DEFAULT_API_BASE_URL
    assert "[OK] smoke_owner_command_ingress_live: ok" in result.stdout


def test_migrate_command_exits_non_zero_on_migration_failure(monkeypatch, tmp_path: Path) -> None:
    alembic_ini = tmp_path / "alembic.ini"
    alembic_ini.write_text("[alembic]\nscript_location = migrations\n", encoding="utf-8")

    def raising_apply(_: Path) -> None:
        raise RuntimeError("migration error")

    monkeypatch.setattr(admin_cli, "apply_migrations", raising_apply)
    result = RUNNER.invoke(
        admin_cli.app,
        ["migrate", "--alembic-ini", str(alembic_ini)],
    )

    assert result.exit_code == 1
    assert "[FAIL] migrate: migration failed: migration error" in result.stdout


def test_apply_migrations_sets_resolved_database_url(monkeypatch, tmp_path: Path) -> None:
    alembic_ini = tmp_path / "alembic.ini"
    alembic_ini.write_text("[alembic]\nscript_location = migrations\n", encoding="utf-8")

    captured: dict[str, str] = {}

    def fake_resolve_database_url(*, override=None, alembic_ini_path=None) -> str:
        return "postgresql+psycopg://resolved-db"

    def fake_upgrade(config, revision) -> None:
        captured["revision"] = revision
        captured["sqlalchemy_url"] = config.get_main_option("sqlalchemy.url")

    monkeypatch.setattr(admin_cli, "resolve_database_url", fake_resolve_database_url)
    monkeypatch.setattr(admin_cli.command, "upgrade", fake_upgrade)

    admin_cli.apply_migrations(alembic_ini)

    assert captured["revision"] == "head"
    assert captured["sqlalchemy_url"] == "postgresql+psycopg://resolved-db"


def test_bootstrap_command_runs_without_migration_when_flag_enabled() -> None:
    result = RUNNER.invoke(admin_cli.app, ["bootstrap", "--skip-migrate", "--smoke-in-process"])

    assert result.exit_code == 0
    assert "[OK] migrate: migration step skipped by flag" in result.stdout
    assert "[OK] pgvector_extension: pgvector extension check skipped by flag" in result.stdout
    assert "[OK] smoke_owner_command_ingress_in_process: accepted task_id=" in result.stdout


def test_bootstrap_short_circuits_smoke_when_migration_fails(monkeypatch, tmp_path: Path) -> None:
    alembic_ini = tmp_path / "alembic.ini"
    alembic_ini.write_text("[alembic]\nscript_location = migrations\n", encoding="utf-8")

    def raising_apply(_: Path) -> None:
        raise RuntimeError("migration error")

    smoke_called = {"value": False}

    def fake_live_smoke(
        *, api_base_url: str, timeout_seconds: float = 5.0
    ) -> admin_cli.CheckResult:
        smoke_called["value"] = True
        return admin_cli.CheckResult("smoke_owner_command_ingress_live", True, "ok")

    monkeypatch.setattr(admin_cli, "apply_migrations", raising_apply)
    monkeypatch.setattr(admin_cli, "run_smoke_check", fake_live_smoke)
    result = RUNNER.invoke(
        admin_cli.app,
        ["bootstrap", "--alembic-ini", str(alembic_ini)],
    )

    assert result.exit_code == 1
    assert smoke_called["value"] is False
    assert "[FAIL] migrate: migration failed: migration error" in result.stdout


def test_bootstrap_short_circuits_smoke_when_pgvector_extension_missing(
    monkeypatch, tmp_path: Path
) -> None:
    alembic_ini = tmp_path / "alembic.ini"
    alembic_ini.write_text("[alembic]\nscript_location = migrations\n", encoding="utf-8")

    def fake_apply(_: Path) -> None:
        return None

    def fake_check_pgvector_extension(_: str) -> tuple[bool, str]:
        return False, "pgvector extension is not installed in target database"

    smoke_called = {"value": False}

    def fake_smoke(*, api_base_url: str, timeout_seconds: float = 5.0) -> admin_cli.CheckResult:
        smoke_called["value"] = True
        return admin_cli.CheckResult("smoke_owner_command_ingress_live", True, "ok")

    monkeypatch.setattr(admin_cli, "apply_migrations", fake_apply)
    monkeypatch.setattr(admin_cli, "check_pgvector_extension", fake_check_pgvector_extension)
    monkeypatch.setattr(admin_cli, "run_smoke_check", fake_smoke)

    result = RUNNER.invoke(
        admin_cli.app,
        ["bootstrap", "--alembic-ini", str(alembic_ini)],
    )

    assert result.exit_code == 1
    assert smoke_called["value"] is False
    assert "[FAIL] pgvector_extension: pgvector extension is not installed in target database" in (
        result.stdout
    )


def test_diagnostics_command_reports_database_ping_failure(monkeypatch) -> None:
    def failing_ping(_: str) -> tuple[bool, str]:
        return False, "db unavailable"

    monkeypatch.setattr(admin_cli, "ping_database", failing_ping)
    result = RUNNER.invoke(
        admin_cli.app,
        [
            "diagnostics",
            "--check-db",
            "--database-url",
            "postgresql+psycopg://user:pass@localhost:5432/openqilin",
        ],
    )

    assert result.exit_code == 1
    assert "[FAIL] diagnostics_database_ping: db unavailable" in result.stdout
