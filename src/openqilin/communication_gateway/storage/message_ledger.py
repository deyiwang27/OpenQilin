"""Message ledger for ACP delivery state transitions."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from openqilin.data_access.repositories.communication import (
    CommunicationMessageRecord,
    CommunicationStateTransition,
    LedgerState,
)

_ALLOWED_TRANSITIONS: dict[LedgerState, frozenset[LedgerState]] = {
    "prepared": frozenset({"sent", "nacked"}),
    "sent": frozenset({"acked", "nacked"}),
    "acked": frozenset(),
    "nacked": frozenset(),
}


class MessageLedgerError(ValueError):
    """Raised when a message-ledger operation violates lifecycle contract."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class LocalMessageLedger:
    """Deterministic in-process ledger for communication message lifecycle."""

    def __init__(self) -> None:
        self._records: dict[str, CommunicationMessageRecord] = {}
        self._records_by_task: dict[str, list[str]] = {}

    def begin_dispatch(
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
        """Persist prepared transition when dispatch pipeline starts."""

        ledger_id = str(uuid4())
        now = datetime.now(tz=UTC)
        prepared_transition = CommunicationStateTransition(
            state="prepared",
            changed_at=now,
            reason_code="dispatch_started",
            message="dispatch pipeline started",
            retryable=None,
        )
        record = CommunicationMessageRecord(
            ledger_id=ledger_id,
            task_id=task_id,
            trace_id=trace_id,
            message_id=message_id,
            external_message_id=external_message_id,
            connector=connector,
            command=command,
            target=target,
            route_key=route_key,
            endpoint=endpoint,
            state="prepared",
            attempt=attempt,
            dispatch_id=None,
            delivery_id=None,
            error_code=None,
            error_message=None,
            retryable=None,
            transitions=(prepared_transition,),
            created_at=now,
            updated_at=now,
        )
        self._records[ledger_id] = record
        self._records_by_task.setdefault(task_id, []).append(ledger_id)
        return record

    def mark_sent(
        self,
        *,
        ledger_id: str,
        dispatch_id: str,
        delivery_id: str,
    ) -> CommunicationMessageRecord:
        """Persist sent transition after ACP client accepted send request."""

        record = self._require_record(ledger_id)
        self._assert_transition(record.state, "sent")
        from dataclasses import replace

        now = datetime.now(tz=UTC)
        sent_transition = CommunicationStateTransition(
            state="sent",
            changed_at=now,
            reason_code="acp_accepted",
            message="ACP send accepted",
            retryable=None,
        )
        updated = replace(
            record,
            state="sent",
            dispatch_id=dispatch_id,
            delivery_id=delivery_id,
            transitions=record.transitions + (sent_transition,),
            updated_at=now,
        )
        self._records[ledger_id] = updated
        return updated

    def mark_acked(
        self,
        *,
        ledger_id: str,
        reason_code: str,
        message: str,
    ) -> CommunicationMessageRecord:
        """Persist terminal acked transition."""

        record = self._require_record(ledger_id)
        self._assert_transition(record.state, "acked")
        from dataclasses import replace

        now = datetime.now(tz=UTC)
        acked_transition = CommunicationStateTransition(
            state="acked",
            changed_at=now,
            reason_code=reason_code,
            message=message,
            retryable=False,
        )
        updated = replace(
            record,
            state="acked",
            retryable=False,
            transitions=record.transitions + (acked_transition,),
            updated_at=now,
        )
        self._records[ledger_id] = updated
        return updated

    def mark_nacked(
        self,
        *,
        ledger_id: str,
        error_code: str,
        message: str,
        retryable: bool,
    ) -> CommunicationMessageRecord:
        """Persist terminal nacked transition with retryability metadata."""

        record = self._require_record(ledger_id)
        self._assert_transition(record.state, "nacked")
        from dataclasses import replace

        now = datetime.now(tz=UTC)
        nacked_transition = CommunicationStateTransition(
            state="nacked",
            changed_at=now,
            reason_code=error_code,
            message=message,
            retryable=retryable,
        )
        updated = replace(
            record,
            state="nacked",
            error_code=error_code,
            error_message=message,
            retryable=retryable,
            transitions=record.transitions + (nacked_transition,),
            updated_at=now,
        )
        self._records[ledger_id] = updated
        return updated

    def get_record(self, ledger_id: str) -> CommunicationMessageRecord | None:
        """Load one message ledger record."""

        return self._records.get(ledger_id)

    def list_records_for_task(self, task_id: str) -> tuple[CommunicationMessageRecord, ...]:
        """List message ledger records for a task."""

        ledger_ids = self._records_by_task.get(task_id, [])
        return tuple(self._records[lid] for lid in ledger_ids if lid in self._records)

    def list_records(self) -> tuple[CommunicationMessageRecord, ...]:
        """List all message ledger records."""

        return tuple(self._records.values())

    def _require_record(self, ledger_id: str) -> CommunicationMessageRecord:
        record = self._records.get(ledger_id)
        if record is None:
            raise MessageLedgerError(
                code="message_ledger_missing_record",
                message="message ledger record not found",
            )
        return record

    @staticmethod
    def _assert_transition(current: LedgerState, next_state: LedgerState) -> None:
        allowed = _ALLOWED_TRANSITIONS[current]
        if next_state in allowed:
            return
        raise MessageLedgerError(
            code="message_ledger_invalid_transition",
            message=f"invalid message ledger transition: {current} -> {next_state}",
        )


# Backward-compatible alias retained for existing imports.
InMemoryMessageLedger = LocalMessageLedger
