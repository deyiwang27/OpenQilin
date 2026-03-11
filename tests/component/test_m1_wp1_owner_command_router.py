from fastapi.testclient import TestClient

from openqilin.control_plane.api.app import create_control_plane_app


def test_submit_owner_command_accepts_valid_payload() -> None:
    app = create_control_plane_app()
    client = TestClient(app)

    response = client.post(
        "/v1/owner/commands",
        headers={
            "X-OpenQilin-User-Id": "owner_123",
            "X-OpenQilin-Connector": "discord",
            "X-OpenQilin-Trace-Id": "trace-component-1",
        },
        json={
            "command": "run_task",
            "args": ["alpha", "beta"],
            "idempotency_key": "idem-12345678",
        },
    )

    body = response.json()
    assert response.status_code == 202
    assert body["status"] == "accepted"
    assert body["task_id"]
    assert body["replayed"] is False
    assert body["principal_id"] == "owner_123"
    assert body["trace_id"] == "trace-component-1"
    assert body["command"] == "run_task"
    assert body["accepted_args"] == ["alpha", "beta"]
    assert body["dispatch_target"] == "sandbox"
    assert body["dispatch_id"]
    task = app.state.runtime_services.runtime_state_repo.get_task_by_id(body["task_id"])
    assert task is not None
    assert task.status == "dispatched"


def test_submit_owner_command_blocks_missing_principal_header() -> None:
    client = TestClient(create_control_plane_app())

    response = client.post(
        "/v1/owner/commands",
        headers={
            "X-OpenQilin-Connector": "discord",
            "X-OpenQilin-Trace-Id": "trace-component-2",
        },
        json={
            "command": "run_task",
            "args": ["alpha"],
            "idempotency_key": "idem-12345678",
        },
    )

    body = response.json()
    assert response.status_code == 400
    assert body["status"] == "blocked"
    assert body["error_code"] == "principal_missing_header"
    assert body["details"]["source"] == "headers"


def test_submit_owner_command_blocks_blank_command() -> None:
    client = TestClient(create_control_plane_app())

    response = client.post(
        "/v1/owner/commands",
        headers={
            "X-OpenQilin-User-Id": "owner_123",
            "X-OpenQilin-Connector": "discord",
            "X-OpenQilin-Trace-Id": "trace-component-3",
        },
        json={
            "command": "   ",
            "args": ["alpha"],
            "idempotency_key": "idem-12345678",
        },
    )

    body = response.json()
    assert response.status_code == 400
    assert body["status"] == "blocked"
    assert body["error_code"] == "envelope_invalid_command"
    assert body["details"]["source"] == "payload"


def test_submit_owner_command_replay_returns_same_task() -> None:
    client = TestClient(create_control_plane_app())

    headers = {
        "X-OpenQilin-User-Id": "owner_999",
        "X-OpenQilin-Connector": "discord",
    }
    payload = {
        "command": "run_task",
        "args": ["alpha", "beta"],
        "idempotency_key": "idem-replay-component-12345",
    }

    first = client.post("/v1/owner/commands", headers=headers, json=payload)
    second = client.post("/v1/owner/commands", headers=headers, json=payload)

    first_body = first.json()
    second_body = second.json()
    assert first.status_code == 202
    assert second.status_code == 202
    assert first_body["replayed"] is False
    assert second_body["replayed"] is True
    assert first_body["task_id"] == second_body["task_id"]
    assert first_body["request_id"] == second_body["request_id"]
    assert first_body["dispatch_target"] == second_body["dispatch_target"]
    assert first_body["dispatch_id"] == second_body["dispatch_id"]


def test_submit_owner_command_blocks_idempotency_key_conflict() -> None:
    client = TestClient(create_control_plane_app())
    headers = {
        "X-OpenQilin-User-Id": "owner_456",
        "X-OpenQilin-Connector": "discord",
    }

    first = client.post(
        "/v1/owner/commands",
        headers=headers,
        json={
            "command": "run_task",
            "args": ["alpha"],
            "idempotency_key": "idem-conflict-component-12345",
        },
    )
    second = client.post(
        "/v1/owner/commands",
        headers=headers,
        json={
            "command": "run_task",
            "args": ["beta"],
            "idempotency_key": "idem-conflict-component-12345",
        },
    )

    assert first.status_code == 202
    second_body = second.json()
    assert second.status_code == 409
    assert second_body["status"] == "blocked"
    assert second_body["error_code"] == "idempotency_key_reused_with_different_payload"
    assert second_body["details"]["source"] == "idempotency"


