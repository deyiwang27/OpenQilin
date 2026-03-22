"""LangGraph TaskState TypedDict and WorkflowServices container."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from typing_extensions import TypedDict

from openqilin.task_orchestrator.loop_control import LoopState

if TYPE_CHECKING:
    from openqilin.budget_runtime.service import BudgetReservationService  # type: ignore[import-untyped]
    from openqilin.data_access.repositories.postgres.task_repository import PostgresTaskRepository
    from openqilin.observability.audit.audit_writer import OTelAuditWriter
    from openqilin.observability.metrics.recorder import OTelMetricRecorder
    from openqilin.observability.testing.stubs import (
        InMemoryAuditWriter,
        InMemoryMetricRecorder,
        InMemoryTracer,
    )
    from openqilin.policy_runtime_integration.client import PolicyRuntimeClient
    from openqilin.task_orchestrator.services.task_service import TaskDispatchService


class TaskState(TypedDict):
    """Mutable state threaded through the LangGraph orchestration nodes.

    Each node reads required fields, performs its action, updates the
    runtime_state_repo directly, and returns a partial dict with updated fields
    for routing logic.
    """

    task_id: str
    project_id: str | None
    principal_role: str
    command: str
    # Policy gate output
    policy_decision: str | None
    policy_version: str
    policy_hash: str
    rule_ids: tuple[str, ...]
    # Obligation gate output
    obligation_satisfied: bool
    blocking_obligation: str | None
    # Dispatch output
    dispatch_accepted: bool
    dispatch_target: str | None
    dispatch_id: str | None
    dispatch_error_code: str | None
    # LLM execution metadata (stored for task status endpoint)
    llm_execution: dict[str, Any] | None
    # Terminal state written by whichever node finishes the task
    final_state: str
    # Per-task loop cap tracking (M13-WP2)
    loop_state: LoopState


@dataclass(frozen=True, slots=True)
class WorkflowServices:
    """Snapshot of runtime service references injected into LangGraph nodes.

    Built once per worker invocation cycle and captured by node closures.
    """

    policy_runtime_client: PolicyRuntimeClient
    budget_reservation_service: BudgetReservationService
    task_dispatch_service: TaskDispatchService
    runtime_state_repo: PostgresTaskRepository
    audit_writer: InMemoryAuditWriter | OTelAuditWriter
    metric_recorder: InMemoryMetricRecorder | OTelMetricRecorder
    tracer: InMemoryTracer
