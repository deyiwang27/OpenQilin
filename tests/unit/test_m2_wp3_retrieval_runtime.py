from openqilin.retrieval_runtime.models import (
    RetrievalArtifactHit,
    RetrievalQueryRequest,
    RetrievalRuntimeError,
)
from openqilin.retrieval_runtime.service import RetrievalQueryService


# ---------------------------------------------------------------------------
# Simulated read model for unit tests
# ---------------------------------------------------------------------------

_SEED_HITS: tuple[RetrievalArtifactHit, ...] = (
    RetrievalArtifactHit(
        project_id="project_1",
        artifact_id="art-001",
        artifact_type="project_charter",
        title="Retrieval Status Rollout Charter",
        snippet="retrieval status rollout plan",
        source_ref="projects/project_1/docs/project_charter--v001.md",
        score=0.95,
    ),
    RetrievalArtifactHit(
        project_id="project_2",
        artifact_id="art-002",
        artifact_type="success_metrics",
        title="Project Status Metrics",
        snippet="status project success criteria",
        source_ref="projects/project_2/docs/success_metrics--v001.md",
        score=0.88,
    ),
)


class _SimulatedArtifactSearchReadModel:
    """Deterministic read model with seeded hits for unit tests."""

    def search(self, request: RetrievalQueryRequest) -> tuple[RetrievalArtifactHit, ...]:
        if "retrieval_error" in request.query:
            raise RetrievalRuntimeError(
                code="retrieval_backend_unavailable",
                message="simulated retrieval backend error",
                retryable=True,
            )
        return tuple(hit for hit in _SEED_HITS if hit.project_id == request.project_id)


def _build_service() -> RetrievalQueryService:
    return RetrievalQueryService(read_model=_SimulatedArtifactSearchReadModel())


def test_retrieval_query_returns_scoped_hits() -> None:
    service = _build_service()

    result = service.search_project_artifacts(
        RetrievalQueryRequest(
            project_id="project_1",
            query="retrieval status rollout",
            limit=5,
        )
    )

    assert result.decision == "ok"
    assert result.error_code is None
    assert result.hits
    assert {hit.project_id for hit in result.hits} == {"project_1"}


def test_retrieval_query_fail_closed_on_runtime_error() -> None:
    service = _build_service()

    result = service.search_project_artifacts(
        RetrievalQueryRequest(
            project_id="project_1",
            query="retrieval_error",
            limit=5,
        )
    )

    assert result.decision == "denied"
    assert result.error_code == "retrieval_runtime_error_fail_closed"
    assert result.retryable is True
    assert result.hits == ()


def test_retrieval_query_applies_project_scope_even_on_common_terms() -> None:
    service = _build_service()

    result = service.search_project_artifacts(
        RetrievalQueryRequest(
            project_id="project_2",
            query="status project",
            limit=5,
        )
    )

    assert result.decision == "ok"
    assert result.hits
    assert {hit.project_id for hit in result.hits} == {"project_2"}


class _UnexpectedReadModel:
    def search(self, request: RetrievalQueryRequest) -> tuple[RetrievalArtifactHit, ...]:
        raise RuntimeError(f"unexpected failure for {request.project_id}")


def test_retrieval_query_fail_closed_on_unexpected_runtime_error() -> None:
    service = RetrievalQueryService(read_model=_UnexpectedReadModel())

    result = service.search_project_artifacts(
        RetrievalQueryRequest(
            project_id="project_1",
            query="status",
            limit=3,
        )
    )

    assert result.decision == "denied"
    assert result.error_code == "retrieval_runtime_unexpected_fail_closed"
    assert result.retryable is False
