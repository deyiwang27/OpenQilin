"""Owner discussion router for proposal-stage governance discussions."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, status
from fastapi.responses import JSONResponse

from openqilin.control_plane.api.dependencies import (
    get_audit_writer,
    get_governance_repository,
)
from openqilin.control_plane.handlers.governance_handler import (
    GovernanceHandlerError,
    submit_proposal_message,
)
from openqilin.control_plane.identity.principal_resolver import (
    PrincipalResolutionError,
    resolve_principal,
)
from openqilin.control_plane.schemas.governance import (
    GovernanceApiError,
    GovernanceApiResponse,
    ProposalDiscussionRequest,
)
from openqilin.data_access.repositories.governance import InMemoryGovernanceRepository
from openqilin.observability.audit.audit_writer import InMemoryAuditWriter

router = APIRouter(tags=["owner_discussions"])


def _governance_response(
    *,
    status_code: int,
    trace_id: str,
    status_value: Literal["ok", "denied", "error"],
    data: dict[str, object] | None = None,
    error: GovernanceApiError | None = None,
) -> JSONResponse:
    payload = GovernanceApiResponse(
        trace_id=trace_id,
        status=status_value,
        data=data,
        error=error,
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump())


def _resolve_principal(
    *,
    external_channel_header: str | None,
    external_actor_id_header: str | None,
    actor_external_id_header: str | None,
    actor_role_header: str | None,
) -> tuple[str, str] | GovernanceApiError:
    headers = {
        "x-external-channel": external_channel_header or "",
        "x-external-actor-id": external_actor_id_header or "",
        "x-openqilin-actor-external-id": actor_external_id_header or "",
    }
    if actor_role_header is not None:
        headers["x-openqilin-actor-role"] = actor_role_header
    try:
        principal = resolve_principal(headers)
    except PrincipalResolutionError as error:
        return GovernanceApiError(
            code=error.code,
            message=error.message,
            retryable=False,
            source_component="identity",
            details={},
        )
    return principal.principal_id, principal.principal_role


def _map_handler_error(
    error: GovernanceHandlerError,
) -> tuple[int, GovernanceApiError, Literal["denied", "error"]]:
    if error.code == "governance_role_forbidden":
        return (
            status.HTTP_403_FORBIDDEN,
            GovernanceApiError(
                code=error.code,
                message=error.message,
                retryable=False,
                source_component="governance",
                details={},
            ),
            "denied",
        )
    if error.code == "governance_project_missing":
        return (
            status.HTTP_404_NOT_FOUND,
            GovernanceApiError(
                code=error.code,
                message=error.message,
                retryable=False,
                source_component="governance_repository",
                details={},
            ),
            "denied",
        )
    if error.code == "governance_project_not_proposed":
        return (
            status.HTTP_409_CONFLICT,
            GovernanceApiError(
                code=error.code,
                message=error.message,
                retryable=False,
                source_component="governance_repository",
                details={},
            ),
            "denied",
        )
    return (
        status.HTTP_400_BAD_REQUEST,
        GovernanceApiError(
            code=error.code,
            message=error.message,
            retryable=False,
            source_component="governance",
            details={},
        ),
        "error",
    )


@router.post(
    "/v1/governance/projects/{project_id}/proposal/messages",
    response_model=GovernanceApiResponse,
)
def post_proposal_discussion_message(
    project_id: str,
    payload: ProposalDiscussionRequest,
    governance_repository: InMemoryGovernanceRepository = Depends(get_governance_repository),
    audit_writer: InMemoryAuditWriter = Depends(get_audit_writer),
    external_channel_header: Annotated[str | None, Header(alias="X-External-Channel")] = None,
    external_actor_id_header: Annotated[str | None, Header(alias="X-External-Actor-Id")] = None,
    actor_external_id_header: Annotated[
        str | None, Header(alias="X-OpenQilin-Actor-External-Id")
    ] = None,
    actor_role_header: Annotated[str | None, Header(alias="X-OpenQilin-Actor-Role")] = None,
) -> JSONResponse:
    """Persist one proposal-stage discussion message for triad roles."""

    resolved = _resolve_principal(
        external_channel_header=external_channel_header,
        external_actor_id_header=external_actor_id_header,
        actor_external_id_header=actor_external_id_header,
        actor_role_header=actor_role_header,
    )
    if isinstance(resolved, GovernanceApiError):
        return _governance_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            trace_id=payload.trace_id,
            status_value="error",
            error=resolved,
        )
    principal_id, principal_role = resolved

    try:
        message = submit_proposal_message(
            repository=governance_repository,
            project_id=project_id,
            actor_id=principal_id,
            actor_role=principal_role,
            content=payload.content,
            trace_id=payload.trace_id,
        )
    except GovernanceHandlerError as error:
        status_code, response_error, status_value = _map_handler_error(error)
        return _governance_response(
            status_code=status_code,
            trace_id=payload.trace_id,
            status_value=status_value,
            error=response_error,
        )

    audit_writer.write_event(
        event_type="proposal.message",
        outcome="ok",
        trace_id=payload.trace_id,
        request_id=None,
        task_id=None,
        principal_id=principal_id,
        principal_role=principal_role,
        source="governance",
        reason_code=None,
        message="proposal discussion message recorded",
        payload={
            "project_id": project_id,
            "message_id": message.message_id,
            "actor_role": principal_role,
        },
    )
    return _governance_response(
        status_code=status.HTTP_201_CREATED,
        trace_id=payload.trace_id,
        status_value="ok",
        data={
            "project_id": project_id,
            "message_id": message.message_id,
            "actor_id": message.actor_id,
            "actor_role": message.actor_role,
            "status": "proposed",
        },
    )
