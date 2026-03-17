"""Unit tests for M12-WP5: OTel Export Wiring.

Tests cover:
- configure_tracer / configure_metrics / configure_otel_logs import and invocation
- OTelAuditWriter: PostgreSQL write (primary, fail-hard) and OTel log (secondary, fail-soft)
- RuntimeSettings.otlp_endpoint default and env population
- dependencies.py wiring: database_url set → OTelAuditWriter; empty → InMemoryAuditWriter
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from openqilin.observability.audit.audit_writer import (
    AuditEvent,
    InMemoryAuditWriter,
    OTelAuditWriter,
    _is_hex_trace_id,
)
from openqilin.shared_kernel.config import RuntimeSettings


# ---------------------------------------------------------------------------
# _is_hex_trace_id helper
# ---------------------------------------------------------------------------


def test_is_hex_trace_id_valid_uuid_hex() -> None:
    assert _is_hex_trace_id("550e8400e29b41d4a716446655440000") is True


def test_is_hex_trace_id_with_dashes() -> None:
    assert _is_hex_trace_id("550e8400-e29b-41d4-a716-446655440000") is True


def test_is_hex_trace_id_invalid() -> None:
    assert _is_hex_trace_id("not-a-hex-string-xxx") is False


# ---------------------------------------------------------------------------
# OTelAuditWriter — PostgreSQL primary write
# ---------------------------------------------------------------------------


def _make_pg_record(event_id: str = "evt-001") -> MagicMock:
    record = MagicMock()
    record.event_id = event_id
    record.event_type = "policy_decision"
    record.trace_id = "trace-abc"
    record.task_id = "task-123"
    record.principal_id = "user-1"
    record.principal_role = "owner"
    record.action = "test_source"
    record.decision = "allow"
    record.rule_ids = ("POL-001",)
    record.payload = {}
    record.created_at = datetime.now(tz=UTC)
    return record


def test_otel_audit_writer_calls_postgres_repo() -> None:
    """PostgreSQL write is called for every event."""
    audit_repo = MagicMock()
    audit_repo.write_event.return_value = _make_pg_record()

    writer = OTelAuditWriter(audit_repo=audit_repo)
    with patch("openqilin.observability.audit.audit_writer._emit_otel_log_record"):
        writer.write_event(
            event_type="policy_decision",
            outcome="allow",
            trace_id="trace-abc",
            request_id="req-1",
            task_id="task-123",
            principal_id="user-1",
            source="test_source",
            reason_code=None,
            message="allowed",
        )

    audit_repo.write_event.assert_called_once()


def test_otel_audit_writer_returns_audit_event() -> None:
    """write_event returns an AuditEvent dataclass."""
    audit_repo = MagicMock()
    audit_repo.write_event.return_value = _make_pg_record()

    writer = OTelAuditWriter(audit_repo=audit_repo)
    with patch("openqilin.observability.audit.audit_writer._emit_otel_log_record"):
        result = writer.write_event(
            event_type="policy_decision",
            outcome="deny",
            trace_id="trace-abc",
            request_id=None,
            task_id=None,
            principal_id=None,
            source="test",
            reason_code="POL-001",
            message="denied",
        )

    assert isinstance(result, AuditEvent)
    assert result.event_type == "policy_decision"
    assert result.outcome == "deny"


def test_otel_audit_writer_postgres_failure_propagates() -> None:
    """PostgreSQL write failure raises and does NOT continue silently."""
    audit_repo = MagicMock()
    audit_repo.write_event.side_effect = RuntimeError("db down")

    writer = OTelAuditWriter(audit_repo=audit_repo)
    with pytest.raises(RuntimeError, match="db down"):
        writer.write_event(
            event_type="policy_decision",
            outcome="allow",
            trace_id="trace-abc",
            request_id=None,
            task_id=None,
            principal_id=None,
            source="test",
            reason_code=None,
            message="ok",
        )


def test_otel_audit_writer_otel_failure_does_not_propagate() -> None:
    """OTel log record failure is caught and does not propagate."""
    audit_repo = MagicMock()
    audit_repo.write_event.return_value = _make_pg_record()

    writer = OTelAuditWriter(audit_repo=audit_repo)
    with patch(
        "openqilin.observability.audit.audit_writer._emit_otel_log_record",
        side_effect=Exception("otel collector down"),
    ):
        # Should NOT raise — OTel failure is tolerated
        result = writer.write_event(
            event_type="policy_decision",
            outcome="allow",
            trace_id="trace-abc",
            request_id=None,
            task_id=None,
            principal_id=None,
            source="test",
            reason_code=None,
            message="ok",
        )
    # PostgreSQL write succeeded and returned result
    assert isinstance(result, AuditEvent)


def test_otel_audit_writer_postgres_write_before_otel() -> None:
    """PostgreSQL write completes before OTel emission attempt."""
    call_order: list[str] = []

    audit_repo = MagicMock()

    def pg_write(**kwargs: object) -> MagicMock:
        call_order.append("postgres")
        return _make_pg_record()

    audit_repo.write_event.side_effect = pg_write

    writer = OTelAuditWriter(audit_repo=audit_repo)

    def otel_write(**kwargs: object) -> None:
        call_order.append("otel")

    with patch(
        "openqilin.observability.audit.audit_writer._emit_otel_log_record",
        side_effect=otel_write,
    ):
        writer.write_event(
            event_type="policy_decision",
            outcome="allow",
            trace_id="trace-abc",
            request_id=None,
            task_id=None,
            principal_id=None,
            source="test",
            reason_code=None,
            message="ok",
        )

    assert call_order == ["postgres", "otel"]


# ---------------------------------------------------------------------------
# configure_tracer
# ---------------------------------------------------------------------------


def test_configure_tracer_sets_global_provider() -> None:
    from openqilin.observability.tracing.tracer import configure_tracer

    with (
        patch(
            "opentelemetry.exporter.otlp.proto.grpc.trace_exporter.OTLPSpanExporter"
        ) as mock_exporter,
        patch("opentelemetry.sdk.trace.TracerProvider") as mock_provider_cls,
        patch("opentelemetry.trace.set_tracer_provider") as mock_set,
    ):
        mock_provider = MagicMock()
        mock_provider_cls.return_value = mock_provider
        mock_exporter.return_value = MagicMock()

        configure_tracer("http://otel:4317")

        mock_set.assert_called_once_with(mock_provider)


# ---------------------------------------------------------------------------
# configure_metrics
# ---------------------------------------------------------------------------


def test_configure_metrics_sets_global_provider() -> None:
    from openqilin.observability.metrics.recorder import configure_metrics

    with (
        patch(
            "opentelemetry.exporter.otlp.proto.grpc.metric_exporter.OTLPMetricExporter"
        ) as mock_exporter,
        patch("opentelemetry.sdk.metrics.MeterProvider") as mock_provider_cls,
        patch("opentelemetry.metrics.set_meter_provider") as mock_set,
    ):
        mock_provider = MagicMock()
        mock_provider_cls.return_value = mock_provider
        mock_exporter.return_value = MagicMock()

        configure_metrics("http://otel:4317")

        mock_set.assert_called_once_with(mock_provider)


# ---------------------------------------------------------------------------
# configure_otel_logs
# ---------------------------------------------------------------------------


def test_configure_otel_logs_sets_global_provider() -> None:
    from openqilin.observability.tracing.tracer import configure_otel_logs

    with (
        patch(
            "opentelemetry.exporter.otlp.proto.grpc._log_exporter.OTLPLogExporter"
        ) as mock_exporter,
        patch("opentelemetry.sdk._logs.LoggerProvider") as mock_provider_cls,
        patch("opentelemetry._logs.set_logger_provider") as mock_set,
    ):
        mock_provider = MagicMock()
        mock_provider_cls.return_value = mock_provider
        mock_exporter.return_value = MagicMock()

        configure_otel_logs("http://otel:4317")

        mock_provider.add_log_record_processor.assert_called_once()
        mock_set.assert_called_once_with(mock_provider)


# ---------------------------------------------------------------------------
# RuntimeSettings
# ---------------------------------------------------------------------------


def test_runtime_settings_otlp_endpoint_defaults_empty() -> None:
    settings = RuntimeSettings()
    assert settings.otlp_endpoint == ""


def test_runtime_settings_otlp_endpoint_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENQILIN_OTLP_ENDPOINT", "http://otel_collector:4317")
    settings = RuntimeSettings()
    assert settings.otlp_endpoint == "http://otel_collector:4317"


# ---------------------------------------------------------------------------
# dependencies.py wiring
# ---------------------------------------------------------------------------


def test_build_runtime_services_uses_inmemory_audit_when_no_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When database_url is empty, InMemoryAuditWriter is used."""
    monkeypatch.setenv("OPENQILIN_DATABASE_URL", "")
    monkeypatch.setenv("OPENQILIN_REDIS_URL", "")
    monkeypatch.setenv("OPENQILIN_OPA_URL", "")

    from openqilin.control_plane.api.dependencies import build_runtime_services

    services = build_runtime_services()
    assert isinstance(services.audit_writer, InMemoryAuditWriter)


def test_dependencies_audit_writer_union_type() -> None:
    """RuntimeServices.audit_writer field accepts both audit writer types."""
    from openqilin.control_plane.api.dependencies import RuntimeServices

    hints = {field.name: field.type for field in RuntimeServices.__dataclass_fields__.values()}
    field_type = str(hints.get("audit_writer", ""))
    assert "InMemoryAuditWriter" in field_type
    assert "OTelAuditWriter" in field_type
