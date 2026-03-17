from fastapi.testclient import TestClient

from openqilin.apps.orchestrator_worker import drain_queued_tasks
from openqilin.control_plane.api.app import create_control_plane_app
from openqilin.testing.owner_command import (
    build_owner_command_headers,
    build_owner_command_request_dict,
)


def test_governed_ingress_communication_send_ack_records_ledger() -> None:
    app = create_control_plane_app()
    client = TestClient(app)
    payload = build_owner_command_request_dict(
        action="msg_notify",
        args=["agent_99"],
        actor_id="owner_wp2_ack",
        idempotency_key="idem-m3-wp2-ack-12345",
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
    task_id = body["data"]["task_id"]

    drain_queued_tasks(app.state.runtime_services)

    records = app.state.runtime_services.task_dispatch_service.list_communication_message_records(
        task_id=task_id
    )
    assert len(records) == 1
    record = records[0]
    assert record.state == "acked"
    assert record.error_code is None
    assert record.retryable is False
    assert tuple(transition.state for transition in record.transitions) == (
        "prepared",
        "sent",
        "acked",
    )


def test_governed_ingress_communication_send_nack_records_ledger() -> None:
    app = create_control_plane_app()
    client = TestClient(app)
    payload = build_owner_command_request_dict(
        action="msg_dispatch_reject",
        args=["agent_101"],
        actor_id="owner_wp2_nack",
        idempotency_key="idem-m3-wp2-nack-12345",
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
    task_id = body["data"]["task_id"]

    drain_queued_tasks(app.state.runtime_services)

    task_body = client.get(f"/v1/tasks/{task_id}").json()
    assert task_body["status"] == "blocked"
    assert task_body["error_code"] == "acp_contract_rejected"
    assert task_body["outcome_source"] == "dispatch_communication_gateway"

    records = app.state.runtime_services.task_dispatch_service.list_communication_message_records(
        task_id=task_id
    )
    assert len(records) == 1
    record = records[0]
    assert record.state == "nacked"
    assert record.error_code == "acp_contract_rejected"
    assert record.retryable is False
    assert tuple(transition.state for transition in record.transitions) == (
        "prepared",
        "sent",
        "nacked",
    )
