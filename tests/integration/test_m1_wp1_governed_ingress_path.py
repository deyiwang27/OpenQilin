from fastapi.testclient import TestClient

from openqilin.apps.api_app import app
from openqilin.testing.owner_command import (
    build_owner_command_headers,
    build_owner_command_request_dict,
)


def test_governed_ingress_accepts_canonical_envelope() -> None:
    client = TestClient(app)
    payload = build_owner_command_request_dict(
        action="run_task",
        args=["alpha"],
        actor_id="owner_987",
        idempotency_key="idem-abcdefgh",
    )

    response = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(payload),
        json=payload,
    )

    body = response.json()
    assert response.status_code == 202
    assert body["status"] == "accepted"
    assert body["data"]["task_id"]
    assert body["data"]["replayed"] is False
    assert body["data"]["dispatch_target"] == "sandbox"
    assert body["data"]["dispatch_id"]
    assert body["data"]["principal_id"] == "owner_987"
    assert body["trace_id"]
    assert isinstance(body["trace_id"], str)


def test_governed_ingress_replay_is_deterministic() -> None:
    client = TestClient(app)
    payload = build_owner_command_request_dict(
        action="run_task",
        args=["arg_1"],
        actor_id="owner_integ_001",
        idempotency_key="idem-integration-replay-12345",
        trace_id="trace-integration-first",
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
    assert first_body["data"]["request_id"] == second_body["data"]["request_id"]
    assert first_body["trace_id"] == second_body["trace_id"]
    assert first_body["data"]["dispatch_target"] == second_body["data"]["dispatch_target"]
    assert first_body["data"]["dispatch_id"] == second_body["data"]["dispatch_id"]


def test_governed_ingress_denied_replay_is_deterministic() -> None:
    client = TestClient(app)
    payload = build_owner_command_request_dict(
        action="policy_uncertain",
        args=["arg_1"],
        actor_id="owner_integ_replay_blocked",
        idempotency_key="idem-integration-replay-blocked-12345",
        trace_id="trace-integration-blocked-first",
    )
    headers = build_owner_command_headers(payload)

    first = client.post("/v1/owner/commands", headers=headers, json=payload)
    second = client.post("/v1/owner/commands", headers=headers, json=payload)

    first_body = first.json()
    second_body = second.json()
    assert first.status_code == 403
    assert second.status_code == 403
    assert first_body["status"] == "denied"
    assert second_body["status"] == "denied"
    assert first_body["error"]["code"] == "policy_uncertain_fail_closed"
    assert second_body["error"]["code"] == "policy_uncertain_fail_closed"
    assert first_body["error"]["details"]["task_id"] == second_body["error"]["details"]["task_id"]
    assert second_body["error"]["details"]["replayed"] == "true"


def test_governed_ingress_fail_closed_on_policy_runtime_error() -> None:
    client = TestClient(app)
    payload = build_owner_command_request_dict(
        action="policy_error",
        args=["alpha"],
        actor_id="owner_policy_error_integration",
        idempotency_key="idem-integration-policy-error-12345",
    )

    response = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(payload),
        json=payload,
    )

    body = response.json()
    assert response.status_code == 403
    assert body["status"] == "denied"
    assert body["error"]["code"] == "policy_runtime_error_fail_closed"
    assert body["error"]["details"]["source"] == "policy_runtime"


def test_governed_ingress_fail_closed_on_budget_runtime_error() -> None:
    client = TestClient(app)
    payload = build_owner_command_request_dict(
        action="budget_error",
        args=["alpha"],
        actor_id="owner_budget_error_integration",
        idempotency_key="idem-integration-budget-error-12345",
    )

    response = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(payload),
        json=payload,
    )

    body = response.json()
    assert response.status_code == 403
    assert body["status"] == "denied"
    assert body["error"]["code"] == "budget_runtime_error_fail_closed"
    assert body["error"]["details"]["source"] == "budget_runtime"


def test_governed_ingress_fail_closed_on_dispatch_reject() -> None:
    client = TestClient(app)
    services = app.state.runtime_services
    before_event_count = len(services.audit_writer.get_events())
    before_span_count = len(services.tracer.get_spans())
    before_metric_value = services.metric_recorder.get_counter_value(
        "owner_command_admission_outcomes_total",
        labels={"outcome": "denied", "source": "dispatch_sandbox_adapter"},
    )
    payload = build_owner_command_request_dict(
        action="dispatch_reject",
        args=["alpha"],
        actor_id="owner_dispatch_reject_integration",
        idempotency_key="idem-integration-dispatch-reject-12345",
    )

    response = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(payload),
        json=payload,
    )

    body = response.json()
    assert response.status_code == 403
    assert body["status"] == "denied"
    assert body["error"]["code"] == "execution_dispatch_failed"
    assert body["error"]["details"]["source"] == "dispatch_sandbox_adapter"

    after_metric_value = services.metric_recorder.get_counter_value(
        "owner_command_admission_outcomes_total",
        labels={"outcome": "denied", "source": "dispatch_sandbox_adapter"},
    )
    assert after_metric_value == before_metric_value + 1

    new_events = services.audit_writer.get_events()[before_event_count:]
    assert [event.event_type for event in new_events] == [
        "policy.decision",
        "budget.decision",
        "owner_command.denied",
    ]
    assert new_events[-1].task_id == body["error"]["details"]["task_id"]

    new_spans = services.tracer.get_spans()[before_span_count:]
    span_names = [span.name for span in new_spans]
    assert "owner_ingress" in span_names
    assert "task_orchestration" in span_names
    assert "policy_evaluation" in span_names
    assert "budget_reservation" in span_names
    assert "execution_sandbox" in span_names
    assert "audit_emit" in span_names
    assert any(span.status == "error" for span in new_spans)
