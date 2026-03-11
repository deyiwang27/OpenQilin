from fastapi.testclient import TestClient

from openqilin.control_plane.api.app import create_control_plane_app
from openqilin.testing.owner_command import (
    build_owner_command_headers,
    build_owner_command_request_dict,
)


def test_communication_command_accepted_response_contract() -> None:
    client = TestClient(create_control_plane_app())
    payload = build_owner_command_request_dict(
        action="msg_notify",
        args=["agent_100"],
        actor_id="owner_contract_msg_accept",
        idempotency_key="idem-contract-msg-accept-12345",
        trace_id="trace-contract-msg-accept",
        target="communication",
    )

    response = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(payload),
        json=payload,
    )

    body = response.json()
    assert response.status_code == 202
    assert body["status"] == "accepted"
    assert body["data"]["dispatch_target"] == "communication"
    assert isinstance(body["data"]["dispatch_id"], str) and body["data"]["dispatch_id"]
    assert body["error"] is None


def test_communication_command_denied_response_contract() -> None:
    client = TestClient(create_control_plane_app())
    payload = build_owner_command_request_dict(
        action="msg_notify",
        args=[],
        actor_id="owner_contract_msg_deny",
        idempotency_key="idem-contract-msg-deny-12345",
        trace_id="trace-contract-msg-deny",
        target="communication",
    )

    response = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(payload),
        json=payload,
    )

    body = response.json()
    assert response.status_code == 403
    assert body["status"] == "denied"
    assert body["data"] is None
    assert body["error"]["code"] == "a2a_missing_recipient_args"
    assert body["error"]["source_component"] == "communication_gateway"
    assert body["error"]["details"]["source"] == "dispatch_communication_gateway"
