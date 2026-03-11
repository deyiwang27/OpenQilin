"""ACP publisher orchestrating send + ack/nack lifecycle persistence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from openqilin.communication_gateway.delivery.ack_handler import MessageAckHandler
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
    message_id: str
    external_message_id: str
    connector: str
    command: str
    target: str
    args: tuple[str, ...]
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
    ledger_id: str


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
    ) -> None:
        self._ledger = message_ledger or InMemoryMessageLedger()
        self._acp_client = acp_client or InMemoryAcpClient()
        self._ack_handler = ack_handler or MessageAckHandler(self._ledger)

    def publish(self, payload: PublishRequest) -> PublishReceipt:
        """Execute send + ack/nack pipeline and persist deterministic transitions."""

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
            return PublishReceipt(
                accepted=False,
                dispatch_id=None,
                error_code=failed.error_code,
                message=failed.error_message or error.message,
                retryable=bool(failed.retryable),
                route_key=failed.route_key,
                ledger_id=failed.ledger_id,
            )

        sent = self._ledger.mark_sent(
            ledger_id=record.ledger_id,
            dispatch_id=send_receipt.dispatch_id,
            delivery_id=send_receipt.delivery_id,
        )
        handled = self._ack_handler.handle(ledger_id=record.ledger_id, send_receipt=send_receipt)
        return PublishReceipt(
            accepted=handled.accepted,
            dispatch_id=handled.dispatch_id,
            error_code=handled.error_code,
            message=handled.message,
            retryable=handled.retryable,
            route_key=sent.route_key,
            ledger_id=sent.ledger_id,
        )

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
