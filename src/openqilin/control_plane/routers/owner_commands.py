"""Owner command ingress router."""

from __future__ import annotations

from typing import Annotated, Any, cast
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, Request, status
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
from openqilin.control_plane.identity.connector_security import (
    ConnectorSecurityError,
    validate_connector_auth,
)
from openqilin.control_plane.identity.discord_governance import (
    DiscordGovernanceError,
    validate_discord_governance,
)
from openqilin.control_plane.identity.principal_resolver import (
    PrincipalResolutionError,
    resolve_principal,
)
from openqilin.data_access.repositories.governance import InMemoryGovernanceRepository
from openqilin.data_access.repositories.identity_channels import (
    InMemoryIdentityChannelRepository,
)
from openqilin.control_plane.schemas.owner_commands import (
    OwnerCommandAcceptedData,
    OwnerCommandError,
    OwnerCommandRequest,
    OwnerCommandResponse,
)
from openqilin.data_access.repositories.runtime_state import (
    InMemoryRuntimeStateRepository,
    TaskRecord,
)
from openqilin.observability.audit.audit_writer import InMemoryAuditWriter
from openqilin.observability.metrics.recorder import InMemoryMetricRecorder
from openqilin.observability.tracing.spans import (
    AUDIT_EMIT_SPAN,
    BUDGET_RESERVATION_SPAN,
    EXECUTION_SANDBOX_SPAN,
    OWNER_COMMAND_INGRESS_SPAN,
    POLICY_EVALUATION_SPAN,
    TASK_ORCHESTRATION_SPAN,
)
from openqilin.observability.tracing.tracer import InMemoryTracer
from openqilin.policy_runtime_integration.client import PolicyRuntimeClient
from openqilin.policy_runtime_integration.fail_closed import evaluate_with_fail_closed
from openqilin.policy_runtime_integration.normalizer import normalize_policy_input
from openqilin.task_orchestrator.admission.envelope_validator import (
    EnvelopeValidationError,
    validate_owner_command_envelope,
)
from openqilin.task_orchestrator.admission.service import (
    AdmissionIdempotencyError,
    AdmissionService,
)
from openqilin.task_orchestrator.dispatch.target_selector import select_dispatch_target
from openqilin.task_orchestrator.services.task_service import TaskDispatchService

router = APIRouter(prefix="/v1/owner/commands", tags=["owner_commands"])


def _parse_rule_ids(raw: str | None) -> list[str]:
    if raw is None:
        return []
    return [value for value in (part.strip() for part in raw.split(",")) if value]


def _build_error(
    *,
    code: str,
    error_class: str,
    message: str,
    retryable: bool,
    source_component: str,
    trace_id: str,
    details: dict[str, Any],
    policy_version: str | None = None,
    policy_hash: str | None = None,
    rule_ids: list[str] | None = None,
) -> OwnerCommandError:
    return OwnerCommandError.model_validate(
        {
            "code": code,
            "class": error_class,
            "message": message,
            "retryable": retryable,
            "source_component": source_component,
            "trace_id": trace_id,
            "policy_version": policy_version,
            "policy_hash": policy_hash,
            "rule_ids": rule_ids or [],
            "details": details,
        }
    )


def _error_response(
    *,
    status_code: int,
    trace_id: str,
    code: str,
    error_class: str,
    message: str,
    retryable: bool,
    source_component: str,
    details: dict[str, Any],
    policy_version: str | None = None,
    policy_hash: str | None = None,
    rule_ids: list[str] | None = None,
) -> JSONResponse:
    payload = OwnerCommandResponse(
        status="error",
        trace_id=trace_id,
        policy_version=policy_version,
        policy_hash=policy_hash,
        rule_ids=rule_ids or [],
        error=_build_error(
            code=code,
            error_class=error_class,
            message=message,
            retryable=retryable,
            source_component=source_component,
            trace_id=trace_id,
            details=details,
            policy_version=policy_version,
            policy_hash=policy_hash,
            rule_ids=rule_ids,
        ),
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump(by_alias=True))


def _denied_response(
    *,
    status_code: int,
    trace_id: str,
    code: str,
    error_class: str,
    message: str,
    source_component: str,
    details: dict[str, Any],
    policy_version: str | None,
    policy_hash: str | None,
    rule_ids: list[str],
) -> JSONResponse:
    payload = OwnerCommandResponse(
        status="denied",
        trace_id=trace_id,
        policy_version=policy_version,
        policy_hash=policy_hash,
        rule_ids=rule_ids,
        error=_build_error(
            code=code,
            error_class=error_class,
            message=message,
            retryable=False,
            source_component=source_component,
            trace_id=trace_id,
            details=details,
            policy_version=policy_version,
            policy_hash=policy_hash,
            rule_ids=rule_ids,
        ),
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump(by_alias=True))


