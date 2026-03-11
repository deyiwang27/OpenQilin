"""ACP publisher orchestrating send + ack/nack lifecycle persistence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from openqilin.communication_gateway.delivery.ack_handler import MessageAckHandler
from openqilin.communication_gateway.delivery.retry_scheduler import (
    DeterministicRetryScheduler,
    RetryScheduler,
)
from openqilin.communication_gateway.storage.idempotency_store import (
    CommunicationIdempotencyRecord,
    InMemoryCommunicationIdempotencyStore,
)
from openqilin.communication_gateway.storage.message_ledger import InMemoryMessageLedger
from openqilin.communication_gateway.transport.acp_client import (
    AcpClient,
    AcpClientError,
    AcpSendRequest,
    InMemoryAcpClient,
)
from openqilin.data_access.repositories.communication import CommunicationMessageRecord


@dataclass(frozen=True, slots=True)
class PublishRequest:
    """Publisher input payload."""

    task_id: str
    trace_id: str
    principal_id: str
    idempotency_key: str
    message_id: str
    external_message_id: str
    connector: str
    command: str
    target: str
    args: tuple[str, ...]
    project_id: str | None
    route_key: str
    endpoint: str


@dataclass(frozen=True, slots=True)
class PublishReceipt:
    """Publisher result mapped back to communication dispatch adapter."""

    accepted: bool
    dispatch_id: str | None
    error_code: str | None
    message: str
    retryable: bool
    route_key: str
    ledger_id: str | None


class DeliveryPublisher(Protocol):
    """Publisher protocol."""

    def publish(self, payload: PublishRequest) -> PublishReceipt:
        """Publish communication message through ACP send lifecycle."""


class InMemoryDeliveryPublisher:
    """Deterministic publisher using in-memory ACP client and message ledger."""

    def __init__(
        self,
        *,
        acp_client: AcpClient | None = None,
        message_ledger: InMemoryMessageLedger | None = None,
        ack_handler: MessageAckHandler | None = None,
        retry_scheduler: RetryScheduler | None = None,
        idempotency_store: InMemoryCommunicationIdempotencyStore | None = None,
    ) -> None:
        self._ledger = message_ledger or InMemoryMessageLedger()
        self._acp_client = acp_client or InMemoryAcpClient()
        self._ack_handler = ack_handler or MessageAckHandler(self._ledger)
        self._retry_scheduler = retry_scheduler or DeterministicRetryScheduler()
        self._idempotency_store = idempotency_store or InMemoryCommunicationIdempotencyStore()

    def publish(self, payload: PublishRequest) -> PublishReceipt:
        """Execute send + ack/nack pipeline and persist deterministic transitions."""

        delivery_key = self._idempotency_store.build_delivery_key(
            connector=payload.connector,
            principal_id=payload.principal_id,
            project_id=payload.project_id,
            idempotency_key=payload.idempotency_key,
            message_id=payload.message_id,
            external_message_id=payload.external_message_id,
        )
        payload_hash = self._idempotency_store.fingerprint_payload(
            {
                "task_id": payload.task_id,
                "trace_id": payload.trace_id,
                "principal_id": payload.principal_id,
                "idempotency_key": payload.idempotency_key,
                "message_id": payload.message_id,
                "external_message_id": payload.external_message_id,
                "connector": payload.connector,
                "command": payload.command,
                "target": payload.target,
                "args": payload.args,
                "project_id": payload.project_id,
                "route_key": payload.route_key,
                "endpoint": payload.endpoint,
            }
        )
        claim_status, claim = self._idempotency_store.claim(
            key=delivery_key,
            payload_hash=payload_hash,
        )
        if claim_status == "conflict":
            return PublishReceipt(
                accepted=False,
                dispatch_id=None,
                error_code="communication_idempotency_conflict",
                message="communication idempotency key reused with different payload",
                retryable=False,
                route_key=payload.route_key,
                ledger_id=None,
            )
        if claim_status == "replay":
            return _cached_result_to_receipt(
                result=claim.result,
                fallback_route_key=payload.route_key,
            )
        if claim_status == "in_progress":
            return PublishReceipt(
                accepted=False,
                dispatch_id=None,
                error_code="communication_idempotency_in_progress",
                message="communication delivery already in progress",
                retryable=True,
                route_key=payload.route_key,
                ledger_id=None,
            )

        attempt = 1
        terminal_receipt: PublishReceipt | None = None
        while True:
            self._idempotency_store.increment_attempt(key=delivery_key)
            record = self._ledger.begin_dispatch(
                task_id=payload.task_id,
                trace_id=payload.trace_id,
                message_id=payload.message_id,
                external_message_id=payload.external_message_id,
                connector=payload.connector,
                command=payload.command,
                target=payload.target,
                route_key=payload.route_key,
                endpoint=payload.endpoint,
                attempt=attempt,
            )
            try:
                send_receipt = self._acp_client.send(
                    AcpSendRequest(
                        task_id=payload.task_id,
                        trace_id=payload.trace_id,
                        message_id=payload.message_id,
                        external_message_id=payload.external_message_id,
                        connector=payload.connector,
                        command=payload.command,
                        target=payload.target,
                        args=payload.args,
                        route_key=payload.route_key,
                        endpoint=payload.endpoint,
                    )
                )
            except AcpClientError as error:
                failed = self._ledger.mark_nacked(
                    ledger_id=record.ledger_id,
                    error_code=error.code,
                    message=error.message,
                    retryable=error.retryable,
                )
                terminal_receipt = PublishReceipt(
                    accepted=False,
                    dispatch_id=None,
                    error_code=failed.error_code,
                    message=failed.error_message or error.message,
                    retryable=bool(failed.retryable),
                    route_key=failed.route_key,
                    ledger_id=failed.ledger_id,
                )
            else:
                sent = self._ledger.mark_sent(
                    ledger_id=record.ledger_id,
                    dispatch_id=send_receipt.dispatch_id,
                    delivery_id=send_receipt.delivery_id,
                )
                handled = self._ack_handler.handle(
                    ledger_id=record.ledger_id,
                    send_receipt=send_receipt,
                )
                terminal_receipt = PublishReceipt(
                    accepted=handled.accepted,
                    dispatch_id=handled.dispatch_id,
                    error_code=handled.error_code,
                    message=handled.message,
                    retryable=handled.retryable,
                    route_key=sent.route_key,
                    ledger_id=sent.ledger_id,
                )

            if terminal_receipt.accepted:
                self._idempotency_store.complete(
                    key=delivery_key,
                    result=_receipt_result_payload(
                        receipt=terminal_receipt,
                        attempts=attempt,
                    ),
                )
                return terminal_receipt

            decision = self._retry_scheduler.schedule_next(
                attempt=attempt,
                error_code=terminal_receipt.error_code or "communication_delivery_failed",
                retryable=terminal_receipt.retryable,
            )
            if decision.retry:
                attempt = decision.next_attempt
                continue

            if decision.reason_code == "communication_retry_exhausted":
                terminal_receipt = PublishReceipt(
                    accepted=False,
                    dispatch_id=None,
                    error_code="communication_retry_exhausted",
                    message=(
                        f"{decision.message}; last_error={terminal_receipt.error_code or 'unknown'}"
                    ),
                    retryable=False,
                    route_key=terminal_receipt.route_key,
                    ledger_id=terminal_receipt.ledger_id,
                )
            self._idempotency_store.complete(
                key=delivery_key,
                result=_receipt_result_payload(
                    receipt=terminal_receipt,
                    attempts=attempt,
                ),
            )
            return terminal_receipt

    def list_message_records(
        self,
        *,
        task_id: str | None = None,
    ) -> tuple[CommunicationMessageRecord, ...]:
        """List persisted message records for diagnostics/tests."""

        if task_id is None:
            return self._ledger.list_records()
        return self._ledger.list_records_for_task(task_id)

    def get_message_record(self, ledger_id: str) -> CommunicationMessageRecord | None:
        """Load one persisted message record."""

        return self._ledger.get_record(ledger_id)

    def list_idempotency_records(self) -> tuple[CommunicationIdempotencyRecord, ...]:
        """List communication idempotency records for diagnostics/tests."""

        return self._idempotency_store.list_records()


def _receipt_result_payload(
    *,
    receipt: PublishReceipt,
    attempts: int,
) -> dict[str, object]:
    return {
        "accepted": receipt.accepted,
        "dispatch_id": receipt.dispatch_id or "",
        "error_code": receipt.error_code or "",
        "message": receipt.message,
        "retryable": str(receipt.retryable).lower(),
        "route_key": receipt.route_key,
        "ledger_id": receipt.ledger_id or "",
        "attempts": attempts,
    }


def _cached_result_to_receipt(
    *,
    result: tuple[tuple[str, str], ...] | None,
    fallback_route_key: str,
) -> PublishReceipt:
    mapped = dict(result or ())
    return PublishReceipt(
        accepted=mapped.get("accepted") == "True",
        dispatch_id=mapped.get("dispatch_id") or None,
        error_code=mapped.get("error_code") or None,
        message=mapped.get("message", "communication delivery replay resolved"),
        retryable=mapped.get("retryable") == "true",
        route_key=mapped.get("route_key", fallback_route_key),
        ledger_id=mapped.get("ledger_id") or None,
    )
