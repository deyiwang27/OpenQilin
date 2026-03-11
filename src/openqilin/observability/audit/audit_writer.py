"""Append-only in-memory audit writer for M1 evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable
from uuid import uuid4

from openqilin.observability.tracing.spans import normalize_attributes, utc_now


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
        """Append a normalized audit event and return it."""

        timestamp = utc_now()
        normalized_rule_ids = tuple(sorted(str(rule_id) for rule_id in (rule_ids or ())))
        normalized_payload = normalize_attributes(
            payload
            or {
                "outcome": outcome,
                "source": source,
                "message": message,
                "request_id": request_id,
                "task_id": task_id,
                "reason_code": reason_code,
            }
        )
        event = AuditEvent(
            event_id=str(uuid4()),
            event_type=event_type,
            timestamp=timestamp,
            outcome=outcome,
            trace_id=trace_id,
            actor_id=principal_id or "unknown-actor",
            actor_role=principal_role or "unknown-role",
            policy_version=policy_version or "policy-version-unknown",
            policy_hash=policy_hash or "policy-hash-unknown",
            rule_ids=normalized_rule_ids,
            payload=normalized_payload,
            request_id=request_id,
            task_id=task_id,
            principal_id=principal_id,
            source=source,
            reason_code=reason_code,
            message=message,
            attributes=normalize_attributes(attributes),
            created_at=timestamp,
        )
        self._events.append(event)
        return event

    def get_events(self) -> tuple[AuditEvent, ...]:
        """Return immutable snapshot of audit events."""

        return tuple(self._events)
