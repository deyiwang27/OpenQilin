from fastapi.testclient import TestClient

from openqilin.apps.api_app import app


def test_governed_ingress_generates_trace_id_when_header_missing() -> None:
    client = TestClient(app)

    response = client.post(
        "/v1/owner/commands",
        headers={
            "X-OpenQilin-User-Id": "owner_987",
            "X-OpenQilin-Connector": "discord",
        },
        json={
            "command": "run_task",
            "args": ["alpha"],
            "idempotency_key": "idem-abcdefgh",
        },
    )

    body = response.json()
    assert response.status_code == 202
    assert body["status"] == "accepted"
    assert body["task_id"]
    assert body["replayed"] is False
    assert body["dispatch_target"] == "sandbox"
    assert body["dispatch_id"]
    assert body["principal_id"] == "owner_987"
    assert body["trace_id"]
    assert isinstance(body["trace_id"], str)


def test_governed_ingress_replay_is_deterministic() -> None:
    client = TestClient(app)
    headers = {
        "X-OpenQilin-User-Id": "owner_integ_001",
        "X-OpenQilin-Connector": "discord",
        "X-OpenQilin-Trace-Id": "trace-integration-first",
    }
    payload = {
        "command": "run_task",
        "args": ["arg_1"],
        "idempotency_key": "idem-integration-replay-12345",
    }

    first = client.post("/v1/owner/commands", headers=headers, json=payload)
    second = client.post(
        "/v1/owner/commands",
        headers={
            "X-OpenQilin-User-Id": "owner_integ_001",
            "X-OpenQilin-Connector": "discord",
            "X-OpenQilin-Trace-Id": "trace-integration-second",
        },
        json=payload,
    )

    first_body = first.json()
    second_body = second.json()
    assert first.status_code == 202
    assert second.status_code == 202
    assert first_body["replayed"] is False
    assert second_body["replayed"] is True
    assert first_body["task_id"] == second_body["task_id"]
    assert first_body["request_id"] == second_body["request_id"]
    assert first_body["trace_id"] == second_body["trace_id"]
    assert first_body["dispatch_target"] == second_body["dispatch_target"]
    assert first_body["dispatch_id"] == second_body["dispatch_id"]


def test_governed_ingress_fail_closed_on_policy_runtime_error() -> None:
    client = TestClient(app)

    response = client.post(
        "/v1/owner/commands",
        headers={
            "X-OpenQilin-User-Id": "owner_policy_error_integration",
            "X-OpenQilin-Connector": "discord",
        },
        json={
            "command": "policy_error",
            "args": ["alpha"],
            "idempotency_key": "idem-integration-policy-error-12345",
        },
    )

    body = response.json()
    assert response.status_code == 403
    assert body["status"] == "blocked"
    assert body["error_code"] == "policy_runtime_error_fail_closed"
    assert body["details"]["source"] == "policy_runtime"


def test_governed_ingress_fail_closed_on_budget_runtime_error() -> None:
    client = TestClient(app)

    response = client.post(
        "/v1/owner/commands",
        headers={
            "X-OpenQilin-User-Id": "owner_budget_error_integration",
            "X-OpenQilin-Connector": "discord",
        },
        json={
            "command": "budget_error",
            "args": ["alpha"],
            "idempotency_key": "idem-integration-budget-error-12345",
        },
    )

    body = response.json()
    assert response.status_code == 403
    assert body["status"] == "blocked"
    assert body["error_code"] == "budget_runtime_error_fail_closed"
    assert body["details"]["source"] == "budget_runtime"


def test_governed_ingress_fail_closed_on_dispatch_reject() -> None:
    client = TestClient(app)
    services = app.state.runtime_services
    before_event_count = len(services.audit_writer.get_events())
    before_span_count = len(services.tracer.get_spans())
    before_metric_value = services.metric_recorder.get_counter_value(
        "owner_command_admission_outcomes_total",
        labels={"outcome": "blocked", "source": "dispatch_stub"},
    )

    response = client.post(
        "/v1/owner/commands",
        headers={
            "X-OpenQilin-User-Id": "owner_dispatch_reject_integration",
            "X-OpenQilin-Connector": "discord",
        },
        json={
            "command": "dispatch_reject",
            "args": ["alpha"],
            "idempotency_key": "idem-integration-dispatch-reject-12345",
        },
    )

    body = response.json()
    assert response.status_code == 403
    assert body["status"] == "blocked"
    assert body["error_code"] == "execution_dispatch_failed"
    assert body["details"]["source"] == "dispatch_stub"

    after_metric_value = services.metric_recorder.get_counter_value(
        "owner_command_admission_outcomes_total",
        labels={"outcome": "blocked", "source": "dispatch_stub"},
    )
    assert after_metric_value == before_metric_value + 1

    new_events = services.audit_writer.get_events()[before_event_count:]
    assert [event.event_type for event in new_events] == [
        "policy.decision",
        "budget.decision",
        "owner_command.blocked",
    ]
    assert new_events[-1].task_id == body["details"]["task_id"]

    new_spans = services.tracer.get_spans()[before_span_count:]
    assert len(new_spans) == 1
    assert new_spans[0].status == "error"
