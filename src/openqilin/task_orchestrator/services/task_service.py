"""Task dispatch orchestration service for governed execution targets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from openqilin.budget_runtime.models import BudgetRuntimeClientProtocol
from openqilin.communication_gateway.delivery.dlq_writer import LocalDeadLetterWriter
from openqilin.communication_gateway.delivery.publisher import LocalDeliveryPublisher
from openqilin.communication_gateway.storage.idempotency_store import (
    CommunicationIdempotencyRecord,
    LocalCommunicationIdempotencyStore,
)
from openqilin.communication_gateway.storage.message_ledger import LocalMessageLedger
from openqilin.data_access.repositories.communication import (
    CommunicationDeadLetterRecord,
    CommunicationMessageRecord,
)
from openqilin.data_access.repositories.postgres.communication_repository import (
    PostgresCommunicationRepository,
)
from openqilin.data_access.repositories.postgres.governance_artifact_repository import (
    PostgresGovernanceArtifactRepository,
)
from openqilin.data_access.repositories.postgres.project_repository import PostgresProjectRepository
from openqilin.data_access.repositories.postgres.task_repository import PostgresTaskRepository
from openqilin.data_access.repositories.runtime_state import TaskRecord
from openqilin.execution_sandbox.tools.read_tools import GovernedReadToolService
from openqilin.execution_sandbox.tools.write_tools import GovernedWriteToolService
from openqilin.llm_gateway.schemas.responses import LlmGatewayResponse
from openqilin.llm_gateway.service import build_llm_gateway_service
from openqilin.observability.audit.audit_writer import OTelAuditWriter
from openqilin.observability.testing.stubs import InMemoryAuditWriter, InMemoryMetricRecorder
from openqilin.retrieval_runtime.service import RetrievalQueryService, build_retrieval_query_service
from openqilin.task_orchestrator.dispatch.communication_dispatch import (
    CommunicationDispatchAdapter,
    CommunicationDispatchRequest,
    LocalCommunicationDispatchAdapter,
)
from openqilin.task_orchestrator.dispatch.llm_dispatch import (
    ConversationStoreProtocol,
    GovernanceProjectReader,
    LlmDispatchAdapter,
    LlmDispatchRequest,
    LlmGatewayDispatchAdapter,
    RetrievalGroundingService,
)
from openqilin.task_orchestrator.dispatch.sandbox_dispatch import (
    LocalSandboxExecutionAdapter,
    SandboxDispatchRequest,
    SandboxExecutionAdapter,
)
from openqilin.task_orchestrator.dispatch.target_selector import (
    DispatchTarget,
    DispatchTargetError,
    select_dispatch_target,
)
from openqilin.task_orchestrator.services.lifecycle_service import TaskLifecycleService

_SYSTEM_PROJECT_ID = "system"


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
    generated_text: str | None
    recipient_role: str
    recipient_id: str | None
    grounding_source_ids: tuple[str, ...]


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
    dead_letter_id: str | None = None
    llm_metadata: TaskDispatchLlmMetadata | None = None


class TaskDispatchService:
    """Coordinates dispatch target selection and lifecycle transitions."""

    def __init__(
        self,
        lifecycle_service: TaskLifecycleService,
        sandbox_execution_adapter: SandboxExecutionAdapter,
        llm_dispatch_adapter: LlmDispatchAdapter,
        communication_dispatch_adapter: CommunicationDispatchAdapter | None = None,
        specialist_agent: Any | None = None,
    ) -> None:
        self._lifecycle_service = lifecycle_service
        self._sandbox_execution_adapter = sandbox_execution_adapter
        self._llm_dispatch_adapter = llm_dispatch_adapter
        self._communication_dispatch_adapter = (
            communication_dispatch_adapter or LocalCommunicationDispatchAdapter()
        )
        self._specialist_agent = specialist_agent
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
                dead_letter_id=existing.dead_letter_id,
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
                    dead_letter_id=None,
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
                    dead_letter_id=None,
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
                    dead_letter_id=None,
                    llm_metadata=None,
                )
        elif target == "llm":
            recipient_role, recipient_id = _extract_primary_recipient(task)
            (
                conversation_guild_id,
                conversation_channel_id,
                conversation_thread_id,
            ) = _extract_discord_conversation_scope(task)
            try:
                llm_receipt = self._llm_dispatch_adapter.dispatch(
                    LlmDispatchRequest(
                        task_id=task.task_id,
                        request_id=task.request_id,
                        trace_id=task.trace_id,
                        principal_id=task.principal_id,
                        principal_role=task.principal_role,
                        project_id=task.project_id,
                        command=task.command,
                        args=task.args,
                        recipient_role=recipient_role,
                        recipient_id=recipient_id,
                        policy_version=policy_version,
                        policy_hash=policy_hash,
                        rule_ids=rule_ids,
                        conversation_guild_id=conversation_guild_id,
                        conversation_channel_id=conversation_channel_id,
                        conversation_thread_id=conversation_thread_id,
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
                    dead_letter_id=None,
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
                    dead_letter_id=None,
                    llm_metadata=_extract_llm_metadata(
                        llm_receipt.gateway_response,
                        recipient_role=llm_receipt.recipient_role,
                        recipient_id=llm_receipt.recipient_id,
                        grounding_source_ids=llm_receipt.grounding_source_ids,
                    ),
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
                    dead_letter_id=None,
                    llm_metadata=_extract_llm_metadata(
                        llm_receipt.gateway_response,
                        recipient_role=llm_receipt.recipient_role,
                        recipient_id=llm_receipt.recipient_id,
                        grounding_source_ids=llm_receipt.grounding_source_ids,
                    ),
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
                    dead_letter_id=None,
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
                    dead_letter_id=communication_receipt.dead_letter_id,
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
                    dead_letter_id=communication_receipt.dead_letter_id,
                    llm_metadata=None,
                )
        elif target == "specialist":
            if self._specialist_agent is None:
                self._lifecycle_service.mark_failed(
                    task.task_id,
                    error_code="specialist_agent_not_configured",
                    message="specialist dispatch requires specialist_agent to be configured",
                    outcome_source="task_dispatch_service",
                )
                raise DispatchTargetError(
                    "specialist dispatch requires specialist_agent to be configured"
                )
            from openqilin.agents.specialist.models import (
                SpecialistDispatchAuthError,
                SpecialistRequest,
            )

            metadata = dict(task.metadata)
            dispatch_source_role = metadata.get("dispatch_source", "unknown")
            approved_tools_raw = metadata.get("approved_tools", "")
            approved_tools: tuple[str, ...] = (
                tuple(tool.strip() for tool in approved_tools_raw.split(",") if tool.strip())
                if approved_tools_raw
                else ()
            )
            try:
                specialist_response = self._specialist_agent.handle(
                    SpecialistRequest(
                        task_id=task.task_id,
                        project_id=task.project_id or _SYSTEM_PROJECT_ID,
                        task_description=task.command,
                        approved_tools=approved_tools,
                        dispatch_source_role=dispatch_source_role,
                        trace_id=task.trace_id,
                    )
                )
            except SpecialistDispatchAuthError as exc:
                self._lifecycle_service.mark_failed(
                    task.task_id,
                    error_code="specialist_dispatch_auth_denied",
                    message=str(exc),
                    outcome_source="task_dispatch_service",
                )
                outcome = TaskDispatchOutcome(
                    accepted=False,
                    target=target,
                    dispatch_id=None,
                    error_code="specialist_dispatch_auth_denied",
                    message=str(exc),
                    replayed=False,
                    source="specialist_agent",
                    retryable=False,
                    dead_letter_id=None,
                    llm_metadata=None,
                )
                self._task_outcomes[task.task_id] = outcome
                return outcome
            if specialist_response.execution_status == "completed":
                dispatch_id = specialist_response.artifact_id or f"specialist-{uuid4()}"
                self._lifecycle_service.mark_dispatched(
                    task.task_id,
                    dispatch_target=target,
                    dispatch_id=dispatch_id,
                    message="specialist task execution completed",
                )
                outcome = TaskDispatchOutcome(
                    accepted=True,
                    target=target,
                    dispatch_id=dispatch_id,
                    error_code=None,
                    message="specialist task execution completed",
                    replayed=False,
                    source="specialist_agent",
                    retryable=False,
                    dead_letter_id=None,
                    llm_metadata=None,
                )
            else:
                error_code = specialist_response.blocker or "specialist_task_blocked"
                self._lifecycle_service.mark_blocked_dispatch(
                    task.task_id,
                    error_code=error_code,
                    message=specialist_response.output_text,
                    dispatch_target=target,
                    outcome_source="specialist_agent",
                )
                outcome = TaskDispatchOutcome(
                    accepted=False,
                    target=target,
                    dispatch_id=None,
                    error_code=error_code,
                    message=specialist_response.output_text,
                    replayed=False,
                    source="specialist_agent",
                    retryable=False,
                    dead_letter_id=None,
                    llm_metadata=None,
                )
        else:
            # H-1: Unknown dispatch targets are fail-closed — never fake a successful dispatch.
            self._lifecycle_service.mark_failed(
                task.task_id,
                error_code="dispatch_target_unknown",
                message=f"unknown dispatch target: {target!r}",
                outcome_source="task_dispatch_service",
            )
            raise DispatchTargetError(f"unknown dispatch target: {target!r}")

        self._task_outcomes[task.task_id] = outcome
        return outcome

    def get_dispatch_outcome(self, task_id: str) -> TaskDispatchOutcome | None:
        """Return the stored dispatch outcome for a task, or None if not yet dispatched."""
        return self._task_outcomes.get(task_id)

    def list_communication_message_records(
        self,
        *,
        task_id: str | None = None,
    ) -> tuple[CommunicationMessageRecord, ...]:
        """Expose communication message ledger records for diagnostics/tests."""

        adapter = self._communication_dispatch_adapter
        if isinstance(adapter, LocalCommunicationDispatchAdapter):
            return adapter.list_message_records(task_id=task_id)
        return ()

    def list_communication_idempotency_records(
        self,
    ) -> tuple[CommunicationIdempotencyRecord, ...]:
        """Expose communication idempotency records for diagnostics/tests."""

        adapter = self._communication_dispatch_adapter
        if isinstance(adapter, LocalCommunicationDispatchAdapter):
            return adapter.list_idempotency_records()
        return ()

    def list_communication_dead_letters(self) -> tuple[CommunicationDeadLetterRecord, ...]:
        """Expose communication dead-letter records for diagnostics/tests."""

        adapter = self._communication_dispatch_adapter
        if isinstance(adapter, LocalCommunicationDispatchAdapter):
            return adapter.list_dead_letters()
        return ()

    def create_specialist_task(
        self,
        *,
        task_id: str,
        project_id: str,
        trace_id: str,
    ) -> str:
        """Create and dispatch a specialist subtask for the given parent task_id."""

        from openqilin.task_orchestrator.admission.envelope_validator import AdmissionEnvelope

        runtime_state_repo = getattr(self._lifecycle_service, "_runtime_state_repo", None)
        if runtime_state_repo is None:
            raise RuntimeError(
                "create_specialist_task requires _runtime_state_repo on lifecycle_service"
            )
        envelope = AdmissionEnvelope(
            request_id=str(uuid4()),
            trace_id=trace_id,
            principal_id="project_manager",
            principal_role="project_manager",
            trust_domain="project",
            connector="internal",
            command="execute_specialist_task",
            target="specialist",
            args=(task_id,),
            metadata=(
                ("dispatch_source", "project_manager"),
                ("source_task_id", task_id),
                ("target_role", "specialist"),
            ),
            project_id=project_id,
            idempotency_key=f"pm-specialist-{project_id}-{task_id}-{trace_id}",
        )
        created_task = runtime_state_repo.create_task_from_envelope(envelope)
        outcome = self.dispatch_admitted_task(
            created_task,
            policy_version="v2",
            policy_hash="project-manager-v1",
            rule_ids=("AUTH-001", "AUTH-002", "ORCH-001", "ORCH-002"),
        )
        return outcome.dispatch_id or created_task.task_id


def build_task_dispatch_service(
    lifecycle_service: TaskLifecycleService,
    *,
    conversation_store: ConversationStoreProtocol | None = None,
    audit_writer: InMemoryAuditWriter | OTelAuditWriter | None = None,
    metric_recorder: InMemoryMetricRecorder | None = None,
    communication_repository: PostgresCommunicationRepository | None = None,
    retrieval_query_service: RetrievalGroundingService | RetrievalQueryService | None = None,
    governance_project_reader: GovernanceProjectReader | None = None,
    governance_repository: PostgresProjectRepository | None = None,
    project_artifact_repository: PostgresGovernanceArtifactRepository | None = None,
    runtime_state_repository: PostgresTaskRepository | None = None,
    budget_runtime_client: BudgetRuntimeClientProtocol | None = None,
    specialist_agent: Any | None = None,
) -> TaskDispatchService:
    """Build task-dispatch service with default sandbox and llm adapters."""

    if communication_repository is None:
        raise RuntimeError(
            "communication_repository is required; configure DATABASE_URL at startup"
        )
    if runtime_state_repository is None:
        raise RuntimeError(
            "runtime_state_repository is required; configure DATABASE_URL at startup"
        )
    governance_repository = governance_repository or (
        governance_project_reader
        if isinstance(governance_project_reader, PostgresProjectRepository)
        else None
    )
    if governance_repository is None:
        raise RuntimeError("governance_repository is required; configure DATABASE_URL at startup")
    if project_artifact_repository is None:
        raise RuntimeError(
            "project_artifact_repository is required; configure DATABASE_URL at startup"
        )
    retrieval_service_for_tools = (
        retrieval_query_service
        if isinstance(retrieval_query_service, RetrievalQueryService)
        else build_retrieval_query_service()
    )
    read_tool_service = GovernedReadToolService(
        governance_repository=governance_repository,
        project_artifact_repository=project_artifact_repository,
        runtime_state_repository=runtime_state_repository,
        retrieval_query_service=retrieval_service_for_tools,
        audit_writer=audit_writer or InMemoryAuditWriter(),
        communication_repository=communication_repository,
    )
    write_tool_service = GovernedWriteToolService(
        governance_repository=governance_repository,
        project_artifact_repository=project_artifact_repository,
        audit_writer=audit_writer or InMemoryAuditWriter(),
        budget_runtime_client=budget_runtime_client,
    )
    message_ledger = LocalMessageLedger()
    dead_letter_writer = LocalDeadLetterWriter(
        audit_writer=audit_writer,
        metric_recorder=metric_recorder,
    )
    communication_publisher = LocalDeliveryPublisher(
        message_ledger=message_ledger,
        dead_letter_writer=dead_letter_writer,
        idempotency_store=LocalCommunicationIdempotencyStore(),
    )
    return TaskDispatchService(
        lifecycle_service=lifecycle_service,
        sandbox_execution_adapter=LocalSandboxExecutionAdapter(),
        llm_dispatch_adapter=LlmGatewayDispatchAdapter(
            llm_gateway_service=build_llm_gateway_service(),
            conversation_store=conversation_store,
            retrieval_query_service=retrieval_query_service,
            governance_project_reader=governance_repository,
            read_tool_service=read_tool_service,
            write_tool_service=write_tool_service,
            budget_client=budget_runtime_client,
        ),
        communication_dispatch_adapter=LocalCommunicationDispatchAdapter(
            publisher=communication_publisher,
        ),
        specialist_agent=specialist_agent,
    )


def _extract_llm_metadata(
    response: LlmGatewayResponse | None,
    *,
    recipient_role: str | None,
    recipient_id: str | None,
    grounding_source_ids: tuple[str, ...],
) -> TaskDispatchLlmMetadata | None:
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
        generated_text=response.generated_text,
        recipient_role=(recipient_role or "").strip().lower() or "runtime_agent",
        recipient_id=(recipient_id or "").strip() or None,
        grounding_source_ids=grounding_source_ids,
    )


def _extract_primary_recipient(task: TaskRecord) -> tuple[str | None, str | None]:
    metadata = dict(task.metadata)
    primary_role = (metadata.get("primary_recipient_role") or "").strip().lower() or None
    primary_id = (metadata.get("primary_recipient_id") or "").strip() or None
    if primary_role is not None or primary_id is not None:
        return primary_role, primary_id

    recipient_roles = _split_csv_values(metadata.get("recipient_types"))
    recipient_ids = _split_csv_values(metadata.get("recipient_ids"))
    role = recipient_roles[0] if recipient_roles else None
    recipient_id = recipient_ids[0] if recipient_ids else None
    return role, recipient_id


def _extract_discord_conversation_scope(
    task: TaskRecord,
) -> tuple[str | None, str | None, str | None]:
    metadata = dict(task.metadata)
    guild_id = (metadata.get("discord_guild_id") or "").strip() or None
    channel_id = (metadata.get("discord_channel_id") or "").strip() or None
    thread_id = (metadata.get("discord_thread_id") or "").strip() or None
    return guild_id, channel_id, thread_id


def _split_csv_values(value: str | None) -> tuple[str, ...]:
    if value is None:
        return ()
    values = tuple(item.strip() for item in value.split(",") if item.strip())
    return values
