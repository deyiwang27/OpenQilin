"""Governance router for proposal approval and lifecycle actions."""

from __future__ import annotations

from string import hexdigits
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, status
from fastapi.responses import JSONResponse

from openqilin.control_plane.api.dependencies import (
    get_audit_writer,
    get_governance_repository,
)
from openqilin.control_plane.handlers.governance_handler import (
    GovernanceHandlerError,
    archive_project_by_governance,
    approve_project_proposal,
    bind_workforce_template_by_cwo,
    create_project_proposal,
    finalize_project_completion_by_c_suite,
    initialize_project_by_cwo,
    pause_project_by_governance,
    record_completion_approval_by_c_suite,
    resume_project_by_governance,
    submit_completion_report_by_project_manager,
    terminate_project_by_governance,
)
from openqilin.control_plane.identity.connector_security import (
    ConnectorSecurityError,
    validate_connector_auth,
)
from openqilin.control_plane.identity.principal_resolver import (
    PrincipalResolutionError,
    resolve_principal,
)
from openqilin.control_plane.schemas.governance import (
    GovernanceApiError,
    GovernanceApiResponse,
    ProjectCompletionApprovalRequest,
    ProjectCompletionFinalizeRequest,
    ProjectCompletionReportRequest,
    ProjectCreateRequest,
    ProjectInitializationRequest,
    ProjectLifecycleActionRequest,
    ProposalApprovalRequest,
    WorkforceTemplateBindingRequest,
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


def _validate_connector_headers(
    *,
    external_channel_header: str | None,
    external_actor_id_header: str | None,
    actor_external_id_header: str | None,
    idempotency_key_header: str | None,
    signature_header: str | None,
    raw_payload_hash_header: str | None,
) -> GovernanceApiError | None:
    if external_channel_header is None or not external_channel_header.strip():
        return GovernanceApiError(
            code="connector_missing_header",
            message="missing required header: X-External-Channel",
            retryable=False,
            source_component="connector_security",
            details={"required_header": "X-External-Channel"},
        )
    if external_actor_id_header is None or not external_actor_id_header.strip():
        return GovernanceApiError(
            code="connector_missing_header",
            message="missing required header: X-External-Actor-Id",
            retryable=False,
            source_component="connector_security",
            details={"required_header": "X-External-Actor-Id"},
        )
    if idempotency_key_header is None or not idempotency_key_header.strip():
        return GovernanceApiError(
            code="idempotency_missing_header",
            message="missing required header: X-Idempotency-Key",
            retryable=False,
            source_component="connector_security",
            details={"required_header": "X-Idempotency-Key"},
        )
    if raw_payload_hash_header is None or not raw_payload_hash_header.strip():
        return GovernanceApiError(
            code="connector_missing_header",
            message="missing required header: X-OpenQilin-Raw-Payload-Hash",
            retryable=False,
            source_component="connector_security",
            details={"required_header": "X-OpenQilin-Raw-Payload-Hash"},
        )
    normalized_hash = raw_payload_hash_header.strip().lower()
    if (
        len(normalized_hash) < 64
        or len(normalized_hash) > 128
        or any(character not in hexdigits for character in normalized_hash)
    ):
        return GovernanceApiError(
            code="connector_payload_hash_invalid",
            message="invalid raw payload hash header format",
            retryable=False,
            source_component="connector_security",
            details={"required_header": "X-OpenQilin-Raw-Payload-Hash"},
        )
    if signature_header is None or not signature_header.strip():
        return GovernanceApiError(
            code="connector_signature_missing",
            message="missing required header: X-OpenQilin-Signature",
            retryable=False,
            source_component="connector_security",
            details={"required_header": "X-OpenQilin-Signature"},
        )

    payload_actor_external_id = (
        actor_external_id_header.strip()
        if actor_external_id_header is not None and actor_external_id_header.strip()
        else external_actor_id_header.strip()
    )
    try:
        validate_connector_auth(
            header_channel=external_channel_header,
            header_actor_external_id=external_actor_id_header,
            header_idempotency_key=idempotency_key_header,
            header_signature=signature_header,
            payload_channel=external_channel_header.strip(),
            payload_actor_external_id=payload_actor_external_id,
            payload_idempotency_key=idempotency_key_header.strip(),
            payload_raw_payload_hash=normalized_hash,
        )
    except ConnectorSecurityError as error:
        return GovernanceApiError(
            code=error.code,
            message=error.message,
            retryable=False,
            source_component="connector_security",
            details={},
        )
    return None


def _map_handler_error(
    error: GovernanceHandlerError,
) -> tuple[int, GovernanceApiError, Literal["denied", "error"]]:
    if error.code in {"governance_approval_role_forbidden", "governance_role_forbidden"} or (
        error.code.endswith("_role_forbidden")
    ):
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
        "governance_project_not_active",
        "governance_project_already_initialized",
        "governance_approval_role_conflict",
        "governance_project_manager_binding_exists",
        "governance_workforce_role_invalid",
        "governance_project_invalid_budget",
        "governance_project_artifact_persistence_failed",
        "governance_project_artifact_integrity_failed",
        "governance_project_artifact_policy_denied",
        "governance_project_manager_template_invalid",
        "governance_project_manager_template_missing_operations",
        "governance_project_exists",
        "governance_project_invalid_create_state",
        "governance_project_completion_report_exists",
        "governance_completion_approval_role_conflict",
        "governance_project_completion_report_missing",
        "governance_project_completion_approval_missing",
        "governance_project_completion_owner_notification_missing",
        "project_invalid_transition",
        "project_invalid_status",
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
    "/v1/governance/projects",
    response_model=GovernanceApiResponse,
)
def create_project(
    payload: ProjectCreateRequest,
    governance_repository: InMemoryGovernanceRepository = Depends(get_governance_repository),
    audit_writer: InMemoryAuditWriter = Depends(get_audit_writer),
    external_channel_header: Annotated[str | None, Header(alias="X-External-Channel")] = None,
    external_actor_id_header: Annotated[str | None, Header(alias="X-External-Actor-Id")] = None,
    actor_external_id_header: Annotated[
        str | None, Header(alias="X-OpenQilin-Actor-External-Id")
    ] = None,
    actor_role_header: Annotated[str | None, Header(alias="X-OpenQilin-Actor-Role")] = None,
    idempotency_key_header: Annotated[str | None, Header(alias="X-Idempotency-Key")] = None,
    signature_header: Annotated[str | None, Header(alias="X-OpenQilin-Signature")] = None,
    raw_payload_hash_header: Annotated[
        str | None, Header(alias="X-OpenQilin-Raw-Payload-Hash")
    ] = None,
) -> JSONResponse:
    """Create proposal-stage project record through governed API path."""

    connector_error = _validate_connector_headers(
        external_channel_header=external_channel_header,
        external_actor_id_header=external_actor_id_header,
        actor_external_id_header=actor_external_id_header,
        idempotency_key_header=idempotency_key_header,
        signature_header=signature_header,
        raw_payload_hash_header=raw_payload_hash_header,
    )
    if connector_error is not None:
        return _governance_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            trace_id=payload.trace_id,
            status_value="error",
            error=connector_error,
        )

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
        outcome = create_project_proposal(
            repository=governance_repository,
            actor_id=principal_id,
            actor_role=principal_role,
            trace_id=payload.trace_id,
            name=payload.name,
            objective=payload.objective,
            project_id=payload.project_id,
            metadata=payload.metadata,
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
        event_type="project.created",
        outcome="ok",
        trace_id=payload.trace_id,
        request_id=None,
        task_id=None,
        principal_id=principal_id,
        principal_role=principal_role,
        source="governance",
        reason_code=None,
        message="proposal-stage project created",
        payload={
            "project_id": outcome.project.project_id,
            "status": outcome.project.status,
            "creator_role": principal_role,
        },
    )
    return _governance_response(
        status_code=status.HTTP_201_CREATED,
        trace_id=payload.trace_id,
        status_value="ok",
        data={
            "project_id": outcome.project.project_id,
            "name": outcome.project.name,
            "objective": outcome.project.objective,
            "status": outcome.project.status,
            "metadata": dict(outcome.project.metadata),
        },
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
    idempotency_key_header: Annotated[str | None, Header(alias="X-Idempotency-Key")] = None,
    signature_header: Annotated[str | None, Header(alias="X-OpenQilin-Signature")] = None,
    raw_payload_hash_header: Annotated[
        str | None, Header(alias="X-OpenQilin-Raw-Payload-Hash")
    ] = None,
) -> JSONResponse:
    """Record proposal approval and promote project when triad approvals complete."""

    connector_error = _validate_connector_headers(
        external_channel_header=external_channel_header,
        external_actor_id_header=external_actor_id_header,
        actor_external_id_header=actor_external_id_header,
        idempotency_key_header=idempotency_key_header,
        signature_header=signature_header,
        raw_payload_hash_header=raw_payload_hash_header,
    )
    if connector_error is not None:
        return _governance_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            trace_id=payload.trace_id,
            status_value="error",
            error=connector_error,
        )

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
    idempotency_key_header: Annotated[str | None, Header(alias="X-Idempotency-Key")] = None,
    signature_header: Annotated[str | None, Header(alias="X-OpenQilin-Signature")] = None,
    raw_payload_hash_header: Annotated[
        str | None, Header(alias="X-OpenQilin-Raw-Payload-Hash")
    ] = None,
) -> JSONResponse:
    """Run CWO initialization workflow and activate approved project."""

    connector_error = _validate_connector_headers(
        external_channel_header=external_channel_header,
        external_actor_id_header=external_actor_id_header,
        actor_external_id_header=actor_external_id_header,
        idempotency_key_header=idempotency_key_header,
        signature_header=signature_header,
        raw_payload_hash_header=raw_payload_hash_header,
    )
    if connector_error is not None:
        return _governance_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            trace_id=payload.trace_id,
            status_value="error",
            error=connector_error,
        )

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
            "charter_storage_uri": initialization.charter_storage_uri if initialization else None,
            "charter_content_hash": initialization.charter_content_hash if initialization else None,
            "scope_statement_storage_uri": initialization.scope_statement_storage_uri
            if initialization
            else None,
            "scope_statement_content_hash": initialization.scope_statement_content_hash
            if initialization
            else None,
            "budget_plan_storage_uri": initialization.budget_plan_storage_uri
            if initialization
            else None,
            "budget_plan_content_hash": initialization.budget_plan_content_hash
            if initialization
            else None,
            "metric_plan_storage_uri": initialization.metric_plan_storage_uri
            if initialization
            else None,
            "metric_plan_content_hash": initialization.metric_plan_content_hash
            if initialization
            else None,
            "workforce_plan_storage_uri": initialization.workforce_plan_storage_uri
            if initialization
            else None,
            "workforce_plan_content_hash": initialization.workforce_plan_content_hash
            if initialization
            else None,
            "execution_plan_storage_uri": initialization.execution_plan_storage_uri
            if initialization
            else None,
            "execution_plan_content_hash": initialization.execution_plan_content_hash
            if initialization
            else None,
        },
    )


