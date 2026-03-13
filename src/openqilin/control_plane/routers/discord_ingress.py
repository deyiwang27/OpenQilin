"""Discord ingress adapter router mapping connector payloads to owner-command envelope."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse

from openqilin.budget_runtime.reservation_service import BudgetReservationService
from openqilin.control_plane.api.dependencies import (
    get_admission_service,
    get_audit_writer,
    get_budget_reservation_service,
    get_governance_repository,
    get_identity_channel_repository,
    get_metric_recorder,
    get_policy_runtime_client,
    get_runtime_state_repository,
    get_task_dispatch_service,
    get_tracer,
)
from openqilin.control_plane.routers.owner_commands import submit_owner_command
from openqilin.control_plane.schemas.discord_ingress import DiscordIngressRequest
from openqilin.control_plane.schemas.owner_commands import (
    OwnerCommandConnectorMetadata,
    OwnerCommandDiscordContext,
    OwnerCommandRequest,
    OwnerCommandResponse,
    OwnerCommandResolution,
    OwnerCommandSender,
)
from openqilin.data_access.repositories.governance import InMemoryGovernanceRepository
from openqilin.data_access.repositories.identity_channels import (
    InMemoryIdentityChannelRepository,
)
from openqilin.data_access.repositories.runtime_state import InMemoryRuntimeStateRepository
from openqilin.observability.audit.audit_writer import InMemoryAuditWriter
from openqilin.observability.metrics.recorder import InMemoryMetricRecorder
from openqilin.observability.tracing.tracer import InMemoryTracer
from openqilin.policy_runtime_integration.client import InMemoryPolicyRuntimeClient
from openqilin.task_orchestrator.admission.service import AdmissionService
from openqilin.task_orchestrator.services.task_service import TaskDispatchService

router = APIRouter(prefix="/v1/connectors/discord", tags=["discord_ingress"])


def _resolve_target(*, action: str, explicit_target: str | None) -> str:
    if explicit_target is not None and explicit_target.strip():
        return explicit_target.strip()
    normalized_action = action.strip().lower()
    if normalized_action.startswith("llm_"):
        return "llm"
    if normalized_action.startswith("msg_"):
        return "communication"
    return "sandbox"


@router.post(
    "/messages",
    response_model=OwnerCommandResponse,
    status_code=202,
)
def submit_discord_message(
    payload: DiscordIngressRequest,
    request: Request,
    admission_service: AdmissionService = Depends(get_admission_service),
    policy_runtime_client: InMemoryPolicyRuntimeClient = Depends(get_policy_runtime_client),
    budget_reservation_service: BudgetReservationService = Depends(get_budget_reservation_service),
    runtime_state_repo: InMemoryRuntimeStateRepository = Depends(get_runtime_state_repository),
    task_dispatch_service: TaskDispatchService = Depends(get_task_dispatch_service),
    tracer: InMemoryTracer = Depends(get_tracer),
    audit_writer: InMemoryAuditWriter = Depends(get_audit_writer),
    metric_recorder: InMemoryMetricRecorder = Depends(get_metric_recorder),
    governance_repository: InMemoryGovernanceRepository = Depends(get_governance_repository),
    identity_channel_repository: InMemoryIdentityChannelRepository = Depends(
        get_identity_channel_repository
    ),
    x_openqilin_signature: Annotated[str | None, Header(alias="X-OpenQilin-Signature")] = None,
) -> OwnerCommandResponse | JSONResponse:
    """Translate Discord connector payload into canonical owner-command ingress contract."""

    owner_payload = OwnerCommandRequest(
        message_id=payload.external_message_id,
        trace_id=payload.trace_id,
        sender=OwnerCommandSender(
            actor_id=payload.actor_external_id,
            actor_role=payload.actor_role,
        ),
        recipients=payload.recipients,
        message_type="command",
        priority=payload.priority,
        timestamp=payload.timestamp,
        content=payload.content,
        project_id=payload.project_id,
        connector=OwnerCommandConnectorMetadata(
            channel="discord",
            external_message_id=payload.external_message_id,
            actor_external_id=payload.actor_external_id,
            idempotency_key=payload.idempotency_key,
            raw_payload_hash=payload.raw_payload_hash,
            discord_context=OwnerCommandDiscordContext(
                guild_id=payload.guild_id,
                channel_id=payload.channel_id,
                channel_type=payload.channel_type,
                chat_class=payload.chat_class,
                bot_role=payload.bot_role,
                bot_id=payload.bot_id,
                bot_user_id=payload.bot_user_id,
            ),
        ),
        command=OwnerCommandResolution(
            action=payload.action,
            target=_resolve_target(action=payload.action, explicit_target=payload.target),
            payload={"args": payload.args},
        ),
    )
    return submit_owner_command(
        payload=owner_payload,
        request=request,
        admission_service=admission_service,
        policy_runtime_client=policy_runtime_client,
        budget_reservation_service=budget_reservation_service,
        runtime_state_repo=runtime_state_repo,
        task_dispatch_service=task_dispatch_service,
        tracer=tracer,
        audit_writer=audit_writer,
        metric_recorder=metric_recorder,
        governance_repository=governance_repository,
        identity_channel_repository=identity_channel_repository,
        x_openqilin_trace_id=payload.trace_id,
        x_external_channel="discord",
        x_external_actor_id=payload.actor_external_id,
        x_idempotency_key=payload.idempotency_key,
        x_openqilin_signature=x_openqilin_signature,
    )
