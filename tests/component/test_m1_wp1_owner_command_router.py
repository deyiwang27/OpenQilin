from fastapi.testclient import TestClient

from openqilin.control_plane.api.app import create_control_plane_app
from openqilin.testing.owner_command import (
    build_owner_command_headers,
    build_owner_command_request_dict,
)


def test_submit_owner_command_accepts_valid_payload() -> None:
    app = create_control_plane_app()
    client = TestClient(app)
    payload = build_owner_command_request_dict(
        action="run_task",
        args=["alpha", "beta"],
        actor_id="owner_123",
        idempotency_key="idem-12345678",
        trace_id="trace-component-1",
    )

    response = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(payload),
        json=payload,
    )

    body = response.json()
    assert response.status_code == 202
    assert body["status"] == "accepted"
    assert body["trace_id"] == "trace-component-1"
    assert body["data"]["task_id"]
    assert body["data"]["replayed"] is False
    assert body["data"]["principal_id"] == "owner_123"
    assert body["data"]["command"] == "run_task"
    assert body["data"]["accepted_args"] == ["alpha", "beta"]
    assert body["data"]["dispatch_target"] == "sandbox"
    assert body["data"]["dispatch_id"]
    task = app.state.runtime_services.runtime_state_repo.get_task_by_id(body["data"]["task_id"])
    assert task is not None
    assert task.status == "dispatched"


def test_submit_owner_command_errors_on_missing_required_header() -> None:
    client = TestClient(create_control_plane_app())
    payload = build_owner_command_request_dict(
        action="run_task",
        args=["alpha"],
        actor_id="owner_123",
        idempotency_key="idem-missing-header-12345",
        trace_id="trace-component-2",
    )
    headers = build_owner_command_headers(payload)
    headers.pop("X-External-Channel")

    response = client.post("/v1/owner/commands", headers=headers, json=payload)

    body = response.json()
    assert response.status_code == 400
    assert body["status"] == "error"
    assert body["error"]["code"] == "connector_missing_header"
    assert body["error"]["class"] == "validation_error"


def test_submit_owner_command_errors_on_invalid_signature() -> None:
    client = TestClient(create_control_plane_app())
    payload = build_owner_command_request_dict(
        action="run_task",
        args=["alpha"],
        actor_id="owner_123",
        idempotency_key="idem-invalid-signature-12345",
    )
    headers = build_owner_command_headers(payload)
    headers["X-OpenQilin-Signature"] = "sha256=deadbeef"

    response = client.post("/v1/owner/commands", headers=headers, json=payload)

    body = response.json()
    assert response.status_code == 400
    assert body["status"] == "error"
    assert body["error"]["code"] == "connector_signature_invalid"


def test_submit_owner_command_errors_on_sender_mismatch() -> None:
    client = TestClient(create_control_plane_app())
    payload = build_owner_command_request_dict(
        action="run_task",
        args=["alpha"],
        actor_id="owner_payload_actor",
        idempotency_key="idem-sender-mismatch-12345",
    )
    headers = build_owner_command_headers(payload)
    headers["X-External-Actor-Id"] = "owner_header_actor"

    response = client.post("/v1/owner/commands", headers=headers, json=payload)

    body = response.json()
    assert response.status_code == 400
    assert body["status"] == "error"
    assert body["error"]["code"] == "connector_actor_mismatch"


def test_submit_owner_command_replay_returns_same_task() -> None:
    app = create_control_plane_app()
    client = TestClient(app)
    payload = build_owner_command_request_dict(
        action="run_task",
        args=["alpha", "beta"],
        actor_id="owner_999",
        idempotency_key="idem-replay-component-12345",
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
    assert first_body["data"]["dispatch_target"] == second_body["data"]["dispatch_target"]
    assert first_body["data"]["dispatch_id"] == second_body["data"]["dispatch_id"]
    events = app.state.runtime_services.audit_writer.get_events()
    assert [event.event_type for event in events] == [
        "policy.decision",
        "budget.decision",
        "owner_command.accepted",
        "owner_command.replayed",
    ]


def test_submit_owner_command_replay_returns_prior_denied_without_re_evaluation() -> None:
    app = create_control_plane_app()
    client = TestClient(app)
    payload = build_owner_command_request_dict(
        action="policy_uncertain",
        args=["alpha"],
        actor_id="owner_replay_block",
        idempotency_key="idem-replay-block-component-12345",
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

    events = app.state.runtime_services.audit_writer.get_events()
    assert [event.event_type for event in events] == [
        "policy.decision",
        "owner_command.denied",
        "owner_command.replayed",
    ]


def test_submit_owner_command_blocks_idempotency_key_conflict() -> None:
    client = TestClient(create_control_plane_app())
    payload_first = build_owner_command_request_dict(
        action="run_task",
        args=["alpha"],
        actor_id="owner_456",
        idempotency_key="idem-conflict-component-12345",
    )
    payload_second = build_owner_command_request_dict(
        action="run_task",
        args=["beta"],
        actor_id="owner_456",
        idempotency_key="idem-conflict-component-12345",
    )

    first = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(payload_first),
        json=payload_first,
    )
    second = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(payload_second),
        json=payload_second,
    )

    assert first.status_code == 202
    second_body = second.json()
    assert second.status_code == 409
    assert second_body["status"] == "error"
    assert second_body["error"]["code"] == "idempotency_key_reused_with_different_payload"