@router.post(
    "/v1/governance/projects/{project_id}/workforce/bind",
    response_model=GovernanceApiResponse,
)
def bind_workforce_template(
    project_id: str,
    payload: WorkforceTemplateBindingRequest,
    governance_repository: InMemoryGovernanceRepository = Depends(get_governance_repository),
    audit_writer: InMemoryAuditWriter = Depends(get_audit_writer),
    external_channel_header: Annotated[str | None, Header(alias="X-External-Channel")] = None,
    external_actor_id_header: Annotated[str | None, Header(alias="X-External-Actor-Id")] = None,
    actor_external_id_header: Annotated[
        str | None, Header(alias="X-OpenQilin-Actor-External-Id")
    ] = None,
    actor_role_header: Annotated[str | None, Header(alias="X-OpenQilin-Actor-Role")] = None,
    idempotency_key_header: Annotated[str | None, Header(alias="X-Idempotency-Key")] = None,
    signature_header: Annotated[str | None, Header(alias="X-OpenQilin-Signature")] = None,
    raw_payload_hash_header: Annotated[
        str | None, Header(alias="X-OpenQilin-Raw-Payload-Hash")
    ] = None,
) -> JSONResponse:
    """Bind workforce template package for Project Manager or declared-disabled Domain Leader."""

    connector_error = _validate_connector_headers(
        external_channel_header=external_channel_header,
        external_actor_id_header=external_actor_id_header,
        actor_external_id_header=actor_external_id_header,
        idempotency_key_header=idempotency_key_header,
        signature_header=signature_header,
        raw_payload_hash_header=raw_payload_hash_header,
    )
    if connector_error is not None:
        return _governance_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            trace_id=payload.trace_id,
            status_value="error",
            error=connector_error,
        )

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
        outcome = bind_workforce_template_by_cwo(
            repository=governance_repository,
            project_id=project_id,
            actor_id=principal_id,
            actor_role=principal_role,
            trace_id=payload.trace_id,
            role=payload.role,
            template_id=payload.template_id,
            llm_routing_profile=payload.llm_routing_profile,
            system_prompt=payload.system_prompt,
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
        event_type="workforce.binding",
        outcome="ok",
        trace_id=payload.trace_id,
        request_id=None,
        task_id=None,
        principal_id=principal_id,
        principal_role=principal_role,
        source="governance",
        reason_code=None,
        message="workforce template binding recorded",
        payload={
            "project_id": project_id,
            "role": outcome.role,
            "binding_status": outcome.binding_status,
            "template_id": outcome.template_id,
            "llm_routing_profile": outcome.llm_routing_profile,
            "mandatory_operations": ",".join(outcome.mandatory_operations),
        },
    )
    return _governance_response(
        status_code=status.HTTP_200_OK,
        trace_id=payload.trace_id,
        status_value="ok",
        data={
            "project_id": project_id,
            "status": outcome.project.status,
            "role": outcome.role,
            "binding_status": outcome.binding_status,
            "template_id": outcome.template_id,
            "llm_routing_profile": outcome.llm_routing_profile,
            "system_prompt_hash": outcome.system_prompt_hash,
            "mandatory_operations": list(outcome.mandatory_operations),
        },
    )