def _emit_outcome_observability(
    *,
    tracer: InMemoryTracer,
    audit_writer: InMemoryAuditWriter,
    metric_recorder: InMemoryMetricRecorder,
    trace_id: str,
    request_id: str | None,
    task_id: str | None,
    principal_id: str | None,
    principal_role: str | None,
    source: str,
    outcome: str,
    error_code: str | None,
    message: str,
    policy_version: str | None = None,
    policy_hash: str | None = None,
    rule_ids: list[str] | None = None,
    attributes: dict[str, object] | None = None,
) -> None:
    """Record final owner-command outcome in metrics and audit streams."""

    metric_recorder.increment_counter(
        "owner_command_admission_outcomes_total",
        labels={"outcome": outcome, "source": source},
    )
    with tracer.start_span(
        trace_id=trace_id or "missing-trace-id",
        name=AUDIT_EMIT_SPAN,
        attributes={"audit.event_type": f"owner_command.{outcome}", "source": source},
    ) as span:
        span.set_attribute("correlation.trace_id", trace_id or "missing-trace-id")
        span.set_attribute("outcome", outcome)
        audit_writer.write_event(
            event_type=f"owner_command.{outcome}",
            outcome=outcome,
            trace_id=trace_id or "missing-trace-id",
            request_id=request_id,
            task_id=task_id,
            principal_id=principal_id,
            principal_role=principal_role,
            source=source,
            reason_code=error_code,
            message=message,
            policy_version=policy_version,
            policy_hash=policy_hash,
            rule_ids=rule_ids,
            payload={
                "outcome": outcome,
                "source": source,
                "error_code": error_code,
                "message": message,
                "request_id": request_id,
                "task_id": task_id,
            },
            attributes=attributes,
        )


def _emit_replay_observability(
    *,
    tracer: InMemoryTracer,
    audit_writer: InMemoryAuditWriter,
    metric_recorder: InMemoryMetricRecorder,
    task: TaskRecord,
    outcome: str,
    source: str,
    message: str,
) -> None:
    """Record replay access without re-emitting stage decision events."""

    metric_recorder.increment_counter(
        "owner_command_replays_total",
        labels={"outcome": outcome, "source": source},
    )
    outcome_details = dict(task.outcome_details or ())
    rule_ids = _parse_rule_ids(outcome_details.get("rule_ids"))
    with tracer.start_span(
        trace_id=task.trace_id,
        name=AUDIT_EMIT_SPAN,
        attributes={"audit.event_type": "owner_command.replayed", "source": source},
    ) as span:
        span.set_attribute("correlation.task_id", task.task_id)
        span.set_attribute("outcome", outcome)
        audit_writer.write_event(
            event_type="owner_command.replayed",
            outcome=outcome,
            trace_id=task.trace_id,
            request_id=task.request_id,
            task_id=task.task_id,
            principal_id=task.principal_id,
            principal_role=task.principal_role,
            source=source,
            reason_code=task.outcome_error_code,
            message=message,
            policy_version=outcome_details.get("policy_version"),
            policy_hash=outcome_details.get("policy_hash"),
            rule_ids=rule_ids,
            payload={
                "replayed": "true",
                "status": task.status,
                "dispatch_target": task.dispatch_target or "unknown",
            },
            attributes={
                "replayed": "true",
                "status": task.status,
                "dispatch_target": task.dispatch_target or "unknown",
            },
        )


