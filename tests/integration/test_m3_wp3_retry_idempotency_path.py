from fastapi.testclient import TestClient

from openqilin.apps.orchestrator_worker import drain_queued_tasks
from openqilin.control_plane.api.app import create_control_plane_app
from openqilin.testing.owner_command import (
    build_owner_command_headers,
    build_owner_command_request_dict,
)


def test_governed_ingress_communication_retry_then_ack_is_deterministic() -> None:
    app = create_control_plane_app()
    client = TestClient(app)
    payload = build_owner_command_request_dict(
        action="msg_dispatch_retry_then_ack",
        args=["agent_retry"],
        actor_id="owner_wp3_retry_ack",
        idempotency_key="idem-m3-wp3-retry-ack-12345",
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
    assert len(records) == 2
    assert records[0].attempt == 1
    assert records[0].state == "nacked"
    assert records[1].attempt == 2
    assert records[1].state == "acked"
    idempotency_records = (
        app.state.runtime_services.task_dispatch_service.list_communication_idempotency_records()
    )
    assert len(idempotency_records) == 1
    assert idempotency_records[0].attempt_count == 2
    assert idempotency_records[0].status == "completed"


def test_governed_ingress_communication_retry_exhausted_fails_closed() -> None:
    app = create_control_plane_app()
    client = TestClient(app)
    payload = build_owner_command_request_dict(
        action="msg_dispatch_retryable_nack",
        args=["agent_retry_exhausted"],
        actor_id="owner_wp3_retry_exhausted",
        idempotency_key="idem-m3-wp3-retry-exhausted-12345",
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
    assert task_body["error_code"] == "communication_retry_exhausted"

    records = app.state.runtime_services.task_dispatch_service.list_communication_message_records(
        task_id=task_id
    )
    assert len(records) == 3
    assert [record.attempt for record in records] == [1, 2, 3]
    assert all(record.state == "nacked" for record in records)
    idempotency_records = (
        app.state.runtime_services.task_dispatch_service.list_communication_idempotency_records()
    )
    assert len(idempotency_records) == 1
    assert idempotency_records[0].attempt_count == 3


def test_governed_ingress_replay_does_not_duplicate_retry_side_effects() -> None:
    app = create_control_plane_app()
    client = TestClient(app)
    payload = build_owner_command_request_dict(
        action="msg_dispatch_retry_then_ack",
        args=["agent_replay"],
        actor_id="owner_wp3_replay",
        idempotency_key="idem-m3-wp3-replay-12345",
        trace_id="trace-m3-wp3-replay",
        target="communication",
    )
    headers = build_owner_command_headers(payload)

    first = client.post("/v1/owner/commands", headers=headers, json=payload)
    second = client.post("/v1/owner/commands", headers=headers, json=payload)

    first_body = first.json()
    second_body = second.json()
    assert first.status_code == 202
    assert second.status_code == 202
    assert first_body["data"]["replayed"] is False
    assert second_body["data"]["replayed"] is True
    assert first_body["data"]["task_id"] == second_body["data"]["task_id"]

    drain_queued_tasks(app.state.runtime_services)

    records = app.state.runtime_services.task_dispatch_service.list_communication_message_records(
        task_id=first_body["data"]["task_id"]
    )
    assert len(records) == 2
    assert [record.attempt for record in records] == [1, 2]