def test_submit_owner_command_blocks_idempotency_key_conflict_on_metadata_change() -> None:
    client = TestClient(create_control_plane_app())
    headers = {
        "X-OpenQilin-User-Id": "owner_460",
        "X-OpenQilin-Connector": "discord",
    }

    first = client.post(
        "/v1/owner/commands",
        headers=headers,
        json={
            "command": "run_task",
            "args": ["alpha"],
            "metadata": {"channel": "discord"},
            "idempotency_key": "idem-conflict-metadata-component-12345",
        },
    )
    second = client.post(
        "/v1/owner/commands",
        headers=headers,
        json={
            "command": "run_task",
            "args": ["alpha"],
            "metadata": {"channel": "telegram"},
            "idempotency_key": "idem-conflict-metadata-component-12345",
        },
    )

    assert first.status_code == 202
    second_body = second.json()
    assert second.status_code == 409
    assert second_body["status"] == "blocked"
    assert second_body["error_code"] == "idempotency_key_reused_with_different_payload"
    assert second_body["details"]["source"] == "idempotency"


def test_submit_owner_command_blocks_policy_deny() -> None:
    app = create_control_plane_app()
    client = TestClient(app)

    response = client.post(
        "/v1/owner/commands",
        headers={
            "X-OpenQilin-User-Id": "owner_policy_deny",
            "X-OpenQilin-Connector": "discord",
        },
        json={
            "command": "deny_delete_project",
            "args": ["project_1"],
            "idempotency_key": "idem-policy-deny-component-12345",
        },
    )

    body = response.json()
    assert response.status_code == 403
    assert body["status"] == "blocked"
    assert body["error_code"] == "policy_denied"
    assert body["details"]["source"] == "policy_runtime"
    assert body["details"]["decision"] == "deny"
    task = app.state.runtime_services.runtime_state_repo.get_task_by_id(body["details"]["task_id"])
    assert task is not None
    assert task.status == "blocked_policy"


def test_submit_owner_command_blocks_policy_uncertain_fail_closed() -> None:
    client = TestClient(create_control_plane_app())

    response = client.post(
        "/v1/owner/commands",
        headers={
            "X-OpenQilin-User-Id": "owner_policy_uncertain",
            "X-OpenQilin-Connector": "discord",
        },
        json={
            "command": "policy_uncertain",
            "args": ["project_1"],
            "idempotency_key": "idem-policy-uncertain-component-12345",
        },
    )

    body = response.json()
    assert response.status_code == 403
    assert body["status"] == "blocked"
    assert body["error_code"] == "policy_uncertain_fail_closed"
    assert body["details"]["source"] == "policy_runtime"
    assert body["details"]["decision"] == "uncertain"


def test_submit_owner_command_blocks_budget_deny() -> None:
    app = create_control_plane_app()
    client = TestClient(app)

    response = client.post(
        "/v1/owner/commands",
        headers={
            "X-OpenQilin-User-Id": "owner_budget_deny",
            "X-OpenQilin-Connector": "discord",
        },
        json={
            "command": "budget_deny_project",
            "args": ["project_1"],
            "idempotency_key": "idem-budget-deny-component-12345",
        },
    )

    body = response.json()
    assert response.status_code == 403
    assert body["status"] == "blocked"
    assert body["error_code"] == "budget_denied"
    assert body["details"]["source"] == "budget_runtime"
    assert body["details"]["decision"] == "deny"
    task = app.state.runtime_services.runtime_state_repo.get_task_by_id(body["details"]["task_id"])
    assert task is not None
    assert task.status == "blocked_budget"


def test_submit_owner_command_blocks_budget_uncertain_fail_closed() -> None:
    client = TestClient(create_control_plane_app())

    response = client.post(
        "/v1/owner/commands",
        headers={
            "X-OpenQilin-User-Id": "owner_budget_uncertain",
            "X-OpenQilin-Connector": "discord",
        },
        json={
            "command": "budget_uncertain",
            "args": ["project_1"],
            "idempotency_key": "idem-budget-uncertain-component-12345",
        },
    )

    body = response.json()
    assert response.status_code == 403
    assert body["status"] == "blocked"
    assert body["error_code"] == "budget_uncertain_fail_closed"
    assert body["details"]["source"] == "budget_runtime"
    assert body["details"]["decision"] == "uncertain"


