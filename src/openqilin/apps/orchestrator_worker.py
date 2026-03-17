"""Async entrypoint for the OpenQilin orchestrator worker."""

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog

from openqilin.shared_kernel.config import RuntimeSettings
from openqilin.shared_kernel.startup_validation import enforce_connector_secret_hardening
from openqilin.task_orchestrator.workflow.graph import build_task_graph
from openqilin.task_orchestrator.workflow.state_models import WorkflowServices

if TYPE_CHECKING:
    from openqilin.control_plane.api.dependencies import RuntimeServices

LOGGER = structlog.get_logger(__name__)
READY_MARKER_PATH = Path("/tmp/openqilin.orchestrator_worker.ready")


def _mark_ready() -> None:
    """Emit deterministic ready marker for container health checks."""

    READY_MARKER_PATH.write_text("ready\n", encoding="utf-8")


def build_workflow_services(runtime_services: "RuntimeServices") -> WorkflowServices:
    """Build a WorkflowServices snapshot from a RuntimeServices container."""

    return WorkflowServices(
        policy_runtime_client=runtime_services.policy_runtime_client,
        budget_reservation_service=runtime_services.budget_reservation_service,
        task_dispatch_service=runtime_services.task_dispatch_service,
        runtime_state_repo=runtime_services.runtime_state_repo,
        audit_writer=runtime_services.audit_writer,
        metric_recorder=runtime_services.metric_recorder,
        tracer=runtime_services.tracer,
    )


def drain_queued_tasks(runtime_services: "RuntimeServices") -> int:
    """Synchronously process all queued tasks through the LangGraph graph.

    Intended for use in tests and integration fixtures.  Builds the graph,
    fetches every task with status == 'queued', and invokes the graph for each.

    Returns the number of tasks drained.
    """

    services = build_workflow_services(runtime_services)
    task_graph = build_task_graph(services)
    queued = [
        task for task in runtime_services.runtime_state_repo.list_tasks() if task.status == "queued"
    ]
    for task in queued:
        initial_state: dict[str, Any] = {
            "task_id": task.task_id,
            "project_id": task.project_id,
            "principal_role": task.principal_role,
            "command": task.command,
            "policy_decision": None,
            "policy_version": "",
            "policy_hash": "",
            "rule_ids": (),
            "obligation_satisfied": False,
            "blocking_obligation": None,
            "budget_decision": None,
            "dispatch_accepted": False,
            "dispatch_target": None,
            "dispatch_id": None,
            "dispatch_error_code": None,
            "llm_execution": None,
            "final_state": "queued",
            "loop_state": {},
        }
        try:
            task_graph.invoke(initial_state)
        except Exception:
            LOGGER.exception("worker.drain.task_error", task_id=task.task_id)
            runtime_services.runtime_state_repo.update_task_status(
                task.task_id,
                "failed",
                outcome_source="orchestrator_worker",
                outcome_error_code="worker_unhandled_exception",
                outcome_message="unhandled exception during task graph invocation",
            )
    return len(queued)


async def main(*, run_once: bool = False) -> None:
    """Run orchestrator worker bootstrap and steady-state polling loop."""

    enforce_connector_secret_hardening(RuntimeSettings())
    LOGGER.info("worker.bootstrap", worker="orchestrator_worker")
    _mark_ready()
    if run_once:
        return

    from openqilin.control_plane.api.dependencies import build_runtime_services

    runtime_services = build_runtime_services()
    services = build_workflow_services(runtime_services)
    task_graph = build_task_graph(services)

    while True:
        queued = [
            task
            for task in runtime_services.runtime_state_repo.list_tasks()
            if task.status == "queued"
        ]
        for task in queued:
            initial_state: dict[str, Any] = {
                "task_id": task.task_id,
                "project_id": task.project_id,
                "principal_role": task.principal_role,
                "command": task.command,
                "policy_decision": None,
                "policy_version": "",
                "policy_hash": "",
                "rule_ids": (),
                "obligation_satisfied": False,
                "blocking_obligation": None,
                "budget_decision": None,
                "dispatch_accepted": False,
                "dispatch_target": None,
                "dispatch_id": None,
                "dispatch_error_code": None,
                "llm_execution": None,
                "final_state": "queued",
                "loop_state": {},
            }
            try:
                await task_graph.ainvoke(initial_state)
            except Exception:
                LOGGER.exception("worker.loop.task_error", task_id=task.task_id)
                runtime_services.runtime_state_repo.update_task_status(
                    task.task_id,
                    "failed",
                    outcome_source="orchestrator_worker",
                    outcome_error_code="worker_unhandled_exception",
                    outcome_message="unhandled exception during task graph invocation",
                )
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
