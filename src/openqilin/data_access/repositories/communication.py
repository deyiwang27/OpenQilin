"""Communication message repository primitives for delivery lifecycle persistence."""

from __future__ import annotations

from collections import defaultdict
import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast
from uuid import uuid4

from openqilin.shared_kernel.config import RuntimeSettings

LedgerState = Literal["prepared", "sent", "acked", "nacked"]


@dataclass(frozen=True, slots=True)
class CommunicationStateTransition:
    """Immutable transition event persisted in the communication message ledger."""

    state: LedgerState
    changed_at: datetime
    reason_code: str
    message: str
    retryable: bool | None


@dataclass(frozen=True, slots=True)
class CommunicationMessageRecord:
    """Persisted communication delivery state for one dispatched message."""

    ledger_id: str
    task_id: str
    trace_id: str
    message_id: str
    external_message_id: str
    connector: str
    command: str
    target: str
    route_key: str
    endpoint: str
    attempt: int
    state: LedgerState
    dispatch_id: str | None
    delivery_id: str | None
    retryable: bool | None
    error_code: str | None
    error_message: str | None
    transitions: tuple[CommunicationStateTransition, ...]
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class CommunicationDeadLetterRecord:
    """Persisted dead-letter entry for exhausted communication deliveries."""

    dead_letter_id: str
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
    created_at: datetime


