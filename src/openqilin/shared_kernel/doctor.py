"""Operator-facing infrastructure diagnostic tool."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import httpx
import redis
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from openqilin.policy_runtime_integration.client import OPAPolicyRuntimeClient
from openqilin.shared_kernel.config import RuntimeSettings

DoctorStatus = Literal["pass", "warn", "fail"]

_LOCAL_ENV_VALUES = frozenset({"local", "local_dev", "development", "test", "ci"})
_INFRA_HINT = "Run: docker compose --profile core up -d"
_MIGRATION_HINT = "Run: uv run alembic upgrade head"


@dataclass(frozen=True, slots=True)
class DoctorCheck:
    name: str
    status: DoctorStatus
    detail: str


@dataclass(frozen=True, slots=True)
class DoctorReport:
    checks: tuple[DoctorCheck, ...]

    def all_passed(self) -> bool:
        """True when every check has status 'pass'."""
        return all(c.status == "pass" for c in self.checks)

    def has_failures(self) -> bool:
        """True when one or more checks have status 'fail'."""
        return any(c.status == "fail" for c in self.checks)


class SystemDoctor:
    """Checks all required infrastructure connections and reports pass/warn/fail."""

    def __init__(self, *, settings: RuntimeSettings) -> None:
        self._settings = settings

    def run(self) -> DoctorReport:
        """Run all checks and return an aggregated report.

        Check order: postgresql → redis → opa → otel → grafana → discord → agent_registry.
        agent_registry check is skipped (reported as 'warn') when postgresql check fails.
        """
        postgres_check = self._check_postgres()
        checks = [
            postgres_check,
            self._check_redis(),
            self._check_opa(),
            self._check_otel(),
            self._check_grafana(),
            self._check_discord(),
        ]
        if postgres_check.status == "fail":
            checks.append(
                DoctorCheck(
                    name="agent_registry",
                    status="warn",
                    detail="skipped — postgresql check failed",
                )
            )
        else:
            checks.append(self._check_agent_registry())
        return DoctorReport(checks=tuple(checks))

    def _check_postgres(self) -> DoctorCheck:
        """Connect to PostgreSQL, run SELECT 1, query alembic_version table."""
        database_url = self._settings.database_url.strip()
        if not database_url:
            return DoctorCheck(
                name="postgresql",
                status="fail",
                detail=f"OPENQILIN_DATABASE_URL not set. {_INFRA_HINT}",
            )

        engine: Engine | None = None
        try:
            engine = create_engine(database_url, pool_pre_ping=True)
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
                table_count = connection.execute(
                    text(
                        "SELECT COUNT(*) FROM information_schema.tables "
                        "WHERE table_schema='public' AND table_name='alembic_version'"
                    )
                ).scalar()
                if int(table_count or 0) == 0:
                    return DoctorCheck(
                        name="postgresql",
                        status="fail",
                        detail=f"Migrations not applied. {_MIGRATION_HINT}",
                    )

                versions = [
                    str(version)
                    for version in connection.execute(
                        text("SELECT version_num FROM alembic_version")
                    ).scalars()
                    if version is not None
                ]
                version_detail = ",".join(versions) if versions else "unknown"
            return DoctorCheck(
                name="postgresql",
                status="pass",
                detail=f"connected; migration_version={version_detail}",
            )
        except Exception as error:
            return DoctorCheck(
                name="postgresql",
                status="fail",
                detail=f"{error}. {_INFRA_HINT}",
            )
        finally:
            if engine is not None:
                engine.dispose()

    def _check_redis(self) -> DoctorCheck:
        """Ping the Redis server."""
        redis_url = self._settings.redis_url.strip()
        if not redis_url:
            return DoctorCheck(
                name="redis",
                status="fail",
                detail=f"OPENQILIN_REDIS_URL not set. {_INFRA_HINT}",
            )

        client: redis.Redis | None = None  # type: ignore[type-arg]
        try:
            client = redis.Redis.from_url(redis_url, decode_responses=True)
            client.ping()
            return DoctorCheck(name="redis", status="pass", detail="reachable")
        except Exception as error:
            return DoctorCheck(name="redis", status="fail", detail=f"{error}. {_INFRA_HINT}")
        finally:
            if client is not None:
                client.close()

    def _check_opa(self) -> DoctorCheck:
        """Call OPA /health endpoint; verify bundle is loaded."""
        opa_url = self._settings.opa_url.strip()
        if not opa_url:
            return DoctorCheck(
                name="opa",
                status="fail",
                detail=f"OPENQILIN_OPA_URL not set. {_INFRA_HINT}",
            )

        client: OPAPolicyRuntimeClient | None = None
        try:
            client = OPAPolicyRuntimeClient(opa_url=opa_url)
            if not client.health_check():
                return DoctorCheck(
                    name="opa",
                    status="fail",
                    detail=f"OPA unreachable at {opa_url}. {_INFRA_HINT}",
                )
            active_version = client.get_active_policy_version()
            return DoctorCheck(
                name="opa",
                status="pass",
                detail=f"reachable; policy_version={active_version}",
            )
        except Exception as error:
            return DoctorCheck(name="opa", status="fail", detail=f"{error}. {_INFRA_HINT}")
        finally:
            if client is not None:
                client.close()

    def _check_otel(self) -> DoctorCheck:
        """HTTP GET to OTLP endpoint root (warn-only)."""
        endpoint = self._settings.otlp_endpoint.strip()
        if not endpoint:
            return DoctorCheck(
                name="otel",
                status="warn",
                detail="OPENQILIN_OTLP_ENDPOINT not set (observability disabled)",
            )

        try:
            with httpx.Client(timeout=3.0) as client:
                response = client.get(endpoint)
            if response.status_code in {200, 400}:
                return DoctorCheck(
                    name="otel",
                    status="pass",
                    detail=f"collector reachable (status={response.status_code})",
                )
            return DoctorCheck(
                name="otel",
                status="warn",
                detail=f"collector returned status={response.status_code}",
            )
        except Exception as error:
            return DoctorCheck(
                name="otel",
                status="warn",
                detail=f"{error}. OTel export will be silently dropped",
            )

    def _check_grafana(self) -> DoctorCheck:
        """HTTP GET to Grafana API /health (warn-only)."""
        grafana_url = self._settings.grafana_public_url.strip()
        if not grafana_url:
            return DoctorCheck(
                name="grafana",
                status="warn",
                detail="OPENQILIN_GRAFANA_PUBLIC_URL not set (dashboard URL not announced)",
            )

        health_url = f"{grafana_url.rstrip('/')}/api/health"
        try:
            with httpx.Client(timeout=3.0) as client:
                response = client.get(health_url)
            return DoctorCheck(
                name="grafana",
                status="pass",
                detail=f"reachable (status={response.status_code})",
            )
        except Exception as error:
            return DoctorCheck(name="grafana", status="warn", detail=str(error))

    def _check_discord(self) -> DoctorCheck:
        """Verify discord_bot_token is configured (warn-only; no live API call)."""
        token = (self._settings.discord_bot_token or "").strip()
        if not token:
            return DoctorCheck(
                name="discord",
                status="warn",
                detail="OPENQILIN_DISCORD_BOT_TOKEN not set (Discord integration disabled)",
            )
        return DoctorCheck(name="discord", status="pass", detail="token configured")

    def _check_agent_registry(self) -> DoctorCheck:
        """Query agent_registry table for institutional agents (requires postgres)."""
        database_url = self._settings.database_url.strip()
        if not database_url:
            return DoctorCheck(
                name="agent_registry",
                status="warn",
                detail="skipped — postgresql not configured",
            )

        engine: Engine | None = None
        try:
            engine = create_engine(database_url, pool_pre_ping=True)
            with engine.connect() as connection:
                result = connection.execute(
                    text("SELECT COUNT(*) FROM agent_registry WHERE agent_type = 'institutional'")
                ).scalar()
            count = int(result or 0)
            if count > 0:
                return DoctorCheck(
                    name="agent_registry",
                    status="pass",
                    detail=f"{count} institutional agents registered",
                )
            return DoctorCheck(
                name="agent_registry",
                status="warn",
                detail="agent registry empty — run bootstrap or restart app",
            )
        except Exception as error:
            return DoctorCheck(name="agent_registry", status="warn", detail=str(error))
        finally:
            if engine is not None:
                engine.dispose()


def run_blocking_startup_checks(settings: RuntimeSettings) -> None:
    """Run only blocking checks (postgresql, redis, opa) at app startup.

    Raises RuntimeError with actionable message if any blocking check fails.
    Called by create_control_plane_app() before build_runtime_services().
    """
    if settings.env.strip().lower() in _LOCAL_ENV_VALUES:
        return

    doctor = SystemDoctor(settings=settings)
    blocking_names = {"postgresql", "redis", "opa"}
    report = doctor.run()
    failures = [c for c in report.checks if c.name in blocking_names and c.status == "fail"]
    if failures:
        details = "; ".join(f"{c.name}: {c.detail}" for c in failures)
        raise RuntimeError(
            f"Startup blocked — infrastructure check failed: {details}. "
            "Run: docker compose --profile core up -d"
        )
