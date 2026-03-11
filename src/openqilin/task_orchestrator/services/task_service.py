"""Task dispatch orchestration service for M1 dispatch stub."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from openqilin.data_access.repositories.runtime_state import TaskRecord
from openqilin.task_orchestrator.dispatch.sandbox_dispatch import (
    SandboxDispatchRequest,
    SandboxDispatchStub,
)
from openqilin.task_orchestrator.dispatch.target_selector import (
    DispatchTarget,
    select_dispatch_target,
)
from openqilin.task_orchestrator.services.lifecycle_service import TaskLifecycleService


@dataclass(frozen=True, slots=True)
class TaskDispatchOutcome:
    """Dispatch decision/result for admitted task."""

    accepted: bool
    target: DispatchTarget
    dispatch_id: str | None
    error_code: str | None
    message: str
    replayed: bool


class TaskDispatchService:
    """Coordinates dispatch target selection and lifecycle transitions."""

    def __init__(
        self,
        lifecycle_service: TaskLifecycleService,
        sandbox_dispatch_stub: SandboxDispatchStub,
    ) -> None:
        self._lifecycle_service = lifecycle_service
        self._sandbox_dispatch_stub = sandbox_dispatch_stub
        self._task_outcomes: dict[str, TaskDispatchOutcome] = {}

    def dispatch_admitted_task(self, task: TaskRecord) -> TaskDispatchOutcome:
        """Dispatch admitted task via controlled M1 stub path."""

        existing = self._task_outcomes.get(task.task_id)
        if existing is not None:
            return TaskDispatchOutcome(
                accepted=existing.accepted,
                target=existing.target,
                dispatch_id=existing.dispatch_id,
                error_code=existing.error_code,
                message=existing.message,
                replayed=True,
            )

        target = select_dispatch_target(task)
        if target == "sandbox":
            receipt = self._sandbox_dispatch_stub.dispatch(
                SandboxDispatchRequest(
                    task_id=task.task_id,
                    trace_id=task.trace_id,
                    command=task.command,
                    args=task.args,
                )
            )
            if receipt.accepted:
                self._lifecycle_service.mark_dispatched(task.task_id)
                outcome = TaskDispatchOutcome(
                    accepted=True,
                    target=target,
                    dispatch_id=receipt.dispatch_id,
                    error_code=None,
                    message=receipt.message,
                    replayed=False,
                )
            else:
                self._lifecycle_service.mark_blocked_dispatch(task.task_id)
                outcome = TaskDispatchOutcome(
                    accepted=False,
                    target=target,
                    dispatch_id=None,
                    error_code=receipt.error_code,
                    message=receipt.message,
                    replayed=False,
                )
        else:
            # M1 keeps non-sandbox execution targets as controlled stubs.
            self._lifecycle_service.mark_dispatched(task.task_id)
            outcome = TaskDispatchOutcome(
                accepted=True,
                target=target,
                dispatch_id=f"{target}-{uuid4()}",
                error_code=None,
                message=f"{target} dispatch stub accepted",
                replayed=False,
            )

        self._task_outcomes[task.task_id] = outcome
        return outcome