@router.post(
    "/v1/governance/projects/{project_id}/completion/report",
    response_model=GovernanceApiResponse,
)
def submit_completion_report(
    project_id: str,
    payload: ProjectCompletionReportRequest,
    governance_repository: InMemoryGovernanceRepository = Depends(get_governance_repository),
    audit_writer: InMemoryAuditWriter = Depends(get_audit_writer),
    external_channel_header: Annotated[str | None, Header(alias="X-External-Channel")] = None,
    external_actor_id_header: Annotated[str | None, Header(alias="X-External-Actor-Id")] = None,
    actor_external_id_header: Annotated[
        str | None, Header(alias="X-OpenQilin-Actor-External-Id")
    ] = None,
    actor_role_header: Annotated[str | None, Header(alias="X-OpenQilin-Actor-Role")] = None,
    idempotency_key_header: Annotated[str | None, Header(alias="X-Idempotency-Key")] = None,
    signature_header: Annotated[str | None, Header(alias="X-OpenQilin-Signature")] = None,
    raw_payload_hash_header: Annotated[
        str | None, Header(alias="X-OpenQilin-Raw-Payload-Hash")
    ] = None,
) -> JSONResponse:
    """Submit completion report under Project Manager governance contract."""

    connector_error = _validate_connector_headers(
        external_channel_header=external_channel_header,
        external_actor_id_header=external_actor_id_header,
        actor_external_id_header=actor_external_id_header,
        idempotency_key_header=idempotency_key_header,
        signature_header=signature_header,
        raw_payload_hash_header=raw_payload_hash_header,
    )
    if connector_error is not None:
        return _governance_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            trace_id=payload.trace_id,
            status_value="error",
            error=connector_error,
        )

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
        outcome = submit_completion_report_by_project_manager(
            repository=governance_repository,
            project_id=project_id,
            actor_id=principal_id,
            actor_role=principal_role,
            trace_id=payload.trace_id,
            summary=payload.summary,
            metric_results=payload.metric_results,
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
        event_type="project.completion_report",
        outcome="ok",
        trace_id=payload.trace_id,
        request_id=None,
        task_id=None,
        principal_id=principal_id,
        principal_role=principal_role,
        source="governance",
        reason_code=None,
        message="project completion report submitted",
        payload={
            "project_id": project_id,
            "report_id": outcome.report.report_id,
            "status": outcome.project.status,
        },
    )
    return _governance_response(
        status_code=status.HTTP_201_CREATED,
        trace_id=payload.trace_id,
        status_value="ok",
        data={
            "project_id": project_id,
            "status": outcome.project.status,
            "report_id": outcome.report.report_id,
            "summary": outcome.report.summary,
            "completion_report_storage_uri": outcome.report.completion_report_storage_uri,
            "completion_report_content_hash": outcome.report.completion_report_content_hash,
        },
    )


