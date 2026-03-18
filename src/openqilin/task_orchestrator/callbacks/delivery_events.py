"""Communication delivery callback processing for orchestrator lifecycle updates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from openqilin.data_access.repositories.runtime_state import TaskRecord
from openqilin.observability.audit.audit_writer import OTelAuditWriter
from openqilin.observability.testing.stubs import InMemoryAuditWriter
from openqilin.observability.testing.stubs import InMemoryMetricRecorder

DeliveryOutcome = Literal["delivered", "nacked", "dead_lettered"]
IMMUTABLE_TASK_STATUSES = frozenset({"completed", "failed", "cancelled"})


class _RuntimeStateRepo(Protocol):
    """Protocol for runtime state repository used by delivery callback processor."""

    def get_task_by_id(self, task_id: str) -> TaskRecord | None:
        """Return one task record by id."""

    def update_task_status(
        self,
        task_id: str,
        status: str,
        *,
        outcome_source: str,
        outcome_error_code: str | None,
        outcome_message: str,
        outcome_details: dict[str, object],
        dispatch_target: str,
        dispatch_id: str | None,
    ) -> TaskRecord | None:
        """Transition task status and return updated record."""


@dataclass(frozen=True, slots=True)
class DeliveryCallbackEvent:
    """Normalized callback event produced by communication gateway outcomes."""

    callback_id: str
    task_id: str
    trace_id: str
    dispatch_target: str
    delivery_outcome: DeliveryOutcome
    message: str
    reason_code: str | None = None
    dispatch_id: str | None = None
    dead_letter_id: str | None = None


@dataclass(frozen=True, slots=True)
class DeliveryCallbackResult:
    """Callback processing result with replay indicator for at-least-once handling."""

    applied: bool
    replayed: bool
    task_status: str
    message: str
    reason_code: str | None


class LocalDeliveryEventCallbackProcessor:
    """Duplicate-safe callback processor for communication delivery lifecycle events."""

    def __init__(
        self,
        *,
        runtime_state_repo: _RuntimeStateRepo,
        audit_writer: InMemoryAuditWriter | OTelAuditWriter,
        metric_recorder: InMemoryMetricRecorder,
    ) -> None:
        self._runtime_state_repo = runtime_state_repo
        self._audit_writer = audit_writer
        self._metric_recorder = metric_recorder
        self._processed_callback_ids: set[str] = set()

    def process(self, event: DeliveryCallbackEvent) -> DeliveryCallbackResult:
        """Process callback event with duplicate-safe semantics."""

        if event.callback_id in self._processed_callback_ids:
            self._metric_recorder.increment_counter(
                "communication_callback_events_total",
                labels={"outcome": event.delivery_outcome, "replayed": "true"},
            )
            return DeliveryCallbackResult(
                applied=False,
                replayed=True,
                task_status="unchanged",
                message="callback event already processed",
                reason_code=event.reason_code,
            )

        task = self._runtime_state_repo.get_task_by_id(event.task_id)
        if task is None:
            self._metric_recorder.increment_counter(
                "communication_callback_events_total",
                labels={"outcome": "missing_task", "replayed": "false"},
            )
            return DeliveryCallbackResult(
                applied=False,
                replayed=False,
                task_status="missing",
                message="callback task not found",
                reason_code="callback_task_not_found",
            )

        if task.status in IMMUTABLE_TASK_STATUSES:
            self._processed_callback_ids.add(event.callback_id)
            self._metric_recorder.increment_counter(
                "communication_callback_events_total",
                labels={"outcome": event.delivery_outcome, "replayed": "false"},
            )
            self._audit_writer.write_event(
                event_type="communication.callback.ignored_terminal",
                outcome="ignored_terminal",
                trace_id=event.trace_id,
                request_id=task.request_id,
                task_id=task.task_id,
                principal_id=task.principal_id,
                principal_role=task.principal_role,
                source="communication_callback",
                reason_code="callback_task_terminal_immutable",
                message="callback ignored because task is already terminal",
                payload={
                    "callback_id": event.callback_id,
                    "delivery_outcome": event.delivery_outcome,
                    "current_status": task.status,
                },
                attributes={
                    "callback_id": event.callback_id,
                    "delivery_outcome": event.delivery_outcome,
                    "current_status": task.status,
                },
            )
            return DeliveryCallbackResult(
                applied=False,
                replayed=False,
                task_status=task.status,
                message="callback ignored for terminal task state",
                reason_code="callback_task_terminal_immutable",
            )

        outcome_details: dict[str, object] = {
            "callback_id": event.callback_id,
            "delivery_outcome": event.delivery_outcome,
            "dispatch_target": event.dispatch_target,
            "dispatch_id": event.dispatch_id or task.dispatch_id or "",
            "dead_letter_id": event.dead_letter_id or "",
            "reason_code": event.reason_code or "",
            "replayed": "false",
        }
        updated = self._apply_task_update(task=task, event=event, outcome_details=outcome_details)
        self._processed_callback_ids.add(event.callback_id)

        self._metric_recorder.increment_counter(
            "communication_callback_events_total",
            labels={"outcome": event.delivery_outcome, "replayed": "false"},
        )
        self._audit_writer.write_event(
            event_type=f"communication.callback.{event.delivery_outcome}",
            outcome=event.delivery_outcome,
            trace_id=event.trace_id,
            request_id=updated.request_id,
            task_id=updated.task_id,
            principal_id=updated.principal_id,
            principal_role=updated.principal_role,
            source="communication_callback",
            reason_code=event.reason_code,
            message=event.message,
            payload=outcome_details,
            attributes={
                "callback_id": event.callback_id,
                "delivery_outcome": event.delivery_outcome,
                "dead_letter_id": event.dead_letter_id or "",
            },
        )
        return DeliveryCallbackResult(
            applied=True,
            replayed=False,
            task_status=updated.status,
            message=event.message,
            reason_code=event.reason_code,
        )

    def _apply_task_update(
        self,
        *,
        task: TaskRecord,
        event: DeliveryCallbackEvent,
        outcome_details: dict[str, object],
    ) -> TaskRecord:
        if event.delivery_outcome == "delivered":
            updated = self._runtime_state_repo.update_task_status(
                task.task_id,
                "dispatched",
                outcome_source="callback_communication_delivery",
                outcome_error_code=None,
                outcome_message=event.message,
                outcome_details=outcome_details,
                dispatch_target=event.dispatch_target,
                dispatch_id=event.dispatch_id or task.dispatch_id,
            )
        elif event.delivery_outcome == "dead_lettered":
            updated = self._runtime_state_repo.update_task_status(
                task.task_id,
                "blocked",
                outcome_source="callback_communication_dead_letter",
                outcome_error_code=event.reason_code or "communication_dead_lettered",
                outcome_message=event.message,
                outcome_details=outcome_details,
                dispatch_target=event.dispatch_target,
                dispatch_id=None,
            )
        else:
            updated = self._runtime_state_repo.update_task_status(
                task.task_id,
                "blocked",
                outcome_source="callback_communication_nack",
                outcome_error_code=event.reason_code or "communication_callback_nack",
                outcome_message=event.message,
                outcome_details=outcome_details,
                dispatch_target=event.dispatch_target,
                dispatch_id=None,
            )

        if updated is None:
            raise RuntimeError(f"callback update failed for task {task.task_id}")
        return updated


# Backward-compatible alias retained for existing imports.
InMemoryDeliveryEventCallbackProcessor = LocalDeliveryEventCallbackProcessor
