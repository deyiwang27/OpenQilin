"""Communication message repository primitives for delivery lifecycle persistence."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

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


class InMemoryCommunicationRepository:
    """In-memory repository storing communication message lifecycle records."""

    def __init__(self) -> None:
        self._records_by_ledger_id: dict[str, CommunicationMessageRecord] = {}
        self._ledger_ids_by_task_id: dict[str, list[str]] = defaultdict(list)

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