def test_submit_owner_command_denies_policy_deny() -> None:
    app = create_control_plane_app()
    client = TestClient(app)
    payload = build_owner_command_request_dict(
        action="deny_delete_project",
        args=["project_1"],
        actor_id="owner_policy_deny",
        idempotency_key="idem-policy-deny-component-12345",
    )

    response = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(payload),
        json=payload,
    )

    body = response.json()
    assert response.status_code == 403
    assert body["status"] == "denied"
    assert body["error"]["code"] == "policy_denied"
    assert body["error"]["class"] == "authorization_error"
    task = app.state.runtime_services.runtime_state_repo.get_task_by_id(
        body["error"]["details"]["task_id"]
    )
    assert task is not None
    assert task.status == "blocked"


def test_submit_owner_command_denies_budget_deny() -> None:
    app = create_control_plane_app()
    client = TestClient(app)
    payload = build_owner_command_request_dict(
        action="budget_deny_project",
        args=["project_1"],
        actor_id="owner_budget_deny",
        idempotency_key="idem-budget-deny-component-12345",
    )

    response = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(payload),
        json=payload,
    )

    body = response.json()
    assert response.status_code == 403
    assert body["status"] == "denied"
    assert body["error"]["code"] == "budget_denied"
    assert body["error"]["class"] == "budget_error"
    task = app.state.runtime_services.runtime_state_repo.get_task_by_id(
        body["error"]["details"]["task_id"]
    )
    assert task is not None
    assert task.status == "blocked"


def test_submit_owner_command_denies_dispatch_reject() -> None:
    app = create_control_plane_app()
    client = TestClient(app)
    payload = build_owner_command_request_dict(
        action="dispatch_reject",
        args=["project_1"],
        actor_id="owner_dispatch_reject",
        idempotency_key="idem-dispatch-reject-component-12345",
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
    assert body["error"]["class"] == "runtime_error"
    task = app.state.runtime_services.runtime_state_repo.get_task_by_id(
        body["error"]["details"]["task_id"]
    )
    assert task is not None
    assert task.status == "blocked"


def test_submit_owner_command_accepts_llm_target_with_usage_cost_metadata() -> None:
    client = TestClient(create_control_plane_app())
    payload = build_owner_command_request_dict(
        action="llm_summarize",
        args=["project_1"],
        actor_id="owner_llm_target",
        idempotency_key="idem-llm-target-component-12345",
    )

    response = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(payload),
        json=payload,
    )

    body = response.json()
    assert response.status_code == 202
    assert body["status"] == "accepted"
    assert body["data"]["dispatch_target"] == "llm"
    assert body["data"]["dispatch_id"]
    assert body["data"]["llm_execution"]["model_selected"]
    assert body["data"]["llm_execution"]["routing_profile"] == "dev_gemini_free"
    assert body["data"]["llm_execution"]["usage"]["total_tokens"] > 0
    assert body["data"]["llm_execution"]["cost"]["cost_source"] in {
        "none",
        "catalog_estimated",
        "provider_reported",
    }


def test_submit_owner_command_denies_llm_gateway_runtime_failure() -> None:
    app = create_control_plane_app()
    client = TestClient(app)
    payload = build_owner_command_request_dict(
        action="llm_runtime_error",
        args=["project_1"],
        actor_id="owner_llm_runtime_failure",
        idempotency_key="idem-llm-runtime-failure-component-12345",
    )

    response = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(payload),
        json=payload,
    )

    body = response.json()
    assert response.status_code == 403
    assert body["status"] == "denied"
    assert body["error"]["code"] == "llm_provider_unavailable"
    assert body["error"]["details"]["source"] == "dispatch_llm_gateway"
    task = app.state.runtime_services.runtime_state_repo.get_task_by_id(
        body["error"]["details"]["task_id"]
    )
    assert task is not None
    assert task.status == "blocked"


def test_submit_owner_command_accepts_communication_target() -> None:
    client = TestClient(create_control_plane_app())
    payload = build_owner_command_request_dict(
        action="msg_notify",
        args=["agent_42"],
        actor_id="owner_communication_target",
        idempotency_key="idem-communication-target-component-12345",
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
    assert body["data"]["dispatch_target"] == "communication"
    assert body["data"]["dispatch_id"]


def test_submit_owner_command_denies_owner_direct_specialist_path() -> None:
    app = create_control_plane_app()
    client = TestClient(app)
    payload = build_owner_command_request_dict(
        action="msg_notify",
        args=["deliver update"],
        actor_id="owner_specialist_denied",
        idempotency_key="idem-specialist-denied-component-12345",
        target="communication",
        recipients=[{"recipient_id": "specialist_1", "recipient_type": "specialist"}],
    )

    response = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(payload),
        json=payload,
    )

    body = response.json()
    assert response.status_code == 403
    assert body["status"] == "denied"
    assert body["error"]["code"] == "governance_specialist_direct_command_denied"
    assert body["error"]["class"] == "authorization_error"
    assert body["error"]["source_component"] == "policy_engine"
    task = app.state.runtime_services.runtime_state_repo.get_task_by_id(
        body["error"]["details"]["task_id"]
    )
    assert task is not None
    assert task.status == "blocked"


