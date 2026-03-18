"""Ack/nack handling for ACP delivery lifecycle."""

from __future__ import annotations

from dataclasses import dataclass

from openqilin.communication_gateway.storage.message_ledger import LocalMessageLedger
from openqilin.communication_gateway.transport.acp_client import AcpSendReceipt


@dataclass(frozen=True, slots=True)
class AckHandlingResult:
    """Normalized ack-handling result for publisher/dispatch mapping."""

    accepted: bool
    dispatch_id: str | None
    error_code: str | None
    message: str
    retryable: bool


class MessageAckHandler:
    """Apply ACP ack/nack outcomes to message ledger and return dispatch result."""

    def __init__(self, ledger: LocalMessageLedger) -> None:
        self._ledger = ledger

    def handle(self, *, ledger_id: str, send_receipt: AcpSendReceipt) -> AckHandlingResult:
        """Persist ack/nack terminal transition and map to dispatch outcome."""

        if send_receipt.status == "ack":
            self._ledger.mark_acked(
                ledger_id=ledger_id,
                reason_code=send_receipt.code,
                message=send_receipt.message,
            )
            return AckHandlingResult(
                accepted=True,
                dispatch_id=send_receipt.dispatch_id,
                error_code=None,
                message=send_receipt.message,
                retryable=False,
            )

        self._ledger.mark_nacked(
            ledger_id=ledger_id,
            error_code=send_receipt.code,
            message=send_receipt.message,
            retryable=send_receipt.retryable,
        )
        return AckHandlingResult(
            accepted=False,
            dispatch_id=None,
            error_code=send_receipt.code,
            message=send_receipt.message,
            retryable=send_receipt.retryable,
        )
