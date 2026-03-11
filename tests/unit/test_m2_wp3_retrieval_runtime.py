from openqilin.retrieval_runtime.models import RetrievalQueryRequest
from openqilin.retrieval_runtime.service import build_retrieval_query_service


def test_retrieval_query_returns_scoped_hits() -> None:
    service = build_retrieval_query_service()

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
    service = build_retrieval_query_service()

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
    service = build_retrieval_query_service()

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
