"""Typer entrypoint for administrative commands."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

import httpx
import typer
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text

from openqilin.apps.api_app import create_app
from openqilin.apps.communication_worker import main as communication_worker_main
from openqilin.apps.discord_bot_worker import main as discord_bot_worker_main
from openqilin.apps.orchestrator_worker import main as orchestrator_worker_main
from openqilin.control_plane.identity.connector_security import sign_payload_hash
from openqilin.data_access.db.engine import (
    check_pgvector_extension,
    create_sqlalchemy_engine,
    ping_database,
    resolve_database_url,
)
from openqilin.shared_kernel.config import RuntimeSettings
from openqilin.shared_kernel.startup_validation import enforce_connector_secret_hardening

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ALEMBIC_INI = PROJECT_ROOT / "alembic.ini"
OWNER_COMMAND_ROUTE = "/v1/owner/commands"
DEFAULT_API_BASE_URL = RuntimeSettings().smoke_api_base_url
DEFAULT_ROLLBACK_DRILL_EVIDENCE = (
    PROJECT_ROOT / "implementation/v1/planning/artifacts/migration_rollback_drill_latest.json"
)

app = typer.Typer(help="OpenQilin administrative CLI.")


@dataclass(frozen=True, slots=True)
class CheckResult:
    """Single command check result."""

    name: str
    success: bool
    details: str


class RollbackMode(str, Enum):
    """Rollback drill mode selector."""

    RESTORE = "restore"
    DOWNGRADE = "downgrade"


def _route_paths(app_instance: FastAPI) -> set[str]:
    """Collect route paths from FastAPI app in a type-safe way."""

    paths: set[str] = set()
    for route in app_instance.routes:
        path = getattr(route, "path", None)
        if isinstance(path, str):
            paths.add(path)
    return paths


def _mask_database_url(database_url: str) -> str:
    """Mask credentials for safe operator output."""

    if "@" not in database_url or "://" not in database_url:
        return database_url
    prefix, suffix = database_url.split("://", 1)
    if "@" not in suffix:
        return database_url
    _, host_path = suffix.split("@", 1)
    return f"{prefix}://***@{host_path}"


def _build_alembic_config(
    *,
    alembic_ini_path: Path,
    database_url_override: str | None = None,
) -> tuple[Config, str]:
    """Create Alembic config with resolved runtime database URL."""

    if not alembic_ini_path.exists():
        raise FileNotFoundError(f"alembic config not found: {alembic_ini_path}")
    config = Config(str(alembic_ini_path))
    database_url = resolve_database_url(
        override=database_url_override,
        alembic_ini_path=alembic_ini_path,
    )
    config.set_main_option("sqlalchemy.url", database_url)
    return config, database_url


def check_knowledge_embedding_table(database_url: str) -> tuple[bool, str]:
    """Verify baseline embedding table is available."""

    engine = None
    try:
        engine = create_sqlalchemy_engine(database_url)
        with engine.connect() as connection:
            table_name = connection.execute(
                text("SELECT to_regclass('public.knowledge_embedding')")
            ).scalar()
        if table_name in {"knowledge_embedding", "public.knowledge_embedding"}:
            return True, "knowledge_embedding table is available"
        return False, "knowledge_embedding table is missing"
    except Exception as error:
        return False, f"knowledge_embedding check failed: {error}"
    finally:
        if engine is not None:
            engine.dispose()


def run_migration_rollback_drill(
    *,
    alembic_ini_path: Path,
    database_url: str | None,
    rollback_mode: RollbackMode,
    rollback_revision: str,
    restore_reference: str | None,
    allow_downgrade_destructive: bool = False,
) -> tuple[list[CheckResult], str]:
    """Run migration validation plus rollback drill checks."""

    try:
        config, resolved_database_url = _build_alembic_config(
            alembic_ini_path=alembic_ini_path,
            database_url_override=database_url,
        )
    except Exception as error:
        return [CheckResult("migration_drill_preflight", False, str(error))], ""

    results: list[CheckResult] = []

    try:
        command.upgrade(config, "head")
        results.append(CheckResult("migration_upgrade_head", True, "migrations applied to head"))
    except Exception as error:
        results.append(
            CheckResult("migration_upgrade_head", False, f"migration head upgrade failed: {error}")
        )
        return results, resolved_database_url

    pgvector_ok, pgvector_message = check_pgvector_extension(resolved_database_url)
    results.append(CheckResult("migration_contract_pgvector", pgvector_ok, pgvector_message))
    if not pgvector_ok:
        return results, resolved_database_url

    embedding_ok, embedding_message = check_knowledge_embedding_table(resolved_database_url)
    results.append(
        CheckResult("migration_contract_embedding_table", embedding_ok, embedding_message)
    )
    if not embedding_ok:
        return results, resolved_database_url

    if rollback_mode is RollbackMode.RESTORE:
        reference = (restore_reference or "").strip()
        if not reference:
            results.append(
                CheckResult(
                    "rollback_restore_reference",
                    False,
                    "restore mode requires --restore-reference (backup or snapshot id)",
                )
            )
            return results, resolved_database_url
        results.append(
            CheckResult(
                "rollback_restore_plan",
                True,
                f"restore-from-backup reference recorded: {reference}",
            )
        )
        return results, resolved_database_url

    if not allow_downgrade_destructive:
        results.append(
            CheckResult(
                "rollback_downgrade_guard",
                False,
                "downgrade mode is blocked by default; pass --allow-downgrade-destructive only for disposable databases",
            )
        )
        return results, resolved_database_url

    try:
        command.downgrade(config, rollback_revision)
        results.append(
            CheckResult("rollback_downgrade", True, f"downgraded to revision {rollback_revision}")
        )
    except Exception as error:
        results.append(
            CheckResult(
                "rollback_downgrade",
                False,
                f"downgrade to revision {rollback_revision} failed: {error}",
            )
        )
        return results, resolved_database_url

    try:
        command.upgrade(config, "head")
        results.append(CheckResult("rollback_recover_head", True, "re-applied migrations to head"))
    except Exception as error:
        results.append(
            CheckResult("rollback_recover_head", False, f"re-upgrade to head failed: {error}")
        )
        return results, resolved_database_url

    rollback_pg_ok, rollback_pg_message = check_pgvector_extension(resolved_database_url)
    results.append(CheckResult("rollback_contract_pgvector", rollback_pg_ok, rollback_pg_message))
    if not rollback_pg_ok:
        return results, resolved_database_url

    rollback_embedding_ok, rollback_embedding_message = check_knowledge_embedding_table(
        resolved_database_url
    )
    results.append(
        CheckResult(
            "rollback_contract_embedding_table",
            rollback_embedding_ok,
            rollback_embedding_message,
        )
    )
    return results, resolved_database_url


def build_migration_drill_evidence_payload(
    *,
    release_version: str,
    operator: str,
    reason: str,
    rollback_mode: RollbackMode,
    rollback_revision: str,
    restore_reference: str | None,
    database_url: str,
    results: list[CheckResult],
) -> dict[str, Any]:
    """Build deterministic evidence payload for rollback drill artifacts."""

    return {
        "timestamp_utc": datetime.now(tz=UTC).isoformat(),
        "release_version": release_version,
        "operator": operator,
        "reason": reason,
        "rollback_mode": rollback_mode.value,
        "rollback_revision": rollback_revision if rollback_mode is RollbackMode.DOWNGRADE else None,
        "restore_reference": (
            (restore_reference or "").strip() if rollback_mode is RollbackMode.RESTORE else None
        ),
        "database_url": _mask_database_url(database_url),
        "overall_success": all(result.success for result in results),
        "steps": [
            {"name": result.name, "success": result.success, "details": result.details}
            for result in results
        ],
    }


def write_migration_drill_evidence(payload: Mapping[str, Any], output_path: Path) -> Path:
    """Persist rollback-drill evidence payload."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return output_path


