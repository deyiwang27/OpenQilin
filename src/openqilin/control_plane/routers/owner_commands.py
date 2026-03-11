"""Owner command ingress router."""

from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, Request, status
from fastapi.responses import JSONResponse

from openqilin.budget_runtime.reservation_service import BudgetReservationService
from openqilin.control_plane.api.dependencies import (
    get_admission_service,
    get_budget_reservation_service,
    get_policy_runtime_client,
    get_runtime_state_repository,
    get_task_dispatch_service,
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
from openqilin.task_orchestrator.services.task_service import TaskDispatchService
from openqilin.data_access.repositories.runtime_state import InMemoryRuntimeStateRepository

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
    x_openqilin_trace_id: Annotated[str | None, Header(alias="X-OpenQilin-Trace-Id")] = None,
) -> OwnerCommandAcceptedResponse | JSONResponse:
    """Validate ingress identity and envelope before admission execution."""

    try:
        principal = resolve_principal(request.headers)
    except PrincipalResolutionError as error:
        return _blocked_response(
            error_code=error.code,
            message=error.message,
            details={"source": "headers"},
        )

    trace_id = x_openqilin_trace_id.strip() if x_openqilin_trace_id else str(uuid4())
    try:
        envelope = validate_owner_command_envelope(
            payload=payload, principal=principal, trace_id=trace_id
        )
    except EnvelopeValidationError as error:
        return _blocked_response(
            error_code=error.code,
            message=error.message,
            details={"source": "payload"},
        )

    try:
        admission_result = admission_service.admit_owner_command(envelope)
    except AdmissionIdempotencyError as error:
        return _blocked_response(
            error_code=error.code,
            message=error.message,
            details={"source": "idempotency"},
            status_code=status.HTTP_409_CONFLICT,
        )

    policy_input = normalize_policy_input(admission_result.task)
    policy_outcome = evaluate_with_fail_closed(policy_input, policy_runtime_client)
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

        runtime_state_repo.update_task_status(admission_result.task.task_id, "blocked_policy")
        return _blocked_response(
            error_code=policy_outcome.error_code or "policy_blocked",
            message=policy_outcome.message,
            details=details,
            status_code=status.HTTP_403_FORBIDDEN,
        )

    budget_outcome = budget_reservation_service.reserve_with_fail_closed(admission_result.task)
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

        runtime_state_repo.update_task_status(admission_result.task.task_id, "blocked_budget")
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

        return _blocked_response(
            error_code=dispatch_outcome.error_code or "execution_dispatch_failed",
            message=dispatch_outcome.message,
            details=details,
            status_code=status.HTTP_403_FORBIDDEN,
        )

    response_task = (
        runtime_state_repo.get_task_by_id(admission_result.task.task_id) or admission_result.task
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
