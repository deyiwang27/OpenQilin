"""Typer entrypoint for administrative commands."""

from __future__ import annotations

import os
import platform
import sys
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import httpx
import typer
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient

from openqilin.apps.api_app import create_app
from openqilin.apps.communication_worker import main as communication_worker_main
from openqilin.apps.orchestrator_worker import main as orchestrator_worker_main
from openqilin.data_access.db.engine import ping_database, resolve_database_url
from openqilin.shared_kernel.config import RuntimeSettings

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ALEMBIC_INI = PROJECT_ROOT / "alembic.ini"
OWNER_COMMAND_ROUTE = "/v1/owner/commands"
DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"

app = typer.Typer(help="OpenQilin administrative CLI.")


@dataclass(frozen=True, slots=True)
class CheckResult:
    """Single command check result."""

    name: str
    success: bool
    details: str


def _route_paths(app_instance: FastAPI) -> set[str]:
    """Collect route paths from FastAPI app in a type-safe way."""

    paths: set[str] = set()
    for route in app_instance.routes:
        path = getattr(route, "path", None)
        if isinstance(path, str):
            paths.add(path)
    return paths


def apply_migrations(alembic_ini_path: Path) -> None:
    """Apply Alembic migrations to `head`."""

    if not alembic_ini_path.exists():
        raise FileNotFoundError(f"alembic config not found: {alembic_ini_path}")
    config = Config(str(alembic_ini_path))
    command.upgrade(config, "head")


def run_migration_check(alembic_ini_path: Path) -> CheckResult:
    """Execute migration check and map into command result."""

    try:
        apply_migrations(alembic_ini_path)
    except Exception as error:
        return CheckResult("migrate", False, f"migration failed: {error}")
    return CheckResult("migrate", True, "migrations applied to head")


def _smoke_payload() -> dict[str, object]:
    return {
        "command": "run_task",
        "args": ["smoke"],
        "idempotency_key": f"idem-admin-smoke-{uuid4()}",
    }


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
    response = client.post(
        OWNER_COMMAND_ROUTE,
        headers={
            "X-OpenQilin-User-Id": "owner_admin_smoke",
            "X-OpenQilin-Connector": "discord",
            "X-OpenQilin-Trace-Id": "trace-admin-smoke",
        },
        json=_smoke_payload(),
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
    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.post(
                route_url,
                headers={
                    "X-OpenQilin-User-Id": "owner_admin_smoke",
                    "X-OpenQilin-Connector": "discord",
                    "X-OpenQilin-Trace-Id": "trace-admin-smoke",
                },
                json=_smoke_payload(),
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
    else:
        migration_result = run_migration_check(alembic_ini_path)
        results.append(migration_result)
        if not migration_result.success:
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

    masked_database_url = configured_database_url
    if "@" in configured_database_url and "://" in configured_database_url:
        prefix, suffix = configured_database_url.split("://", 1)
        if "@" in suffix:
            _, host_path = suffix.split("@", 1)
            masked_database_url = f"{prefix}://***@{host_path}"

    results: list[CheckResult] = [
        CheckResult("diagnostics_env", True, f"env={settings.env}"),
        CheckResult("diagnostics_python", True, f"python={platform.python_version()}"),
        CheckResult("diagnostics_platform", True, f"platform={platform.platform()}"),
        CheckResult("diagnostics_owner_command_route", route_present, OWNER_COMMAND_ROUTE),
        CheckResult(
            "diagnostics_worker_entrypoints",
            callable(orchestrator_worker_main) and callable(communication_worker_main),
            "worker entrypoints importable",
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
        help="Base URL for live smoke probe (used unless --smoke-in-process is set).",
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
        help="Base URL for live smoke probe.",
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
