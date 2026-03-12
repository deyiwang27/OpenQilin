from fastapi.testclient import TestClient

from openqilin.control_plane.api.app import create_control_plane_app
from openqilin.testing.owner_command import (
    build_owner_command_headers,
    build_owner_command_request_dict,
)


def test_owner_command_accepted_response_contract() -> None:
    client = TestClient(create_control_plane_app())
    payload = build_owner_command_request_dict(
        action="run_task",
        args=["alpha"],
        actor_id="owner_contract_accept",
        idempotency_key="idem-contract-accept-12345",
        trace_id="trace-contract-accept",
    )

    response = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(payload),
        json=payload,
    )

    body = response.json()
    assert response.status_code == 202
    assert set(body.keys()) == {
        "status",
        "trace_id",
        "policy_version",
        "policy_hash",
        "rule_ids",
        "data",
        "error",
    }
    assert body["status"] == "accepted"
    assert body["trace_id"] == "trace-contract-accept"
    assert body["error"] is None

    data = body["data"]
    assert isinstance(data["task_id"], str) and data["task_id"]
    assert isinstance(data["replayed"], bool)
    assert data["principal_id"] == "owner_contract_accept"
    assert isinstance(data["dispatch_id"], str) and data["dispatch_id"]
    assert data["admission_state"] == "dispatched"


def test_owner_command_denied_response_contract() -> None:
    client = TestClient(create_control_plane_app())
    payload = build_owner_command_request_dict(
        action="policy_uncertain",
        args=["alpha"],
        actor_id="owner_contract_block",
        idempotency_key="idem-contract-block-12345",
        trace_id="trace-contract-block",
    )

    response = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(payload),
        json=payload,
    )

    body = response.json()
    assert response.status_code == 403
    assert set(body.keys()) == {
        "status",
        "trace_id",
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
        "class",
        "message",
        "retryable",
        "source_component",
        "trace_id",
        "policy_version",
        "policy_hash",
        "rule_ids",
        "details",
    }
    assert error["code"] == "policy_uncertain_fail_closed"
    assert error["class"] == "authorization_error"
    assert isinstance(error["message"], str) and error["message"]
    assert error["details"]["source"] == "policy_runtime"
    assert isinstance(error["details"]["task_id"], str) and error["details"]["task_id"]


def test_owner_command_specialist_touchability_denied_response_contract() -> None:
    client = TestClient(create_control_plane_app())
    payload = build_owner_command_request_dict(
        action="msg_notify",
        args=["deliver update"],
        actor_id="owner_contract_specialist_block",
        idempotency_key="idem-contract-specialist-block-12345",
        trace_id="trace-contract-specialist-block",
        target="communication",
        recipients=[{"recipient_id": "specialist_1", "recipient_type": "specialist"}],
    )

    response = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(payload),
        json=payload,
    )

    body = response.json()
    assert response.status_code == 403
    assert body["status"] == "denied"

    error = body["error"]
    assert error["code"] == "governance_specialist_direct_command_denied"
    assert error["class"] == "authorization_error"
    assert error["source_component"] == "policy_engine"
    assert error["details"]["source"] == "policy_runtime"
    assert isinstance(error["details"]["task_id"], str) and error["details"]["task_id"]