def apply_migrations(alembic_ini_path: Path) -> None:
    """Apply Alembic migrations to `head`."""

    config, _ = _build_alembic_config(alembic_ini_path=alembic_ini_path)
    command.upgrade(config, "head")


def run_migration_check(alembic_ini_path: Path) -> CheckResult:
    """Execute migration check and map into command result."""

    try:
        apply_migrations(alembic_ini_path)
    except Exception as error:
        return CheckResult("migrate", False, f"migration failed: {error}")
    return CheckResult("migrate", True, "migrations applied to head")


def _serialize_for_hash(data: Mapping[str, Any]) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _smoke_payload() -> tuple[dict[str, Any], str]:
    idempotency_key = f"idem-admin-smoke-{uuid4()}"
    trace_id = f"trace-admin-smoke-{uuid4()}"
    core_payload: dict[str, Any] = {
        "message_id": f"msg-admin-smoke-{uuid4()}",
        "trace_id": trace_id,
        "sender": {"actor_id": "owner_admin_smoke", "actor_role": "owner"},
        "recipients": [{"recipient_id": "sandbox", "recipient_type": "runtime"}],
        "message_type": "command",
        "priority": "normal",
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "content": "admin smoke command",
        "project_id": "smoke-project",
        "connector": {
            "channel": "discord",
            "external_message_id": f"ext-admin-smoke-{uuid4()}",
            "actor_external_id": "owner_admin_smoke",
            "idempotency_key": idempotency_key,
            "discord_context": {
                "guild_id": "guild-admin-smoke",
                "channel_id": "channel-admin-smoke",
                "channel_type": "text",
                "chat_class": "project",
            },
        },
        "command": {
            "action": "run_task",
            "target": "sandbox",
            "payload": {"args": ["smoke"]},
        },
    }
    raw_payload_hash = hashlib.sha256(_serialize_for_hash(core_payload)).hexdigest()
    connector = dict(core_payload["connector"])
    connector["raw_payload_hash"] = raw_payload_hash
    payload = dict(core_payload)
    payload["connector"] = connector
    return payload, raw_payload_hash


