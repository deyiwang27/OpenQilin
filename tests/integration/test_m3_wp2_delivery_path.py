from fastapi.testclient import TestClient

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
    records = app.state.runtime_services.task_dispatch_service.list_communication_message_records(
        task_id=body["data"]["task_id"]
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
    assert response.status_code == 403
    assert body["status"] == "denied"
    assert body["error"]["code"] == "acp_contract_rejected"
    assert body["error"]["source_component"] == "communication_gateway"
    assert body["error"]["details"]["retryable"] == "false"
    records = app.state.runtime_services.task_dispatch_service.list_communication_message_records(
        task_id=body["error"]["details"]["task_id"]
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
