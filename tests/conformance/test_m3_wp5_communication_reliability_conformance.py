from fastapi.testclient import TestClient

from openqilin.apps.api_app import create_app
from openqilin.communication_gateway.callbacks.outcome_notifier import (
    CommunicationOutcomeNotification,
)
from openqilin.testing.owner_command import (
    build_owner_command_headers,
    build_owner_command_request_dict,
)


def test_m3_reliability_conformance_callback_at_least_once_duplicate_safe() -> None:
    app = create_app()
    client = TestClient(app)
    payload = build_owner_command_request_dict(
        action="msg_notify",
        args=["agent_conformance_cb"],
        actor_id="owner_m3_conformance_cb",
        idempotency_key="idem-m3-conformance-callback-12345",
        trace_id="trace-m3-conformance-callback-12345",
        target="communication",
    )

    response = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(payload),
        json=payload,
    )
    body = response.json()
    assert response.status_code == 202
    services = app.state.runtime_services
    task_id = body["data"]["task_id"]
    dispatch_id = body["data"]["dispatch_id"]

    first = services.communication_outcome_notifier.notify_delivery_outcome(
        CommunicationOutcomeNotification(
            callback_id="cb-conformance-001",
            task_id=task_id,
            trace_id=body["trace_id"],
            dispatch_target="communication",
            delivery_outcome="delivered",
            message="callback delivered",
            dispatch_id=dispatch_id,
        )
    )
    second = services.communication_outcome_notifier.notify_delivery_outcome(
        CommunicationOutcomeNotification(
            callback_id="cb-conformance-001",
            task_id=task_id,
            trace_id=body["trace_id"],
            dispatch_target="communication",
            delivery_outcome="delivered",
            message="callback delivered",
            dispatch_id=dispatch_id,
        )
    )

    assert first.applied is True
    assert second.replayed is True
    assert (
        services.metric_recorder.get_counter_value(
            "communication_callback_events_total",
            labels={"outcome": "delivered", "replayed": "false"},
        )
        == 1
    )
    assert (
        services.metric_recorder.get_counter_value(
            "communication_callback_events_total",
            labels={"outcome": "delivered", "replayed": "true"},
        )
        == 1
    )


def test_m3_reliability_conformance_dead_letter_callback_guarantees() -> None:
    app = create_app()
    client = TestClient(app)
    payload = build_owner_command_request_dict(
        action="msg_dispatch_retryable_nack",
        args=["agent_conformance_dlq"],
        actor_id="owner_m3_conformance_dlq",
        idempotency_key="idem-m3-conformance-dlq-12345",
        trace_id="trace-m3-conformance-dlq-12345",
        target="communication",
    )

    response = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(payload),
        json=payload,
    )
    body = response.json()
    assert response.status_code == 403
    services = app.state.runtime_services
    task_id = body["error"]["details"]["task_id"]
    dead_letter_id = body["error"]["details"]["dead_letter_id"]

    callback = services.communication_outcome_notifier.notify_delivery_outcome(
        CommunicationOutcomeNotification(
            callback_id="cb-conformance-dlq-001",
            task_id=task_id,
            trace_id=body["trace_id"],
            dispatch_target="communication",
            delivery_outcome="dead_lettered",
            message="callback dead-lettered",
            reason_code="communication_retry_exhausted",
            dead_letter_id=dead_letter_id,
        )
    )

    assert callback.applied is True
    dead_letters = services.task_dispatch_service.list_communication_dead_letters()
    assert len(dead_letters) == 1
    assert dead_letters[0].dead_letter_id == dead_letter_id
    assert (
        services.metric_recorder.get_counter_value(
            "communication_dead_letter_total",
            labels={"connector": "discord", "reason_code": "communication_retry_exhausted"},
        )
        == 1
    )
