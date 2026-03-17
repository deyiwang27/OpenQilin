"""PostgreSQL-backed audit event repository for AUD-001 immutable audit trail."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker


@dataclass(frozen=True, slots=True)
class AuditEventRecord:
    """Immutable audit event persisted to PostgreSQL."""

    event_id: str
    event_type: str
    trace_id: str
    task_id: str | None
    principal_id: str | None
    principal_role: str | None
    action: str | None
    target: str | None
    decision: str | None
    rule_ids: tuple[str, ...]
    payload: dict[str, object]
    created_at: datetime


class PostgresAuditEventRepository:
    """PostgreSQL-backed audit event repository — append-only, AUD-001 compliant."""

    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def write_event(
        self,
        *,
        event_type: str,
        trace_id: str,
        task_id: str | None = None,
        principal_id: str | None = None,
        principal_role: str | None = None,
        action: str | None = None,
        target: str | None = None,
        decision: str | None = None,
        rule_ids: tuple[str, ...] = (),
        payload: dict[str, object] | None = None,
    ) -> AuditEventRecord:
        """Append one immutable audit event record."""

        record = AuditEventRecord(
            event_id=str(uuid4()),
            event_type=event_type,
            trace_id=trace_id,
            task_id=task_id,
            principal_id=principal_id,
            principal_role=principal_role,
            action=action,
            target=target,
            decision=decision,
            rule_ids=rule_ids,
            payload=payload or {},
            created_at=datetime.now(tz=UTC),
        )
        with self._session_factory() as session:
            session.execute(
                text(
                    """
                    INSERT INTO audit_events (
                        event_id, event_type, trace_id, task_id, principal_id,
                        principal_role, action, target, decision, rule_ids, payload, created_at
                    ) VALUES (
                        :event_id, :event_type, :trace_id, :task_id, :principal_id,
                        :principal_role, :action, :target, :decision,
                        :rule_ids::jsonb, :payload::jsonb, :created_at
                    )
                    """
                ),
                {
                    "event_id": record.event_id,
                    "event_type": record.event_type,
                    "trace_id": record.trace_id,
                    "task_id": record.task_id,
                    "principal_id": record.principal_id,
                    "principal_role": record.principal_role,
                    "action": record.action,
                    "target": record.target,
                    "decision": record.decision,
                    "rule_ids": json.dumps(list(record.rule_ids)),
                    "payload": json.dumps(record.payload),
                    "created_at": record.created_at,
                },
            )
            session.commit()
        return record

    def list_events_for_trace(self, trace_id: str) -> tuple[AuditEventRecord, ...]:
        """Load all audit events for a trace, ordered by creation time."""

        with self._session_factory() as session:
            rows = (
                session.execute(
                    text(
                        """
                    SELECT * FROM audit_events
                    WHERE trace_id = :trace_id
                    ORDER BY created_at ASC
                    """
                    ),
                    {"trace_id": trace_id},
                )
                .mappings()
                .all()
            )
        return tuple(_event_from_row(dict(row)) for row in rows)


def _event_from_row(row: dict[str, object]) -> AuditEventRecord:
    rule_ids_raw = row.get("rule_ids") or []
    if isinstance(rule_ids_raw, str):
        rule_ids_raw = json.loads(rule_ids_raw)
    payload_raw = row.get("payload") or {}
    if isinstance(payload_raw, str):
        payload_raw = json.loads(payload_raw)
    created_at = row["created_at"]
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at).astimezone(UTC)
    elif hasattr(created_at, "tzinfo") and created_at.tzinfo is None:  # type: ignore[attr-defined]
        created_at = created_at.replace(tzinfo=UTC)  # type: ignore[attr-defined]
    return AuditEventRecord(
        event_id=str(row["event_id"]),
        event_type=str(row["event_type"]),
        trace_id=str(row["trace_id"]),
        task_id=str(row["task_id"]) if row.get("task_id") else None,
        principal_id=str(row["principal_id"]) if row.get("principal_id") else None,
        principal_role=str(row["principal_role"]) if row.get("principal_role") else None,
        action=str(row["action"]) if row.get("action") else None,
        target=str(row["target"]) if row.get("target") else None,
        decision=str(row["decision"]) if row.get("decision") else None,
        rule_ids=tuple(str(r) for r in (rule_ids_raw if isinstance(rule_ids_raw, list) else [])),
        payload=payload_raw if isinstance(payload_raw, dict) else {},
        created_at=created_at,  # type: ignore[arg-type]
    )
