from openqilin.control_plane.identity.principal_resolver import resolve_principal
from openqilin.data_access.repositories.runtime_state import (
    InMemoryRuntimeStateRepository,
    TaskRecord,
)
from openqilin.task_orchestrator.admission.envelope_validator import validate_owner_command_envelope
from openqilin.task_orchestrator.dispatch.sandbox_dispatch import SandboxDispatchStub
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
        lifecycle_service=lifecycle, sandbox_dispatch_stub=SandboxDispatchStub()
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
        lifecycle_service=lifecycle, sandbox_dispatch_stub=SandboxDispatchStub()
    )

    outcome = service.dispatch_admitted_task(task)

    assert outcome.accepted is False
    assert outcome.error_code == "execution_dispatch_failed"
    updated = repository.get_task_by_id(task.task_id)
    assert updated is not None
    assert updated.status == "blocked_dispatch"


def test_dispatch_service_is_replay_safe_by_task_id() -> None:
    task, repository = _build_task("run_task")
    lifecycle = TaskLifecycleService(runtime_state_repo=repository)
    service = TaskDispatchService(
        lifecycle_service=lifecycle, sandbox_dispatch_stub=SandboxDispatchStub()
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
        lifecycle_service=lifecycle, sandbox_dispatch_stub=SandboxDispatchStub()
    )

    outcome = service.dispatch_admitted_task(task)

    assert outcome.accepted is True
    assert outcome.target == "llm"
    assert outcome.dispatch_id
