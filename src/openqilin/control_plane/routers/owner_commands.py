"""Owner command ingress router."""

from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Header, Request, status
from fastapi.responses import JSONResponse

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

router = APIRouter(prefix="/v1/owner/commands", tags=["owner_commands"])


def _blocked_response(error_code: str, message: str, details: dict[str, str]) -> JSONResponse:
    payload = OwnerCommandRejectedResponse(
        error_code=error_code,
        message=message,
        details=details,
    )
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=payload.model_dump())


@router.post(
    "",
    response_model=OwnerCommandAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={status.HTTP_400_BAD_REQUEST: {"model": OwnerCommandRejectedResponse}},
)
def submit_owner_command(
    payload: OwnerCommandRequest,
    request: Request,
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

    return OwnerCommandAcceptedResponse(
        request_id=envelope.request_id,
        trace_id=envelope.trace_id,
        principal_id=envelope.principal_id,
        connector=envelope.connector,
        command=envelope.command,
        accepted_args=list(envelope.args),
    )