def test_submit_owner_command_blocks_budget_runtime_error_fail_closed() -> None:
    client = TestClient(create_control_plane_app())

    response = client.post(
        "/v1/owner/commands",
        headers={
            "X-OpenQilin-User-Id": "owner_budget_error",
            "X-OpenQilin-Connector": "discord",
        },
        json={
            "command": "budget_error",
            "args": ["project_1"],
            "idempotency_key": "idem-budget-error-component-12345",
        },
    )

    body = response.json()
    assert response.status_code == 403
    assert body["status"] == "blocked"
    assert body["error_code"] == "budget_runtime_error_fail_closed"
    assert body["details"]["source"] == "budget_runtime"


def test_submit_owner_command_blocks_dispatch_reject() -> None:
    app = create_control_plane_app()
    client = TestClient(app)

    response = client.post(
        "/v1/owner/commands",
        headers={
            "X-OpenQilin-User-Id": "owner_dispatch_reject",
            "X-OpenQilin-Connector": "discord",
        },
        json={
            "command": "dispatch_reject",
            "args": ["project_1"],
            "idempotency_key": "idem-dispatch-reject-component-12345",
        },
    )

    body = response.json()
    assert response.status_code == 403
    assert body["status"] == "blocked"
    assert body["error_code"] == "execution_dispatch_failed"
    assert body["details"]["source"] == "dispatch_stub"
    task = app.state.runtime_services.runtime_state_repo.get_task_by_id(body["details"]["task_id"])
    assert task is not None
    assert task.status == "blocked_dispatch"


def test_submit_owner_command_accepts_llm_target_stub() -> None:
    client = TestClient(create_control_plane_app())

    response = client.post(
        "/v1/owner/commands",
        headers={
            "X-OpenQilin-User-Id": "owner_llm_target",
            "X-OpenQilin-Connector": "discord",
        },
        json={
            "command": "llm_summarize",
            "args": ["project_1"],
            "idempotency_key": "idem-llm-target-component-12345",
        },
    )

    body = response.json()
    assert response.status_code == 202
    assert body["status"] == "accepted"
    assert body["dispatch_target"] == "llm"
    assert body["dispatch_id"]


def test_submit_owner_command_emits_observability_on_accept() -> None:
    app = create_control_plane_app()
    client = TestClient(app)

    response = client.post(
        "/v1/owner/commands",
        headers={
            "X-OpenQilin-User-Id": "owner_obs_accept",
            "X-OpenQilin-Connector": "discord",
            "X-OpenQilin-Trace-Id": "trace-observability-accept-component",
        },
        json={
            "command": "run_task",
            "args": ["alpha"],
            "idempotency_key": "idem-observability-accept-component-12345",
        },
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
    assert accepted_event.request_id == body["request_id"]
    assert accepted_event.task_id == body["task_id"]

    spans = services.tracer.get_spans()
    assert len(spans) == 1
    span_attrs = dict(spans[0].attributes)
    assert spans[0].trace_id == body["trace_id"]
    assert spans[0].name == "owner_command.ingress"
    assert span_attrs["outcome"] == "accepted"
    assert span_attrs["correlation.task_id"] == body["task_id"]


def test_submit_owner_command_emits_observability_on_policy_block() -> None:
    app = create_control_plane_app()
    client = TestClient(app)

    response = client.post(
        "/v1/owner/commands",
        headers={
            "X-OpenQilin-User-Id": "owner_obs_policy_block",
            "X-OpenQilin-Connector": "discord",
            "X-OpenQilin-Trace-Id": "trace-observability-policy-block-component",
        },
        json={
            "command": "deny_delete_project",
            "args": ["alpha"],
            "idempotency_key": "idem-observability-policy-block-component-12345",
        },
    )

    body = response.json()
    assert response.status_code == 403
    services = app.state.runtime_services
    metric_value = services.metric_recorder.get_counter_value(
        "owner_command_admission_outcomes_total",
        labels={"outcome": "blocked", "source": "policy_runtime"},
    )
    assert metric_value == 1

    audit_events = services.audit_writer.get_events()
    assert [event.event_type for event in audit_events] == [
        "policy.decision",
        "owner_command.blocked",
    ]
    blocked_event = audit_events[-1]
    blocked_task = services.runtime_state_repo.get_task_by_id(body["details"]["task_id"])
    assert blocked_task is not None
    assert blocked_event.outcome == "blocked"
    assert blocked_event.source == "policy_runtime"
    assert blocked_event.trace_id == blocked_task.trace_id
    assert blocked_event.task_id == blocked_task.task_id

    spans = services.tracer.get_spans()
    assert len(spans) == 1
    span_attrs = dict(spans[0].attributes)
    assert spans[0].status == "error"
    assert span_attrs["outcome"] == "blocked"
    assert span_attrs["source"] == "policy_runtime"
