"""Owner command ingress router."""

from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, Request, status
from fastapi.responses import JSONResponse

from openqilin.control_plane.api.dependencies import get_admission_service
from openqilin.control_plane.identity.principal_resolver import (
    PrincipalResolutionError,
    resolve_principal,
)
from openqilin.control_plane.schemas.owner_commands import (
    OwnerCommandAcceptedResponse,
    OwnerCommandRejectedResponse,
    OwnerCommandRequest,
)
from openqilin.task_orchestrator.admission.envelope_validator import (
    EnvelopeValidationError,
    validate_owner_command_envelope,
)
from openqilin.task_orchestrator.admission.service import AdmissionIdempotencyError, AdmissionService

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
    },
)
def submit_owner_command(
    payload: OwnerCommandRequest,
    request: Request,
    admission_service: AdmissionService = Depends(get_admission_service),
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
        envelope = validate_owner_command_envelope(payload=payload, principal=principal, trace_id=trace_id)
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

    return OwnerCommandAcceptedResponse(
        task_id=admission_result.task.task_id,
        replayed=admission_result.replayed,
        request_id=admission_result.task.request_id,
        trace_id=admission_result.task.trace_id,
        principal_id=admission_result.task.principal_id,
        connector=admission_result.task.connector,
        command=admission_result.task.command,
        accepted_args=list(admission_result.task.args),
    )
