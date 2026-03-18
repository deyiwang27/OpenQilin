from openqilin.control_plane.identity.principal_resolver import resolve_principal
from openqilin.data_access.repositories.runtime_state import TaskRecord
from tests.testing.infra_stubs import InMemoryRuntimeStateRepository
from openqilin.task_orchestrator.admission.envelope_validator import validate_owner_command_envelope
from openqilin.task_orchestrator.dispatch.sandbox_dispatch import (
    InMemorySandboxExecutionAdapter,
    SandboxDispatchRequest,
    SandboxDispatchReceipt,
)
from openqilin.task_orchestrator.dispatch.llm_dispatch import LlmGatewayDispatchAdapter
from openqilin.task_orchestrator.dispatch.llm_dispatch import (
    LlmDispatchReceipt,
    LlmDispatchRequest,
)
from openqilin.shared_kernel.config import RuntimeSettings
from openqilin.llm_gateway.service import build_llm_gateway_service
from openqilin.task_orchestrator.services.lifecycle_service import TaskLifecycleService
from openqilin.task_orchestrator.services.task_service import TaskDispatchService
from openqilin.testing.owner_command import build_owner_command_request_model


def _build_task(
    command: str,
    *,
    args: list[str] | None = None,
    target: str = "sandbox",
    recipients: list[dict[str, str]] | None = None,
) -> tuple[TaskRecord, InMemoryRuntimeStateRepository]:
    payload = build_owner_command_request_model(
        action=command,
        args=["alpha"] if args is None else args,
        actor_id="owner_dispatch_001",
        idempotency_key=f"idem-{command}-12345678",
        trace_id="trace-dispatch-test",
        target=target,
        recipients=recipients,
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
    # Advance to 'authorized' (as if policy evaluation passed) so dispatch
    # tests start from the correct pre-dispatch state.
    repository.update_task_status(task.task_id, "authorized")
    task = repository.get_task_by_id(task.task_id)  # type: ignore[assignment]
    return task, repository


def test_dispatch_service_marks_dispatched_on_success() -> None:
    task, repository = _build_task("run_task")
    lifecycle = TaskLifecycleService(runtime_state_repo=repository)
    service = TaskDispatchService(
        lifecycle_service=lifecycle,
        sandbox_execution_adapter=InMemorySandboxExecutionAdapter(),
        llm_dispatch_adapter=LlmGatewayDispatchAdapter(
            llm_gateway_service=build_llm_gateway_service()
        ),
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
        llm_dispatch_adapter=LlmGatewayDispatchAdapter(
            llm_gateway_service=build_llm_gateway_service()
        ),
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
        llm_dispatch_adapter=LlmGatewayDispatchAdapter(
            llm_gateway_service=build_llm_gateway_service()
        ),
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
        llm_dispatch_adapter=LlmGatewayDispatchAdapter(
            llm_gateway_service=build_llm_gateway_service()
        ),
    )

    outcome = service.dispatch_admitted_task(task)

    assert outcome.accepted is True
    assert outcome.target == "llm"
    assert outcome.dispatch_id
    assert outcome.source == "dispatch_llm_gateway"
    assert outcome.llm_metadata is not None
    assert outcome.llm_metadata.total_tokens > 0
    assert outcome.llm_metadata.cost_source in {"none", "catalog_estimated", "provider_reported"}


def test_dispatch_service_passes_primary_recipient_context_to_llm_metadata() -> None:
    task, repository = _build_task(
        "llm_summarize",
        target="llm",
        recipients=[{"recipient_id": "ceo_core", "recipient_type": "ceo"}],
    )
    lifecycle = TaskLifecycleService(runtime_state_repo=repository)
    service = TaskDispatchService(
        lifecycle_service=lifecycle,
        sandbox_execution_adapter=InMemorySandboxExecutionAdapter(),
        llm_dispatch_adapter=LlmGatewayDispatchAdapter(
            llm_gateway_service=build_llm_gateway_service()
        ),
    )

    outcome = service.dispatch_admitted_task(task)

    assert outcome.accepted is True
    assert outcome.target == "llm"
    assert outcome.llm_metadata is not None
    assert outcome.llm_metadata.recipient_role == "ceo"
    assert outcome.llm_metadata.recipient_id == "ceo_core"


def test_dispatch_service_blocks_on_llm_gateway_failure() -> None:
    task, repository = _build_task("llm_runtime_error")
    lifecycle = TaskLifecycleService(runtime_state_repo=repository)
    service = TaskDispatchService(
        lifecycle_service=lifecycle,
        sandbox_execution_adapter=InMemorySandboxExecutionAdapter(),
        llm_dispatch_adapter=LlmGatewayDispatchAdapter(
            llm_gateway_service=build_llm_gateway_service()
        ),
    )

    outcome = service.dispatch_admitted_task(task)

    assert outcome.accepted is False
    assert outcome.target == "llm"
    assert outcome.source == "dispatch_llm_gateway"
    assert outcome.error_code == "llm_provider_unavailable"
    updated = repository.get_task_by_id(task.task_id)
    assert updated is not None
    assert updated.status == "blocked"
    assert updated.outcome_source == "dispatch_llm_gateway"


def test_dispatch_service_uses_runtime_llm_dispatch_settings() -> None:
    task, repository = _build_task("llm_summarize")
    lifecycle = TaskLifecycleService(runtime_state_repo=repository)
    service = TaskDispatchService(
        lifecycle_service=lifecycle,
        sandbox_execution_adapter=InMemorySandboxExecutionAdapter(),
        llm_dispatch_adapter=LlmGatewayDispatchAdapter(
            llm_gateway_service=build_llm_gateway_service(),
            settings=RuntimeSettings(
                llm_default_routing_profile="prod_controlled",
                llm_default_quota_request_cap=500,
                llm_default_quota_token_cap=40000,
                llm_default_allocation_mode="ratio",
                llm_default_project_share_ratio=0.2,
                llm_default_budget_window="weekly",
            ),
        ),
    )

    outcome = service.dispatch_admitted_task(task)

    assert outcome.accepted is True
    assert outcome.target == "llm"
    assert outcome.llm_metadata is not None
    assert outcome.llm_metadata.routing_profile == "prod_controlled"


def test_dispatch_service_accepts_communication_target() -> None:
    task, repository = _build_task("msg_notify", target="communication")
    lifecycle = TaskLifecycleService(runtime_state_repo=repository)
    service = TaskDispatchService(
        lifecycle_service=lifecycle,
        sandbox_execution_adapter=InMemorySandboxExecutionAdapter(),
        llm_dispatch_adapter=LlmGatewayDispatchAdapter(
            llm_gateway_service=build_llm_gateway_service()
        ),
    )

    outcome = service.dispatch_admitted_task(task)

    assert outcome.accepted is True
    assert outcome.target == "communication"
    assert outcome.dispatch_id
    assert outcome.source == "dispatch_communication_gateway"
    updated = repository.get_task_by_id(task.task_id)
    assert updated is not None
    assert updated.status == "dispatched"
    assert updated.outcome_source == "dispatch_communication"


def test_dispatch_service_blocks_on_communication_contract_violation() -> None:
    task, repository = _build_task(
        "msg_notify",
        args=[],
        target="communication",
    )
    lifecycle = TaskLifecycleService(runtime_state_repo=repository)
    service = TaskDispatchService(
        lifecycle_service=lifecycle,
        sandbox_execution_adapter=InMemorySandboxExecutionAdapter(),
        llm_dispatch_adapter=LlmGatewayDispatchAdapter(
            llm_gateway_service=build_llm_gateway_service()
        ),
    )

    outcome = service.dispatch_admitted_task(task)

    assert outcome.accepted is False
    assert outcome.target == "communication"
    assert outcome.error_code == "a2a_missing_recipient_args"
    assert outcome.source == "dispatch_communication_gateway"
    updated = repository.get_task_by_id(task.task_id)
    assert updated is not None
    assert updated.status == "blocked"
    assert updated.outcome_source == "dispatch_communication_gateway"


class _RaisingSandboxAdapter:
    def dispatch(self, payload: SandboxDispatchRequest) -> SandboxDispatchReceipt:
        raise RuntimeError(f"simulated adapter failure for {payload.task_id}")


class _CapturingLlmAdapter:
    def __init__(self) -> None:
        self.last_payload: LlmDispatchRequest | None = None

    def dispatch(self, payload: LlmDispatchRequest) -> LlmDispatchReceipt:
        self.last_payload = payload
        return LlmDispatchReceipt(
            accepted=True,
            dispatch_id="llm-captured-1",
            error_code=None,
            message="captured",
            gateway_response=None,
            recipient_role=payload.recipient_role,
            recipient_id=payload.recipient_id,
            grounding_source_ids=(),
        )


def test_dispatch_service_fails_closed_when_sandbox_adapter_raises() -> None:
    task, repository = _build_task("run_task")
    lifecycle = TaskLifecycleService(runtime_state_repo=repository)
    service = TaskDispatchService(
        lifecycle_service=lifecycle,
        sandbox_execution_adapter=_RaisingSandboxAdapter(),
        llm_dispatch_adapter=LlmGatewayDispatchAdapter(
            llm_gateway_service=build_llm_gateway_service()
        ),
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


def test_dispatch_service_passes_discord_conversation_scope_to_llm_adapter() -> None:
    task, repository = _build_task(
        "llm_reason",
        target="llm",
        recipients=[{"recipient_id": "ceo_core", "recipient_type": "ceo"}],
    )
    lifecycle = TaskLifecycleService(runtime_state_repo=repository)
    llm_adapter = _CapturingLlmAdapter()
    service = TaskDispatchService(
        lifecycle_service=lifecycle,
        sandbox_execution_adapter=InMemorySandboxExecutionAdapter(),
        llm_dispatch_adapter=llm_adapter,
    )

    outcome = service.dispatch_admitted_task(task)

    assert outcome.accepted is True
    assert llm_adapter.last_payload is not None
    assert llm_adapter.last_payload.conversation_guild_id is not None
    assert llm_adapter.last_payload.conversation_channel_id is not None