@router.post(
    "/v1/governance/projects/{project_id}/completion/approve",
    response_model=GovernanceApiResponse,
)
def approve_completion(
    project_id: str,
    payload: ProjectCompletionApprovalRequest,
    governance_repository: InMemoryGovernanceRepository = Depends(get_governance_repository),
    audit_writer: InMemoryAuditWriter = Depends(get_audit_writer),
    external_channel_header: Annotated[str | None, Header(alias="X-External-Channel")] = None,
    external_actor_id_header: Annotated[str | None, Header(alias="X-External-Actor-Id")] = None,
    actor_external_id_header: Annotated[
        str | None, Header(alias="X-OpenQilin-Actor-External-Id")
    ] = None,
    actor_role_header: Annotated[str | None, Header(alias="X-OpenQilin-Actor-Role")] = None,
    idempotency_key_header: Annotated[str | None, Header(alias="X-Idempotency-Key")] = None,
    signature_header: Annotated[str | None, Header(alias="X-OpenQilin-Signature")] = None,
    raw_payload_hash_header: Annotated[
        str | None, Header(alias="X-OpenQilin-Raw-Payload-Hash")
    ] = None,
) -> JSONResponse:
    """Record CWO/CEO completion approval and owner-notification evidence."""

    connector_error = _validate_connector_headers(
        external_channel_header=external_channel_header,
        external_actor_id_header=external_actor_id_header,
        actor_external_id_header=actor_external_id_header,
        idempotency_key_header=idempotency_key_header,
        signature_header=signature_header,
        raw_payload_hash_header=raw_payload_hash_header,
    )
    if connector_error is not None:
        return _governance_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            trace_id=payload.trace_id,
            status_value="error",
            error=connector_error,
        )

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
        outcome = record_completion_approval_by_c_suite(
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
        event_type="project.completion_approval",
        outcome="ok",
        trace_id=payload.trace_id,
        request_id=None,
        task_id=None,
        principal_id=principal_id,
        principal_role=principal_role,
        source="governance",
        reason_code=None,
        message="project completion approval recorded",
        payload={
            "project_id": project_id,
            "approval_recorded": str(outcome.approval_recorded).lower(),
            "approval_roles": ",".join(outcome.approval_roles),
            "owner_notified": str(outcome.owner_notified).lower(),
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
            "owner_notified": outcome.owner_notified,
        },
    )