def _emit_stage_decision_audit(
    *,
    tracer: InMemoryTracer,
    audit_writer: InMemoryAuditWriter,
    trace_id: str,
    request_id: str,
    task_id: str,
    principal_id: str,
    principal_role: str,
    stage: str,
    decision: str,
    source: str,
    reason_code: str | None,
    message: str,
    policy_version: str | None = None,
    policy_hash: str | None = None,
    rule_ids: list[str] | None = None,
    attributes: dict[str, object] | None = None,
) -> None:
    """Record policy/budget stage decisions as immutable audit events."""

    with tracer.start_span(
        trace_id=trace_id,
        name=AUDIT_EMIT_SPAN,
        attributes={"audit.event_type": f"{stage}.decision", "stage": stage},
    ) as span:
        span.set_attribute("correlation.task_id", task_id)
        span.set_attribute("decision", decision)
        audit_writer.write_event(
            event_type=f"{stage}.decision",
            outcome=decision,
            trace_id=trace_id,
            request_id=request_id,
            task_id=task_id,
            principal_id=principal_id,
            principal_role=principal_role,
            source=source,
            reason_code=reason_code,
            message=message,
            policy_version=policy_version,
            policy_hash=policy_hash,
            rule_ids=rule_ids,
            payload={
                "stage": stage,
                "decision": decision,
                "source": source,
                "reason_code": reason_code,
            },
            attributes=attributes,
        )


def _replayed_response(task: TaskRecord) -> OwnerCommandResponse | JSONResponse:
    """Reconstruct deterministic response from previously processed task state."""

    outcome_details = dict(task.outcome_details or ())
    policy_version = outcome_details.get("policy_version")
    policy_hash = outcome_details.get("policy_hash")
    rule_ids = _parse_rule_ids(outcome_details.get("rule_ids"))

    if task.status == "dispatched":
        dispatch_target = task.dispatch_target or select_dispatch_target(task)
        dispatch_id = task.dispatch_id or "dispatch-id-missing"
        return OwnerCommandResponse(
            status="accepted",
            trace_id=task.trace_id,
            policy_version=policy_version,
            policy_hash=policy_hash,
            rule_ids=rule_ids,
            data=OwnerCommandAcceptedData(
                task_id=task.task_id,
                admission_state="dispatched",
                replayed=True,
                request_id=task.request_id,
                principal_id=task.principal_id,
                connector=task.connector,
                command=task.command,
                accepted_args=list(task.args),
                dispatch_target=dispatch_target,
                dispatch_id=dispatch_id,
            ),
        )

    source = task.outcome_source or "governance"
    error_code = task.outcome_error_code or "governance_blocked"
    message = task.outcome_message or "task replay resolved to prior denied outcome"
    details = dict(outcome_details) if outcome_details else {}
    details.setdefault("source", source)
    details.setdefault("task_id", task.task_id)
    details["replayed"] = "true"
    if task.dispatch_target is not None:
        details.setdefault("dispatch_target", task.dispatch_target)
    if task.outcome_error_code is not None and "reason_code" not in details:
        details["reason_code"] = task.outcome_error_code
    return _denied_response(
        status_code=status.HTTP_403_FORBIDDEN,
        trace_id=task.trace_id,
        code=error_code,
        error_class="authorization_error",
        message=message,
        source_component=source,
        details=details,
        policy_version=policy_version,
        policy_hash=policy_hash,
        rule_ids=rule_ids,
    )


