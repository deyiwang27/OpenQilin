"""Issue #163 component tests - PM->DL pair-hop check in TaskDispatchService."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from openqilin.agents.domain_leader.models import DomainLeaderResponse
from openqilin.task_orchestrator.dispatch.target_selector import DispatchTargetError
from openqilin.task_orchestrator.loop_control import LoopCapBreachError, LoopState
from openqilin.task_orchestrator.services.lifecycle_service import TaskLifecycleService
from openqilin.task_orchestrator.services.task_service import TaskDispatchService
from tests.testing.infra_stubs import InMemoryRuntimeStateRepository


def _make_dl_agent() -> MagicMock:
    dl = MagicMock()
    dl.handle_escalation.return_value = DomainLeaderResponse(
        advisory_text="All good.",
        domain_outcome="resolved",
        trace_id="trace-dl",
    )
    return dl


def _make_service(*, domain_leader_agent: MagicMock | None = None) -> TaskDispatchService:
    return TaskDispatchService(
        lifecycle_service=TaskLifecycleService(runtime_state_repo=InMemoryRuntimeStateRepository()),
        sandbox_execution_adapter=MagicMock(),
        llm_dispatch_adapter=MagicMock(),
        domain_leader_agent=domain_leader_agent,
    )


def test_pm_dl_pair_cap_breach() -> None:
    """Two PM->DL escalations succeed; third raises LoopCapBreachError."""

    dl_agent = _make_dl_agent()
    svc = _make_service(domain_leader_agent=dl_agent)
    loop_state = LoopState()

    svc.escalate_to_domain_leader("Q1", "proj-001", "trace-1", loop_state=loop_state)
    svc.escalate_to_domain_leader("Q2", "proj-001", "trace-2", loop_state=loop_state)

    with pytest.raises(LoopCapBreachError):
        svc.escalate_to_domain_leader("Q3", "proj-001", "trace-3", loop_state=loop_state)

    assert dl_agent.handle_escalation.call_count == 2


def test_pm_dl_no_loop_state_no_cap() -> None:
    """When loop_state is None, pair check is skipped and DL is called freely."""

    dl_agent = _make_dl_agent()
    svc = _make_service(domain_leader_agent=dl_agent)

    for i in range(5):
        svc.escalate_to_domain_leader(f"Q{i}", "proj-001", f"trace-{i}")

    assert dl_agent.handle_escalation.call_count == 5


def test_pm_dl_no_agent_raises_dispatch_error() -> None:
    """DispatchTargetError raised when no domain_leader_agent is configured."""

    svc = _make_service()

    with pytest.raises(DispatchTargetError):
        svc.escalate_to_domain_leader("Q", "proj-001", "trace-1", loop_state=LoopState())