@router.post(
    "/v1/governance/projects/{project_id}/completion/finalize",
    response_model=GovernanceApiResponse,
)
def finalize_completion(
    project_id: str,
    payload: ProjectCompletionFinalizeRequest,
    governance_repository: InMemoryGovernanceRepository = Depends(get_governance_repository),
    audit_writer: InMemoryAuditWriter = Depends(get_audit_writer),
    external_channel_header: Annotated[str | None, Header(alias="X-External-Channel")] = None,
    external_actor_id_header: Annotated[str | None, Header(alias="X-External-Actor-Id")] = None,
    actor_external_id_header: Annotated[
        str | None, Header(alias="X-OpenQilin-Actor-External-Id")
    ] = None,
    actor_role_header: Annotated[str | None, Header(alias="X-OpenQilin-Actor-Role")] = None,
    idempotency_key_header: Annotated[str | None, Header(alias="X-Idempotency-Key")] = None,
    signature_header: Annotated[str | None, Header(alias="X-OpenQilin-Signature")] = None,
    raw_payload_hash_header: Annotated[
        str | None, Header(alias="X-OpenQilin-Raw-Payload-Hash")
    ] = None,
) -> JSONResponse:
    """Finalize project completion transition after report and approvals are in place."""

    connector_error = _validate_connector_headers(
        external_channel_header=external_channel_header,
        external_actor_id_header=external_actor_id_header,
        actor_external_id_header=actor_external_id_header,
        idempotency_key_header=idempotency_key_header,
        signature_header=signature_header,
        raw_payload_hash_header=raw_payload_hash_header,
    )
    if connector_error is not None:
        return _governance_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            trace_id=payload.trace_id,
            status_value="error",
            error=connector_error,
        )

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
        outcome = finalize_project_completion_by_c_suite(
            repository=governance_repository,
            project_id=project_id,
            actor_role=principal_role,
            trace_id=payload.trace_id,
            reason_code=payload.reason_code,
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
        event_type="project.completed",
        outcome="ok",
        trace_id=payload.trace_id,
        request_id=None,
        task_id=None,
        principal_id=principal_id,
        principal_role=principal_role,
        source="governance",
        reason_code=payload.reason_code,
        message="project completion finalized",
        payload={
            "project_id": project_id,
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
        },
    )


