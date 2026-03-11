from openqilin.control_plane.identity.principal_resolver import resolve_principal
from openqilin.data_access.repositories.runtime_state import (
    InMemoryRuntimeStateRepository,
    TaskRecord,
)
from openqilin.task_orchestrator.admission.envelope_validator import validate_owner_command_envelope
from openqilin.task_orchestrator.dispatch.sandbox_dispatch import (
    InMemorySandboxExecutionAdapter,
    SandboxDispatchRequest,
    SandboxDispatchReceipt,
)
from openqilin.task_orchestrator.services.lifecycle_service import TaskLifecycleService
from openqilin.task_orchestrator.services.task_service import TaskDispatchService
from openqilin.testing.owner_command import build_owner_command_request_model


def _build_task(command: str) -> tuple[TaskRecord, InMemoryRuntimeStateRepository]:
    payload = build_owner_command_request_model(
        action=command,
        args=["alpha"],
        actor_id="owner_dispatch_001",
        idempotency_key=f"idem-{command}-12345678",
        trace_id="trace-dispatch-test",
    )
    principal = resolve_principal(
        {
            "x-external-channel": "discord",
            "x-openqilin-actor-external-id": "owner_dispatch_001",
        }
    )
    envelope = validate_owner_command_envelope(payload=payload, principal=principal)
    repository = InMemoryRuntimeStateRepository()
    task = repository.create_task_from_envelope(envelope)
    return task, repository


def test_dispatch_service_marks_dispatched_on_success() -> None:
    task, repository = _build_task("run_task")
    lifecycle = TaskLifecycleService(runtime_state_repo=repository)
    service = TaskDispatchService(
        lifecycle_service=lifecycle,
        sandbox_execution_adapter=InMemorySandboxExecutionAdapter(),
    )

    outcome = service.dispatch_admitted_task(task)

    assert outcome.accepted is True
    assert outcome.target == "sandbox"
    assert outcome.dispatch_id
    updated = repository.get_task_by_id(task.task_id)
    assert updated is not None
    assert updated.status == "dispatched"


def test_dispatch_service_marks_blocked_dispatch_on_reject() -> None:
    task, repository = _build_task("dispatch_reject")
    lifecycle = TaskLifecycleService(runtime_state_repo=repository)
    service = TaskDispatchService(
        lifecycle_service=lifecycle,
        sandbox_execution_adapter=InMemorySandboxExecutionAdapter(),
    )

    outcome = service.dispatch_admitted_task(task)

    assert outcome.accepted is False
    assert outcome.error_code == "execution_dispatch_failed"
    updated = repository.get_task_by_id(task.task_id)
    assert updated is not None
    assert updated.status == "blocked"
    assert updated.outcome_source == "dispatch_sandbox_adapter"


def test_dispatch_service_is_replay_safe_by_task_id() -> None:
    task, repository = _build_task("run_task")
    lifecycle = TaskLifecycleService(runtime_state_repo=repository)
    service = TaskDispatchService(
        lifecycle_service=lifecycle,
        sandbox_execution_adapter=InMemorySandboxExecutionAdapter(),
    )

    first = service.dispatch_admitted_task(task)
    second = service.dispatch_admitted_task(task)

    assert first.accepted is True
    assert second.accepted is True
    assert first.dispatch_id == second.dispatch_id
    assert second.replayed is True


def test_dispatch_service_selects_llm_target_stub() -> None:
    task, repository = _build_task("llm_summarize")
    lifecycle = TaskLifecycleService(runtime_state_repo=repository)
    service = TaskDispatchService(
        lifecycle_service=lifecycle,
        sandbox_execution_adapter=InMemorySandboxExecutionAdapter(),
    )

    outcome = service.dispatch_admitted_task(task)

    assert outcome.accepted is True
    assert outcome.target == "llm"
    assert outcome.dispatch_id


class _RaisingSandboxAdapter:
    def dispatch(self, payload: SandboxDispatchRequest) -> SandboxDispatchReceipt:
        raise RuntimeError(f"simulated adapter failure for {payload.task_id}")


def test_dispatch_service_fails_closed_when_sandbox_adapter_raises() -> None:
    task, repository = _build_task("run_task")
    lifecycle = TaskLifecycleService(runtime_state_repo=repository)
    service = TaskDispatchService(
        lifecycle_service=lifecycle,
        sandbox_execution_adapter=_RaisingSandboxAdapter(),
    )

    outcome = service.dispatch_admitted_task(task)

    assert outcome.accepted is False
    assert outcome.target == "sandbox"
    assert outcome.error_code == "execution_dispatch_adapter_error"
    assert outcome.source == "dispatch_sandbox_adapter"
    updated = repository.get_task_by_id(task.task_id)
    assert updated is not None
    assert updated.status == "blocked"
    assert updated.outcome_source == "dispatch_sandbox_adapter"
