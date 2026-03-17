from fastapi.testclient import TestClient

from openqilin.apps.orchestrator_worker import drain_queued_tasks
from openqilin.control_plane.api.app import create_control_plane_app
from openqilin.testing.owner_command import (
    build_owner_command_headers,
    build_owner_command_request_dict,
)


def test_communication_command_accepted_response_contract() -> None:
    app = create_control_plane_app()
    services = app.state.runtime_services
    client = TestClient(app)
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
    assert body["data"]["admission_state"] == "queued"
    assert body["error"] is None

    task_id = body["data"]["task_id"]
    drain_queued_tasks(services)

    task_response = client.get(f"/v1/tasks/{task_id}")
    task_body = task_response.json()
    assert task_response.status_code == 200
    assert task_body["status"] == "dispatched"
    assert task_body["dispatch_target"] == "communication"
    assert isinstance(task_body["dispatch_id"], str) and task_body["dispatch_id"]


def test_communication_command_denied_response_contract() -> None:
    app = create_control_plane_app()
    services = app.state.runtime_services
    client = TestClient(app)
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
    assert response.status_code == 202
    assert body["status"] == "accepted"
    assert body["data"]["admission_state"] == "queued"

    task_id = body["data"]["task_id"]
    drain_queued_tasks(services)

    task_response = client.get(f"/v1/tasks/{task_id}")
    task_body = task_response.json()
    assert task_response.status_code == 200
    assert task_body["status"] == "blocked"
    assert task_body["error_code"] == "a2a_missing_recipient_args"
    assert task_body["outcome_source"] == "dispatch_communication_gateway"
