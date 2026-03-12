"""Governance router for proposal approval and lifecycle actions."""

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
    approve_project_proposal,
    initialize_project_by_cwo,
)
from openqilin.control_plane.identity.principal_resolver import (
    PrincipalResolutionError,
    resolve_principal,
)
from openqilin.control_plane.schemas.governance import (
    GovernanceApiError,
    GovernanceApiResponse,
    ProjectInitializationRequest,
    ProposalApprovalRequest,
)
from openqilin.data_access.repositories.governance import InMemoryGovernanceRepository
from openqilin.observability.audit.audit_writer import InMemoryAuditWriter

router = APIRouter(tags=["governance"])


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
    if error.code in {"governance_approval_role_forbidden", "governance_role_forbidden"}:
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
    if error.code in {
        "governance_project_not_proposed",
        "governance_project_not_approved",
        "governance_project_already_initialized",
        "governance_approval_role_conflict",
        "governance_project_invalid_budget",
    }:
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
    "/v1/governance/projects/{project_id}/proposal/approve",
    response_model=GovernanceApiResponse,
)
def approve_proposal(
    project_id: str,
    payload: ProposalApprovalRequest,
    governance_repository: InMemoryGovernanceRepository = Depends(get_governance_repository),
    audit_writer: InMemoryAuditWriter = Depends(get_audit_writer),
    external_channel_header: Annotated[str | None, Header(alias="X-External-Channel")] = None,
    external_actor_id_header: Annotated[str | None, Header(alias="X-External-Actor-Id")] = None,
    actor_external_id_header: Annotated[
        str | None, Header(alias="X-OpenQilin-Actor-External-Id")
    ] = None,
    actor_role_header: Annotated[str | None, Header(alias="X-OpenQilin-Actor-Role")] = None,
) -> JSONResponse:
    """Record proposal approval and promote project when triad approvals complete."""

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
        outcome = approve_project_proposal(
            repository=governance_repository,
            project_id=project_id,
            actor_id=principal_id,
            actor_role=principal_role,
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
        event_type="proposal.approval",
        outcome="ok",
        trace_id=payload.trace_id,
        request_id=None,
        task_id=None,
        principal_id=principal_id,
        principal_role=principal_role,
        source="governance",
        reason_code=None,
        message="proposal approval recorded",
        payload={
            "project_id": project_id,
            "approval_recorded": str(outcome.approval_recorded).lower(),
            "approval_roles": ",".join(outcome.approval_roles),
            "status": outcome.project.status,
        },
    )
    return _governance_response(
        status_code=status.HTTP_200_OK,
        trace_id=payload.trace_id,
        status_value="ok",
        data={
            "project_id": project_id,
            "status": outcome.project.status,
            "approval_recorded": outcome.approval_recorded,
            "approval_roles": list(outcome.approval_roles),
        },
    )


@router.post(
    "/v1/governance/projects/{project_id}/initialize",
    response_model=GovernanceApiResponse,
)
def initialize_project(
    project_id: str,
    payload: ProjectInitializationRequest,
    governance_repository: InMemoryGovernanceRepository = Depends(get_governance_repository),
    audit_writer: InMemoryAuditWriter = Depends(get_audit_writer),
    external_channel_header: Annotated[str | None, Header(alias="X-External-Channel")] = None,
    external_actor_id_header: Annotated[str | None, Header(alias="X-External-Actor-Id")] = None,
    actor_external_id_header: Annotated[
        str | None, Header(alias="X-OpenQilin-Actor-External-Id")
    ] = None,
    actor_role_header: Annotated[str | None, Header(alias="X-OpenQilin-Actor-Role")] = None,
) -> JSONResponse:
    """Run CWO initialization workflow and activate approved project."""

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
        outcome = initialize_project_by_cwo(
            repository=governance_repository,
            project_id=project_id,
            actor_id=principal_id,
            actor_role=principal_role,
            trace_id=payload.trace_id,
            objective=payload.objective,
            budget_currency_total=payload.budget_currency_total,
            budget_quota_total=payload.budget_quota_total,
            metric_plan=payload.metric_plan,
            workforce_plan=payload.workforce_plan,
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
        event_type="project.initialized",
        outcome="ok",
        trace_id=payload.trace_id,
        request_id=None,
        task_id=None,
        principal_id=principal_id,
        principal_role=principal_role,
        source="governance",
        reason_code=None,
        message="cwo project initialization completed",
        payload={
            "project_id": project_id,
            "status": outcome.project.status,
            "budget_currency_total": payload.budget_currency_total,
            "budget_quota_total": payload.budget_quota_total,
        },
    )
    initialization = outcome.project.initialization
    return _governance_response(
        status_code=status.HTTP_200_OK,
        trace_id=payload.trace_id,
        status_value="ok",
        data={
            "project_id": project_id,
            "status": outcome.project.status,
            "objective": outcome.project.objective,
            "budget_currency_total": initialization.budget_currency_total
            if initialization
            else None,
            "budget_quota_total": initialization.budget_quota_total if initialization else None,
            "metric_plan": dict(initialization.metric_plan) if initialization else {},
            "workforce_plan": dict(initialization.workforce_plan) if initialization else {},
        },
    )
