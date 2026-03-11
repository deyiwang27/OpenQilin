"""Append-only in-memory audit writer for M1 evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from openqilin.observability.tracing.spans import normalize_attributes, utc_now


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """Immutable audit entry captured during governed ingress."""

    event_id: str
    event_type: str
    outcome: str
    trace_id: str
    request_id: str | None
    task_id: str | None
    principal_id: str | None
    source: str
    reason_code: str | None
    message: str
    attributes: tuple[tuple[str, str], ...]
    created_at: datetime


class InMemoryAuditWriter:
    """Stores audit events in memory for deterministic M1 tests."""

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def write_event(
        self,
        *,
        event_type: str,
        outcome: str,
        trace_id: str,
        request_id: str | None,
        task_id: str | None,
        principal_id: str | None,
        source: str,
        reason_code: str | None,
        message: str,
        attributes: dict[str, object] | None = None,
    ) -> AuditEvent:
        """Append a normalized audit event and return it."""

        event = AuditEvent(
            event_id=str(uuid4()),
            event_type=event_type,
            outcome=outcome,
            trace_id=trace_id,
            request_id=request_id,
            task_id=task_id,
            principal_id=principal_id,
            source=source,
            reason_code=reason_code,
            message=message,
            attributes=normalize_attributes(attributes),
            created_at=utc_now(),
        )
        self._events.append(event)
        return event

    def get_events(self) -> tuple[AuditEvent, ...]:
        """Return immutable snapshot of audit events."""

        return tuple(self._events)
