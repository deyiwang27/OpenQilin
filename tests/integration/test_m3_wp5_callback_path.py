from fastapi.testclient import TestClient

from openqilin.apps.orchestrator_worker import drain_queued_tasks
from openqilin.control_plane.api.dependencies import RuntimeServices
from openqilin.control_plane.api.app import create_control_plane_app
from openqilin.communication_gateway.callbacks.outcome_notifier import (
    CommunicationOutcomeNotification,
)
from openqilin.testing.owner_command import (
    build_owner_command_headers,
    build_owner_command_request_dict,
)


def _runtime_services(app) -> RuntimeServices:
    return app.state.runtime_services


def test_callback_delivery_updates_task_state_and_is_duplicate_safe() -> None:
    app = create_control_plane_app()
    client = TestClient(app)
    payload = build_owner_command_request_dict(
        action="msg_notify",
        args=["agent_cb_int"],
        actor_id="owner_cb_int_001",
        idempotency_key="idem-callback-int-001",
        trace_id="trace-callback-int-001",
        target="communication",
    )

    response = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(payload),
        json=payload,
    )
    body = response.json()
    assert response.status_code == 202
    task_id = body["data"]["task_id"]
    services = _runtime_services(app)

    drain_queued_tasks(services)

    task_body = client.get(f"/v1/tasks/{task_id}").json()
    assert task_body["status"] == "dispatched"
    dispatch_id = task_body["dispatch_id"]

    first = services.communication_outcome_notifier.notify_delivery_outcome(
        CommunicationOutcomeNotification(
            callback_id="cb-int-delivered-001",
            task_id=task_id,
            trace_id=body["trace_id"],
            dispatch_target="communication",
            delivery_outcome="delivered",
            message="delivery callback acknowledged",
            dispatch_id=dispatch_id,
        )
    )
    second = services.communication_outcome_notifier.notify_delivery_outcome(
        CommunicationOutcomeNotification(
            callback_id="cb-int-delivered-001",
            task_id=task_id,
            trace_id=body["trace_id"],
            dispatch_target="communication",
            delivery_outcome="delivered",
            message="delivery callback acknowledged",
            dispatch_id=dispatch_id,
        )
    )

    assert first.applied is True
    assert first.replayed is False
    assert second.applied is False
    assert second.replayed is True
    task = services.runtime_state_repo.get_task_by_id(task_id)
    assert task is not None
    assert task.status == "dispatched"
    assert task.outcome_source == "callback_communication_delivery"
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


def test_callback_dead_letter_transition_preserves_dead_letter_guarantee() -> None:
    app = create_control_plane_app()
    client = TestClient(app)
    payload = build_owner_command_request_dict(
        action="msg_dispatch_retryable_nack",
        args=["agent_cb_dlq"],
        actor_id="owner_cb_int_002",
        idempotency_key="idem-callback-int-002",
        trace_id="trace-callback-int-002",
        target="communication",
    )

    response = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(payload),
        json=payload,
    )
    body = response.json()
    assert response.status_code == 202
    task_id = body["data"]["task_id"]
    services = _runtime_services(app)

    drain_queued_tasks(services)

    dead_letters = services.task_dispatch_service.list_communication_dead_letters()
    assert len(dead_letters) == 1
    dead_letter_id = dead_letters[0].dead_letter_id

    callback_result = services.communication_outcome_notifier.notify_delivery_outcome(
        CommunicationOutcomeNotification(
            callback_id="cb-int-dlq-001",
            task_id=task_id,
            trace_id=body["trace_id"],
            dispatch_target="communication",
            delivery_outcome="dead_lettered",
            message="dead-letter callback acknowledged",
            reason_code="communication_retry_exhausted",
            dead_letter_id=dead_letter_id,
        )
    )

    assert callback_result.applied is True
    assert callback_result.replayed is False
    task = services.runtime_state_repo.get_task_by_id(task_id)
    assert task is not None
    assert task.status == "blocked"
    assert task.outcome_source == "callback_communication_dead_letter"
    assert dict(task.outcome_details or ())["dead_letter_id"] == dead_letter_id
    dead_letters_after = services.task_dispatch_service.list_communication_dead_letters()
    assert len(dead_letters_after) == 1
    assert dead_letters_after[0].dead_letter_id == dead_letter_id
