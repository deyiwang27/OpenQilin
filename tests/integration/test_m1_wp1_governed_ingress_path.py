from fastapi.testclient import TestClient

from openqilin.apps.api_app import app
from openqilin.apps.orchestrator_worker import drain_queued_tasks
from openqilin.testing.owner_command import (
    build_owner_command_headers,
    build_owner_command_request_dict,
)


def test_governed_ingress_accepts_canonical_envelope() -> None:
    client = TestClient(app)
    services = app.state.runtime_services
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
    assert body["data"]["principal_id"] == "owner_987"
    assert body["trace_id"]
    assert isinstance(body["trace_id"], str)

    task_id = body["data"]["task_id"]
    drain_queued_tasks(services)

    task_response = client.get(f"/v1/tasks/{task_id}")
    task_body = task_response.json()
    assert task_body["status"] == "dispatched"
    assert task_body["dispatch_target"] == "sandbox"
    assert task_body["dispatch_id"]


def test_governed_ingress_llm_accept_includes_usage_cost_metadata() -> None:
    client = TestClient(app)
    services = app.state.runtime_services
    payload = build_owner_command_request_dict(
        action="llm_summarize",
        args=["alpha"],
        actor_id="owner_llm_integ_001",
        idempotency_key="idem-integration-llm-accept-12345",
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
    drain_queued_tasks(services)

    task_body = client.get(f"/v1/tasks/{task_id}").json()
    assert task_body["status"] == "dispatched"
    assert task_body["dispatch_target"] == "llm"
    assert task_body["llm_execution"]["model_selected"]
    assert task_body["llm_execution"]["usage"]["total_tokens"] > 0
    assert task_body["llm_execution"]["cost"]["estimated_cost_usd"] >= 0


def test_governed_ingress_accepts_communication_target() -> None:
    client = TestClient(app)
    services = app.state.runtime_services
    payload = build_owner_command_request_dict(
        action="msg_notify",
        args=["agent_99"],
        actor_id="owner_communication_integ_001",
        idempotency_key="idem-integration-communication-accept-12345",
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
    drain_queued_tasks(services)

    task_body = client.get(f"/v1/tasks/{task_id}").json()
    assert task_body["status"] == "dispatched"
    assert task_body["dispatch_target"] == "communication"
    assert task_body["dispatch_id"]


def test_governed_ingress_fail_closed_on_communication_contract_violation() -> None:
    client = TestClient(app)
    services = app.state.runtime_services
    payload = build_owner_command_request_dict(
        action="msg_notify",
        args=[],
        actor_id="owner_communication_integ_002",
        idempotency_key="idem-integration-communication-denied-12345",
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
    drain_queued_tasks(services)

    task_body = client.get(f"/v1/tasks/{task_id}").json()
    assert task_body["status"] == "blocked"
    assert task_body["error_code"] == "a2a_missing_recipient_args"
    assert task_body["outcome_source"] == "dispatch_communication_gateway"


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


def test_governed_ingress_denied_replay_is_deterministic() -> None:
    client = TestClient(app)
    services = app.state.runtime_services
    payload = build_owner_command_request_dict(
        action="policy_uncertain",
        args=["arg_1"],
        actor_id="owner_integ_replay_blocked",
        idempotency_key="idem-integration-replay-blocked-12345",
        trace_id="trace-integration-blocked-first",
    )
    headers = build_owner_command_headers(payload)

    first = client.post("/v1/owner/commands", headers=headers, json=payload)
    first_body = first.json()
    assert first.status_code == 202
    assert first_body["status"] == "accepted"
    task_id = first_body["data"]["task_id"]

    drain_queued_tasks(services)

    second = client.post("/v1/owner/commands", headers=headers, json=payload)
    second_body = second.json()
    assert second.status_code == 403
    assert second_body["status"] == "denied"
    assert second_body["error"]["code"] == "policy_uncertain_fail_closed"
    assert second_body["error"]["details"]["task_id"] == task_id
    assert second_body["error"]["details"]["replayed"] == "true"


def test_governed_ingress_fail_closed_on_policy_runtime_error() -> None:
    client = TestClient(app)
    services = app.state.runtime_services
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
    assert response.status_code == 202
    assert body["status"] == "accepted"

    task_id = body["data"]["task_id"]
    drain_queued_tasks(services)

    task_body = client.get(f"/v1/tasks/{task_id}").json()
    assert task_body["status"] == "blocked"
    assert task_body["error_code"] == "policy_runtime_error_fail_closed"
    assert task_body["outcome_source"] == "policy_runtime"


def test_governed_ingress_fail_closed_on_budget_runtime_error() -> None:
    client = TestClient(app)
    services = app.state.runtime_services
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
    assert response.status_code == 202
    assert body["status"] == "accepted"

    task_id = body["data"]["task_id"]
    drain_queued_tasks(services)

    task_body = client.get(f"/v1/tasks/{task_id}").json()
    assert task_body["status"] == "blocked"
    assert task_body["error_code"] == "budget_runtime_error_fail_closed"
    assert task_body["outcome_source"] == "budget_runtime"


def test_governed_ingress_fail_closed_on_dispatch_reject() -> None:
    from openqilin.observability.audit.audit_writer import OTelAuditWriter

    client = TestClient(app)
    services = app.state.runtime_services
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
    assert response.status_code == 202
    assert body["status"] == "accepted"
    task_id = body["data"]["task_id"]

    drain_queued_tasks(services)

    task_body = client.get(f"/v1/tasks/{task_id}").json()
    assert task_body["status"] == "blocked"
    assert task_body["error_code"] == "execution_dispatch_failed"
    assert task_body["outcome_source"] == "dispatch_sandbox_adapter"

    after_metric_value = services.metric_recorder.get_counter_value(
        "owner_command_admission_outcomes_total",
        labels={"outcome": "denied", "source": "dispatch_sandbox_adapter"},
    )
    assert after_metric_value == before_metric_value + 1

    assert isinstance(services.audit_writer, OTelAuditWriter)
    audit_repo = services.audit_writer._audit_repo  # type: ignore[attr-defined]
    task_record = services.runtime_state_repo.get_task_by_id(task_id)
    assert task_record is not None
    new_events = audit_repo.list_events_for_trace(task_record.trace_id)
    assert [event.event_type for event in new_events] == [
        "policy.decision",
        "budget.decision",
        "owner_command.denied",
    ]
    assert new_events[-1].task_id == task_id

    new_spans = services.tracer.get_spans()[before_span_count:]
    span_names = [span.name for span in new_spans]
    assert "owner_ingress" in span_names
    assert "task_orchestration" in span_names
    assert "policy_evaluation" in span_names
    assert "budget_reservation" in span_names
    assert "execution_sandbox" in span_names
    assert "audit_emit" in span_names


def test_governed_ingress_fail_closed_on_llm_gateway_runtime_error() -> None:
    client = TestClient(app)
    services = app.state.runtime_services
    before_metric_value = services.metric_recorder.get_counter_value(
        "owner_command_admission_outcomes_total",
        labels={"outcome": "denied", "source": "dispatch_llm_gateway"},
    )
    payload = build_owner_command_request_dict(
        action="llm_runtime_error",
        args=["alpha"],
        actor_id="owner_llm_runtime_error_integration",
        idempotency_key="idem-integration-llm-runtime-error-12345",
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

    drain_queued_tasks(services)

    task_body = client.get(f"/v1/tasks/{task_id}").json()
    assert task_body["status"] == "blocked"
    assert task_body["error_code"] == "llm_provider_unavailable"
    assert task_body["outcome_source"] == "dispatch_llm_gateway"

    after_metric_value = services.metric_recorder.get_counter_value(
        "owner_command_admission_outcomes_total",
        labels={"outcome": "denied", "source": "dispatch_llm_gateway"},
    )
    assert after_metric_value == before_metric_value + 1


def test_governed_ingress_llm_reason_denies_without_grounding_evidence() -> None:
    client = TestClient(app)
    services = app.state.runtime_services
    payload = build_owner_command_request_dict(
        action="llm_reason",
        target="llm",
        args=["Summarize budget risk for a non-existent project scope."],
        actor_id="owner_llm_grounding_missing_integration",
        idempotency_key="idem-integration-llm-grounding-missing-12345",
        project_id="project_unknown_scope",
        recipients=[{"recipient_id": "ceo_core", "recipient_type": "ceo"}],
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

    drain_queued_tasks(services)

    task_body = client.get(f"/v1/tasks/{task_id}").json()
    assert task_body["status"] == "blocked"
    assert task_body["error_code"] == "llm_grounding_insufficient_evidence"
    assert task_body["outcome_source"] == "dispatch_llm_gateway"


def test_governed_ingress_llm_reason_denies_when_citations_missing() -> None:
    client = TestClient(app)
    services = app.state.runtime_services
    payload = build_owner_command_request_dict(
        action="llm_reason",
        target="llm",
        args=["Summarize retrieval status rollout for project 1."],
        actor_id="owner_llm_grounding_citation_integration",
        idempotency_key="idem-integration-llm-grounding-citation-12345",
        project_id="project_1",
        recipients=[{"recipient_id": "ceo_core", "recipient_type": "ceo"}],
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

    drain_queued_tasks(services)

    task_body = client.get(f"/v1/tasks/{task_id}").json()
    assert task_body["status"] == "blocked"
    assert task_body["error_code"] == "llm_grounding_citation_missing"
    assert task_body["outcome_source"] == "dispatch_llm_gateway"