class CommunicationRepositoryError(ValueError):
    """Raised when communication snapshot persistence cannot be completed."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class InMemoryCommunicationRepository:
    """In-memory repository storing communication message lifecycle records."""

    def __init__(self, *, snapshot_path: Path | None = None) -> None:
        self._records_by_ledger_id: dict[str, CommunicationMessageRecord] = {}
        self._ledger_ids_by_task_id: dict[str, list[str]] = defaultdict(list)
        self._dead_letters_by_id: dict[str, CommunicationDeadLetterRecord] = {}
        self._dead_letter_ids_by_task_id: dict[str, list[str]] = defaultdict(list)
        self._snapshot_path = snapshot_path
        if self._snapshot_path is not None:
            self._load_snapshot()

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
        self._records_by_ledger_id[record.ledger_id] = record
        self._ledger_ids_by_task_id[task_id].append(record.ledger_id)
        self._flush_snapshot()
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

        current = self._records_by_ledger_id.get(ledger_id)
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
        self._records_by_ledger_id[ledger_id] = updated
        self._flush_snapshot()
        return updated

    def get_record(self, ledger_id: str) -> CommunicationMessageRecord | None:
        """Load message record by ledger identifier."""

        return self._records_by_ledger_id.get(ledger_id)

    def list_records_for_task(self, task_id: str) -> tuple[CommunicationMessageRecord, ...]:
        """List all message records associated with task identifier."""

        ledger_ids = self._ledger_ids_by_task_id.get(task_id, [])
        return tuple(
            self._records_by_ledger_id[ledger_id]
            for ledger_id in ledger_ids
            if ledger_id in self._records_by_ledger_id
        )

    def list_records(self) -> tuple[CommunicationMessageRecord, ...]:
        """List all persisted communication message records."""

        return tuple(self._records_by_ledger_id.values())

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
        """Persist terminal dead-letter entry for exhausted delivery."""

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
        self._dead_letters_by_id[record.dead_letter_id] = record
        self._dead_letter_ids_by_task_id[task_id].append(record.dead_letter_id)
        self._flush_snapshot()
        return record

    def get_dead_letter(self, dead_letter_id: str) -> CommunicationDeadLetterRecord | None:
        """Load one dead-letter record by id."""

        return self._dead_letters_by_id.get(dead_letter_id)

    def list_dead_letters_for_task(self, task_id: str) -> tuple[CommunicationDeadLetterRecord, ...]:
        """List dead-letter records for task."""

        dead_letter_ids = self._dead_letter_ids_by_task_id.get(task_id, [])
        return tuple(
            self._dead_letters_by_id[dead_letter_id]
            for dead_letter_id in dead_letter_ids
            if dead_letter_id in self._dead_letters_by_id
        )

    def list_dead_letters(self) -> tuple[CommunicationDeadLetterRecord, ...]:
        """List all dead-letter records."""

        return tuple(self._dead_letters_by_id.values())

    def _load_snapshot(self) -> None:
        path = self._resolved_snapshot_path()
        if not path.exists():
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as error:
            raise CommunicationRepositoryError(
                code="communication_snapshot_load_failed",
                message=f"failed to load communication snapshot: {path}",
            ) from error
        records = payload.get("records", [])
        dead_letters = payload.get("dead_letters", [])
        if not isinstance(records, list) or not isinstance(dead_letters, list):
            raise CommunicationRepositoryError(
                code="communication_snapshot_invalid",
                message="communication snapshot payload is invalid",
            )
        for raw in records:
            record = _message_record_from_dict(raw)
            self._records_by_ledger_id[record.ledger_id] = record
            self._ledger_ids_by_task_id[record.task_id].append(record.ledger_id)
        for raw in dead_letters:
            dead_letter = _dead_letter_from_dict(raw)
            self._dead_letters_by_id[dead_letter.dead_letter_id] = dead_letter
            self._dead_letter_ids_by_task_id[dead_letter.task_id].append(dead_letter.dead_letter_id)

    def _flush_snapshot(self) -> None:
        if self._snapshot_path is None:
            return
        path = self._resolved_snapshot_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "records": [
                _message_record_to_dict(record) for record in self._records_by_ledger_id.values()
            ],
            "dead_letters": [
                _dead_letter_to_dict(record) for record in self._dead_letters_by_id.values()
            ],
        }
        try:
            path.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")
        except OSError as error:
            raise CommunicationRepositoryError(
                code="communication_snapshot_write_failed",
                message=f"failed to write communication snapshot: {path}",
            ) from error

    def _resolved_snapshot_path(self) -> Path:
        if self._snapshot_path is not None:
            return self._snapshot_path
        return RuntimeSettings().communication_snapshot_path


def _message_record_to_dict(record: CommunicationMessageRecord) -> dict[str, object]:
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
        "transitions": [
            {
                "state": transition.state,
                "changed_at": transition.changed_at.isoformat(),
                "reason_code": transition.reason_code,
                "message": transition.message,
                "retryable": transition.retryable,
            }
            for transition in record.transitions
        ],
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
    }


def _message_record_from_dict(raw: object) -> CommunicationMessageRecord:
    if not isinstance(raw, dict):
        raise CommunicationRepositoryError(
            code="communication_snapshot_invalid_record",
            message="communication record must be an object",
        )
    transitions_raw = raw.get("transitions", [])
    transitions = tuple(
        CommunicationStateTransition(
            state=_parse_ledger_state(str(transition["state"])),
            changed_at=datetime.fromisoformat(str(transition["changed_at"])).astimezone(UTC),
            reason_code=str(transition["reason_code"]),
            message=str(transition["message"]),
            retryable=bool(transition["retryable"])
            if transition.get("retryable") is not None
            else None,
        )
        for transition in _list_or_empty(transitions_raw)
        if isinstance(transition, dict)
    )
    return CommunicationMessageRecord(
        ledger_id=str(raw["ledger_id"]),
        task_id=str(raw["task_id"]),
        trace_id=str(raw["trace_id"]),
        message_id=str(raw["message_id"]),
        external_message_id=str(raw["external_message_id"]),
        connector=str(raw["connector"]),
        command=str(raw["command"]),
        target=str(raw["target"]),
        route_key=str(raw["route_key"]),
        endpoint=str(raw["endpoint"]),
        attempt=int(raw["attempt"]),
        state=_parse_ledger_state(str(raw["state"])),
        dispatch_id=str(raw["dispatch_id"]) if raw.get("dispatch_id") is not None else None,
        delivery_id=str(raw["delivery_id"]) if raw.get("delivery_id") is not None else None,
        retryable=bool(raw["retryable"]) if raw.get("retryable") is not None else None,
        error_code=str(raw["error_code"]) if raw.get("error_code") is not None else None,
        error_message=str(raw["error_message"]) if raw.get("error_message") is not None else None,
        transitions=transitions,
        created_at=datetime.fromisoformat(str(raw["created_at"])).astimezone(UTC),
        updated_at=datetime.fromisoformat(str(raw["updated_at"])).astimezone(UTC),
    )


def _dead_letter_to_dict(record: CommunicationDeadLetterRecord) -> dict[str, object]:
    return {
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
        "created_at": record.created_at.isoformat(),
    }


def _dead_letter_from_dict(raw: object) -> CommunicationDeadLetterRecord:
    if not isinstance(raw, dict):
        raise CommunicationRepositoryError(
            code="communication_snapshot_invalid_dead_letter",
            message="communication dead-letter record must be an object",
        )
    return CommunicationDeadLetterRecord(
        dead_letter_id=str(raw["dead_letter_id"]),
        task_id=str(raw["task_id"]),
        trace_id=str(raw["trace_id"]),
        principal_id=str(raw["principal_id"]),
        idempotency_key=str(raw["idempotency_key"]),
        message_id=str(raw["message_id"]),
        external_message_id=str(raw["external_message_id"]),
        connector=str(raw["connector"]),
        command=str(raw["command"]),
        target=str(raw["target"]),
        route_key=str(raw["route_key"]),
        endpoint=str(raw["endpoint"]),
        error_code=str(raw["error_code"]),
        error_message=str(raw["error_message"]),
        attempts=int(raw["attempts"]),
        ledger_id=str(raw["ledger_id"]) if raw.get("ledger_id") is not None else None,
        created_at=datetime.fromisoformat(str(raw["created_at"])).astimezone(UTC),
    )


def _list_or_empty(value: object) -> list[object]:
    if isinstance(value, list):
        return value
    return []


def _parse_ledger_state(value: str) -> LedgerState:
    normalized = value.strip().lower()
    if normalized in {"prepared", "sent", "acked", "nacked"}:
        return cast(LedgerState, normalized)
    raise CommunicationRepositoryError(
        code="communication_snapshot_invalid_state",
        message=f"invalid communication ledger state in snapshot: {value}",
    )
