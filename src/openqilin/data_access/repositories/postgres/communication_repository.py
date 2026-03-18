"""PostgreSQL-backed communication repository replacing InMemoryCommunicationRepository."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from openqilin.data_access.repositories.communication import (
    CommunicationDeadLetterRecord,
    CommunicationMessageRecord,
    CommunicationStateTransition,
    LedgerState,
)


class PostgresCommunicationRepository:
    """PostgreSQL-backed communication message lifecycle repository."""

    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def create_record(
        self,
        *,
        task_id: str,
        trace_id: str,
        message_id: str,
        external_message_id: str,
        connector: str,
        command: str,
        target: str,
        route_key: str,
        endpoint: str,
        attempt: int = 1,
    ) -> CommunicationMessageRecord:
        """Create a new prepared-state communication message record."""

        now = datetime.now(tz=UTC)
        initial_transition = CommunicationStateTransition(
            state="prepared",
            changed_at=now,
            reason_code="dispatch_prepared",
            message="communication dispatch prepared",
            retryable=None,
        )
        record = CommunicationMessageRecord(
            ledger_id=str(uuid4()),
            task_id=task_id,
            trace_id=trace_id,
            message_id=message_id,
            external_message_id=external_message_id,
            connector=connector,
            command=command,
            target=target,
            route_key=route_key,
            endpoint=endpoint,
            attempt=attempt,
            state="prepared",
            dispatch_id=None,
            delivery_id=None,
            retryable=None,
            error_code=None,
            error_message=None,
            transitions=(initial_transition,),
            created_at=now,
            updated_at=now,
        )
        with self._session_factory() as session:
            session.execute(
                text(
                    """
                    INSERT INTO messages (
                        ledger_id, task_id, trace_id, message_id, external_message_id,
                        connector, command, target, route_key, endpoint,
                        attempt, state, dispatch_id, delivery_id, retryable,
                        error_code, error_message, transitions, created_at, updated_at
                    ) VALUES (
                        :ledger_id, :task_id, :trace_id, :message_id, :external_message_id,
                        :connector, :command, :target, :route_key, :endpoint,
                        :attempt, :state, :dispatch_id, :delivery_id, :retryable,
                        :error_code, :error_message, CAST(:transitions AS JSONB), :created_at, :updated_at
                    )
                    """
                ),
                _record_to_params(record),
            )
            session.commit()
        return record

    def append_transition(
        self,
        ledger_id: str,
        *,
        state: LedgerState,
        reason_code: str,
        message: str,
        retryable: bool | None,
        dispatch_id: str | None,
        delivery_id: str | None,
        error_code: str | None,
        error_message: str | None,
    ) -> CommunicationMessageRecord | None:
        """Append transition and update current state for existing ledger record."""

        from dataclasses import replace

        current = self.get_record(ledger_id)
        if current is None:
            return None
        now = datetime.now(tz=UTC)
        transition = CommunicationStateTransition(
            state=state,
            changed_at=now,
            reason_code=reason_code,
            message=message,
            retryable=retryable,
        )
        updated = replace(
            current,
            state=state,
            dispatch_id=dispatch_id if dispatch_id is not None else current.dispatch_id,
            delivery_id=delivery_id if delivery_id is not None else current.delivery_id,
            retryable=retryable,
            error_code=error_code,
            error_message=error_message,
            transitions=(*current.transitions, transition),
            updated_at=now,
        )
        with self._session_factory() as session:
            session.execute(
                text(
                    """
                    UPDATE messages SET
                        state           = :state,
                        dispatch_id     = COALESCE(:dispatch_id, dispatch_id),
                        delivery_id     = COALESCE(:delivery_id, delivery_id),
                        retryable       = :retryable,
                        error_code      = :error_code,
                        error_message   = :error_message,
                        transitions     = CAST(:transitions AS JSONB),
                        updated_at      = :updated_at
                    WHERE ledger_id = :ledger_id
                    """
                ),
                {
                    "ledger_id": ledger_id,
                    "state": updated.state,
                    "dispatch_id": dispatch_id,
                    "delivery_id": delivery_id,
                    "retryable": retryable,
                    "error_code": error_code,
                    "error_message": error_message,
                    "transitions": json.dumps(
                        [_transition_to_dict(t) for t in updated.transitions]
                    ),
                    "updated_at": updated.updated_at,
                },
            )
            session.commit()
        return updated

    def get_record(self, ledger_id: str) -> CommunicationMessageRecord | None:
        """Load message record by ledger identifier."""

        with self._session_factory() as session:
            row = (
                session.execute(
                    text("SELECT * FROM messages WHERE ledger_id = :ledger_id"),
                    {"ledger_id": ledger_id},
                )
                .mappings()
                .first()
            )
        if row is None:
            return None
        return _record_from_row(dict(row))

    def list_records_for_task(self, task_id: str) -> tuple[CommunicationMessageRecord, ...]:
        """List all message records associated with task identifier."""

        with self._session_factory() as session:
            rows = (
                session.execute(
                    text("SELECT * FROM messages WHERE task_id = :task_id ORDER BY created_at ASC"),
                    {"task_id": task_id},
                )
                .mappings()
                .all()
            )
        return tuple(_record_from_row(dict(row)) for row in rows)

    def list_records(self) -> tuple[CommunicationMessageRecord, ...]:
        """List all persisted communication message records."""

        with self._session_factory() as session:
            rows = (
                session.execute(text("SELECT * FROM messages ORDER BY created_at ASC"))
                .mappings()
                .all()
            )
        return tuple(_record_from_row(dict(row)) for row in rows)

    def create_dead_letter_record(
        self,
        *,
        task_id: str,
        trace_id: str,
        principal_id: str,
        idempotency_key: str,
        message_id: str,
        external_message_id: str,
        connector: str,
        command: str,
        target: str,
        route_key: str,
        endpoint: str,
        error_code: str,
        error_message: str,
        attempts: int,
        ledger_id: str | None,
    ) -> CommunicationDeadLetterRecord:
        """Create one dead-letter record for an exhausted message delivery."""

        record = CommunicationDeadLetterRecord(
            dead_letter_id=str(uuid4()),
            task_id=task_id,
            trace_id=trace_id,
            principal_id=principal_id,
            idempotency_key=idempotency_key,
            message_id=message_id,
            external_message_id=external_message_id,
            connector=connector,
            command=command,
            target=target,
            route_key=route_key,
            endpoint=endpoint,
            error_code=error_code,
            error_message=error_message,
            attempts=attempts,
            ledger_id=ledger_id,
            created_at=datetime.now(tz=UTC),
        )
        with self._session_factory() as session:
            session.execute(
                text(
                    """
                    INSERT INTO dead_letters (
                        dead_letter_id, task_id, trace_id, principal_id, idempotency_key,
                        message_id, external_message_id, connector, command, target,
                        route_key, endpoint, error_code, error_message, attempts,
                        ledger_id, created_at
                    ) VALUES (
                        :dead_letter_id, :task_id, :trace_id, :principal_id, :idempotency_key,
                        :message_id, :external_message_id, :connector, :command, :target,
                        :route_key, :endpoint, :error_code, :error_message, :attempts,
                        :ledger_id, :created_at
                    )
                    """
                ),
                {
                    "dead_letter_id": record.dead_letter_id,
                    "task_id": record.task_id,
                    "trace_id": record.trace_id,
                    "principal_id": record.principal_id,
                    "idempotency_key": record.idempotency_key,
                    "message_id": record.message_id,
                    "external_message_id": record.external_message_id,
                    "connector": record.connector,
                    "command": record.command,
                    "target": record.target,
                    "route_key": record.route_key,
                    "endpoint": record.endpoint,
                    "error_code": record.error_code,
                    "error_message": record.error_message,
                    "attempts": record.attempts,
                    "ledger_id": record.ledger_id,
                    "created_at": record.created_at,
                },
            )
            session.commit()
        return record

    def get_dead_letter_record(self, dead_letter_id: str) -> CommunicationDeadLetterRecord | None:
        """Load one dead-letter record by identifier."""

        with self._session_factory() as session:
            row = (
                session.execute(
                    text("SELECT * FROM dead_letters WHERE dead_letter_id = :dead_letter_id"),
                    {"dead_letter_id": dead_letter_id},
                )
                .mappings()
                .first()
            )
        if row is None:
            return None
        return _dead_letter_from_row(dict(row))

    def list_dead_letter_records(self) -> tuple[CommunicationDeadLetterRecord, ...]:
        """List all dead-letter records."""

        with self._session_factory() as session:
            rows = (
                session.execute(text("SELECT * FROM dead_letters ORDER BY created_at ASC"))
                .mappings()
                .all()
            )
        return tuple(_dead_letter_from_row(dict(row)) for row in rows)


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def _transition_to_dict(t: CommunicationStateTransition) -> dict[str, object]:
    return {
        "state": t.state,
        "changed_at": t.changed_at.isoformat(),
        "reason_code": t.reason_code,
        "message": t.message,
        "retryable": t.retryable,
    }


def _transition_from_dict(d: dict[str, object]) -> CommunicationStateTransition:
    changed_at_raw = d.get("changed_at")
    if isinstance(changed_at_raw, str):
        changed_at = datetime.fromisoformat(changed_at_raw).astimezone(UTC)
    elif hasattr(changed_at_raw, "tzinfo"):
        changed_at = changed_at_raw if changed_at_raw.tzinfo else changed_at_raw.replace(tzinfo=UTC)  # type: ignore[attr-defined, assignment]
    else:
        changed_at = datetime.now(tz=UTC)
    return CommunicationStateTransition(
        state=str(d["state"]),  # type: ignore[arg-type]
        changed_at=changed_at,
        reason_code=str(d["reason_code"]),
        message=str(d["message"]),
        retryable=d.get("retryable"),  # type: ignore[arg-type]
    )


def _record_to_params(record: CommunicationMessageRecord) -> dict[str, object]:
    return {
        "ledger_id": record.ledger_id,
        "task_id": record.task_id,
        "trace_id": record.trace_id,
        "message_id": record.message_id,
        "external_message_id": record.external_message_id,
        "connector": record.connector,
        "command": record.command,
        "target": record.target,
        "route_key": record.route_key,
        "endpoint": record.endpoint,
        "attempt": record.attempt,
        "state": record.state,
        "dispatch_id": record.dispatch_id,
        "delivery_id": record.delivery_id,
        "retryable": record.retryable,
        "error_code": record.error_code,
        "error_message": record.error_message,
        "transitions": json.dumps([_transition_to_dict(t) for t in record.transitions]),
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


def _parse_dt(value: object) -> datetime:
    if isinstance(value, str):
        return datetime.fromisoformat(value).astimezone(UTC)
    if hasattr(value, "tzinfo"):
        if value.tzinfo is None:  # type: ignore[attr-defined]
            return value.replace(tzinfo=UTC)  # type: ignore[attr-defined, return-value]
        return value  # type: ignore[return-value]
    return datetime.now(tz=UTC)


def _record_from_row(row: dict[str, object]) -> CommunicationMessageRecord:
    transitions_raw = row.get("transitions") or "[]"
    if isinstance(transitions_raw, str):
        transitions_raw = json.loads(transitions_raw)
    return CommunicationMessageRecord(
        ledger_id=str(row["ledger_id"]),
        task_id=str(row["task_id"]),
        trace_id=str(row["trace_id"]),
        message_id=str(row["message_id"]),
        external_message_id=str(row["external_message_id"]),
        connector=str(row["connector"]),
        command=str(row["command"]),
        target=str(row["target"]),
        route_key=str(row["route_key"]),
        endpoint=str(row["endpoint"]),
        attempt=int(row.get("attempt", 1)),  # type: ignore[call-overload]
        state=str(row["state"]),  # type: ignore[arg-type]
        dispatch_id=str(row["dispatch_id"]) if row.get("dispatch_id") else None,
        delivery_id=str(row["delivery_id"]) if row.get("delivery_id") else None,
        retryable=bool(row["retryable"]) if row.get("retryable") is not None else None,
        error_code=str(row["error_code"]) if row.get("error_code") else None,
        error_message=str(row["error_message"]) if row.get("error_message") else None,
        transitions=tuple(
            _transition_from_dict(t)
            for t in (transitions_raw if isinstance(transitions_raw, list) else [])
        ),
        created_at=_parse_dt(row["created_at"]),
        updated_at=_parse_dt(row["updated_at"]),
    )


def _dead_letter_from_row(row: dict[str, object]) -> CommunicationDeadLetterRecord:
    return CommunicationDeadLetterRecord(
        dead_letter_id=str(row["dead_letter_id"]),
        task_id=str(row["task_id"]),
        trace_id=str(row["trace_id"]),
        principal_id=str(row["principal_id"]),
        idempotency_key=str(row["idempotency_key"]),
        message_id=str(row["message_id"]),
        external_message_id=str(row["external_message_id"]),
        connector=str(row["connector"]),
        command=str(row["command"]),
        target=str(row["target"]),
        route_key=str(row["route_key"]),
        endpoint=str(row["endpoint"]),
        error_code=str(row["error_code"]),
        error_message=str(row["error_message"]),
        attempts=int(row.get("attempts", 0)),  # type: ignore[call-overload]
        ledger_id=str(row["ledger_id"]) if row.get("ledger_id") else None,
        created_at=_parse_dt(row["created_at"]),
    )
