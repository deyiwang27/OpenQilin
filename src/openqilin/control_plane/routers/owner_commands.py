"""Owner command ingress router."""

from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, Request, status
from fastapi.responses import JSONResponse

from openqilin.budget_runtime.reservation_service import BudgetReservationService
from openqilin.control_plane.api.dependencies import (
    get_admission_service,
    get_audit_writer,
    get_budget_reservation_service,
    get_metric_recorder,
    get_policy_runtime_client,
    get_runtime_state_repository,
    get_task_dispatch_service,
    get_tracer,
)
from openqilin.control_plane.identity.principal_resolver import (
    PrincipalResolutionError,
    resolve_principal,
)
from openqilin.control_plane.schemas.owner_commands import (
    OwnerCommandAcceptedResponse,
    OwnerCommandRejectedResponse,
    OwnerCommandRequest,
)
from openqilin.observability.audit.audit_writer import InMemoryAuditWriter
from openqilin.observability.metrics.recorder import InMemoryMetricRecorder
from openqilin.observability.tracing.spans import OWNER_COMMAND_INGRESS_SPAN
from openqilin.observability.tracing.tracer import InMemoryTracer
from openqilin.policy_runtime_integration.client import InMemoryPolicyRuntimeClient
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
from openqilin.data_access.repositories.runtime_state import (
    InMemoryRuntimeStateRepository,
    TaskRecord,
)

router = APIRouter(prefix="/v1/owner/commands", tags=["owner_commands"])


def _blocked_response(
    error_code: str,
    message: str,
    details: dict[str, str],
    *,
    status_code: int = status.HTTP_400_BAD_REQUEST,
) -> JSONResponse:
    payload = OwnerCommandRejectedResponse(
        error_code=error_code,
        message=message,
        details=details,
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump())


def _emit_outcome_observability(
    *,
    audit_writer: InMemoryAuditWriter,
    metric_recorder: InMemoryMetricRecorder,
    trace_id: str,
    request_id: str | None,
    task_id: str | None,
    principal_id: str | None,
    source: str,
    outcome: str,
    error_code: str | None,
    message: str,
    attributes: dict[str, object] | None = None,
) -> None:
    """Record final owner-command outcome in metrics and audit streams."""

    metric_recorder.increment_counter(
        "owner_command_admission_outcomes_total",
        labels={"outcome": outcome, "source": source},
    )
    audit_writer.write_event(
        event_type=f"owner_command.{outcome}",
        outcome=outcome,
        trace_id=trace_id or "missing-trace-id",
        request_id=request_id,
        task_id=task_id,
        principal_id=principal_id,
        source=source,
        reason_code=error_code,
        message=message,
        attributes=attributes,
    )