@router.post(
    "/v1/governance/projects/{project_id}/lifecycle/pause",
    response_model=GovernanceApiResponse,
)
def pause_project(
    project_id: str,
    payload: ProjectLifecycleActionRequest,
    governance_repository: InMemoryGovernanceRepository = Depends(get_governance_repository),
    audit_writer: InMemoryAuditWriter = Depends(get_audit_writer),
    external_channel_header: Annotated[str | None, Header(alias="X-External-Channel")] = None,
    external_actor_id_header: Annotated[str | None, Header(alias="X-External-Actor-Id")] = None,
    actor_external_id_header: Annotated[
        str | None, Header(alias="X-OpenQilin-Actor-External-Id")
    ] = None,
    actor_role_header: Annotated[str | None, Header(alias="X-OpenQilin-Actor-Role")] = None,
    idempotency_key_header: Annotated[str | None, Header(alias="X-Idempotency-Key")] = None,
    signature_header: Annotated[str | None, Header(alias="X-OpenQilin-Signature")] = None,
    raw_payload_hash_header: Annotated[
        str | None, Header(alias="X-OpenQilin-Raw-Payload-Hash")
    ] = None,
) -> JSONResponse:
    """Pause one active project through governed lifecycle API."""

    connector_error = _validate_connector_headers(
        external_channel_header=external_channel_header,
        external_actor_id_header=external_actor_id_header,
        actor_external_id_header=actor_external_id_header,
        idempotency_key_header=idempotency_key_header,
        signature_header=signature_header,
        raw_payload_hash_header=raw_payload_hash_header,
    )
    if connector_error is not None:
        return _governance_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            trace_id=payload.trace_id,
            status_value="error",
            error=connector_error,
        )
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
        outcome = pause_project_by_governance(
            repository=governance_repository,
            project_id=project_id,
            actor_role=principal_role,
            trace_id=payload.trace_id,
            reason_code=payload.reason_code,
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
        event_type="project.paused",
        outcome="ok",
        trace_id=payload.trace_id,
        request_id=None,
        task_id=None,
        principal_id=principal_id,
        principal_role=principal_role,
        source="governance",
        reason_code=payload.reason_code,
        message="project paused through governed lifecycle API",
        payload={
            "project_id": project_id,
            "previous_status": outcome.previous_status,
            "status": outcome.project.status,
        },
    )
    return _governance_response(
        status_code=status.HTTP_200_OK,
        trace_id=payload.trace_id,
        status_value="ok",
        data={
            "project_id": project_id,
            "previous_status": outcome.previous_status,
            "status": outcome.project.status,
            "reason_code": payload.reason_code,
        },
    )


