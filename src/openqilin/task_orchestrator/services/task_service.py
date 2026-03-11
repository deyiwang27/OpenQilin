"""Task dispatch orchestration service for governed execution targets."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from openqilin.data_access.repositories.runtime_state import TaskRecord
from openqilin.task_orchestrator.dispatch.sandbox_dispatch import (
    InMemorySandboxExecutionAdapter,
    SandboxDispatchRequest,
    SandboxExecutionAdapter,
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
    source: str


class TaskDispatchService:
    """Coordinates dispatch target selection and lifecycle transitions."""

    def __init__(
        self,
        lifecycle_service: TaskLifecycleService,
        sandbox_execution_adapter: SandboxExecutionAdapter,
    ) -> None:
        self._lifecycle_service = lifecycle_service
        self._sandbox_execution_adapter = sandbox_execution_adapter
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
                source=existing.source,
            )

        target = select_dispatch_target(task)
        if target == "sandbox":
            try:
                receipt = self._sandbox_execution_adapter.dispatch(
                    SandboxDispatchRequest(
                        task_id=task.task_id,
                        trace_id=task.trace_id,
                        command=task.command,
                        args=task.args,
                    )
                )
            except Exception:
                self._lifecycle_service.mark_blocked_dispatch(
                    task.task_id,
                    error_code="execution_dispatch_adapter_error",
                    message="sandbox adapter execution failed",
                    dispatch_target=target,
                    outcome_source="dispatch_sandbox_adapter",
                )
                outcome = TaskDispatchOutcome(
                    accepted=False,
                    target=target,
                    dispatch_id=None,
                    error_code="execution_dispatch_adapter_error",
                    message="sandbox adapter execution failed",
                    replayed=False,
                    source="dispatch_sandbox_adapter",
                )
                self._task_outcomes[task.task_id] = outcome
                return outcome
            if receipt.accepted:
                dispatch_id = receipt.dispatch_id or f"sandbox-{uuid4()}"
                self._lifecycle_service.mark_dispatched(
                    task.task_id,
                    dispatch_target=target,
                    dispatch_id=dispatch_id,
                    message=receipt.message,
                )
                outcome = TaskDispatchOutcome(
                    accepted=True,
                    target=target,
                    dispatch_id=dispatch_id,
                    error_code=None,
                    message=receipt.message,
                    replayed=False,
                    source="dispatch_sandbox_adapter",
                )
            else:
                self._lifecycle_service.mark_blocked_dispatch(
                    task.task_id,
                    error_code=receipt.error_code,
                    message=receipt.message,
                    dispatch_target=target,
                    outcome_source="dispatch_sandbox_adapter",
                )
                outcome = TaskDispatchOutcome(
                    accepted=False,
                    target=target,
                    dispatch_id=None,
                    error_code=receipt.error_code,
                    message=receipt.message,
                    replayed=False,
                    source="dispatch_sandbox_adapter",
                )
        else:
            # M2-WP1 keeps non-sandbox targets as controlled stubs.
            dispatch_id = f"{target}-{uuid4()}"
            message = f"{target} dispatch stub accepted"
            self._lifecycle_service.mark_dispatched(
                task.task_id,
                dispatch_target=target,
                dispatch_id=dispatch_id,
                message=message,
            )
            outcome = TaskDispatchOutcome(
                accepted=True,
                target=target,
                dispatch_id=dispatch_id,
                error_code=None,
                message=message,
                replayed=False,
                source=f"dispatch_{target}",
            )

        self._task_outcomes[task.task_id] = outcome
        return outcome


def build_task_dispatch_service(lifecycle_service: TaskLifecycleService) -> TaskDispatchService:
    """Build task-dispatch service with default in-memory sandbox adapter."""

    return TaskDispatchService(
        lifecycle_service=lifecycle_service,
        sandbox_execution_adapter=InMemorySandboxExecutionAdapter(),
    )
