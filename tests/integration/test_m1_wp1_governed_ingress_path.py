from fastapi.testclient import TestClient

from openqilin.apps.api_app import app


def test_governed_ingress_generates_trace_id_when_header_missing() -> None:
    client = TestClient(app)

    response = client.post(
        "/v1/owner/commands",
        headers={
            "X-OpenQilin-User-Id": "owner_987",
            "X-OpenQilin-Connector": "discord",
        },
        json={
            "command": "run_task",
            "args": ["alpha"],
            "idempotency_key": "idem-abcdefgh",
        },
    )

    body = response.json()
    assert response.status_code == 202
    assert body["status"] == "accepted"
    assert body["task_id"]
    assert body["replayed"] is False
    assert body["principal_id"] == "owner_987"
    assert body["trace_id"]
    assert isinstance(body["trace_id"], str)


def test_governed_ingress_replay_is_deterministic() -> None:
    client = TestClient(app)
    headers = {
        "X-OpenQilin-User-Id": "owner_integ_001",
        "X-OpenQilin-Connector": "discord",
        "X-OpenQilin-Trace-Id": "trace-integration-first",
    }
    payload = {
        "command": "run_task",
        "args": ["arg_1"],
        "idempotency_key": "idem-integration-replay-12345",
    }

    first = client.post("/v1/owner/commands", headers=headers, json=payload)
    second = client.post(
        "/v1/owner/commands",
        headers={
            "X-OpenQilin-User-Id": "owner_integ_001",
            "X-OpenQilin-Connector": "discord",
            "X-OpenQilin-Trace-Id": "trace-integration-second",
        },
        json=payload,
    )

    first_body = first.json()
    second_body = second.json()
    assert first.status_code == 202
    assert second.status_code == 202
    assert first_body["replayed"] is False
    assert second_body["replayed"] is True
    assert first_body["task_id"] == second_body["task_id"]
    assert first_body["request_id"] == second_body["request_id"]
    assert first_body["trace_id"] == second_body["trace_id"]


def test_governed_ingress_fail_closed_on_policy_runtime_error() -> None:
    client = TestClient(app)

    response = client.post(
        "/v1/owner/commands",
        headers={
            "X-OpenQilin-User-Id": "owner_policy_error_integration",
            "X-OpenQilin-Connector": "discord",
        },
        json={
            "command": "policy_error",
            "args": ["alpha"],
            "idempotency_key": "idem-integration-policy-error-12345",
        },
    )

    body = response.json()
    assert response.status_code == 403
    assert body["status"] == "blocked"
    assert body["error_code"] == "policy_runtime_error_fail_closed"
    assert body["details"]["source"] == "policy_runtime"