def _emit_replay_observability(
    *,
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
    audit_writer.write_event(
        event_type="owner_command.replayed",
        outcome=outcome,
        trace_id=task.trace_id,
        request_id=task.request_id,
        task_id=task.task_id,
        principal_id=task.principal_id,
        source=source,
        reason_code=task.outcome_error_code,
        message=message,
        attributes={
            "replayed": "true",
            "status": task.status,
            "dispatch_target": task.dispatch_target or "unknown",
        },
    )


def _emit_stage_decision_audit(
    *,
    audit_writer: InMemoryAuditWriter,
    trace_id: str,
    request_id: str,
    task_id: str,
    principal_id: str,
    stage: str,
    decision: str,
    source: str,
    reason_code: str | None,
    message: str,
    attributes: dict[str, object] | None = None,
) -> None:
    """Record policy/budget stage decisions as immutable audit events."""

    audit_writer.write_event(
        event_type=f"{stage}.decision",
        outcome=decision,
        trace_id=trace_id,
        request_id=request_id,
        task_id=task_id,
        principal_id=principal_id,
        source=source,
        reason_code=reason_code,
        message=message,
        attributes=attributes,
    )


def _replayed_response(task: TaskRecord) -> OwnerCommandAcceptedResponse | JSONResponse:
    """Reconstruct deterministic response from previously processed task state."""

    if task.status == "dispatched":
        dispatch_target = task.dispatch_target or select_dispatch_target(task)
        dispatch_id = task.dispatch_id or "dispatch-id-missing"
        return OwnerCommandAcceptedResponse(
            task_id=task.task_id,
            replayed=True,
            request_id=task.request_id,
            trace_id=task.trace_id,
            principal_id=task.principal_id,
            connector=task.connector,
            command=task.command,
            accepted_args=list(task.args),
            dispatch_target=dispatch_target,
            dispatch_id=dispatch_id,
        )

    source = task.outcome_source or "governance"
    error_code = task.outcome_error_code or "governance_blocked"
    message = task.outcome_message or "task replay resolved to prior blocked outcome"
    details = {
        "source": source,
        "task_id": task.task_id,
        "replayed": "true",
    }
    if task.dispatch_target is not None:
        details["dispatch_target"] = task.dispatch_target
    if task.outcome_error_code is not None:
        details["reason_code"] = task.outcome_error_code
    return _blocked_response(
        error_code=error_code,
        message=message,
        details=details,
        status_code=status.HTTP_403_FORBIDDEN,
    )


@router.post(
    "",
    response_model=OwnerCommandAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": OwnerCommandRejectedResponse},
        status.HTTP_409_CONFLICT: {"model": OwnerCommandRejectedResponse},
        status.HTTP_403_FORBIDDEN: {"model": OwnerCommandRejectedResponse},
    },
)
def submit_owner_command(
    payload: OwnerCommandRequest,
    request: Request,
    admission_service: AdmissionService = Depends(get_admission_service),
    policy_runtime_client: InMemoryPolicyRuntimeClient = Depends(get_policy_runtime_client),
    budget_reservation_service: BudgetReservationService = Depends(get_budget_reservation_service),
    runtime_state_repo: InMemoryRuntimeStateRepository = Depends(get_runtime_state_repository),
    task_dispatch_service: TaskDispatchService = Depends(get_task_dispatch_service),
    tracer: InMemoryTracer = Depends(get_tracer),
    audit_writer: InMemoryAuditWriter = Depends(get_audit_writer),
    metric_recorder: InMemoryMetricRecorder = Depends(get_metric_recorder),
    x_openqilin_trace_id: Annotated[str | None, Header(alias="X-OpenQilin-Trace-Id")] = None,
) -> OwnerCommandAcceptedResponse | JSONResponse:
    """Validate ingress identity and envelope before admission execution."""
    trace_id = x_openqilin_trace_id.strip() if x_openqilin_trace_id else str(uuid4())
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

        try:
            principal = resolve_principal(request.headers)
        except PrincipalResolutionError as error:
            span.set_status("error")
            span.set_attribute("outcome", "blocked")
            span.set_attribute("source", "headers")
            _emit_outcome_observability(
                audit_writer=audit_writer,
                metric_recorder=metric_recorder,
                trace_id=trace_id,
                request_id=request_id,
                task_id=task_id,
                principal_id=principal_id,
                source="headers",
                outcome="blocked",
                error_code=error.code,
                message=error.message,
            )
            return _blocked_response(
                error_code=error.code,
                message=error.message,
                details={"source": "headers"},
            )

        principal_id = principal.principal_id
        span.set_attribute("principal_id", principal_id)
        span.set_attribute("connector", principal.connector)
        try:
            envelope = validate_owner_command_envelope(
                payload=payload, principal=principal, trace_id=trace_id
            )
        except EnvelopeValidationError as error:
            span.set_status("error")
            span.set_attribute("outcome", "blocked")
            span.set_attribute("source", "payload")
            _emit_outcome_observability(
                audit_writer=audit_writer,
                metric_recorder=metric_recorder,
                trace_id=trace_id,
                request_id=request_id,
                task_id=task_id,
                principal_id=principal_id,
                source="payload",
                outcome="blocked",
                error_code=error.code,
                message=error.message,
            )
            return _blocked_response(
                error_code=error.code,
                message=error.message,
                details={"source": "payload"},
            )

        request_id = envelope.request_id
        span.set_attribute("correlation.request_id", request_id)
        try:
            admission_result = admission_service.admit_owner_command(envelope)
        except AdmissionIdempotencyError as error:
            span.set_status("error")
            span.set_attribute("outcome", "blocked")
            span.set_attribute("source", "idempotency")
            _emit_outcome_observability(
                audit_writer=audit_writer,
                metric_recorder=metric_recorder,
                trace_id=trace_id,
                request_id=request_id,
                task_id=task_id,
                principal_id=principal_id,
                source="idempotency",
                outcome="blocked",
                error_code=error.code,
                message=error.message,
            )
            return _blocked_response(
                error_code=error.code,
                message=error.message,
                details={"source": "idempotency"},
                status_code=status.HTTP_409_CONFLICT,
            )

        task_id = admission_result.task.task_id
        request_id = admission_result.task.request_id
        principal_id = admission_result.task.principal_id
        trace_id = admission_result.task.trace_id
        span.set_attribute("correlation.trace_id", trace_id)
        span.set_attribute("correlation.task_id", task_id)
        span.set_attribute("replayed", str(admission_result.replayed).lower())
        if admission_result.replayed and admission_result.task.status != "admitted":
            replay_outcome = (
                "accepted" if admission_result.task.status == "dispatched" else "blocked"
            )
            replay_source = admission_result.task.outcome_source or "governance"
            replay_message = (
                admission_result.task.outcome_message
                or "replayed owner command resolved from prior task outcome"
            )
            span.set_attribute("outcome", replay_outcome)
            span.set_attribute("source", replay_source)
            _emit_replay_observability(
                audit_writer=audit_writer,
                metric_recorder=metric_recorder,
                task=admission_result.task,
                outcome=replay_outcome,
                source=replay_source,
                message=replay_message,
            )
            return _replayed_response(admission_result.task)

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
        _emit_stage_decision_audit(
            audit_writer=audit_writer,
            trace_id=trace_id,
            request_id=request_id,
            task_id=task_id,
            principal_id=principal_id,
            stage="policy",
            decision=policy_decision,
            source="policy_runtime",
            reason_code=policy_reason,
            message=policy_outcome.message,
            attributes={
                "policy_version": policy_version,
                "replayed": str(admission_result.replayed).lower(),
            },
        )
        if not policy_outcome.allowed:
            details = {
                "source": "policy_runtime",
                "task_id": admission_result.task.task_id,
                "replayed": str(admission_result.replayed).lower(),
            }
            if policy_outcome.policy_result is not None:
                details["decision"] = policy_outcome.policy_result.decision
                details["reason_code"] = policy_outcome.policy_result.reason_code
                details["policy_version"] = policy_outcome.policy_result.policy_version

            runtime_state_repo.update_task_status(
                admission_result.task.task_id,
                "blocked_policy",
                outcome_source="policy_runtime",
                outcome_error_code=policy_outcome.error_code or "policy_blocked",
                outcome_message=policy_outcome.message,
            )
            span.set_status("error")
            span.set_attribute("outcome", "blocked")
            span.set_attribute("source", "policy_runtime")
            _emit_outcome_observability(
                audit_writer=audit_writer,
                metric_recorder=metric_recorder,
                trace_id=trace_id,
                request_id=request_id,
                task_id=task_id,
                principal_id=principal_id,
                source="policy_runtime",
                outcome="blocked",
                error_code=policy_outcome.error_code or "policy_blocked",
                message=policy_outcome.message,
                attributes={"decision": policy_decision, "policy_version": policy_version},
            )
            return _blocked_response(
                error_code=policy_outcome.error_code or "policy_blocked",
                message=policy_outcome.message,
                details=details,
                status_code=status.HTTP_403_FORBIDDEN,
            )

        budget_outcome = budget_reservation_service.reserve_with_fail_closed(admission_result.task)
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
            audit_writer=audit_writer,
            trace_id=trace_id,
            request_id=request_id,
            task_id=task_id,
            principal_id=principal_id,
            stage="budget",
            decision=budget_decision,
            source="budget_runtime",
            reason_code=budget_reason,
            message=budget_outcome.message,
            attributes={
                "budget_version": budget_version,
                "replayed": str(admission_result.replayed).lower(),
            },
        )
        if not budget_outcome.allowed:
            details = {
                "source": "budget_runtime",
                "task_id": admission_result.task.task_id,
                "replayed": str(admission_result.replayed).lower(),
            }
            if budget_outcome.reservation is not None:
                details["decision"] = budget_outcome.reservation.decision
                details["reason_code"] = budget_outcome.reservation.reason_code
                details["budget_version"] = budget_outcome.reservation.budget_version
                if budget_outcome.reservation.remaining_units is not None:
                    details["remaining_units"] = str(budget_outcome.reservation.remaining_units)

            runtime_state_repo.update_task_status(
                admission_result.task.task_id,
                "blocked_budget",
                outcome_source="budget_runtime",
                outcome_error_code=budget_outcome.error_code or "budget_blocked",
                outcome_message=budget_outcome.message,
            )
            span.set_status("error")
            span.set_attribute("outcome", "blocked")
            span.set_attribute("source", "budget_runtime")
            _emit_outcome_observability(
                audit_writer=audit_writer,
                metric_recorder=metric_recorder,
                trace_id=trace_id,
                request_id=request_id,
                task_id=task_id,
                principal_id=principal_id,
                source="budget_runtime",
                outcome="blocked",
                error_code=budget_outcome.error_code or "budget_blocked",
                message=budget_outcome.message,
                attributes={"decision": budget_decision, "budget_version": budget_version},
            )
            return _blocked_response(
                error_code=budget_outcome.error_code or "budget_blocked",
                message=budget_outcome.message,
                details=details,
                status_code=status.HTTP_403_FORBIDDEN,
            )

        dispatch_outcome = task_dispatch_service.dispatch_admitted_task(admission_result.task)
        if not dispatch_outcome.accepted:
            details = {
                "source": "dispatch_stub",
                "task_id": admission_result.task.task_id,
                "replayed": str(dispatch_outcome.replayed).lower(),
                "dispatch_target": dispatch_outcome.target,
            }
            if dispatch_outcome.error_code is not None:
                details["reason_code"] = dispatch_outcome.error_code

            span.set_status("error")
            span.set_attribute("outcome", "blocked")
            span.set_attribute("source", "dispatch_stub")
            span.set_attribute("dispatch_target", dispatch_outcome.target)
            _emit_outcome_observability(
                audit_writer=audit_writer,
                metric_recorder=metric_recorder,
                trace_id=trace_id,
                request_id=request_id,
                task_id=task_id,
                principal_id=principal_id,
                source="dispatch_stub",
                outcome="blocked",
                error_code=dispatch_outcome.error_code or "execution_dispatch_failed",
                message=dispatch_outcome.message,
                attributes={"dispatch_target": dispatch_outcome.target},
            )
            return _blocked_response(
                error_code=dispatch_outcome.error_code or "execution_dispatch_failed",
                message=dispatch_outcome.message,
                details=details,
                status_code=status.HTTP_403_FORBIDDEN,
            )

        response_task = (
            runtime_state_repo.get_task_by_id(admission_result.task.task_id)
            or admission_result.task
        )
        span.set_attribute("outcome", "accepted")
        span.set_attribute("source", "dispatch")
        span.set_attribute("dispatch_target", dispatch_outcome.target)
        _emit_outcome_observability(
            audit_writer=audit_writer,
            metric_recorder=metric_recorder,
            trace_id=response_task.trace_id,
            request_id=response_task.request_id,
            task_id=response_task.task_id,
            principal_id=response_task.principal_id,
            source=f"dispatch_{dispatch_outcome.target}",
            outcome="accepted",
            error_code=None,
            message=dispatch_outcome.message,
            attributes={
                "dispatch_target": dispatch_outcome.target,
                "dispatch_id": dispatch_outcome.dispatch_id or "dispatch-id-missing",
                "replayed": str(dispatch_outcome.replayed).lower(),
            },
        )

        return OwnerCommandAcceptedResponse(
            task_id=response_task.task_id,
            replayed=admission_result.replayed,
            request_id=response_task.request_id,
            trace_id=response_task.trace_id,
            principal_id=response_task.principal_id,
            connector=response_task.connector,
            command=response_task.command,
            accepted_args=list(response_task.args),
            dispatch_target=dispatch_outcome.target,
            dispatch_id=dispatch_outcome.dispatch_id or "dispatch-id-missing",
        )
    raise RuntimeError("unreachable owner command control flow")
