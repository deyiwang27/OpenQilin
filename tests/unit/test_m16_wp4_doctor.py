from __future__ import annotations

from unittest.mock import patch

import pytest
from sqlalchemy.exc import OperationalError

from openqilin.shared_kernel.config import RuntimeSettings
from openqilin.shared_kernel.doctor import (
    DoctorCheck,
    DoctorReport,
    SystemDoctor,
    run_blocking_startup_checks,
)


def _set_required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENQILIN_ENV", "production")
    monkeypatch.setenv(
        "OPENQILIN_DATABASE_URL",
        "postgresql+psycopg://openqilin:openqilin@localhost:5432/openqilin",
    )
    monkeypatch.setenv("OPENQILIN_REDIS_URL", "redis://localhost:6379")
    monkeypatch.setenv("OPENQILIN_OPA_URL", "http://localhost:8181")


def test_doctor_report_all_passed_when_all_pass() -> None:
    report = DoctorReport(
        checks=(
            DoctorCheck(name="postgresql", status="pass", detail="ok"),
            DoctorCheck(name="redis", status="pass", detail="ok"),
        )
    )
    assert report.all_passed() is True
    assert report.has_failures() is False


def test_doctor_report_has_failures_when_any_fail() -> None:
    report = DoctorReport(
        checks=(
            DoctorCheck(name="postgresql", status="pass", detail="ok"),
            DoctorCheck(name="redis", status="fail", detail="down"),
        )
    )
    assert report.has_failures() is True
    assert report.all_passed() is False


def test_doctor_report_warn_does_not_trigger_failures() -> None:
    report = DoctorReport(
        checks=(
            DoctorCheck(name="otel", status="warn", detail="disabled"),
            DoctorCheck(name="grafana", status="warn", detail="disabled"),
        )
    )
    assert report.has_failures() is False
    assert report.all_passed() is False


def test_check_postgres_fails_when_url_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_required_env(monkeypatch)
    monkeypatch.setenv("OPENQILIN_DATABASE_URL", "")
    settings = RuntimeSettings()
    doctor = SystemDoctor(settings=settings)
    check = doctor._check_postgres()
    assert check.status == "fail"
    assert "not set" in check.detail


def test_check_redis_fails_when_url_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_required_env(monkeypatch)
    monkeypatch.setenv("OPENQILIN_REDIS_URL", "")
    settings = RuntimeSettings()
    doctor = SystemDoctor(settings=settings)
    check = doctor._check_redis()
    assert check.status == "fail"
    assert "not set" in check.detail


def test_check_opa_fails_when_url_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_required_env(monkeypatch)
    monkeypatch.setenv("OPENQILIN_OPA_URL", "")
    settings = RuntimeSettings()
    doctor = SystemDoctor(settings=settings)
    check = doctor._check_opa()
    assert check.status == "fail"
    assert "not set" in check.detail


def test_check_otel_warns_when_endpoint_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_required_env(monkeypatch)
    monkeypatch.setenv("OPENQILIN_OTLP_ENDPOINT", "")
    settings = RuntimeSettings()
    doctor = SystemDoctor(settings=settings)
    check = doctor._check_otel()
    assert check.status == "warn"


def test_check_grafana_warns_when_url_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_required_env(monkeypatch)
    monkeypatch.setenv("OPENQILIN_GRAFANA_PUBLIC_URL", "")
    settings = RuntimeSettings()
    doctor = SystemDoctor(settings=settings)
    check = doctor._check_grafana()
    assert check.status == "warn"