@router.post(
    "/v1/governance/projects/{project_id}/lifecycle/resume",
    response_model=GovernanceApiResponse,
)
def resume_project(
    project_id: str,
    payload: ProjectLifecycleActionRequest,
    governance_repository: InMemoryGovernanceRepository = Depends(get_governance_repository),
    audit_writer: InMemoryAuditWriter = Depends(get_audit_writer),
    external_channel_header: Annotated[str | None, Header(alias="X-External-Channel")] = None,
    external_actor_id_header: Annotated[str | None, Header(alias="X-External-Actor-Id")] = None,
    actor_external_id_header: Annotated[
        str | None, Header(alias="X-OpenQilin-Actor-External-Id")
    ] = None,
    actor_role_header: Annotated[str | None, Header(alias="X-OpenQilin-Actor-Role")] = None,
    idempotency_key_header: Annotated[str | None, Header(alias="X-Idempotency-Key")] = None,
    signature_header: Annotated[str | None, Header(alias="X-OpenQilin-Signature")] = None,
    raw_payload_hash_header: Annotated[
        str | None, Header(alias="X-OpenQilin-Raw-Payload-Hash")
    ] = None,
) -> JSONResponse:
    """Resume one paused project through governed lifecycle API."""

    connector_error = _validate_connector_headers(
        external_channel_header=external_channel_header,
        external_actor_id_header=external_actor_id_header,
        actor_external_id_header=actor_external_id_header,
        idempotency_key_header=idempotency_key_header,
        signature_header=signature_header,
        raw_payload_hash_header=raw_payload_hash_header,
    )
    if connector_error is not None:
        return _governance_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            trace_id=payload.trace_id,
            status_value="error",
            error=connector_error,
        )
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
        outcome = resume_project_by_governance(
            repository=governance_repository,
            project_id=project_id,
            actor_role=principal_role,
            trace_id=payload.trace_id,
            reason_code=payload.reason_code,
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
        event_type="project.resumed",
        outcome="ok",
        trace_id=payload.trace_id,
        request_id=None,
        task_id=None,
        principal_id=principal_id,
        principal_role=principal_role,
        source="governance",
        reason_code=payload.reason_code,
        message="project resumed through governed lifecycle API",
        payload={
            "project_id": project_id,
            "previous_status": outcome.previous_status,
            "status": outcome.project.status,
        },
    )
    return _governance_response(
        status_code=status.HTTP_200_OK,
        trace_id=payload.trace_id,
        status_value="ok",
        data={
            "project_id": project_id,
            "previous_status": outcome.previous_status,
            "status": outcome.project.status,
            "reason_code": payload.reason_code,
        },
    )


