from fastapi.testclient import TestClient

from openqilin.control_plane.api.app import create_control_plane_app
from openqilin.testing.owner_command import (
    build_owner_command_headers,
    build_owner_command_request_dict,
)


def test_governed_ingress_retry_exhaustion_routes_to_dead_letter_sink() -> None:
    app = create_control_plane_app()
    client = TestClient(app)
    payload = build_owner_command_request_dict(
        action="msg_dispatch_retryable_nack",
        args=["agent_dlq"],
        actor_id="owner_wp4_dlq",
        idempotency_key="idem-m3-wp4-dlq-12345",
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
    assert body["error"]["code"] == "communication_retry_exhausted"
    dead_letter_id = body["error"]["details"].get("dead_letter_id")
    assert isinstance(dead_letter_id, str) and dead_letter_id
    services = app.state.runtime_services
    dead_letters = services.task_dispatch_service.list_communication_dead_letters()
    assert len(dead_letters) == 1
    assert dead_letters[0].dead_letter_id == dead_letter_id
    assert dead_letters[0].task_id == body["error"]["details"]["task_id"]
    assert dead_letters[0].attempts == 3
    assert dead_letters[0].error_code == "communication_retry_exhausted"

    metric_value = services.metric_recorder.get_counter_value(
        "communication_dead_letter_total",
        labels={"connector": "discord", "reason_code": "communication_retry_exhausted"},
    )
    assert metric_value == 1

    events = services.audit_writer.get_events()
    dlq_events = [event for event in events if event.event_type == "communication.dead_letter"]
    assert len(dlq_events) == 1
    assert dlq_events[0].task_id == body["error"]["details"]["task_id"]
    assert dlq_events[0].reason_code == "communication_retry_exhausted"


def test_governed_ingress_replay_does_not_duplicate_dead_letter_records() -> None:
    app = create_control_plane_app()
    client = TestClient(app)
    payload = build_owner_command_request_dict(
        action="msg_dispatch_retryable_nack",
        args=["agent_dlq_replay"],
        actor_id="owner_wp4_dlq_replay",
        idempotency_key="idem-m3-wp4-dlq-replay-12345",
        trace_id="trace-m3-wp4-dlq-replay",
        target="communication",
    )
    headers = build_owner_command_headers(payload)

    first = client.post("/v1/owner/commands", headers=headers, json=payload)
    second = client.post("/v1/owner/commands", headers=headers, json=payload)

    first_body = first.json()
    second_body = second.json()
    assert first.status_code == 403
    assert second.status_code == 403
    assert first_body["error"]["code"] == "communication_retry_exhausted"
    assert second_body["error"]["code"] == "communication_retry_exhausted"
    services = app.state.runtime_services
    dead_letters = services.task_dispatch_service.list_communication_dead_letters()
    assert len(dead_letters) == 1
    metric_value = services.metric_recorder.get_counter_value(
        "communication_dead_letter_total",
        labels={"connector": "discord", "reason_code": "communication_retry_exhausted"},
    )
    assert metric_value == 1
