"""Dead-letter sink writer with audit/metric emission."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from openqilin.data_access.repositories.communication import (
    CommunicationDeadLetterRecord,
)
from openqilin.observability.audit.audit_writer import OTelAuditWriter
from openqilin.observability.testing.stubs import InMemoryAuditWriter
from openqilin.observability.testing.stubs import InMemoryMetricRecorder


@dataclass(frozen=True, slots=True)
class DeadLetterWriteRequest:
    """Terminal delivery payload routed to dead-letter sink."""

    task_id: str
    trace_id: str
    principal_id: str
    idempotency_key: str
    message_id: str
    external_message_id: str
    connector: str
    command: str
    target: str
    route_key: str
    endpoint: str
    error_code: str
    error_message: str
    attempts: int
    ledger_id: str | None


class LocalDeadLetterWriter:
    """Local in-process dead-letter writer with operator-visible observability signals."""

    def __init__(
        self,
        *,
        audit_writer: InMemoryAuditWriter | OTelAuditWriter | None = None,
        metric_recorder: InMemoryMetricRecorder | None = None,
    ) -> None:
        self._dead_letters: list[CommunicationDeadLetterRecord] = []
        self._audit_writer = audit_writer or InMemoryAuditWriter()
        self._metric_recorder = metric_recorder or InMemoryMetricRecorder()

    def write_dead_letter(self, payload: DeadLetterWriteRequest) -> CommunicationDeadLetterRecord:
        """Persist dead-letter record and emit audit/metric observability."""

        record = CommunicationDeadLetterRecord(
            dead_letter_id=str(uuid4()),
            task_id=payload.task_id,
            trace_id=payload.trace_id,
            principal_id=payload.principal_id,
            idempotency_key=payload.idempotency_key,
            message_id=payload.message_id,
            external_message_id=payload.external_message_id,
            connector=payload.connector,
            command=payload.command,
            target=payload.target,
            route_key=payload.route_key,
            endpoint=payload.endpoint,
            error_code=payload.error_code,
            error_message=payload.error_message,
            attempts=payload.attempts,
            ledger_id=payload.ledger_id,
            created_at=datetime.now(tz=UTC),
        )
        self._dead_letters.append(record)
        self._metric_recorder.increment_counter(
            "communication_dead_letter_total",
            labels={
                "connector": payload.connector,
                "reason_code": payload.error_code,
            },
        )
        self._audit_writer.write_event(
            event_type="communication.dead_letter",
            outcome="dead_lettered",
            trace_id=payload.trace_id,
            request_id=None,
            task_id=payload.task_id,
            principal_id=payload.principal_id,
            principal_role="owner",
            source="communication_gateway_dlq",
            reason_code=payload.error_code,
            message=payload.error_message,
            payload={
                "dead_letter_id": record.dead_letter_id,
                "attempts": payload.attempts,
                "ledger_id": payload.ledger_id,
                "connector": payload.connector,
                "route_key": payload.route_key,
            },
            attributes={
                "dead_letter_id": record.dead_letter_id,
                "connector": payload.connector,
                "command": payload.command,
                "target": payload.target,
                "attempts": payload.attempts,
            },
        )
        return record

    def list_dead_letters(self) -> tuple[CommunicationDeadLetterRecord, ...]:
        """List persisted dead-letter records."""

        return tuple(self._dead_letters)


# Backward-compat alias
InMemoryDeadLetterWriter = LocalDeadLetterWriter
