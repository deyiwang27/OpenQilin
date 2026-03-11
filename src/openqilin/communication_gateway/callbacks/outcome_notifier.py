"""Outcome notifier bridging communication gateway outcomes to orchestrator callbacks."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from openqilin.task_orchestrator.callbacks.delivery_events import (
    DeliveryCallbackEvent,
    DeliveryCallbackResult,
    DeliveryOutcome,
    InMemoryDeliveryEventCallbackProcessor,
)


@dataclass(frozen=True, slots=True)
class CommunicationOutcomeNotification:
    """Communication gateway outcome payload forwarded to callback processor."""

    task_id: str
    trace_id: str
    dispatch_target: str
    delivery_outcome: DeliveryOutcome
    message: str
    callback_id: str | None = None
    reason_code: str | None = None
    dispatch_id: str | None = None
    dead_letter_id: str | None = None


class CommunicationOutcomeNotifier:
    """Converts gateway outcomes to callback events with deterministic IDs."""

    def __init__(self, callback_processor: InMemoryDeliveryEventCallbackProcessor) -> None:
        self._callback_processor = callback_processor

    def notify_delivery_outcome(
        self,
        payload: CommunicationOutcomeNotification,
    ) -> DeliveryCallbackResult:
        """Notify orchestrator callback processor of communication delivery outcome."""

        callback_id = payload.callback_id or self._deterministic_callback_id(payload)
        event = DeliveryCallbackEvent(
            callback_id=callback_id,
            task_id=payload.task_id,
            trace_id=payload.trace_id,
            dispatch_target=payload.dispatch_target,
            delivery_outcome=payload.delivery_outcome,
            message=payload.message,
            reason_code=payload.reason_code,
            dispatch_id=payload.dispatch_id,
            dead_letter_id=payload.dead_letter_id,
        )
        return self._callback_processor.process(event)

    @staticmethod
    def _deterministic_callback_id(payload: CommunicationOutcomeNotification) -> str:
        suffix = payload.dead_letter_id or payload.dispatch_id or payload.reason_code
        if suffix:
            return f"cb:{payload.task_id}:{payload.delivery_outcome}:{suffix}"
        return f"cb:{payload.task_id}:{payload.delivery_outcome}:{uuid4()}"
