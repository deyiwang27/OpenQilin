"""Integration tests for M13-WP2: loop cap enforcement in the orchestrator drain path.

Verifies:
- A task with a pre-exhausted loop_state (hop_count at limit) is blocked after drain
- Task status = "blocked" with error_code = "loop_cap_breach" after 6th hop
- Audit event "loop_cap.breach" is emitted during drain
- LoopState is per-task: multiple tasks in a single drain cycle are independent
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from openqilin.apps.orchestrator_worker import drain_queued_tasks
from openqilin.control_plane.api.app import create_control_plane_app
from openqilin.task_orchestrator.loop_control import LoopCapBreachError, LoopState
from openqilin.testing.owner_command import (
    build_owner_command_headers,
    build_owner_command_request_dict,
)


def _admit_task(client: TestClient, *, action: str, actor_id: str, idempotency_key: str) -> str:
    """Admit a task via POST /v1/owner/commands; return task_id."""
    payload = build_owner_command_request_dict(
        action=action,
        args=["loop_cap_test"],
        actor_id=actor_id,
        idempotency_key=idempotency_key,
        trace_id=f"trace-{idempotency_key}",
    )
    resp = client.post(
        "/v1/owner/commands",
        headers=build_owner_command_headers(payload),
        json=payload,
    )
    assert resp.status_code == 202
    return resp.json()["data"]["task_id"]


def test_loop_cap_breach_blocks_task_and_emits_audit_event() -> None:
    """Task with hop_count at limit=5 is blocked on 6th hop; audit event emitted."""
    from openqilin.observability.audit.audit_writer import OTelAuditWriter

    app = create_control_plane_app()
    client = TestClient(app)
    services = app.state.runtime_services

    task_id = _admit_task(
        client,
        action="run_task",
        actor_id="owner_m13_wp2_loop_001",
        idempotency_key="idem-m13-wp2-loop-breach-001",
    )

    # Manually pre-exhaust the loop state so the next drain triggers a breach.
    # drain_queued_tasks creates a new LoopState per task; simulate by patching
    # the task to appear as if 5 hops have already occurred — achieved by
    # monkey-patching LoopState to start at hop_count=5.
    original_init = LoopState.__init__

    def exhausted_init(self: LoopState) -> None:
        original_init(self)
        self.hop_count = 5  # one more hop → breach

    LoopState.__init__ = exhausted_init  # type: ignore[method-assign, assignment]
    try:
        drained = drain_queued_tasks(services)
    finally:
        LoopState.__init__ = original_init  # type: ignore[method-assign, assignment]

    assert drained >= 1

    task_resp = client.get(f"/v1/tasks/{task_id}")
    task_body = task_resp.json()
    assert task_resp.status_code == 200
    assert task_body["status"] == "blocked"
    assert task_body["error_code"] == "loop_cap_breach"

    assert isinstance(services.audit_writer, OTelAuditWriter)
    audit_repo = services.audit_writer._audit_repo  # type: ignore[attr-defined]
    task_record = services.runtime_state_repo.get_task_by_id(task_id)
    assert task_record is not None
    new_events = audit_repo.list_events_for_trace(task_record.trace_id)
    event_types = [e.event_type for e in new_events]
    assert "loop_cap.breach" in event_types

    breach_events = [e for e in new_events if e.event_type == "loop_cap.breach"]
    assert len(breach_events) == 1
    assert breach_events[0].task_id == task_id


def test_loop_states_are_independent_across_tasks_in_same_drain() -> None:
    """Two tasks in the same drain cycle do not share loop state."""
    app = create_control_plane_app()
    client = TestClient(app)
    services = app.state.runtime_services

    task_id_1 = _admit_task(
        client,
        action="run_task",
        actor_id="owner_m13_wp2_loop_002a",
        idempotency_key="idem-m13-wp2-loop-indep-001",
    )
    task_id_2 = _admit_task(
        client,
        action="run_task",
        actor_id="owner_m13_wp2_loop_002b",
        idempotency_key="idem-m13-wp2-loop-indep-002",
    )

    drained = drain_queued_tasks(services)
    assert drained >= 2

    # Both tasks should complete normally (dispatched) since LoopState is fresh per task.
    # 4 hops for a normal run (policy+obligation+budget+dispatch) is within limit=5.
    for task_id in (task_id_1, task_id_2):
        resp = client.get(f"/v1/tasks/{task_id}")
        body = resp.json()
        assert resp.status_code == 200
        assert body["status"] == "dispatched", (
            f"task {task_id} expected dispatched, got {body['status']}"
        )
        assert body["error_code"] is None


def test_loop_cap_breach_error_attributes() -> None:
    """LoopCapBreachError carries correct cap_type, count, limit attributes."""
    err = LoopCapBreachError("hop_count", 6, 5)
    assert err.cap_type == "hop_count"
    assert err.count == 6
    assert err.limit == 5
    assert err.pair is None

    pair_err = LoopCapBreachError("pair_rounds", 3, 2, pair=("pm", "dl"))
    assert pair_err.cap_type == "pair_rounds"
    assert pair_err.pair == ("pm", "dl")
