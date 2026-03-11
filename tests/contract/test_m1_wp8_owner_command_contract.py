from fastapi.testclient import TestClient

from openqilin.control_plane.api.app import create_control_plane_app


def test_owner_command_accepted_response_contract() -> None:
    client = TestClient(create_control_plane_app())

    response = client.post(
        "/v1/owner/commands",
        headers={
            "X-OpenQilin-User-Id": "owner_contract_accept",
            "X-OpenQilin-Connector": "discord",
            "X-OpenQilin-Trace-Id": "trace-contract-accept",
        },
        json={
            "command": "run_task",
            "args": ["alpha"],
            "idempotency_key": "idem-contract-accept-12345",
        },
    )

    body = response.json()
    assert response.status_code == 202
    assert set(body.keys()) == {
        "status",
        "task_id",
        "replayed",
        "request_id",
        "trace_id",
        "principal_id",
        "connector",
        "command",
        "accepted_args",
        "dispatch_target",
        "dispatch_id",
    }
    assert body["status"] == "accepted"
    assert isinstance(body["task_id"], str) and body["task_id"]
    assert isinstance(body["replayed"], bool)
    assert body["trace_id"] == "trace-contract-accept"
    assert body["principal_id"] == "owner_contract_accept"
    assert isinstance(body["dispatch_id"], str) and body["dispatch_id"]


def test_owner_command_blocked_response_contract() -> None:
    client = TestClient(create_control_plane_app())

    response = client.post(
        "/v1/owner/commands",
        headers={
            "X-OpenQilin-User-Id": "owner_contract_block",
            "X-OpenQilin-Connector": "discord",
            "X-OpenQilin-Trace-Id": "trace-contract-block",
        },
        json={
            "command": "policy_uncertain",
            "args": ["alpha"],
            "idempotency_key": "idem-contract-block-12345",
        },
    )

    body = response.json()
    assert response.status_code == 403
    assert set(body.keys()) == {"status", "error_code", "message", "details"}
    assert body["status"] == "blocked"
    assert body["error_code"] == "policy_uncertain_fail_closed"
    assert isinstance(body["message"], str) and body["message"]
    assert isinstance(body["details"], dict)
    assert body["details"]["source"] == "policy_runtime"
    assert isinstance(body["details"]["task_id"], str) and body["details"]["task_id"]
