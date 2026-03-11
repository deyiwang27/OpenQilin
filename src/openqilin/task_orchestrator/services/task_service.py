"""Task dispatch orchestration service for governed execution targets."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from openqilin.data_access.repositories.runtime_state import TaskRecord
from openqilin.data_access.repositories.communication import CommunicationMessageRecord
from openqilin.llm_gateway.schemas.responses import LlmGatewayResponse
from openqilin.llm_gateway.service import build_llm_gateway_service
from openqilin.task_orchestrator.dispatch.llm_dispatch import (
    LlmDispatchAdapter,
    LlmDispatchRequest,
    LlmGatewayDispatchAdapter,
)
from openqilin.task_orchestrator.dispatch.communication_dispatch import (
    CommunicationDispatchAdapter,
    CommunicationDispatchRequest,
    InMemoryCommunicationDispatchAdapter,
)
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
class TaskDispatchLlmMetadata:
    """LLM metadata extracted from gateway response for owner response contract."""

    decision: str
    model_selected: str
    routing_profile: str
    quota_limit_source: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    request_units: int
    estimated_cost_usd: float
    actual_cost_usd: float | None
    cost_source: str
    currency_delta_usd: float
    quota_token_units: int


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
    retryable: bool = False
    llm_metadata: TaskDispatchLlmMetadata | None = None


class TaskDispatchService:
    """Coordinates dispatch target selection and lifecycle transitions."""

    def __init__(
        self,
        lifecycle_service: TaskLifecycleService,
        sandbox_execution_adapter: SandboxExecutionAdapter,
        llm_dispatch_adapter: LlmDispatchAdapter,
        communication_dispatch_adapter: CommunicationDispatchAdapter | None = None,
    ) -> None:
        self._lifecycle_service = lifecycle_service
        self._sandbox_execution_adapter = sandbox_execution_adapter
        self._llm_dispatch_adapter = llm_dispatch_adapter
        self._communication_dispatch_adapter = (
            communication_dispatch_adapter or InMemoryCommunicationDispatchAdapter()
        )
        self._task_outcomes: dict[str, TaskDispatchOutcome] = {}

    def dispatch_admitted_task(
        self,
        task: TaskRecord,
        *,
        policy_version: str = "policy-version-unknown",
        policy_hash: str = "policy-hash-unknown",
        rule_ids: tuple[str, ...] = (),
    ) -> TaskDispatchOutcome:
        """Dispatch admitted task through governed target boundaries."""

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
                retryable=existing.retryable,
                llm_metadata=existing.llm_metadata,
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
                    retryable=False,
                    llm_metadata=None,
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
                    retryable=False,
                    llm_metadata=None,
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
                    retryable=False,
                    llm_metadata=None,
                )
        elif target == "llm":
            try:
                llm_receipt = self._llm_dispatch_adapter.dispatch(
                    LlmDispatchRequest(
                        task_id=task.task_id,
                        request_id=task.request_id,
                        trace_id=task.trace_id,
                        principal_id=task.principal_id,
                        project_id=task.project_id,
                        command=task.command,
                        args=task.args,
                        policy_version=policy_version,
                        policy_hash=policy_hash,
                        rule_ids=rule_ids,
                    )
                )
            except Exception:
                self._lifecycle_service.mark_blocked_dispatch(
                    task.task_id,
                    error_code="llm_gateway_runtime_error",
                    message="llm gateway dispatch failed",
                    dispatch_target=target,
                    outcome_source="dispatch_llm_gateway",
                )
                outcome = TaskDispatchOutcome(
                    accepted=False,
                    target=target,
                    dispatch_id=None,
                    error_code="llm_gateway_runtime_error",
                    message="llm gateway dispatch failed",
                    replayed=False,
                    source="dispatch_llm_gateway",
                    retryable=False,
                    llm_metadata=None,
                )
                self._task_outcomes[task.task_id] = outcome
                return outcome
            if llm_receipt.accepted:
                dispatch_id = llm_receipt.dispatch_id or f"llm-{uuid4()}"
                self._lifecycle_service.mark_dispatched(
                    task.task_id,
                    dispatch_target=target,
                    dispatch_id=dispatch_id,
                    message=llm_receipt.message,
                )
                outcome = TaskDispatchOutcome(
                    accepted=True,
                    target=target,
                    dispatch_id=dispatch_id,
                    error_code=None,
                    message=llm_receipt.message,
                    replayed=False,
                    source="dispatch_llm_gateway",
                    retryable=False,
                    llm_metadata=_extract_llm_metadata(llm_receipt.gateway_response),
                )
            else:
                self._lifecycle_service.mark_blocked_dispatch(
                    task.task_id,
                    error_code=llm_receipt.error_code,
                    message=llm_receipt.message,
                    dispatch_target=target,
                    outcome_source="dispatch_llm_gateway",
                )
                outcome = TaskDispatchOutcome(
                    accepted=False,
                    target=target,
                    dispatch_id=None,
                    error_code=llm_receipt.error_code,
                    message=llm_receipt.message,
                    replayed=False,
                    source="dispatch_llm_gateway",
                    retryable=bool(
                        llm_receipt.gateway_response.retryable
                        if llm_receipt.gateway_response is not None
                        else False
                    ),
                    llm_metadata=_extract_llm_metadata(llm_receipt.gateway_response),
                )
        elif target == "communication":
            try:
                communication_receipt = self._communication_dispatch_adapter.dispatch(
                    CommunicationDispatchRequest(
                        task_id=task.task_id,
                        trace_id=task.trace_id,
                        principal_id=task.principal_id,
                        connector=task.connector,
                        command=task.command,
                        target=task.target,
                        args=task.args,
                        idempotency_key=task.idempotency_key,
                        project_id=task.project_id,
                        created_at=task.created_at,
                        metadata=task.metadata,
                    )
                )
            except Exception:
                self._lifecycle_service.mark_blocked_dispatch(
                    task.task_id,
                    error_code="communication_dispatch_adapter_error",
                    message="communication adapter execution failed",
                    dispatch_target=target,
                    outcome_source="dispatch_communication_gateway",
                )
                outcome = TaskDispatchOutcome(
                    accepted=False,
                    target=target,
                    dispatch_id=None,
                    error_code="communication_dispatch_adapter_error",
                    message="communication adapter execution failed",
                    replayed=False,
                    source="dispatch_communication_gateway",
                    retryable=False,
                    llm_metadata=None,
                )
                self._task_outcomes[task.task_id] = outcome
                return outcome
            if communication_receipt.accepted:
                dispatch_id = communication_receipt.dispatch_id or f"communication-{uuid4()}"
                self._lifecycle_service.mark_dispatched(
                    task.task_id,
                    dispatch_target=target,
                    dispatch_id=dispatch_id,
                    message=communication_receipt.message,
                )
                outcome = TaskDispatchOutcome(
                    accepted=True,
                    target=target,
                    dispatch_id=dispatch_id,
                    error_code=None,
                    message=communication_receipt.message,
                    replayed=False,
                    source="dispatch_communication_gateway",
                    retryable=False,
                    llm_metadata=None,
                )
            else:
                self._lifecycle_service.mark_blocked_dispatch(
                    task.task_id,
                    error_code=communication_receipt.error_code or "communication_dispatch_failed",
                    message=communication_receipt.message,
                    dispatch_target=target,
                    outcome_source="dispatch_communication_gateway",
                )
                outcome = TaskDispatchOutcome(
                    accepted=False,
                    target=target,
                    dispatch_id=None,
                    error_code=communication_receipt.error_code or "communication_dispatch_failed",
                    message=communication_receipt.message,
                    replayed=False,
                    source="dispatch_communication_gateway",
                    retryable=communication_receipt.retryable,
                    llm_metadata=None,
                )
        else:
            # Fallback is retained for forward-compatible targets not yet modeled.
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
                retryable=False,
                llm_metadata=None,
            )

        self._task_outcomes[task.task_id] = outcome
        return outcome

    def list_communication_message_records(
        self,
        *,
        task_id: str | None = None,
    ) -> tuple[CommunicationMessageRecord, ...]:
        """Expose communication message ledger records for diagnostics/tests."""

        adapter = self._communication_dispatch_adapter
        if isinstance(adapter, InMemoryCommunicationDispatchAdapter):
            return adapter.list_message_records(task_id=task_id)
        return ()


def build_task_dispatch_service(lifecycle_service: TaskLifecycleService) -> TaskDispatchService:
    """Build task-dispatch service with default sandbox and llm adapters."""

    return TaskDispatchService(
        lifecycle_service=lifecycle_service,
        sandbox_execution_adapter=InMemorySandboxExecutionAdapter(),
        llm_dispatch_adapter=LlmGatewayDispatchAdapter(
            llm_gateway_service=build_llm_gateway_service(),
        ),
        communication_dispatch_adapter=InMemoryCommunicationDispatchAdapter(),
    )


def _extract_llm_metadata(response: LlmGatewayResponse | None) -> TaskDispatchLlmMetadata | None:
    """Extract llm metadata from gateway response when available."""

    if (
        response is None
        or response.usage is None
        or response.cost is None
        or response.budget_usage is None
    ):
        return None
    return TaskDispatchLlmMetadata(
        decision=response.decision,
        model_selected=response.model_selected or "model-unspecified",
        routing_profile=response.route_metadata.get("routing_profile", "profile-unspecified"),
        quota_limit_source=response.quota_limit_source,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        total_tokens=response.usage.total_tokens,
        request_units=response.usage.request_units,
        estimated_cost_usd=response.cost.estimated_cost_usd,
        actual_cost_usd=response.cost.actual_cost_usd,
        cost_source=response.cost.cost_source,
        currency_delta_usd=response.budget_usage.currency_delta_usd,
        quota_token_units=response.budget_usage.token_units,
    )
