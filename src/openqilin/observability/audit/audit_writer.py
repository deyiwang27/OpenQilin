"""Append-only audit writers: OTel+PostgreSQL for production; test stub re-exported from testing."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Iterable

from openqilin.observability.tracing.spans import normalize_attributes, utc_now

if TYPE_CHECKING:
    from openqilin.data_access.repositories.postgres.audit_event_repository import (
        PostgresAuditEventRepository,
    )

_logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """Immutable audit entry captured during governed ingress."""

    event_id: str
    event_type: str
    timestamp: datetime
    outcome: str
    trace_id: str
    actor_id: str
    actor_role: str
    policy_version: str
    policy_hash: str
    rule_ids: tuple[str, ...]
    payload: tuple[tuple[str, str], ...]
    request_id: str | None
    task_id: str | None
    principal_id: str | None
    source: str
    reason_code: str | None
    message: str
    attributes: tuple[tuple[str, str], ...]
    created_at: datetime


class OTelAuditWriter:
    """Dual-write audit writer: durable PostgreSQL row + streaming OTel log record.

    Write semantics (AUD-001):
    - PostgreSQL write is primary: failure propagates and blocks the calling path.
    - OTel log record is secondary: failure is caught, logged locally, and does not
      block the caller.  The durable row is always written first.
    """

    def __init__(self, *, audit_repo: "PostgresAuditEventRepository") -> None:
        self._audit_repo = audit_repo

    def write_event(
        self,
        *,
        event_type: str,
        outcome: str,
        trace_id: str,
        request_id: str | None,
        task_id: str | None,
        principal_id: str | None,
        principal_role: str | None = None,
        source: str,
        reason_code: str | None,
        message: str,
        policy_version: str | None = None,
        policy_hash: str | None = None,
        rule_ids: Iterable[str] | None = None,
        payload: dict[str, object] | None = None,
        attributes: dict[str, object] | None = None,
    ) -> AuditEvent:
        """Write audit event to PostgreSQL (fail-hard) then emit OTel log (fail-soft)."""

        timestamp = utc_now()
        normalized_rule_ids = tuple(sorted(str(rule_id) for rule_id in (rule_ids or ())))
        normalized_payload: dict[str, object] = dict(
            payload
            or {
                "outcome": outcome,
                "source": source,
                "message": message,
                "request_id": str(request_id) if request_id else None,
                "task_id": str(task_id) if task_id else None,
                "reason_code": str(reason_code) if reason_code else None,
            }
        )

        # 1. Durable write to PostgreSQL — failure propagates (AUD-001 compliance).
        pg_record = self._audit_repo.write_event(
            event_type=event_type,
            trace_id=trace_id,
            task_id=task_id,
            principal_id=principal_id,
            principal_role=principal_role,
            action=source,
            target=None,
            decision=outcome,
            rule_ids=normalized_rule_ids,
            payload=normalized_payload,
        )

        # 2. Streaming OTel log record — failure is tolerated.
        try:
            _emit_otel_log_record(
                event_id=pg_record.event_id,
                event_type=event_type,
                trace_id=trace_id,
                outcome=outcome,
                principal_id=principal_id,
                principal_role=principal_role,
                task_id=task_id,
                rule_ids=normalized_rule_ids,
                message=message,
            )
        except Exception:
            _logger.warning(
                "OTel audit log emission failed for event_id=%s — PostgreSQL row written, "
                "continuing without OTel record.",
                pg_record.event_id,
                exc_info=True,
            )

        normalized_payload_tuple = normalize_attributes(normalized_payload)
        return AuditEvent(
            event_id=pg_record.event_id,
            event_type=event_type,
            timestamp=timestamp,
            outcome=outcome,
            trace_id=trace_id,
            actor_id=principal_id or "unknown-actor",
            actor_role=principal_role or "unknown-role",
            policy_version=policy_version or "policy-version-unknown",
            policy_hash=policy_hash or "policy-hash-unknown",
            rule_ids=normalized_rule_ids,
            payload=normalized_payload_tuple,
            request_id=request_id,
            task_id=task_id,
            principal_id=principal_id,
            source=source,
            reason_code=reason_code,
            message=message,
            attributes=normalize_attributes(attributes),
            created_at=timestamp,
        )


def _emit_otel_log_record(
    *,
    event_id: str,
    event_type: str,
    trace_id: str,
    outcome: str,
    principal_id: str | None,
    principal_role: str | None,
    task_id: str | None,
    rule_ids: tuple[str, ...],
    message: str,
) -> None:
    """Emit one OTel log record for the audit event.

    Uses the globally-configured LoggerProvider.  If the provider is the no-op
    default (OTel collector not configured), this is a no-op.
    """

    from opentelemetry._logs import get_logger
    from opentelemetry._logs._internal import LogRecord
    from opentelemetry._logs.severity import SeverityNumber
    from opentelemetry.trace import TraceFlags

    otel_logger = get_logger("openqilin.audit")
    record = LogRecord(
        timestamp=int(utc_now().timestamp() * 1e9),
        trace_id=int(trace_id.replace("-", ""), 16) if _is_hex_trace_id(trace_id) else 0,
        span_id=0,
        trace_flags=TraceFlags(0x01),
        severity_text="INFO",
        severity_number=SeverityNumber.INFO,
        body=message,
        attributes={
            "audit.event_id": event_id,
            "audit.event_type": event_type,
            "audit.outcome": outcome,
            "audit.trace_id": trace_id,
            "audit.principal_id": principal_id or "",
            "audit.principal_role": principal_role or "",
            "audit.task_id": task_id or "",
            "audit.rule_ids": ",".join(rule_ids),
        },
    )
    otel_logger.emit(record)


def _is_hex_trace_id(value: str) -> bool:
    try:
        int(value.replace("-", ""), 16)
        return True
    except ValueError:
        return False
