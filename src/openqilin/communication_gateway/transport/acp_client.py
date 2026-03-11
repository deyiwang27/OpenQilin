"""Deterministic ACP transport adapter for communication delivery pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol
from uuid import uuid4

AcpDeliveryStatus = Literal["ack", "nack"]


class AcpClientError(RuntimeError):
    """Raised when ACP transport call cannot be completed."""

    def __init__(self, code: str, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


@dataclass(frozen=True, slots=True)
class AcpSendRequest:
    """Normalized ACP send payload."""

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
class AcpSendReceipt:
    """ACP transport send result with deterministic ack/nack semantics."""

    dispatch_id: str
    delivery_id: str
    status: AcpDeliveryStatus
    code: str
    message: str
    retryable: bool


class AcpClient(Protocol):
    """ACP transport client protocol."""

    def send(self, payload: AcpSendRequest) -> AcpSendReceipt:
        """Send communication payload through ACP transport."""


class InMemoryAcpClient:
    """Deterministic in-memory ACP client for send/ack/nack lifecycle tests."""

    def send(self, payload: AcpSendRequest) -> AcpSendReceipt:
        """Send message and return deterministic ack/nack outcome."""

        if payload.command == "msg_transport_error":
            raise AcpClientError(
                code="acp_transport_unavailable",
                message="ACP transport unavailable during send",
                retryable=True,
            )

        dispatch_id = f"acp-{uuid4()}"
        delivery_id = f"delivery-{uuid4()}"
        if payload.command == "msg_dispatch_reject":
            return AcpSendReceipt(
                dispatch_id=dispatch_id,
                delivery_id=delivery_id,
                status="nack",
                code="acp_contract_rejected",
                message="ACP contract rejected communication payload",
                retryable=False,
            )
        if payload.command == "msg_dispatch_retryable_nack":
            return AcpSendReceipt(
                dispatch_id=dispatch_id,
                delivery_id=delivery_id,
                status="nack",
                code="acp_delivery_nack_retryable",
                message="ACP transport returned retryable nack",
                retryable=True,
            )
        if payload.command == "msg_dispatch_nack":
            return AcpSendReceipt(
                dispatch_id=dispatch_id,
                delivery_id=delivery_id,
                status="nack",
                code="acp_delivery_nack",
                message="ACP transport returned nack",
                retryable=False,
            )
        return AcpSendReceipt(
            dispatch_id=dispatch_id,
            delivery_id=delivery_id,
            status="ack",
            code="acp_delivery_acked",
            message=f"ACP delivery acknowledged via {payload.route_key}",
            retryable=False,
        )
