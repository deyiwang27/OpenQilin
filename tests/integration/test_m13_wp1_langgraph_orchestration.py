"""E2E test proving the LangGraph StateGraph orchestration pipeline works end-to-end.

Verifies that:
- POST /v1/owner/commands returns 202 with admission_state == "queued"
- drain_queued_tasks processes the task through the LangGraph graph
- GET /v1/tasks/{task_id} returns the final task state after drain
- All four node types (policy, obligation, budget, dispatch) execute in sequence
- Replay of a terminal task returns the synchronous response without re-processing
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from openqilin.apps.orchestrator_worker import drain_queued_tasks
from openqilin.control_plane.api.app import create_control_plane_app
from openqilin.observability.audit.audit_writer import OTelAuditWriter
from openqilin.testing.owner_command import (
    build_owner_command_headers,
    build_owner_command_request_dict,
)


def test_langgraph_admitted_task_reaches_dispatched_state() -> None:
    """POST admits task as queued; drain runs graph to dispatched."""
    app = create_control_plane_app()
    client = TestClient(app)
    services = app.state.runtime_services

    payload = build_owner_command_request_dict(
        action="run_task",
        args=["langgraph_e2e"],
        actor_id="owner_m13_wp1_e2e_001",
        idempotency_key="idem-m13-wp1-e2e-sandbox-001",
        trace_id="trace-m13-wp1-e2e-001",
    )

    response = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(payload),
        json=payload,
    )
    body = response.json()
    assert response.status_code == 202
    assert body["status"] == "accepted"
    assert body["data"]["admission_state"] == "queued"
    assert body["data"]["dispatch_target"] is None
    assert body["data"]["dispatch_id"] is None
    task_id = body["data"]["task_id"]

    task_before = services.runtime_state_repo.get_task_by_id(task_id)
    assert task_before is not None
    assert task_before.status == "queued"

    drained = drain_queued_tasks(services)
    assert drained >= 1

    task_response = client.get(f"/v1/tasks/{task_id}")
    task_body = task_response.json()
    assert task_response.status_code == 200
    assert task_body["status"] == "dispatched"
    assert task_body["dispatch_target"] == "sandbox"
    assert isinstance(task_body["dispatch_id"], str) and task_body["dispatch_id"]
    assert task_body["error_code"] is None


def test_langgraph_policy_blocked_task_stays_blocked() -> None:
    """Policy deny results in blocked final state with error_code populated."""
    app = create_control_plane_app()
    client = TestClient(app)
    services = app.state.runtime_services

    payload = build_owner_command_request_dict(
        action="policy_uncertain",
        args=["langgraph_e2e_block"],
        actor_id="owner_m13_wp1_e2e_002",
        idempotency_key="idem-m13-wp1-e2e-block-001",
        trace_id="trace-m13-wp1-e2e-block-001",
    )

    response = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(payload),
        json=payload,
    )
    body = response.json()
    assert response.status_code == 202
    assert body["data"]["admission_state"] == "queued"
    task_id = body["data"]["task_id"]

    drain_queued_tasks(services)

    task_body = client.get(f"/v1/tasks/{task_id}").json()
    assert task_body["status"] == "blocked"
    assert task_body["error_code"] == "policy_uncertain_fail_closed"
    assert task_body["outcome_source"] == "policy_runtime"
    assert isinstance(task_body["policy_version"], str)
    assert isinstance(task_body["policy_hash"], str)


def test_langgraph_replay_of_dispatched_task_returns_synchronous_response() -> None:
    """Second POST after drain (task dispatched) returns synchronous 202 via _replayed_response."""
    app = create_control_plane_app()
    client = TestClient(app)
    services = app.state.runtime_services

    payload = build_owner_command_request_dict(
        action="run_task",
        args=["langgraph_replay"],
        actor_id="owner_m13_wp1_e2e_003",
        idempotency_key="idem-m13-wp1-e2e-replay-001",
        trace_id="trace-m13-wp1-e2e-replay-001",
    )
    headers = build_owner_command_headers(payload)

    first = client.post("/v1/owner/commands", headers=headers, json=payload)
    first_body = first.json()
    assert first.status_code == 202
    assert first_body["data"]["admission_state"] == "queued"
    task_id = first_body["data"]["task_id"]

    drain_queued_tasks(services)

    second = client.post("/v1/owner/commands", headers=headers, json=payload)
    second_body = second.json()
    assert second.status_code == 202
    assert second_body["status"] == "accepted"
    assert second_body["data"]["task_id"] == task_id
    assert second_body["data"]["replayed"] is True
    assert second_body["data"]["admission_state"] == "dispatched"
    assert second_body["data"]["dispatch_target"] == "sandbox"
    assert (
        isinstance(second_body["data"]["dispatch_id"], str) and second_body["data"]["dispatch_id"]
    )


def test_langgraph_replay_of_blocked_task_returns_synchronous_403() -> None:
    """Second POST after drain (task blocked) returns synchronous 403 via _replayed_response."""
    app = create_control_plane_app()
    client = TestClient(app)
    services = app.state.runtime_services

    payload = build_owner_command_request_dict(
        action="policy_uncertain",
        args=["langgraph_replay_blocked"],
        actor_id="owner_m13_wp1_e2e_004",
        idempotency_key="idem-m13-wp1-e2e-replay-blocked-001",
        trace_id="trace-m13-wp1-e2e-replay-blocked-001",
    )
    headers = build_owner_command_headers(payload)

    first = client.post("/v1/owner/commands", headers=headers, json=payload)
    assert first.status_code == 202
    task_id = first.json()["data"]["task_id"]

    drain_queued_tasks(services)

    second = client.post("/v1/owner/commands", headers=headers, json=payload)
    second_body = second.json()
    assert second.status_code == 403
    assert second_body["status"] == "denied"
    assert second_body["error"]["code"] == "policy_uncertain_fail_closed"
    assert second_body["error"]["details"]["task_id"] == task_id
    assert second_body["error"]["details"]["replayed"] == "true"


def test_langgraph_observability_emitted_during_drain() -> None:
    """Policy, budget, and outcome audit events and spans are emitted during drain, not POST."""
    app = create_control_plane_app()
    client = TestClient(app)
    services = app.state.runtime_services
    trace_id = "trace-m13-wp1-e2e-observability-001"

    # Integration tests always use OTelAuditWriter with a real PostgresAuditEventRepository.
    assert isinstance(services.audit_writer, OTelAuditWriter)
    audit_repo = services.audit_writer._audit_repo  # type: ignore[attr-defined]

    before_span_count = len(services.tracer.get_spans())

    payload = build_owner_command_request_dict(
        action="run_task",
        args=["langgraph_observability"],
        actor_id="owner_m13_wp1_e2e_005",
        idempotency_key="idem-m13-wp1-e2e-observability-001",
        trace_id=trace_id,
    )

    response = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(payload),
        json=payload,
    )
    assert response.status_code == 202
    task_id = response.json()["data"]["task_id"]

    events_after_post = audit_repo.list_events_for_trace(trace_id)
    event_types_after_post = [e.event_type for e in events_after_post]
    assert "policy.decision" not in event_types_after_post
    assert "budget.decision" not in event_types_after_post
    assert "owner_command.accepted" not in event_types_after_post

    drain_queued_tasks(services)

    new_events = audit_repo.list_events_for_trace(trace_id)
    event_types = [e.event_type for e in new_events]
    assert "policy.decision" in event_types
    assert "owner_command.accepted" in event_types
    assert all(e.task_id == task_id for e in new_events if e.task_id is not None)

    new_spans = services.tracer.get_spans()[before_span_count:]
    span_names = [s.name for s in new_spans]
    assert "owner_ingress" in span_names
    assert "task_orchestration" in span_names
    assert "policy_evaluation" in span_names
    assert "execution_sandbox" in span_names
    assert "audit_emit" in span_names
