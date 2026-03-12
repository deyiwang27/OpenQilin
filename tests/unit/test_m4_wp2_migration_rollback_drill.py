import json
from pathlib import Path

from typer.testing import CliRunner

from openqilin.apps import admin_cli

RUNNER = CliRunner()


def _write_alembic_ini(path: Path) -> Path:
    alembic_ini = path / "alembic.ini"
    alembic_ini.write_text("[alembic]\nscript_location = migrations\n", encoding="utf-8")
    return alembic_ini


def test_run_migration_rollback_drill_restore_mode_requires_reference(
    monkeypatch,
    tmp_path: Path,
) -> None:
    alembic_ini = _write_alembic_ini(tmp_path)

    def fake_upgrade(config, revision: str) -> None:
        assert revision == "head"

    monkeypatch.setattr(admin_cli.command, "upgrade", fake_upgrade)
    monkeypatch.setattr(admin_cli, "check_pgvector_extension", lambda _: (True, "ok"))
    monkeypatch.setattr(admin_cli, "check_knowledge_embedding_table", lambda _: (True, "ok"))

    results, resolved_url = admin_cli.run_migration_rollback_drill(
        alembic_ini_path=alembic_ini,
        database_url="postgresql+psycopg://user:pass@localhost:5432/openqilin",
        rollback_mode=admin_cli.RollbackMode.RESTORE,
        rollback_revision="-1",
        restore_reference=None,
    )

    assert resolved_url == "postgresql+psycopg://user:pass@localhost:5432/openqilin"
    assert [result.name for result in results] == [
        "migration_upgrade_head",
        "migration_contract_pgvector",
        "migration_contract_embedding_table",
        "rollback_restore_reference",
    ]
    assert results[-1].success is False


def test_run_migration_rollback_drill_downgrade_mode_round_trip(
    monkeypatch, tmp_path: Path
) -> None:
    alembic_ini = _write_alembic_ini(tmp_path)
    calls: list[tuple[str, str]] = []

    def fake_upgrade(config, revision: str) -> None:
        calls.append(("upgrade", revision))

    def fake_downgrade(config, revision: str) -> None:
        calls.append(("downgrade", revision))

    monkeypatch.setattr(admin_cli.command, "upgrade", fake_upgrade)
    monkeypatch.setattr(admin_cli.command, "downgrade", fake_downgrade)
    monkeypatch.setattr(admin_cli, "check_pgvector_extension", lambda _: (True, "ok"))
    monkeypatch.setattr(admin_cli, "check_knowledge_embedding_table", lambda _: (True, "ok"))

    results, _ = admin_cli.run_migration_rollback_drill(
        alembic_ini_path=alembic_ini,
        database_url="postgresql+psycopg://user:pass@localhost:5432/openqilin",
        rollback_mode=admin_cli.RollbackMode.DOWNGRADE,
        rollback_revision="-1",
        restore_reference=None,
        allow_downgrade_destructive=True,
    )

    assert calls == [("upgrade", "head"), ("downgrade", "-1"), ("upgrade", "head")]
    assert [result.name for result in results] == [
        "migration_upgrade_head",
        "migration_contract_pgvector",
        "migration_contract_embedding_table",
        "rollback_downgrade",
        "rollback_recover_head",
        "rollback_contract_pgvector",
        "rollback_contract_embedding_table",
    ]
    assert all(result.success for result in results)


def test_run_migration_rollback_drill_downgrade_mode_blocked_without_guard_flag(
    monkeypatch, tmp_path: Path
) -> None:
    alembic_ini = _write_alembic_ini(tmp_path)
    calls: list[tuple[str, str]] = []

    def fake_upgrade(config, revision: str) -> None:
        calls.append(("upgrade", revision))

    def fake_downgrade(config, revision: str) -> None:
        calls.append(("downgrade", revision))

    monkeypatch.setattr(admin_cli.command, "upgrade", fake_upgrade)
    monkeypatch.setattr(admin_cli.command, "downgrade", fake_downgrade)
    monkeypatch.setattr(admin_cli, "check_pgvector_extension", lambda _: (True, "ok"))
    monkeypatch.setattr(admin_cli, "check_knowledge_embedding_table", lambda _: (True, "ok"))

    results, _ = admin_cli.run_migration_rollback_drill(
        alembic_ini_path=alembic_ini,
        database_url="postgresql+psycopg://user:pass@localhost:5432/openqilin",
        rollback_mode=admin_cli.RollbackMode.DOWNGRADE,
        rollback_revision="-1",
        restore_reference=None,
    )

    assert calls == [("upgrade", "head")]
    assert results[-1].name == "rollback_downgrade_guard"
    assert results[-1].success is False


def test_build_and_write_migration_drill_evidence_payload(tmp_path: Path) -> None:
    payload = admin_cli.build_migration_drill_evidence_payload(
        release_version="0.1.0-rc1",
        operator="release_manager",
        reason="drill",
        rollback_mode=admin_cli.RollbackMode.RESTORE,
        rollback_revision="-1",
        restore_reference="backup-2026-03-12T020000Z",
        database_url="postgresql+psycopg://user:pass@localhost:5432/openqilin",
        results=[admin_cli.CheckResult("migration_upgrade_head", True, "ok")],
    )
    assert payload["database_url"] == "postgresql+psycopg://***@localhost:5432/openqilin"
    output_path = admin_cli.write_migration_drill_evidence(
        payload,
        tmp_path / "artifacts" / "migration_rollback_drill.json",
    )
    loaded = json.loads(output_path.read_text(encoding="utf-8"))
    assert loaded["overall_success"] is True
    assert loaded["steps"][0]["name"] == "migration_upgrade_head"


def test_rollback_drill_command_writes_evidence_and_exits_zero(monkeypatch, tmp_path: Path) -> None:
    evidence_path = tmp_path / "drill-evidence.json"

    def fake_run_migration_rollback_drill(**kwargs):
        return [admin_cli.CheckResult("migration_upgrade_head", True, "ok")], (
            "postgresql+psycopg://user:pass@localhost:5432/openqilin"
        )

    monkeypatch.setattr(
        admin_cli, "run_migration_rollback_drill", fake_run_migration_rollback_drill
    )
    result = RUNNER.invoke(
        admin_cli.app,
        [
            "rollback-drill",
            "--rollback-mode",
            "restore",
            "--restore-reference",
            "backup-123",
            "--evidence-output",
            str(evidence_path),
        ],
    )

    assert result.exit_code == 0
    assert evidence_path.exists()
    assert "[OK] rollback_drill_evidence: evidence written to" in result.stdout