def run_in_process_smoke_check() -> CheckResult:
    """Exercise owner-command ingress path in-process."""

    app_instance = create_app()
    if OWNER_COMMAND_ROUTE not in _route_paths(app_instance):
        return CheckResult(
            "smoke_owner_command_route",
            False,
            f"required route missing: {OWNER_COMMAND_ROUTE}",
        )

    client = TestClient(app_instance)
    payload, raw_payload_hash = _smoke_payload()
    signature = sign_payload_hash(raw_payload_hash, RuntimeSettings().connector_shared_secret)
    response = client.post(
        OWNER_COMMAND_ROUTE,
        headers={
            "X-OpenQilin-Trace-Id": str(payload["trace_id"]),
            "X-External-Channel": "discord",
            "X-External-Actor-Id": "owner_admin_smoke",
            "X-Idempotency-Key": str(payload["connector"]["idempotency_key"]),
            "X-OpenQilin-Signature": signature,
        },
        json=payload,
    )
    if response.status_code != 202:
        return CheckResult(
            "smoke_owner_command_ingress_in_process",
            False,
            f"expected 202 from {OWNER_COMMAND_ROUTE}, got {response.status_code}",
        )

    body = response.json()
    return CheckResult(
        "smoke_owner_command_ingress_in_process",
        True,
        f"accepted task_id={body.get('task_id', 'missing-task-id')}",
    )


def run_smoke_check(*, api_base_url: str, timeout_seconds: float = 5.0) -> CheckResult:
    """Exercise owner-command ingress path against a running API service."""

    route_url = f"{api_base_url.rstrip('/')}{OWNER_COMMAND_ROUTE}"
    payload, raw_payload_hash = _smoke_payload()
    signature = sign_payload_hash(raw_payload_hash, RuntimeSettings().connector_shared_secret)
    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.post(
                route_url,
                headers={
                    "X-OpenQilin-Trace-Id": str(payload["trace_id"]),
                    "X-External-Channel": "discord",
                    "X-External-Actor-Id": "owner_admin_smoke",
                    "X-Idempotency-Key": str(payload["connector"]["idempotency_key"]),
                    "X-OpenQilin-Signature": signature,
                },
                json=payload,
            )
    except Exception as error:
        return CheckResult(
            "smoke_owner_command_ingress_live",
            False,
            f"request failed for {route_url}: {error}",
        )

    if response.status_code != 202:
        return CheckResult(
            "smoke_owner_command_ingress_live",
            False,
            f"expected 202 from {route_url}, got {response.status_code}",
        )

    body = response.json()
    return CheckResult(
        "smoke_owner_command_ingress_live",
        True,
        f"accepted task_id={body.get('task_id', 'missing-task-id')}",
    )


