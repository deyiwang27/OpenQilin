from fastapi.testclient import TestClient

from openqilin.control_plane.api.app import create_control_plane_app


def _query_headers(*, actor_id: str, project_scope: str, trace_id: str) -> dict[str, str]:
    return {
        "X-Trace-Id": trace_id,
        "X-External-Channel": "discord",
        "X-External-Actor-Id": actor_id,
        "X-OpenQilin-Project-Scope": project_scope,
    }


def test_query_contract_ok_response_shape() -> None:
    client = TestClient(create_control_plane_app())

    response = client.post(
        "/v1/projects/project_1/artifacts/search",
        headers=_query_headers(
            actor_id="owner_contract_query_1",
            project_scope="project_1",
            trace_id="trace-contract-query-ok",
        ),
        json={"query": "retrieval status", "limit": 5},
    )

    body = response.json()
    assert response.status_code == 200
    assert set(body.keys()) == {
        "trace_id",
        "contract_name",
        "status",
        "policy_version",
        "policy_hash",
        "rule_ids",
        "data",
        "error",
    }
    assert body["status"] == "ok"
    assert body["contract_name"] == "search_project_artifacts"
    assert isinstance(body["policy_version"], str) and body["policy_version"]
    assert isinstance(body["policy_hash"], str) and body["policy_hash"]
    assert isinstance(body["rule_ids"], list)
    assert body["error"] is None

    data = body["data"]
    assert data["project_id"] == "project_1"
    assert isinstance(data["result_count"], int)
    assert isinstance(data["results"], list)


def test_query_contract_denied_response_shape() -> None:
    client = TestClient(create_control_plane_app())

    response = client.post(
        "/v1/projects/project_2/artifacts/search",
        headers=_query_headers(
            actor_id="owner_contract_query_2",
            project_scope="project_1",
            trace_id="trace-contract-query-denied",
        ),
        json={"query": "status", "limit": 5},
    )

    body = response.json()
    assert response.status_code == 403
    assert set(body.keys()) == {
        "trace_id",
        "contract_name",
        "status",
        "policy_version",
        "policy_hash",
        "rule_ids",
        "data",
        "error",
    }
    assert body["status"] == "denied"
    assert body["data"] is None

    error = body["error"]
    assert set(error.keys()) == {
        "code",
        "message",
        "retryable",
        "source_component",
        "details",
    }
    assert error["code"] == "query_scope_denied"
    assert error["source_component"] == "policy_runtime"
    assert error["details"]["project_id"] == "project_2"


def test_query_contract_missing_scope_response_shape() -> None:
    client = TestClient(create_control_plane_app())

    response = client.post(
        "/v1/projects/project_1/artifacts/search",
        headers={
            "X-Trace-Id": "trace-contract-query-missing-scope",
            "X-External-Channel": "discord",
            "X-External-Actor-Id": "owner_contract_query_3",
        },
        json={"query": "status", "limit": 5},
    )

    body = response.json()
    assert response.status_code == 403
    assert set(body.keys()) == {
        "trace_id",
        "contract_name",
        "status",
        "policy_version",
        "policy_hash",
        "rule_ids",
        "data",
        "error",
    }
    assert body["status"] == "denied"
    assert body["data"] is None

    error = body["error"]
    assert set(error.keys()) == {
        "code",
        "message",
        "retryable",
        "source_component",
        "details",
    }
    assert error["code"] == "query_scope_missing"
    assert error["source_component"] == "identity"
    assert error["details"]["project_id"] == "project_1"