@router.post(
    "",
    response_model=OwnerCommandResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": OwnerCommandResponse},
        status.HTTP_403_FORBIDDEN: {"model": OwnerCommandResponse},
        status.HTTP_409_CONFLICT: {"model": OwnerCommandResponse},
    },
)
def submit_owner_command(
    payload: OwnerCommandRequest,
    request: Request,
    admission_service: AdmissionService = Depends(get_admission_service),
    policy_runtime_client: PolicyRuntimeClient = Depends(get_policy_runtime_client),
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
    x_openqilin_trace_id: Annotated[str | None, Header(alias="X-OpenQilin-Trace-Id")] = None,
    x_external_channel: Annotated[str | None, Header(alias="X-External-Channel")] = None,
    x_external_actor_id: Annotated[str | None, Header(alias="X-External-Actor-Id")] = None,
    x_idempotency_key: Annotated[str | None, Header(alias="X-Idempotency-Key")] = None,
    x_openqilin_signature: Annotated[str | None, Header(alias="X-OpenQilin-Signature")] = None,
) -> OwnerCommandResponse | JSONResponse:
    """Validate ingress identity and envelope before admission execution."""
    payload_trace_id = payload.trace_id.strip()
    trace_id = payload_trace_id or (
        x_openqilin_trace_id.strip() if x_openqilin_trace_id else str(uuid4())
    )
    with tracer.start_span(
        trace_id=trace_id or "missing-trace-id",
        name=OWNER_COMMAND_INGRESS_SPAN,
        attributes={
            "http.method": "POST",
            "http.route": "/v1/owner/commands",
        },
    ) as span:
        span.set_attribute("correlation.trace_id", trace_id or "missing-trace-id")
        task_id: str | None = None
        request_id: str | None = None
        principal_id: str | None = None

        if x_external_channel is None or not x_external_channel.strip():
            return _error_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                trace_id=trace_id,
                code="connector_missing_header",
                error_class="validation_error",
                message="missing required header: X-External-Channel",
                retryable=False,
                source_component="api",
                details={"source": "headers", "required_header": "X-External-Channel"},
            )
        if x_external_actor_id is None or not x_external_actor_id.strip():
            return _error_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                trace_id=trace_id,
                code="connector_missing_header",
                error_class="validation_error",
                message="missing required header: X-External-Actor-Id",
                retryable=False,
                source_component="api",
                details={"source": "headers", "required_header": "X-External-Actor-Id"},
            )
        if x_idempotency_key is None or not x_idempotency_key.strip():
            return _error_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                trace_id=trace_id,
                code="idempotency_missing_header",
                error_class="validation_error",
                message="missing required header: X-Idempotency-Key",
                retryable=False,
                source_component="api",
                details={"source": "headers", "required_header": "X-Idempotency-Key"},
            )

        try:
            validate_connector_auth(
                header_channel=x_external_channel,
                header_actor_external_id=x_external_actor_id,
                header_idempotency_key=x_idempotency_key,
                header_signature=x_openqilin_signature,
                payload_channel=payload.connector.channel,
                payload_actor_external_id=payload.connector.actor_external_id,
                payload_idempotency_key=payload.connector.idempotency_key,
                payload_raw_payload_hash=payload.connector.raw_payload_hash,
            )
        except ConnectorSecurityError as error:
            span.set_status("error")
            span.set_attribute("outcome", "denied")
            span.set_attribute("source", "connector_security")
            _emit_outcome_observability(
                tracer=tracer,
                audit_writer=audit_writer,
                metric_recorder=metric_recorder,
                trace_id=trace_id,
                request_id=request_id,
                task_id=task_id,
                principal_id=principal_id,
                principal_role=payload.sender.actor_role,
                source="connector_security",
                outcome="denied",
                error_code=error.code,
                message=error.message,
            )
            return _error_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                trace_id=trace_id,
                code=error.code,
                error_class="authorization_error",
                message=error.message,
                retryable=False,
                source_component="api",
                details={"source": "connector_security"},
            )

        principal_headers = {
            "x-external-channel": x_external_channel,
            "x-openqilin-actor-external-id": x_external_actor_id,
            "x-openqilin-actor-role": payload.sender.actor_role,
        }
        try:
            principal = resolve_principal(principal_headers)
        except PrincipalResolutionError as error:
            span.set_status("error")
            span.set_attribute("outcome", "denied")
            span.set_attribute("source", "identity")
            _emit_outcome_observability(
                tracer=tracer,
                audit_writer=audit_writer,
                metric_recorder=metric_recorder,
                trace_id=trace_id,
                request_id=request_id,
                task_id=task_id,
                principal_id=principal_id,
                principal_role=payload.sender.actor_role,
                source="identity",
                outcome="denied",
                error_code=error.code,
                message=error.message,
            )
            return _error_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                trace_id=trace_id,
                code=error.code,
                error_class="authorization_error",
                message=error.message,
                retryable=False,
                source_component="api",
                details={"source": "identity"},
            )

        principal_id = principal.principal_id
        span.set_attribute("principal_id", principal_id)
        span.set_attribute("principal_role", principal.principal_role)
        span.set_attribute("connector", principal.connector)
        try:
            envelope = validate_owner_command_envelope(
                payload=payload,
                principal=principal,
                trace_id_override=trace_id,
            )
        except EnvelopeValidationError as error:
            span.set_status("error")
            span.set_attribute("outcome", "denied")
            span.set_attribute("source", "payload")
            _emit_outcome_observability(
                tracer=tracer,
                audit_writer=audit_writer,
                metric_recorder=metric_recorder,
                trace_id=trace_id,
                request_id=request_id,
                task_id=task_id,
                principal_id=principal_id,
                principal_role=principal.principal_role,
                source="payload",
                outcome="denied",
                error_code=error.code,
                message=error.message,
            )
            return _error_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                trace_id=trace_id,
                code=error.code,
                error_class="validation_error",
                message=error.message,
                retryable=False,
                source_component="api",
                details={"source": "payload"},
            )

        try:
            discord_decision = validate_discord_governance(
                payload=payload,
                principal_role=principal.principal_role,
                identity_channel_repository=identity_channel_repository,
                governance_repository=governance_repository,
            )
            if discord_decision is not None:
                span.set_attribute("discord.chat_class", discord_decision.chat_class)
                span.set_attribute("discord.mapping_status", discord_decision.mapping.status)
                if discord_decision.project_status is not None:
                    span.set_attribute("discord.project_status", discord_decision.project_status)
        except DiscordGovernanceError as error:
            span.set_status("error")
            span.set_attribute("outcome", "denied")
            span.set_attribute("source", "discord_governance")
            denial_details = dict(error.details)
            denial_details.setdefault("source", "discord_governance")
            source_component = (
                "policy_engine"
                if error.code == "governance_specialist_direct_command_denied"
                else "governance"
            )
            _emit_outcome_observability(
                tracer=tracer,
                audit_writer=audit_writer,
                metric_recorder=metric_recorder,
                trace_id=trace_id,
                request_id=None,
                task_id=None,
                principal_id=principal_id,
                principal_role=principal.principal_role,
                source="discord_governance",
                outcome="denied",
                error_code=error.code,
                message=error.message,
                attributes=cast(dict[str, object], denial_details),
            )
            return _denied_response(
                status_code=status.HTTP_403_FORBIDDEN,
                trace_id=trace_id,
                code=error.code,
                error_class="authorization_error",
                message=error.message,
                source_component=source_component,
                details=denial_details,
                policy_version=None,
                policy_hash=None,
                rule_ids=[],
            )

        request_id = envelope.request_id
        span.set_attribute("correlation.request_id", request_id)
        try:
            with tracer.start_span(
                trace_id=trace_id,
                name=TASK_ORCHESTRATION_SPAN,
                attributes={"stage": "admission"},
            ) as orchestration_span:
                orchestration_span.set_attribute("correlation.request_id", request_id)
                admission_result = admission_service.admit_owner_command(envelope)
        except AdmissionIdempotencyError as error:
            span.set_status("error")
            span.set_attribute("outcome", "denied")
            span.set_attribute("source", "idempotency")
            _emit_outcome_observability(
                tracer=tracer,
                audit_writer=audit_writer,
                metric_recorder=metric_recorder,
                trace_id=trace_id,
                request_id=request_id,
                task_id=task_id,
                principal_id=principal_id,
                principal_role=principal.principal_role,
                source="idempotency",
                outcome="denied",
                error_code=error.code,
                message=error.message,
            )
            return _error_response(
                status_code=status.HTTP_409_CONFLICT,
                trace_id=trace_id,
                code=error.code,
                error_class="validation_error",
                message=error.message,
                retryable=False,
                source_component="task_orchestrator",
                details={"source": "idempotency"},
            )

        task_id = admission_result.task.task_id
        request_id = admission_result.task.request_id
        principal_id = admission_result.task.principal_id
        trace_id = admission_result.task.trace_id
        span.set_attribute("correlation.trace_id", trace_id)
        span.set_attribute("correlation.task_id", task_id)
        span.set_attribute("replayed", str(admission_result.replayed).lower())

        if admission_result.replayed and admission_result.task.status not in {
            "queued",
            "authorized",
        }:
            replay_outcome = (
                "accepted" if admission_result.task.status == "dispatched" else "denied"
            )
            replay_source = admission_result.task.outcome_source or "governance"
            replay_message = (
                admission_result.task.outcome_message
                or "replayed owner command resolved from prior task outcome"
            )
            span.set_attribute("outcome", replay_outcome)
            span.set_attribute("source", replay_source)
            _emit_replay_observability(
                tracer=tracer,
                audit_writer=audit_writer,
                metric_recorder=metric_recorder,
                task=admission_result.task,
                outcome=replay_outcome,
                source=replay_source,
                message=replay_message,
            )
            return _replayed_response(admission_result.task)

        with tracer.start_span(
            trace_id=trace_id,
            name=POLICY_EVALUATION_SPAN,
            attributes={"stage": "policy_evaluation"},
        ) as policy_span:
            policy_span.set_attribute("correlation.task_id", task_id)
            policy_input = normalize_policy_input(admission_result.task)
            policy_outcome = evaluate_with_fail_closed(policy_input, policy_runtime_client)
        policy_decision = (
            policy_outcome.policy_result.decision
            if policy_outcome.policy_result is not None
            else "error"
        )
        policy_reason = (
            policy_outcome.policy_result.reason_code
            if policy_outcome.policy_result is not None
            else policy_outcome.error_code
        )
        policy_version = (
            policy_outcome.policy_result.policy_version
            if policy_outcome.policy_result is not None
            else "policy-version-unknown"
        )
        policy_hash = (
            policy_outcome.policy_result.policy_hash
            if policy_outcome.policy_result is not None
            else "policy-hash-unknown"
        )
        rule_ids = (
            list(policy_outcome.policy_result.rule_ids)
            if policy_outcome.policy_result is not None
            else []
        )

        _emit_stage_decision_audit(
            tracer=tracer,
            audit_writer=audit_writer,
            trace_id=trace_id,
            request_id=request_id,
            task_id=task_id,
            principal_id=principal_id,
            principal_role=admission_result.task.principal_role,
            stage="policy",
            decision=policy_decision,
            source="policy_runtime",
            reason_code=policy_reason,
            message=policy_outcome.message,
            policy_version=policy_version,
            policy_hash=policy_hash,
            rule_ids=rule_ids,
            attributes={
                "policy_version": policy_version,
                "policy_hash": policy_hash,
                "rule_ids": ",".join(rule_ids),
                "replayed": str(admission_result.replayed).lower(),
            },
        )

        if not policy_outcome.allowed:
            details = {
                "source": "policy_runtime",
                "task_id": admission_result.task.task_id,
                "replayed": str(admission_result.replayed).lower(),
                "policy_version": policy_version,
                "policy_hash": policy_hash,
                "rule_ids": ",".join(rule_ids),
            }
            if policy_outcome.policy_result is not None:
                details["decision"] = policy_outcome.policy_result.decision
                details["reason_code"] = policy_outcome.policy_result.reason_code

            runtime_state_repo.update_task_status(
                admission_result.task.task_id,
                "blocked",
                outcome_source="policy_runtime",
                outcome_error_code=policy_outcome.error_code or "policy_blocked",
                outcome_message=policy_outcome.message,
                outcome_details=details,
            )
            span.set_status("error")
            span.set_attribute("outcome", "denied")
            span.set_attribute("source", "policy_runtime")
            _emit_outcome_observability(
                tracer=tracer,
                audit_writer=audit_writer,
                metric_recorder=metric_recorder,
                trace_id=trace_id,
                request_id=request_id,
                task_id=task_id,
                principal_id=principal_id,
                principal_role=admission_result.task.principal_role,
                source="policy_runtime",
                outcome="denied",
                error_code=policy_outcome.error_code or "policy_blocked",
                message=policy_outcome.message,
                policy_version=policy_version,
                policy_hash=policy_hash,
                rule_ids=rule_ids,
                attributes={
                    "decision": policy_decision,
                    "policy_version": policy_version,
                    "policy_hash": policy_hash,
                    "rule_ids": ",".join(rule_ids),
                },
            )
            return _denied_response(
                status_code=status.HTTP_403_FORBIDDEN,
                trace_id=trace_id,
                code=policy_outcome.error_code or "policy_blocked",
                error_class="authorization_error",
                message=policy_outcome.message,
                source_component="policy_engine",
                details=details,
                policy_version=policy_version,
                policy_hash=policy_hash,
                rule_ids=rule_ids,
            )

        runtime_state_repo.update_task_status(
            admission_result.task.task_id,
            "authorized",
            outcome_source="policy_runtime",
            outcome_error_code=None,
            outcome_message="policy authorized command",
            outcome_details={
                "decision": policy_decision,
                "policy_version": policy_version,
                "policy_hash": policy_hash,
                "rule_ids": ",".join(rule_ids),
            },
        )

        with tracer.start_span(
            trace_id=trace_id,
            name=BUDGET_RESERVATION_SPAN,
            attributes={"stage": "budget_reservation"},
        ) as budget_span:
            budget_span.set_attribute("correlation.task_id", task_id)
            budget_outcome = budget_reservation_service.reserve_with_fail_closed(
                admission_result.task
            )
        budget_decision = (
            budget_outcome.reservation.decision
            if budget_outcome.reservation is not None
            else "error"
        )
        budget_reason = (
            budget_outcome.reservation.reason_code
            if budget_outcome.reservation is not None
            else budget_outcome.error_code
        )
        budget_version = (
            budget_outcome.reservation.budget_version
            if budget_outcome.reservation is not None
            else "budget-version-unknown"
        )

        _emit_stage_decision_audit(
            tracer=tracer,
            audit_writer=audit_writer,
            trace_id=trace_id,
            request_id=request_id,
            task_id=task_id,
            principal_id=principal_id,
            principal_role=admission_result.task.principal_role,
            stage="budget",
            decision=budget_decision,
            source="budget_runtime",
            reason_code=budget_reason,
            message=budget_outcome.message,
            policy_version=policy_version,
            policy_hash=policy_hash,
            rule_ids=rule_ids,
            attributes={
                "budget_version": budget_version,
                "policy_version": policy_version,
                "policy_hash": policy_hash,
                "rule_ids": ",".join(rule_ids),
                "replayed": str(admission_result.replayed).lower(),
            },
        )

        if not budget_outcome.allowed:
            details = {
                "source": "budget_runtime",
                "task_id": admission_result.task.task_id,
                "replayed": str(admission_result.replayed).lower(),
                "policy_version": policy_version,
                "policy_hash": policy_hash,
                "rule_ids": ",".join(rule_ids),
            }
            if budget_outcome.reservation is not None:
                details["decision"] = budget_outcome.reservation.decision
                details["reason_code"] = budget_outcome.reservation.reason_code
                details["budget_version"] = budget_outcome.reservation.budget_version
                if budget_outcome.reservation.remaining_units is not None:
                    details["remaining_units"] = str(budget_outcome.reservation.remaining_units)

            runtime_state_repo.update_task_status(
                admission_result.task.task_id,
                "blocked",
                outcome_source="budget_runtime",
                outcome_error_code=budget_outcome.error_code or "budget_blocked",
                outcome_message=budget_outcome.message,
                outcome_details=details,
            )
            span.set_status("error")
            span.set_attribute("outcome", "denied")
            span.set_attribute("source", "budget_runtime")
            _emit_outcome_observability(
                tracer=tracer,
                audit_writer=audit_writer,
                metric_recorder=metric_recorder,
                trace_id=trace_id,
                request_id=request_id,
                task_id=task_id,
                principal_id=principal_id,
                principal_role=admission_result.task.principal_role,
                source="budget_runtime",
                outcome="denied",
                error_code=budget_outcome.error_code or "budget_blocked",
                message=budget_outcome.message,
                policy_version=policy_version,
                policy_hash=policy_hash,
                rule_ids=rule_ids,
                attributes={"decision": budget_decision, "budget_version": budget_version},
            )
            return _denied_response(
                status_code=status.HTTP_403_FORBIDDEN,
                trace_id=trace_id,
                code=budget_outcome.error_code or "budget_blocked",
                error_class="budget_error",
                message=budget_outcome.message,
                source_component="budget_engine",
                details=details,
                policy_version=policy_version,
                policy_hash=policy_hash,
                rule_ids=rule_ids,
            )

        with tracer.start_span(
            trace_id=trace_id,
            name=EXECUTION_SANDBOX_SPAN,
            attributes={"stage": "execution_dispatch"},
        ) as dispatch_span:
            dispatch_span.set_attribute("correlation.task_id", task_id)
            dispatch_outcome = task_dispatch_service.dispatch_admitted_task(
                admission_result.task,
                policy_version=policy_version,
                policy_hash=policy_hash,
                rule_ids=tuple(rule_ids),
            )
        if not dispatch_outcome.accepted:
            dispatch_source = dispatch_outcome.source
            details = {
                "source": dispatch_source,
                "task_id": admission_result.task.task_id,
                "replayed": str(dispatch_outcome.replayed).lower(),
                "dispatch_target": dispatch_outcome.target,
                "policy_version": policy_version,
                "policy_hash": policy_hash,
                "rule_ids": ",".join(rule_ids),
            }
            if dispatch_outcome.error_code is not None:
                details["reason_code"] = dispatch_outcome.error_code
            details["retryable"] = str(dispatch_outcome.retryable).lower()
            if dispatch_outcome.dead_letter_id is not None:
                details["dead_letter_id"] = dispatch_outcome.dead_letter_id

            span.set_status("error")
            span.set_attribute("outcome", "denied")
            span.set_attribute("source", dispatch_source)
            span.set_attribute("dispatch_target", dispatch_outcome.target)
            _emit_outcome_observability(
                tracer=tracer,
                audit_writer=audit_writer,
                metric_recorder=metric_recorder,
                trace_id=trace_id,
                request_id=request_id,
                task_id=task_id,
                principal_id=principal_id,
                principal_role=admission_result.task.principal_role,
                source=dispatch_source,
                outcome="denied",
                error_code=dispatch_outcome.error_code or "execution_dispatch_failed",
                message=dispatch_outcome.message,
                policy_version=policy_version,
                policy_hash=policy_hash,
                rule_ids=rule_ids,
                attributes={"dispatch_target": dispatch_outcome.target},
            )
            if dispatch_source == "dispatch_llm_gateway":
                source_component = "llm_gateway"
            elif dispatch_source.startswith("dispatch_communication"):
                source_component = "communication_gateway"
            else:
                source_component = "sandbox"
            return _denied_response(
                status_code=status.HTTP_403_FORBIDDEN,
                trace_id=trace_id,
                code=dispatch_outcome.error_code or "execution_dispatch_failed",
                error_class="runtime_error",
                message=dispatch_outcome.message,
                source_component=source_component,
                details=details,
                policy_version=policy_version,
                policy_hash=policy_hash,
                rule_ids=rule_ids,
            )

        response_task = (
            runtime_state_repo.get_task_by_id(admission_result.task.task_id)
            or admission_result.task
        )
        span.set_attribute("outcome", "accepted")
        span.set_attribute("source", "dispatch")
        span.set_attribute("dispatch_target", dispatch_outcome.target)
        _emit_outcome_observability(
            tracer=tracer,
            audit_writer=audit_writer,
            metric_recorder=metric_recorder,
            trace_id=response_task.trace_id,
            request_id=response_task.request_id,
            task_id=response_task.task_id,
            principal_id=response_task.principal_id,
            principal_role=response_task.principal_role,
            source=f"dispatch_{dispatch_outcome.target}",
            outcome="accepted",
            error_code=None,
            message=dispatch_outcome.message,
            policy_version=policy_version,
            policy_hash=policy_hash,
            rule_ids=rule_ids,
            attributes={
                "dispatch_target": dispatch_outcome.target,
                "dispatch_id": dispatch_outcome.dispatch_id or "dispatch-id-missing",
                "replayed": str(dispatch_outcome.replayed).lower(),
            },
        )

        return OwnerCommandResponse(
            status="accepted",
            trace_id=response_task.trace_id,
            policy_version=policy_version,
            policy_hash=policy_hash,
            rule_ids=rule_ids,
            data=OwnerCommandAcceptedData(
                task_id=response_task.task_id,
                admission_state="dispatched",
                replayed=admission_result.replayed,
                request_id=response_task.request_id,
                principal_id=response_task.principal_id,
                connector=response_task.connector,
                command=response_task.command,
                accepted_args=list(response_task.args),
                dispatch_target=dispatch_outcome.target,
                dispatch_id=dispatch_outcome.dispatch_id or "dispatch-id-missing",
                llm_execution=(
                    {
                        "decision": dispatch_outcome.llm_metadata.decision,
                        "model_selected": dispatch_outcome.llm_metadata.model_selected,
                        "routing_profile": dispatch_outcome.llm_metadata.routing_profile,
                        "quota_limit_source": dispatch_outcome.llm_metadata.quota_limit_source,
                        "usage": {
                            "input_tokens": dispatch_outcome.llm_metadata.input_tokens,
                            "output_tokens": dispatch_outcome.llm_metadata.output_tokens,
                            "total_tokens": dispatch_outcome.llm_metadata.total_tokens,
                            "request_units": dispatch_outcome.llm_metadata.request_units,
                        },
                        "cost": {
                            "estimated_cost_usd": dispatch_outcome.llm_metadata.estimated_cost_usd,
                            "actual_cost_usd": dispatch_outcome.llm_metadata.actual_cost_usd,
                            "cost_source": dispatch_outcome.llm_metadata.cost_source,
                        },
                        "budget_usage": {
                            "currency_delta_usd": dispatch_outcome.llm_metadata.currency_delta_usd,
                            "quota_token_units": dispatch_outcome.llm_metadata.quota_token_units,
                        },
                        "generated_text": dispatch_outcome.llm_metadata.generated_text,
                        "recipient_role": dispatch_outcome.llm_metadata.recipient_role,
                        "recipient_id": dispatch_outcome.llm_metadata.recipient_id,
                        "grounding_sources": list(
                            dispatch_outcome.llm_metadata.grounding_source_ids
                        ),
                    }
                    if dispatch_outcome.llm_metadata is not None
                    else None
                ),
            ),
        )
    raise RuntimeError("unreachable owner command control flow")