def run_bootstrap_checks(
    *,
    skip_migrate: bool,
    alembic_ini_path: Path,
    smoke_api_base_url: str,
    smoke_in_process: bool,
) -> list[CheckResult]:
    """Run baseline bootstrap checks used by `bootstrap` command."""

    results: list[CheckResult] = []
    if skip_migrate:
        results.append(CheckResult("migrate", True, "migration step skipped by flag"))
        results.append(
            CheckResult("pgvector_extension", True, "pgvector extension check skipped by flag")
        )
    else:
        migration_result = run_migration_check(alembic_ini_path)
        results.append(migration_result)
        if not migration_result.success:
            return results
        database_url = resolve_database_url(alembic_ini_path=alembic_ini_path)
        pgvector_ok, pgvector_message = check_pgvector_extension(database_url)
        pgvector_result = CheckResult("pgvector_extension", pgvector_ok, pgvector_message)
        results.append(pgvector_result)
        if not pgvector_ok:
            return results
    smoke_result = (
        run_in_process_smoke_check()
        if smoke_in_process
        else run_smoke_check(api_base_url=smoke_api_base_url)
    )
    results.append(smoke_result)
    return results


def run_diagnostics_checks(
    *,
    check_db: bool,
    database_url: str | None,
    alembic_ini_path: Path,
) -> list[CheckResult]:
    """Collect runtime diagnostics checks."""

    settings = RuntimeSettings()
    api_app = create_app()
    route_present = OWNER_COMMAND_ROUTE in _route_paths(api_app)
    configured_database_url = resolve_database_url(
        override=database_url,
        alembic_ini_path=alembic_ini_path,
    )
    masked_database_url = _mask_database_url(configured_database_url)

    results: list[CheckResult] = [
        CheckResult("diagnostics_env", True, f"env={settings.env}"),
        CheckResult("diagnostics_python", True, f"python={platform.python_version()}"),
        CheckResult("diagnostics_platform", True, f"platform={platform.platform()}"),
        CheckResult("diagnostics_owner_command_route", route_present, OWNER_COMMAND_ROUTE),
        CheckResult(
            "diagnostics_worker_entrypoints",
            callable(orchestrator_worker_main)
            and callable(communication_worker_main)
            and callable(discord_bot_worker_main),
            "worker entrypoints importable",
        ),
        CheckResult(
            "diagnostics_connector_secret_hardening",
            _validate_connector_secret_hardening(settings),
            "non-local runtime requires non-default connector secret",
        ),
        CheckResult(
            "diagnostics_database_url",
            True,
            masked_database_url,
        ),
    ]

    if check_db:
        db_ok, db_message = ping_database(configured_database_url)
        results.append(CheckResult("diagnostics_database_ping", db_ok, db_message))

    return results


def _validate_connector_secret_hardening(settings: RuntimeSettings) -> bool:
    """Return whether startup secret-hardening contract is satisfied."""

    try:
        enforce_connector_secret_hardening(settings)
    except RuntimeError:
        return False
    return True


def _render_and_exit(results: list[CheckResult]) -> None:
    """Render check output and exit with explicit success/failure status."""

    has_failure = False
    for result in results:
        status_label = "OK" if result.success else "FAIL"
        typer.echo(f"[{status_label}] {result.name}: {result.details}")
        if not result.success:
            has_failure = True
    raise typer.Exit(code=1 if has_failure else 0)


@app.command()
def migrate(
    alembic_ini: Path = typer.Option(
        DEFAULT_ALEMBIC_INI,
        "--alembic-ini",
        help="Path to Alembic config file.",
    ),
) -> None:
    """Apply forward-only database migrations."""

    _render_and_exit([run_migration_check(alembic_ini)])


@app.command()
def bootstrap(
    skip_migrate: bool = typer.Option(
        False,
        "--skip-migrate",
        help="Skip migration step and run remaining bootstrap checks.",
    ),
    alembic_ini: Path = typer.Option(
        DEFAULT_ALEMBIC_INI,
        "--alembic-ini",
        help="Path to Alembic config file.",
    ),
    smoke_api_base_url: str = typer.Option(
        DEFAULT_API_BASE_URL,
        "--smoke-api-base-url",
        help=(
            "Base URL for live smoke probe (used unless --smoke-in-process is set). "
            "Default comes from OPENQILIN_SMOKE_API_BASE_URL."
        ),
    ),
    smoke_in_process: bool = typer.Option(
        False,
        "--smoke-in-process",
        help="Run in-process smoke check instead of live API probe.",
    ),
) -> None:
    """Run baseline bootstrap and readiness checks."""

    _render_and_exit(
        run_bootstrap_checks(
            skip_migrate=skip_migrate,
            alembic_ini_path=alembic_ini,
            smoke_api_base_url=smoke_api_base_url,
            smoke_in_process=smoke_in_process,
        )
    )


