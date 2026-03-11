from pathlib import Path

from typer.testing import CliRunner

from openqilin.apps import admin_cli

RUNNER = CliRunner()


def test_smoke_command_succeeds() -> None:
    result = RUNNER.invoke(admin_cli.app, ["smoke"])

    assert result.exit_code == 0
    assert "[OK] smoke_owner_command_ingress: accepted task_id=" in result.stdout


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


def test_bootstrap_command_runs_without_migration_when_flag_enabled() -> None:
    result = RUNNER.invoke(admin_cli.app, ["bootstrap", "--skip-migrate"])

    assert result.exit_code == 0
    assert "[OK] migrate: migration step skipped by flag" in result.stdout
    assert "[OK] smoke_owner_command_ingress: accepted task_id=" in result.stdout


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
