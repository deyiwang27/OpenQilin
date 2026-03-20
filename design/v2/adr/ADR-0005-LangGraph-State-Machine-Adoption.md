# ADR-0005 — LangGraph StateGraph Adoption for Task Orchestration

**Date:** 2026-03-17
**Status:** Approved
**Author:** Claude (Architect)
**Ratified by:** Owner — approved retroactively on 2026-03-17 (M13-WP1 merge)
**Supersedes:** —
**Superseded by:** —

---

## Context

Prior to M13, task orchestration was implemented as a linear synchronous flow inside the HTTP request handler (`owner_commands.py`). The request handler received a task, evaluated policy, applied obligations, reserved budget, and dispatched — all in a single synchronous call chain before returning the HTTP response.

This violated bug finding C-9 ("orchestration is not a real state machine") and created several structural problems:
- The HTTP response was blocked until the full dispatch chain completed, coupling latency to policy/budget evaluation time.
- There was no durable task state between orchestration steps — a crash mid-pipeline lost the task silently.
- Adding new pipeline stages (e.g., loop cap enforcement, project-space routing) required modifying the HTTP handler directly.
- The pipeline had no conditional branching — all paths executed regardless of prior step outcomes.

M13 required a real orchestration engine that could express the four-node pipeline as a graph with conditional exit edges.

---

## Decision

Adopt **LangGraph `StateGraph`** as the task orchestration runtime, running in a dedicated async worker process separate from the HTTP control plane.

**Architecture:**
- The HTTP handler (`owner_commands.py`) becomes admission-only: it validates the request, enqueues a task with status `queued` in PostgreSQL, and returns `202 Accepted`.
- A separate `orchestrator_worker.py` process polls PostgreSQL for `queued` tasks and invokes the LangGraph graph for each.
- The graph (`task_orchestrator/workflow/graph.py`) defines three nodes with conditional edges:
  ```
  policy_evaluation_node
    → (denied/error) END
    → (authorized) obligation_check_node
        → (not satisfied) END
        → (satisfied) dispatch_node → END
  ```
  Note: a standalone `budget_reservation_node` existed between obligation_check_node and dispatch_node until M15-WP3, when it was removed. Budget reservation is now handled exclusively via the `reserve_budget` obligation within obligation_check_node.
- Each node is a **closure over `WorkflowServices`**, making the graph stateless across invocations and safe to reuse between polling cycles.
- Task state is typed as `TaskState` (TypedDict), flowing through the graph as an immutable snapshot updated by each node.

**Loop cap enforcement** is layered on top: `LoopState` tracks hop and pair counts per task; `check_and_increment_hop/pair()` raises `LoopCapBreachError` before dispatching if limits are exceeded.

**LangSmith tracing** is optional: when `LANGCHAIN_TRACING_V2=true` is set, LangGraph emits traces automatically. This is not an audit source and does not satisfy governance audit requirements.

---

## Rationale

| Option | Reason accepted / rejected |
|---|---|
| **Chosen: LangGraph StateGraph** | Already a project dependency (M11 added `langgraph>=0.2`). Native support for typed state, conditional edges, and async node execution. Well-aligned with the pipeline's linear-with-early-exit topology. |
| Alternative: Custom state machine (hand-rolled) | More code to maintain, harder to visualize, no built-in tracing integration. |
| Alternative: Celery / task queue | Heavyweight; requires separate broker service; overkill for a single-tenant solopreneur system. Celery has no native graph/conditional edge semantics. |
| Alternative: Temporal / Prefect | Production orchestration platforms designed for distributed teams. Adds significant operational complexity for a solo operator. |
| Alternative: Keep synchronous HTTP handler | Does not fix C-9. Cannot support durable mid-pipeline state. Blocks HTTP connection during policy evaluation. |

---

## Consequences

- **Implementation:** `workflow/graph.py`, `workflow/nodes.py`, `workflow/state_models.py`, `state/state_machine.py`, `apps/orchestrator_worker.py`.
- **Tests:** E2E LangGraph tests in `test_m13_wp1_langgraph_orchestration.py`; node unit tests with mock `WorkflowServices`; conditional edge routing tests.
- **Governance:** Owner commands now return `202` immediately. Callers must poll `GET /v1/tasks/{task_id}` for status. All node functions must be fail-closed: non-authorized/non-approved outcomes exit to END, never proceed to dispatch.
- **Compose:** Orchestrator worker is a separate process. `compose.yml` must run both `api_app` (control plane) and `orchestrator_worker` services.
- **LangGraph dependency:** `langgraph>=0.2` and `langchain-core>=0.2` added to `pyproject.toml` (already present from M11).

---

## References

- Spec: `spec/orchestration/control/TaskOrchestrator.md`
- Component delta: `design/v2/components/OrchestratorComponentDelta-v2.md`
- Milestone design: `design/v2/architecture/M13-ProjectSpaceAndOrchestrationModuleDesign-v2.md`
- Implementing commit: `68c175e` — feat(m13-wp1): adopt LangGraph StateGraph for task orchestration pipeline
- GitHub issue: #89 (M13-WP1)
- Related: ADR-0008 (InMemory Stub Removal, which completes the worker infrastructure)
