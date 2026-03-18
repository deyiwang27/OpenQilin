"""Communication message repository primitives for delivery lifecycle persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

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
