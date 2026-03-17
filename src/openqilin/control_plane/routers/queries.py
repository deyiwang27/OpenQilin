"""Governed query router."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, status
from fastapi.responses import JSONResponse

from openqilin.control_plane.api.dependencies import (
    get_policy_runtime_client,
    get_retrieval_query_service,
    get_runtime_state_repository,
    get_task_dispatch_service,
)
from openqilin.control_plane.handlers.query_handler import map_retrieval_result
from openqilin.control_plane.identity.principal_resolver import (
    PrincipalResolutionError,
    resolve_principal,
)
from openqilin.data_access.repositories.postgres.task_repository import PostgresTaskRepository
from openqilin.data_access.repositories.runtime_state import InMemoryRuntimeStateRepository
from openqilin.policy_runtime_integration.client import PolicyRuntimeClient
from openqilin.policy_runtime_integration.fail_closed import evaluate_with_fail_closed
from openqilin.policy_runtime_integration.models import PolicyEvaluationInput
from openqilin.control_plane.schemas.queries import (
    ArtifactSearchRequest,
    QueryContractError,
    QueryContractResponse,
)
from openqilin.retrieval_runtime.models import RetrievalQueryRequest
from openqilin.retrieval_runtime.service import RetrievalQueryService
from openqilin.task_orchestrator.services.task_service import TaskDispatchService

router = APIRouter(tags=["queries"])


def _parse_project_scope(header_value: str | None) -> set[str]:
    if header_value is None:
        return set()
    return {value for value in (part.strip() for part in header_value.split(",")) if value}


def _denied_response(
    *,
    trace_id: str,
    code: str,
    message: str,
    retryable: bool,
    source_component: str,
    project_id: str,
    policy_version: str | None = None,
    policy_hash: str | None = None,
    rule_ids: list[str] | None = None,
) -> JSONResponse:
    response = QueryContractResponse(
        trace_id=trace_id,
        contract_name="search_project_artifacts",
        status="denied",
        policy_version=policy_version,
        policy_hash=policy_hash,
        rule_ids=rule_ids or [],
        error=QueryContractError(
            code=code,
            message=message,
            retryable=retryable,
            source_component=source_component,
            details={"project_id": project_id},
        ),
    )
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content=response.model_dump(),
    )


@router.post(
    "/v1/projects/{project_id}/artifacts/search",
    response_model=QueryContractResponse,
)
def search_project_artifacts(
    project_id: str,
    payload: ArtifactSearchRequest,
    retrieval_service: RetrievalQueryService = Depends(get_retrieval_query_service),
    policy_runtime_client: PolicyRuntimeClient = Depends(get_policy_runtime_client),
    trace_id_header: Annotated[str | None, Header(alias="X-Trace-Id")] = None,
    external_channel_header: Annotated[str | None, Header(alias="X-External-Channel")] = None,
    external_actor_id_header: Annotated[str | None, Header(alias="X-External-Actor-Id")] = None,
    actor_external_id_header: Annotated[
        str | None, Header(alias="X-OpenQilin-Actor-External-Id")
    ] = None,
    actor_role_header: Annotated[str | None, Header(alias="X-OpenQilin-Actor-Role")] = None,
    project_scope_header: Annotated[str | None, Header(alias="X-OpenQilin-Project-Scope")] = None,
) -> JSONResponse:
    """Execute scoped project artifact search through retrieval boundary."""

    trace_id = trace_id_header or f"trace-query-{uuid4()}"
    principal_headers = {
        "x-external-channel": external_channel_header or "",
        "x-external-actor-id": external_actor_id_header or "",
        "x-openqilin-actor-external-id": actor_external_id_header or "",
    }
    if actor_role_header is not None:
        principal_headers["x-openqilin-actor-role"] = actor_role_header
    try:
        principal = resolve_principal(principal_headers)
    except PrincipalResolutionError as error:
        return _denied_response(
            trace_id=trace_id,
            code=error.code,
            message=error.message,
            retryable=False,
            source_component="identity",
            project_id=project_id,
        )

    allowed_scopes = _parse_project_scope(project_scope_header)
    if not allowed_scopes:
        return _denied_response(
            trace_id=trace_id,
            code="query_scope_missing",
            message="missing required header: X-OpenQilin-Project-Scope",
            retryable=False,
            source_component="identity",
            project_id=project_id,
        )
    if project_id not in allowed_scopes and "*" not in allowed_scopes:
        return _denied_response(
            trace_id=trace_id,
            code="query_scope_denied",
            message="project is outside caller scope",
            retryable=False,
            source_component="policy_runtime",
            project_id=project_id,
        )

    policy_input = PolicyEvaluationInput(
        task_id=f"query-task-{uuid4()}",
        request_id=f"query-request-{uuid4()}",
        trace_id=trace_id,
        principal_id=principal.principal_id,
        principal_role=principal.principal_role,
        trust_domain=principal.trust_domain,
        connector=principal.connector,
        action="query_search_project_artifacts",
        target="artifact_search",
        recipient_types=(),
        recipient_ids=(),
        args=(payload.query, payload.artifact_type or ""),
        project_id=project_id,
    )
    policy_outcome = evaluate_with_fail_closed(policy_input, policy_runtime_client)
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
    if not policy_outcome.allowed:
        return _denied_response(
            trace_id=trace_id,
            code=policy_outcome.error_code or "query_policy_denied",
            message=policy_outcome.message,
            retryable=False,
            source_component="policy_runtime",
            project_id=project_id,
            policy_version=policy_version,
            policy_hash=policy_hash,
            rule_ids=rule_ids,
        )

    handled = map_retrieval_result(
        retrieval_service.search_project_artifacts(
            RetrievalQueryRequest(
                project_id=project_id,
                query=payload.query,
                limit=payload.limit,
                artifact_type=payload.artifact_type,
            )
        )
    )

    if handled.status == "ok":
        response = QueryContractResponse(
            trace_id=trace_id,
            contract_name="search_project_artifacts",
            status="ok",
            policy_version=policy_version,
            policy_hash=policy_hash,
            rule_ids=rule_ids,
            data={
                "project_id": project_id,
                "result_count": len(handled.hits),
                "results": [hit.model_dump() for hit in handled.hits],
            },
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=response.model_dump(),
        )

    return _denied_response(
        trace_id=trace_id,
        code=handled.error_code or "retrieval_query_denied",
        message=handled.message,
        retryable=handled.retryable,
        source_component="retrieval_runtime",
        project_id=project_id,
        policy_version=policy_version,
        policy_hash=policy_hash,
        rule_ids=rule_ids,
    )


@router.get("/v1/tasks/{task_id}")
def get_task_status(
    task_id: str,
    runtime_state_repo: InMemoryRuntimeStateRepository | PostgresTaskRepository = Depends(
        get_runtime_state_repository
    ),
    task_dispatch_service: TaskDispatchService = Depends(get_task_dispatch_service),
) -> JSONResponse:
    """Return the current status of a task by task_id.

    Used by callers to poll for the result after the HTTP handler returns 202 accepted.
    """
    task = runtime_state_repo.get_task_by_id(task_id)
    if task is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"status": "not_found", "task_id": task_id},
        )
    dispatch_outcome = task_dispatch_service.get_dispatch_outcome(task_id)
    outcome_details = dict(task.outcome_details or ())
    llm_execution: dict[str, Any] | None = None
    if dispatch_outcome is not None and dispatch_outcome.llm_metadata is not None:
        meta = dispatch_outcome.llm_metadata
        llm_execution = {
            "decision": meta.decision,
            "model_selected": meta.model_selected,
            "routing_profile": meta.routing_profile,
            "quota_limit_source": meta.quota_limit_source,
            "usage": {
                "input_tokens": meta.input_tokens,
                "output_tokens": meta.output_tokens,
                "total_tokens": meta.total_tokens,
                "request_units": meta.request_units,
            },
            "cost": {
                "estimated_cost_usd": meta.estimated_cost_usd,
                "actual_cost_usd": meta.actual_cost_usd,
                "cost_source": meta.cost_source,
            },
            "budget_usage": {
                "currency_delta_usd": meta.currency_delta_usd,
                "quota_token_units": meta.quota_token_units,
            },
            "generated_text": meta.generated_text,
            "recipient_role": meta.recipient_role,
            "recipient_id": meta.recipient_id,
            "grounding_sources": list(meta.grounding_source_ids),
        }
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "task_id": task_id,
            "trace_id": task.trace_id,
            "status": task.status,
            "principal_id": task.principal_id,
            "principal_role": task.principal_role,
            "command": task.command,
            "dispatch_target": task.dispatch_target,
            "dispatch_id": task.dispatch_id,
            "error_code": task.outcome_error_code,
            "error_message": task.outcome_message,
            "outcome_source": task.outcome_source,
            "policy_version": outcome_details.get("policy_version"),
            "policy_hash": outcome_details.get("policy_hash"),
            "rule_ids": outcome_details.get("rule_ids", "").split(",")
            if outcome_details.get("rule_ids")
            else [],
            "llm_execution": llm_execution,
        },
    )
