"""M16-WP5 component tests for loop-cap breach handling and pair enforcement."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from openqilin.agents.specialist.models import SpecialistResponse
from openqilin.apps import orchestrator_worker
from openqilin.control_plane.api.app import create_control_plane_app
from openqilin.data_access.repositories.runtime_state import TaskRecord
from openqilin.task_orchestrator.admission.envelope_validator import AdmissionEnvelope
from openqilin.task_orchestrator.loop_control import LoopCapBreachError, LoopState
from openqilin.task_orchestrator.services.lifecycle_service import TaskLifecycleService
from openqilin.task_orchestrator.services.task_service import TaskDispatchService
from tests.testing.infra_stubs import InMemoryRuntimeStateRepository


def _seed_queued_task(services: object, *, suffix: str) -> str:
    runtime_state_repo = getattr(services, "runtime_state_repo")
    envelope = AdmissionEnvelope(
        request_id=f"req-{suffix}",
        trace_id=f"trace-{suffix}",
        principal_id="owner-loop-test",
        principal_role="owner",
        trust_domain="project",
        connector="discord",
        command="run_task",
        target="sandbox",
        args=("alpha",),
        metadata=(
            ("sender_role", "owner"),
            ("message_type", "owner_command"),
        ),
        project_id="project-loop",
        idempotency_key=f"idem-{suffix}",
    )
    task = runtime_state_repo.create_task_from_envelope(envelope)
    return task.task_id


def _specialist_task_record(*, task_id: str) -> TaskRecord:
    return TaskRecord(
        task_id=task_id,
        request_id=f"req-{task_id}",
        trace_id=f"trace-{task_id}",
        principal_id="project_manager",
        principal_role="project_manager",
        trust_domain="project",
        connector="internal",
        command="execute_specialist_task",
        target="specialist",
        args=("execute",),
        metadata=(("dispatch_source", "project_manager"),),
        project_id="project-specialist",
        idempotency_key=f"idem-{task_id}",
        status="authorized",
        created_at=datetime.now(tz=UTC),
    )


def test_hop_cap_breach_blocks_task(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_control_plane_app()
    services = app.state.runtime_services
    task_id = _seed_queued_task(services, suffix="hop-block")

    monkeypatch.setattr(orchestrator_worker, "LoopState", lambda: LoopState(hop_count=5))
    orchestrator_worker.drain_queued_tasks(services)

    task = services.runtime_state_repo.get_task_by_id(task_id)
    assert task is not None
    assert task.status == "blocked"
    assert task.outcome_error_code == "loop_cap_breach"


def test_hop_cap_breach_emits_audit_event(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_control_plane_app()
    services = app.state.runtime_services
    _seed_queued_task(services, suffix="hop-audit")

    monkeypatch.setattr(orchestrator_worker, "LoopState", lambda: LoopState(hop_count=5))
    orchestrator_worker.drain_queued_tasks(services)

    assert any(
        event.event_type == "loop_cap.breach" for event in services.audit_writer.get_events()
    )


def test_hop_cap_breach_increments_metric(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_control_plane_app()
    services = app.state.runtime_services
    _seed_queued_task(services, suffix="hop-metric")

    monkeypatch.setattr(orchestrator_worker, "LoopState", lambda: LoopState(hop_count=5))
    orchestrator_worker.drain_queued_tasks(services)

    assert (
        services.metric_recorder.get_counter_value(
            "loop_cap_breach_total",
            labels={"cap_type": "hop_count"},
        )
        >= 1
    )


def test_separate_tasks_independent_loop_state() -> None:
    app = create_control_plane_app()
    services = app.state.runtime_services
    task_a = _seed_queued_task(services, suffix="loop-a")
    task_b = _seed_queued_task(services, suffix="loop-b")

    orchestrator_worker.drain_queued_tasks(services)

    record_a = services.runtime_state_repo.get_task_by_id(task_a)
    record_b = services.runtime_state_repo.get_task_by_id(task_b)
    assert record_a is not None
    assert record_b is not None
    assert record_a.status == "dispatched"
    assert record_b.status == "dispatched"
    assert record_a.outcome_error_code != "loop_cap_breach"
    assert record_b.outcome_error_code != "loop_cap_breach"


def test_pm_specialist_pair_cap_breach() -> None:
    specialist_agent = MagicMock()
    specialist_agent.handle.return_value = SpecialistResponse(
        execution_status="completed",
        output_text="done",
        artifact_id="artifact-001",
        blocker=None,
        trace_id="trace-specialist",
    )

    lifecycle_service = TaskLifecycleService(runtime_state_repo=InMemoryRuntimeStateRepository())
    task_dispatch_service = TaskDispatchService(
        lifecycle_service=lifecycle_service,
        sandbox_execution_adapter=MagicMock(),
        llm_dispatch_adapter=MagicMock(),
        specialist_agent=specialist_agent,
    )

    loop_state = LoopState()
    task_dispatch_service.dispatch_admitted_task(
        _specialist_task_record(task_id="task-specialist-1"),
        loop_state=loop_state,
    )
    task_dispatch_service.dispatch_admitted_task(
        _specialist_task_record(task_id="task-specialist-2"),
        loop_state=loop_state,
    )

    with pytest.raises(LoopCapBreachError):
        task_dispatch_service.dispatch_admitted_task(
            _specialist_task_record(task_id="task-specialist-3"),
            loop_state=loop_state,
        )

    assert specialist_agent.handle.call_count == 2
