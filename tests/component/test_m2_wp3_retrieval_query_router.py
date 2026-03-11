from fastapi.testclient import TestClient

from openqilin.control_plane.api.app import create_control_plane_app


def _query_headers(*, actor_id: str, project_scope: str) -> dict[str, str]:
    return {
        "X-Trace-Id": "trace-query-component-1",
        "X-External-Channel": "discord",
        "X-External-Actor-Id": actor_id,
        "X-OpenQilin-Project-Scope": project_scope,
    }


def test_search_project_artifacts_returns_scoped_results() -> None:
    client = TestClient(create_control_plane_app())

    response = client.post(
        "/v1/projects/project_1/artifacts/search",
        headers=_query_headers(actor_id="owner_query_component", project_scope="project_1"),
        json={
            "query": "retrieval status rollout",
            "limit": 5,
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "ok"
    assert body["trace_id"] == "trace-query-component-1"
    assert body["contract_name"] == "search_project_artifacts"
    assert body["data"]["project_id"] == "project_1"
    assert body["data"]["result_count"] >= 1
    assert all(result["artifact_id"].startswith("artifact_") for result in body["data"]["results"])


def test_search_project_artifacts_fail_closed_on_retrieval_runtime_error() -> None:
    client = TestClient(create_control_plane_app())

    response = client.post(
        "/v1/projects/project_1/artifacts/search",
        headers=_query_headers(actor_id="owner_query_component", project_scope="project_1"),
        json={
            "query": "retrieval_error",
            "limit": 5,
        },
    )

    body = response.json()
    assert response.status_code == 403
    assert body["status"] == "denied"
    assert body["contract_name"] == "search_project_artifacts"
    assert body["error"]["code"] == "retrieval_runtime_error_fail_closed"
    assert body["error"]["source_component"] == "retrieval_runtime"


def test_search_project_artifacts_denies_out_of_scope_project() -> None:
    client = TestClient(create_control_plane_app())

    response = client.post(
        "/v1/projects/project_2/artifacts/search",
        headers=_query_headers(actor_id="owner_query_component", project_scope="project_1"),
        json={"query": "status", "limit": 5},
    )

    body = response.json()
    assert response.status_code == 403
    assert body["status"] == "denied"
    assert body["error"]["code"] == "query_scope_denied"
    assert body["error"]["source_component"] == "policy_runtime"