@router.post(
    "/v1/governance/projects/{project_id}/lifecycle/terminate",
    response_model=GovernanceApiResponse,
)
def terminate_project(
    project_id: str,
    payload: ProjectLifecycleActionRequest,
    governance_repository: InMemoryGovernanceRepository = Depends(get_governance_repository),
    audit_writer: InMemoryAuditWriter = Depends(get_audit_writer),
    external_channel_header: Annotated[str | None, Header(alias="X-External-Channel")] = None,
    external_actor_id_header: Annotated[str | None, Header(alias="X-External-Actor-Id")] = None,
    actor_external_id_header: Annotated[
        str | None, Header(alias="X-OpenQilin-Actor-External-Id")
    ] = None,
    actor_role_header: Annotated[str | None, Header(alias="X-OpenQilin-Actor-Role")] = None,
    idempotency_key_header: Annotated[str | None, Header(alias="X-Idempotency-Key")] = None,
    signature_header: Annotated[str | None, Header(alias="X-OpenQilin-Signature")] = None,
    raw_payload_hash_header: Annotated[
        str | None, Header(alias="X-OpenQilin-Raw-Payload-Hash")
    ] = None,
) -> JSONResponse:
    """Terminate one active or paused project through governed lifecycle API."""

    connector_error = _validate_connector_headers(
        external_channel_header=external_channel_header,
        external_actor_id_header=external_actor_id_header,
        actor_external_id_header=actor_external_id_header,
        idempotency_key_header=idempotency_key_header,
        signature_header=signature_header,
        raw_payload_hash_header=raw_payload_hash_header,
    )
    if connector_error is not None:
        return _governance_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            trace_id=payload.trace_id,
            status_value="error",
            error=connector_error,
        )
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
        outcome = terminate_project_by_governance(
            repository=governance_repository,
            project_id=project_id,
            actor_role=principal_role,
            trace_id=payload.trace_id,
            reason_code=payload.reason_code,
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
        event_type="project.terminated",
        outcome="ok",
        trace_id=payload.trace_id,
        request_id=None,
        task_id=None,
        principal_id=principal_id,
        principal_role=principal_role,
        source="governance",
        reason_code=payload.reason_code,
        message="project terminated through governed lifecycle API",
        payload={
            "project_id": project_id,
            "previous_status": outcome.previous_status,
            "status": outcome.project.status,
        },
    )
    return _governance_response(
        status_code=status.HTTP_200_OK,
        trace_id=payload.trace_id,
        status_value="ok",
        data={
            "project_id": project_id,
            "previous_status": outcome.previous_status,
            "status": outcome.project.status,
            "reason_code": payload.reason_code,
        },
    )


@router.post(
    "/v1/governance/projects/{project_id}/lifecycle/archive",
    response_model=GovernanceApiResponse,
)
def archive_project(
    project_id: str,
    payload: ProjectLifecycleActionRequest,
    governance_repository: InMemoryGovernanceRepository = Depends(get_governance_repository),
    audit_writer: InMemoryAuditWriter = Depends(get_audit_writer),
    external_channel_header: Annotated[str | None, Header(alias="X-External-Channel")] = None,
    external_actor_id_header: Annotated[str | None, Header(alias="X-External-Actor-Id")] = None,
    actor_external_id_header: Annotated[
        str | None, Header(alias="X-OpenQilin-Actor-External-Id")
    ] = None,
    actor_role_header: Annotated[str | None, Header(alias="X-OpenQilin-Actor-Role")] = None,
    idempotency_key_header: Annotated[str | None, Header(alias="X-Idempotency-Key")] = None,
    signature_header: Annotated[str | None, Header(alias="X-OpenQilin-Signature")] = None,
    raw_payload_hash_header: Annotated[
        str | None, Header(alias="X-OpenQilin-Raw-Payload-Hash")
    ] = None,
) -> JSONResponse:
    """Archive one completed or terminated project through governed lifecycle API."""

    connector_error = _validate_connector_headers(
        external_channel_header=external_channel_header,
        external_actor_id_header=external_actor_id_header,
        actor_external_id_header=actor_external_id_header,
        idempotency_key_header=idempotency_key_header,
        signature_header=signature_header,
        raw_payload_hash_header=raw_payload_hash_header,
    )
    if connector_error is not None:
        return _governance_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            trace_id=payload.trace_id,
            status_value="error",
            error=connector_error,
        )
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
        outcome = archive_project_by_governance(
            repository=governance_repository,
            project_id=project_id,
            actor_role=principal_role,
            trace_id=payload.trace_id,
            reason_code=payload.reason_code,
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
        event_type="project.archived",
        outcome="ok",
        trace_id=payload.trace_id,
        request_id=None,
        task_id=None,
        principal_id=principal_id,
        principal_role=principal_role,
        source="governance",
        reason_code=payload.reason_code,
        message="project archived through governed lifecycle API",
        payload={
            "project_id": project_id,
            "previous_status": outcome.previous_status,
            "status": outcome.project.status,
        },
    )
    return _governance_response(
        status_code=status.HTTP_200_OK,
        trace_id=payload.trace_id,
        status_value="ok",
        data={
            "project_id": project_id,
            "previous_status": outcome.previous_status,
            "status": outcome.project.status,
            "reason_code": payload.reason_code,
        },
    )
