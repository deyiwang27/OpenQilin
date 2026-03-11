"""Retrieval runtime service boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from openqilin.data_access.read_models.artifact_search import InMemoryArtifactSearchReadModel
from openqilin.retrieval_runtime.models import (
    RetrievalArtifactHit,
    RetrievalQueryRequest,
    RetrievalQueryResult,
    RetrievalRuntimeError,
)


class ArtifactSearchReadModel(Protocol):
    """Read-model boundary for scoped artifact retrieval."""

    def search(self, request: RetrievalQueryRequest) -> tuple[RetrievalArtifactHit, ...]:
        """Execute scoped retrieval query."""


@dataclass(frozen=True, slots=True)
class RetrievalQueryService:
    """Scoped retrieval service with deterministic fail-closed mapping."""

    read_model: ArtifactSearchReadModel

    def search_project_artifacts(self, request: RetrievalQueryRequest) -> RetrievalQueryResult:
        """Execute retrieval query within project scope."""

        if not request.project_id:
            return RetrievalQueryResult(
                decision="denied",
                hits=(),
                error_code="retrieval_scope_invalid",
                message="project scope is required for retrieval query",
                retryable=False,
            )
        try:
            hits = self.read_model.search(request)
        except RetrievalRuntimeError:
            return RetrievalQueryResult(
                decision="denied",
                hits=(),
                error_code="retrieval_runtime_error_fail_closed",
                message="retrieval runtime unavailable; query denied fail-closed",
                retryable=True,
            )
        return RetrievalQueryResult(
            decision="ok",
            hits=hits,
            error_code=None,
            message="retrieval query completed",
            retryable=False,
        )


def build_retrieval_query_service() -> RetrievalQueryService:
    """Build retrieval query service with in-memory baseline read model."""

    return RetrievalQueryService(read_model=InMemoryArtifactSearchReadModel())