def test_submit_owner_command_allows_owner_to_project_manager_path() -> None:
    client = TestClient(create_control_plane_app())
    payload = build_owner_command_request_dict(
        action="msg_notify",
        args=["delegate to specialist"],
        actor_id="owner_pm_allowed",
        idempotency_key="idem-owner-pm-allowed-component-12345",
        target="communication",
        recipients=[{"recipient_id": "project_manager_1", "recipient_type": "project_manager"}],
    )

    response = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(payload),
        json=payload,
    )

    body = response.json()
    assert response.status_code == 202
    assert body["status"] == "accepted"
    assert body["data"]["dispatch_target"] == "communication"
    assert body["data"]["dispatch_id"]


def test_submit_owner_command_denies_communication_contract_violation() -> None:
    app = create_control_plane_app()
    client = TestClient(app)
    payload = build_owner_command_request_dict(
        action="msg_notify",
        args=[],
        actor_id="owner_communication_denied",
        idempotency_key="idem-communication-denied-component-12345",
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
    assert body["error"]["code"] == "a2a_missing_recipient_args"
    assert body["error"]["source_component"] == "communication_gateway"
    task = app.state.runtime_services.runtime_state_repo.get_task_by_id(
        body["error"]["details"]["task_id"]
    )
    assert task is not None
    assert task.status == "blocked"


def test_submit_owner_command_emits_observability_on_accept() -> None:
    app = create_control_plane_app()
    client = TestClient(app)
    payload = build_owner_command_request_dict(
        action="run_task",
        args=["alpha"],
        actor_id="owner_obs_accept",
        idempotency_key="idem-observability-accept-component-12345",
        trace_id="trace-observability-accept-component",
    )

    response = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(payload),
        json=payload,
    )

    body = response.json()
    assert response.status_code == 202
    services = app.state.runtime_services
    metric_value = services.metric_recorder.get_counter_value(
        "owner_command_admission_outcomes_total",
        labels={"outcome": "accepted", "source": "dispatch_sandbox"},
    )
    assert metric_value == 1

    audit_events = services.audit_writer.get_events()
    assert [event.event_type for event in audit_events] == [
        "policy.decision",
        "budget.decision",
        "owner_command.accepted",
    ]
    accepted_event = audit_events[-1]
    assert accepted_event.outcome == "accepted"
    assert accepted_event.trace_id == body["trace_id"]
    assert accepted_event.request_id == body["data"]["request_id"]
    assert accepted_event.task_id == body["data"]["task_id"]

    spans = services.tracer.get_spans()
    span_names = [span.name for span in spans]
    assert "owner_ingress" in span_names
    assert "task_orchestration" in span_names
    assert "policy_evaluation" in span_names
    assert "budget_reservation" in span_names
    assert "execution_sandbox" in span_names
    assert "audit_emit" in span_names


def test_submit_owner_command_emits_observability_on_policy_deny() -> None:
    app = create_control_plane_app()
    client = TestClient(app)
    payload = build_owner_command_request_dict(
        action="deny_delete_project",
        args=["alpha"],
        actor_id="owner_obs_policy_block",
        idempotency_key="idem-observability-policy-block-component-12345",
        trace_id="trace-observability-policy-block-component",
    )

    response = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(payload),
        json=payload,
    )

    body = response.json()
    assert response.status_code == 403
    services = app.state.runtime_services
    metric_value = services.metric_recorder.get_counter_value(
        "owner_command_admission_outcomes_total",
        labels={"outcome": "denied", "source": "policy_runtime"},
    )
    assert metric_value == 1

    audit_events = services.audit_writer.get_events()
    assert [event.event_type for event in audit_events] == [
        "policy.decision",
        "owner_command.denied",
    ]
    denied_event = audit_events[-1]
    denied_task = services.runtime_state_repo.get_task_by_id(body["error"]["details"]["task_id"])
    assert denied_task is not None
    assert denied_event.outcome == "denied"
    assert denied_event.source == "policy_runtime"
    assert denied_event.trace_id == denied_task.trace_id
    assert denied_event.task_id == denied_task.task_id

    spans = services.tracer.get_spans()
    span_names = [span.name for span in spans]
    assert "owner_ingress" in span_names
    assert "task_orchestration" in span_names
    assert "policy_evaluation" in span_names
    assert "audit_emit" in span_names
    assert any(span.status == "error" for span in spans)