def test_check_discord_warns_when_token_none(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_required_env(monkeypatch)
    monkeypatch.delenv("OPENQILIN_DISCORD_BOT_TOKEN", raising=False)
    settings = RuntimeSettings()
    doctor = SystemDoctor(settings=settings)
    check = doctor._check_discord()
    assert check.status == "warn"


def test_check_discord_passes_when_token_set(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_required_env(monkeypatch)
    monkeypatch.setenv("OPENQILIN_DISCORD_BOT_TOKEN", "tok")
    settings = RuntimeSettings()
    doctor = SystemDoctor(settings=settings)
    check = doctor._check_discord()
    assert check.status == "pass"


def test_check_postgres_fails_on_connection_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_required_env(monkeypatch)
    settings = RuntimeSettings()
    doctor = SystemDoctor(settings=settings)
    with patch(
        "openqilin.shared_kernel.doctor.create_engine",
        side_effect=OperationalError("SELECT 1", {}, Exception("db down")),
    ):
        check = doctor._check_postgres()
    assert check.status == "fail"


def test_check_redis_fails_on_connection_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_required_env(monkeypatch)
    settings = RuntimeSettings()
    doctor = SystemDoctor(settings=settings)
    with patch(
        "openqilin.shared_kernel.doctor.redis.Redis.from_url",
        side_effect=ConnectionError("redis down"),
    ):
        check = doctor._check_redis()
    assert check.status == "fail"


def test_check_opa_fails_when_health_check_returns_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_required_env(monkeypatch)
    settings = RuntimeSettings()
    doctor = SystemDoctor(settings=settings)
    with patch("openqilin.shared_kernel.doctor.OPAPolicyRuntimeClient") as client_cls:
        client = client_cls.return_value
        client.health_check.return_value = False
        check = doctor._check_opa()
    assert check.status == "fail"
    client.close.assert_called_once()


def test_run_blocking_startup_checks_no_op_in_local_env() -> None:
    settings = RuntimeSettings(
        env="local_dev",
        database_url="",
        redis_url="",
        opa_url="",
    )
    with patch(
        "openqilin.shared_kernel.doctor.SystemDoctor.run",
        side_effect=AssertionError("doctor must be skipped in local env"),
    ):
        run_blocking_startup_checks(settings)


def test_run_blocking_startup_checks_raises_on_failure() -> None:
    settings = RuntimeSettings(
        env="production",
        database_url="postgresql+psycopg://openqilin:openqilin@localhost:5432/openqilin",
        redis_url="redis://localhost:6379",
        opa_url="http://localhost:8181",
    )
    with (
        patch.object(
            SystemDoctor,
            "_check_postgres",
            return_value=DoctorCheck(name="postgresql", status="fail", detail="db down"),
        ),
        patch.object(
            SystemDoctor,
            "_check_redis",
            return_value=DoctorCheck(name="redis", status="pass", detail="reachable"),
        ),
        patch.object(
            SystemDoctor,
            "_check_opa",
            return_value=DoctorCheck(name="opa", status="pass", detail="reachable"),
        ),
        patch.object(
            SystemDoctor,
            "_check_otel",
            return_value=DoctorCheck(name="otel", status="warn", detail="disabled"),
        ),
        patch.object(
            SystemDoctor,
            "_check_grafana",
            return_value=DoctorCheck(name="grafana", status="warn", detail="disabled"),
        ),
        patch.object(
            SystemDoctor,
            "_check_discord",
            return_value=DoctorCheck(name="discord", status="warn", detail="disabled"),
        ),
    ):
        with pytest.raises(RuntimeError) as error:
            run_blocking_startup_checks(settings)
    assert "postgresql: db down" in str(error.value)


def test_agent_registry_check_skipped_when_postgres_fails() -> None:
    settings = RuntimeSettings(
        env="production",
        database_url="postgresql+psycopg://openqilin:openqilin@localhost:5432/openqilin",
        redis_url="redis://localhost:6379",
        opa_url="http://localhost:8181",
    )
    with (
        patch.object(
            SystemDoctor,
            "_check_postgres",
            return_value=DoctorCheck(name="postgresql", status="fail", detail="db down"),
        ),
        patch.object(
            SystemDoctor,
            "_check_redis",
            return_value=DoctorCheck(name="redis", status="pass", detail="reachable"),
        ),
        patch.object(
            SystemDoctor,
            "_check_opa",
            return_value=DoctorCheck(name="opa", status="pass", detail="reachable"),
        ),
        patch.object(
            SystemDoctor,
            "_check_otel",
            return_value=DoctorCheck(name="otel", status="warn", detail="disabled"),
        ),
        patch.object(
            SystemDoctor,
            "_check_grafana",
            return_value=DoctorCheck(name="grafana", status="warn", detail="disabled"),
        ),
        patch.object(
            SystemDoctor,
            "_check_discord",
            return_value=DoctorCheck(name="discord", status="warn", detail="disabled"),
        ),
    ):
        report = SystemDoctor(settings=settings).run()

    agent_registry = next(check for check in report.checks if check.name == "agent_registry")
    assert agent_registry.status == "warn"
    assert "skipped" in agent_registry.detail