@app.command()
def smoke(
    api_base_url: str = typer.Option(
        DEFAULT_API_BASE_URL,
        "--api-base-url",
        help="Base URL for live smoke probe. Default comes from OPENQILIN_SMOKE_API_BASE_URL.",
    ),
    in_process: bool = typer.Option(
        False,
        "--in-process",
        help="Run in-process smoke check instead of live API probe.",
    ),
) -> None:
    """Run operational smoke checks."""

    result = (
        run_in_process_smoke_check() if in_process else run_smoke_check(api_base_url=api_base_url)
    )
    _render_and_exit([result])


@app.command("rollback-drill")
def rollback_drill(
    rollback_mode: RollbackMode = typer.Option(
        RollbackMode.RESTORE,
        "--rollback-mode",
        help="Rollback drill mode: restore (policy path) or downgrade (ephemeral-db drill).",
    ),
    rollback_revision: str = typer.Option(
        "-1",
        "--rollback-revision",
        help="Revision target used only when --rollback-mode downgrade.",
    ),
    allow_downgrade_destructive: bool = typer.Option(
        False,
        "--allow-downgrade-destructive",
        help="Explicitly allow destructive downgrade drill mode (disposable databases only).",
    ),
    restore_reference: str | None = typer.Option(
        None,
        "--restore-reference",
        help="Backup/snapshot reference required when --rollback-mode restore.",
    ),
    release_version: str = typer.Option(
        "0.1.0-dev",
        "--release-version",
        help="Release version tag recorded in rollback drill evidence.",
    ),
    operator: str = typer.Option(
        "unknown_operator",
        "--operator",
        help="Operator identity recorded in rollback drill evidence.",
    ),
    reason: str = typer.Option(
        "release_readiness_drill",
        "--reason",
        help="Reason string recorded in rollback drill evidence.",
    ),
    evidence_output: Path = typer.Option(
        DEFAULT_ROLLBACK_DRILL_EVIDENCE,
        "--evidence-output",
        help="Path for writing rollback drill evidence JSON.",
    ),
    database_url: str | None = typer.Option(
        None,
        "--database-url",
        help="Optional database URL override used for migration drill.",
    ),
    alembic_ini: Path = typer.Option(
        DEFAULT_ALEMBIC_INI,
        "--alembic-ini",
        help="Path to Alembic config file used for drill execution.",
    ),
) -> None:
    """Run migration validation and rollback drill with evidence output."""

    results, resolved_database_url = run_migration_rollback_drill(
        alembic_ini_path=alembic_ini,
        database_url=database_url,
        rollback_mode=rollback_mode,
        rollback_revision=rollback_revision,
        restore_reference=restore_reference,
        allow_downgrade_destructive=allow_downgrade_destructive,
    )
    if not resolved_database_url:
        resolved_database_url = resolve_database_url(
            override=database_url,
            alembic_ini_path=alembic_ini,
        )
    payload = build_migration_drill_evidence_payload(
        release_version=release_version,
        operator=operator,
        reason=reason,
        rollback_mode=rollback_mode,
        rollback_revision=rollback_revision,
        restore_reference=restore_reference,
        database_url=resolved_database_url,
        results=results,
    )
    try:
        output_path = write_migration_drill_evidence(payload, evidence_output)
        results.append(
            CheckResult(
                "rollback_drill_evidence",
                True,
                f"evidence written to {output_path}",
            )
        )
    except Exception as error:
        results.append(
            CheckResult(
                "rollback_drill_evidence",
                False,
                f"failed to write evidence file: {error}",
            )
        )
    _render_and_exit(results)


@app.command()
def diagnostics(
    check_db: bool = typer.Option(
        False,
        "--check-db",
        help="Include live database connectivity probe.",
    ),
    database_url: str | None = typer.Option(
        None,
        "--database-url",
        help="Optional database URL override for diagnostics.",
    ),
    alembic_ini: Path = typer.Option(
        DEFAULT_ALEMBIC_INI,
        "--alembic-ini",
        help="Path to Alembic config file used for URL resolution fallback.",
    ),
) -> None:
    """Run runtime diagnostics."""

    results = run_diagnostics_checks(
        check_db=check_db,
        database_url=database_url,
        alembic_ini_path=alembic_ini,
    )
    _render_and_exit(results)


if __name__ == "__main__":
    if "PYTHONASYNCIODEBUG" not in os.environ:
        os.environ["PYTHONASYNCIODEBUG"] = "0"
    sys.exit(app())
