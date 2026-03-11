from fastapi.testclient import TestClient

from openqilin.apps.api_app import app


def test_retrieval_query_path_returns_results_from_project_scope() -> None:
    client = TestClient(app)

    response = client.post(
        "/v1/projects/project_1/artifacts/search",
        headers={"X-Trace-Id": "trace-query-integration-1"},
        json={
            "query": "execution plan retrieval",
            "limit": 10,
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "ok"
    assert body["trace_id"] == "trace-query-integration-1"
    assert body["data"]["project_id"] == "project_1"
    result_ids = [result["artifact_id"] for result in body["data"]["results"]]
    assert "artifact_status_002" not in result_ids


def test_retrieval_query_path_denies_when_backend_uncertain_fail_closed() -> None:
    client = TestClient(app)

    response = client.post(
        "/v1/projects/project_1/artifacts/search",
        json={
            "query": "retrieval_error",
            "limit": 3,
        },
    )

    body = response.json()
    assert response.status_code == 403
    assert body["status"] == "denied"
    assert body["error"]["code"] == "retrieval_runtime_error_fail_closed"
    assert body["error"]["retryable"] is True
