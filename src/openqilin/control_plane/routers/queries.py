"""Governed query router."""

from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, status
from fastapi.responses import JSONResponse

from openqilin.control_plane.api.dependencies import get_retrieval_query_service
from openqilin.control_plane.handlers.query_handler import map_retrieval_result
from openqilin.control_plane.schemas.queries import (
    ArtifactSearchRequest,
    QueryContractError,
    QueryContractResponse,
)
from openqilin.retrieval_runtime.models import RetrievalQueryRequest
from openqilin.retrieval_runtime.service import RetrievalQueryService

router = APIRouter(tags=["queries"])


@router.post(
    "/v1/projects/{project_id}/artifacts/search",
    response_model=QueryContractResponse,
)
def search_project_artifacts(
    project_id: str,
    payload: ArtifactSearchRequest,
    retrieval_service: RetrievalQueryService = Depends(get_retrieval_query_service),
    trace_id_header: Annotated[str | None, Header(alias="X-Trace-Id")] = None,
) -> JSONResponse:
    """Execute scoped project artifact search through retrieval boundary."""

    trace_id = trace_id_header or f"trace-query-{uuid4()}"
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

    response = QueryContractResponse(
        trace_id=trace_id,
        contract_name="search_project_artifacts",
        status="denied",
        error=QueryContractError(
            code=handled.error_code or "retrieval_query_denied",
            message=handled.message,
            retryable=handled.retryable,
            source_component="retrieval_runtime",
            details={"project_id": project_id},
        ),
    )
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content=response.model_dump(),
    )
