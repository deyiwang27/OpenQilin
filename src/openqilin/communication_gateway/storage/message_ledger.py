"""Message ledger for ACP delivery state transitions."""

from __future__ import annotations

from openqilin.data_access.repositories.communication import (
    CommunicationMessageRecord,
    InMemoryCommunicationRepository,
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


class InMemoryMessageLedger:
    """Deterministic in-memory ledger for communication message lifecycle."""

    def __init__(self, repository: InMemoryCommunicationRepository | None = None) -> None:
        self._repository = repository or InMemoryCommunicationRepository()

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

        return self._repository.create_record(
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
        )

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
        updated = self._repository.append_transition(
            ledger_id,
            state="sent",
            reason_code="acp_send_accepted",
            message="ACP client accepted send request",
            retryable=None,
            dispatch_id=dispatch_id,
            delivery_id=delivery_id,
            error_code=None,
            error_message=None,
        )
        if updated is None:
            raise MessageLedgerError(
                code="message_ledger_missing_record",
                message="message ledger record missing during sent transition",
            )
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
        updated = self._repository.append_transition(
            ledger_id,
            state="acked",
            reason_code=reason_code,
            message=message,
            retryable=False,
            dispatch_id=record.dispatch_id,
            delivery_id=record.delivery_id,
            error_code=None,
            error_message=None,
        )
        if updated is None:
            raise MessageLedgerError(
                code="message_ledger_missing_record",
                message="message ledger record missing during ack transition",
            )
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
        updated = self._repository.append_transition(
            ledger_id,
            state="nacked",
            reason_code=error_code,
            message=message,
            retryable=retryable,
            dispatch_id=record.dispatch_id,
            delivery_id=record.delivery_id,
            error_code=error_code,
            error_message=message,
        )
        if updated is None:
            raise MessageLedgerError(
                code="message_ledger_missing_record",
                message="message ledger record missing during nack transition",
            )
        return updated

    def get_record(self, ledger_id: str) -> CommunicationMessageRecord | None:
        """Load one message ledger record."""

        return self._repository.get_record(ledger_id)

    def list_records_for_task(self, task_id: str) -> tuple[CommunicationMessageRecord, ...]:
        """List message ledger records for a task."""

        return self._repository.list_records_for_task(task_id)

    def list_records(self) -> tuple[CommunicationMessageRecord, ...]:
        """List all message ledger records."""

        return self._repository.list_records()

    def _require_record(self, ledger_id: str) -> CommunicationMessageRecord:
        record = self._repository.get_record(ledger_id)
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
