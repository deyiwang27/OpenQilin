# M13 Work Packages — Project Space Binding, Routing, and Orchestration Foundation

Milestone: `M13`
Status: `planned`
Entry gate: M12 complete (OPA live, PostgreSQL wired, role self-assertion fixed)
Design ref: `design/v2/architecture/M13-ProjectSpaceAndOrchestrationModuleDesign-v2.md`, `design/v2/adr/ADR-0005`, `design/v2/components/OrchestratorComponentDelta-v2.md`

---

## Milestone Goal

Adopt LangGraph as the real orchestration engine, replacing the linear HTTP-handler call chain. Introduce project-space binding and PM-default routing. Activate Domain Leader as a backend-routed virtual agent. Fix the snapshot split-brain bug. Begin real sandbox enforcement.

---

## WP M13-01 — LangGraph Orchestration Adoption

**Goal:** Replace the linear synchronous call chain inside the HTTP request handler with a real LangGraph StateGraph running in an async worker loop.

**Bug ref:** C-9 | **Design ref:** `design/v2/adr/ADR-0005-LangGraph-State-Machine-Adoption.md`, `design/v2/components/OrchestratorComponentDelta-v2.md §1.1, §1.5`

**Entry criteria:** M12 complete; PostgreSQL task queue available; OPA and obligation dispatcher wired.

### Tasks

- [ ] Add `langgraph>=0.2` and `langchain-core>=0.2` to `pyproject.toml`
- [ ] Create `src/openqilin/task_orchestrator/workflow/state_models.py` — `TaskState` TypedDict: `task_id`, `project_id`, `principal_role`, `command`, `policy_decision`, `obligation_result`, `budget_reservation`, `final_state`, `loop_state`
- [ ] Implement `workflow/nodes.py` — four async node functions:
  - `policy_evaluation_node(state)` — calls `OPAPolicyRuntimeClient.evaluate()`; returns updated state with `policy_decision`
  - `obligation_check_node(state)` — calls `ObligationDispatcher.apply()`; returns updated state with `obligation_result`
  - `budget_reservation_node(state)` — calls budget client reserve (M14 completes this; M13 wires the stub that will be swapped)
  - `dispatch_node(state)` — dispatches to execution sandbox; writes final status
- [ ] Implement `workflow/graph.py` — `build_task_graph()` returns a compiled `StateGraph` connecting the four nodes with conditional edges for `blocked` and `failed` outcomes; replace the existing one-line placeholder
- [ ] Implement `state/state_machine.py` — graph compilation and transition enforcement using `transition_guard`; replace the existing one-line placeholder
- [ ] Implement `apps/orchestrator_worker.py` as real async polling loop:
  ```python
  async def run():
      task_graph = build_task_graph()
      async for task in task_queue.subscribe():
          async with db_session() as session:
              try:
                  result = await task_graph.ainvoke({"task_id": task.id})
                  await update_task_status(session, task.id, result.final_state)
              except Exception as e:
                  await update_task_status(session, task.id, "failed", reason=str(e))
  ```
- [ ] Update HTTP command handler to be admission-only: insert task as `queued` → return `accepted {task_id}` immediately; remove all orchestration logic from HTTP handler

### Outputs

- LangGraph `StateGraph` active as the real orchestration engine
- `orchestrator_worker` is a real async processing loop
- HTTP handler is admission-only

### Done criteria

- [ ] End-to-end test: `queued` task progresses through all four nodes to `completed` via real LangGraph graph
- [ ] OPA deny in `policy_evaluation_node` → task transitions to `blocked` without reaching dispatch
- [ ] HTTP handler returns `202 accepted` immediately; task result visible only via status poll
- [ ] `InMemory` task state machine placeholder replaced

---

## WP M13-02 — Loop Controls Enforcement

**Goal:** Implement per-trace hop count and pair-round caps. On breach: audit event, task blocked, owner notified.

**Design ref:** `design/v2/components/OrchestratorComponentDelta-v2.md §1.4`, `spec/orchestration/communication/AgentLoopControls.md`

**Entry criteria:** WP M13-01 complete (LangGraph nodes exist).

### Tasks

- [ ] Implement `src/openqilin/task_orchestrator/loop_control.py`:
  - `LoopState` dataclass: `hop_count: int = 0`, `pair_rounds: dict[tuple[str, str], int]`
  - `check_and_increment_hop(state, limit=5)` — raises `LoopCapBreachError("hop_count", count)` if exceeded
  - `check_and_increment_pair(state, sender, recipient, limit=2)` — per-pair tracking; raises `LoopCapBreachError("pair_rounds", count)` if exceeded
- [ ] Add `loop_state: LoopState` field to `TaskState` (WP M13-01)
- [ ] Call `check_and_increment_hop()` in each LangGraph node before processing
- [ ] Call `check_and_increment_pair()` for all A2A delegation hops (PM → DL, DL → specialist)
- [ ] Wire `LoopCapBreachError` handler in the LangGraph graph exception path: emit audit event → task `blocked` → owner notification
- [ ] Add integration tests: 6th hop raises `LoopCapBreachError`; 3rd pair round for same pair raises `LoopCapBreachError`

### Outputs

- Loop cap enforced on all inter-agent hops in every task trace
- Cap breach produces audit event and blocked task (not silent drop)

### Done criteria

- [ ] Trace with 6 hops is blocked after the 5th; task status = `blocked`
- [ ] Audit event emitted on cap breach
- [ ] `LoopState` is per-task (not shared across tasks)
- [ ] Owner notified on loop cap breach

---

## WP M13-03 — Project Space Binding and Routing

**Goal:** Automate Discord channel creation and binding per project. Resolve inbound Discord messages to project context and PM-default routing.

**Design ref:** `design/v2/architecture/M13-ProjectSpaceAndOrchestrationModuleDesign-v2.md §3`, `spec/orchestration/communication/ProjectSpaceBindingModel.md`

**Entry criteria:** M12 PostgreSQL repos active; Discord connector running.

### Tasks

- [ ] Write Alembic migration `0007_create_project_space_bindings_table.py`:
  - `project_space_bindings(id, project_id, guild_id, channel_id, binding_state, default_recipient, created_at, updated_at)`
- [ ] Implement `src/openqilin/project_spaces/models.py` — `ProjectSpaceBinding`, `BindingState` enum (`proposed → pending_approval → active → archived → locked`), `LifecycleEvent`
- [ ] Implement `src/openqilin/project_spaces/binding_repository.py` — `PostgresProjectSpaceBindingRepository`
- [ ] Implement `src/openqilin/project_spaces/discord_automator.py`:
  - `create_channel(project_id, guild_id)` — creates Discord channel; returns `channel_id`
  - `archive_channel(channel_id)` — marks channel read-only
  - `lock_channel(channel_id)` — locks channel for terminal project states
- [ ] Implement `src/openqilin/project_spaces/binding_service.py` — `ProjectSpaceBindingService`:
  - `create_and_bind(project_id)` — creates channel, inserts binding record
  - `transition(project_id, event)` — updates binding state; triggers automator
- [ ] Implement `src/openqilin/project_spaces/routing_resolver.py` — `ProjectSpaceRoutingResolver`:
  - `resolve(guild_id, channel_id)` → `RoutingContext | None`
  - Default recipient = `project_manager` per PSB-004
  - Unknown channel → `None` (fail-closed)
- [ ] Wire routing resolver into Discord ingress path: resolve channel → project context before grammar layer

### Outputs

- Project space created and Discord channel bound automatically on project creation
- All inbound project-channel messages routed to PM by default
- Binding state follows project lifecycle

### Done criteria

- [ ] Project creation triggers automatic Discord channel creation and binding record insert
- [ ] Message in known project channel resolves to correct `project_id` and `project_manager`
- [ ] Message in unknown channel returns `None` routing context; fails closed
- [ ] `binding_state` transitions (active → archived) reflected in Discord channel status

---

## WP M13-04 — H-3 Fix: Snapshot Split-Brain

**Goal:** Fix the split-brain where a filesystem write failure leaves disk and in-memory state diverged with no recovery protocol.

**Bug ref:** H-3 | **Design ref:** `design/v2/components/OrchestratorComponentDelta-v2.md §1.6`

**Entry criteria:** WP M12-03 complete (PostgreSQL task repo active — H-3 is fixed by writing durable state to PostgreSQL instead of filesystem).

### Tasks

- [ ] In `src/openqilin/data_access/repositories/runtime_state.py` `update_task_status()`: reorder operations:
  1. `assert_legal_transition()` (transition guard — already wired in WP M12-07)
  2. `await self._pg_repo.update_status(task_id, status)` — durable write first
  3. `self._tasks[task_id].status = status` — in-memory cache update only after durable write succeeds
- [ ] Remove all filesystem-based `_flush_snapshot()` calls — PostgreSQL is now the durable store
- [ ] Add unit test: simulated PostgreSQL write failure → in-memory state NOT updated; exception propagated

### Outputs

- Task state durably written to PostgreSQL before in-memory cache update
- No filesystem snapshot dependency

### Done criteria

- [ ] Simulated DB write failure → in-memory state unchanged; error propagated to caller
- [ ] Process restart → task state recovered from PostgreSQL, not in-memory or filesystem

---

## WP M13-05 — Domain Leader Virtual Agent Activation

**Goal:** Activate Domain Leader as a backend-routed virtual agent scoped to project context. DL is not a standalone Discord bot; it is surfaced only through PM escalation.

**Design ref:** `design/v2/architecture/M13-ProjectSpaceAndOrchestrationModuleDesign-v2.md §3`

**Entry criteria:** WP M13-01 (LangGraph active), WP M13-03 (project-space routing active), M12 OPA wired.

### Tasks

- [ ] Create `src/openqilin/agents/domain_leader/` package: `agent.py`, `escalation_handler.py`, `prompts.py`, `models.py`
- [ ] Implement `DomainLeaderAgent.handle_escalation(request)` — receives PM escalation; produces domain response; does NOT reply directly to Discord channel
- [ ] Implement `EscalationHandler` — PM calls DL; DL produces `DLResponse`; PM synthesizes response for channel reply
- [ ] Bind DL to project context: DL always requires `project_id` in request; rejected without it
- [ ] Confirm DL is NOT a default Discord channel participant; NOT accessible by direct owner mention (no DM surface)
- [ ] Add integration test: PM escalates to DL; DL response returned to PM; channel receives PM-synthesized reply (not raw DL response)

### Outputs

- `DomainLeaderAgent` active as backend-routed virtual agent
- DL surfaced only through PM escalation path

### Done criteria

- [ ] PM escalation to DL produces DL domain response
- [ ] DL response NOT sent directly to Discord channel
- [ ] DL invocation without `project_id` is rejected
- [ ] DL not accessible via direct owner message or DM

---

## WP M13-06 — Sandbox Enforcement Scaffolding

**Goal:** Replace the empty `enforcement.py` placeholder with real sandbox enforcement scaffolding. Full isolation is out of scope for M13; M13 delivers the seccomp profile application hook.

**Bug ref:** C-10 (partial) | **Design ref:** `design/v2/architecture/M13-ProjectSpaceAndOrchestrationModuleDesign-v2.md §3`

**Entry criteria:** `execution_sandbox/profiles/enforcement.py` exists as empty placeholder.

### Tasks

- [ ] Replace placeholder with `SandboxProfileEnforcer` class with real enforcement logic
- [ ] Create `src/openqilin/execution_sandbox/profiles/seccomp_profiles/default.json` — seccomp profile for sandboxed tool execution
- [ ] Apply seccomp profile to subprocess execution via `subprocess.Popen` options (M13 scope)
- [ ] Enforce `sandbox_profile` from obligation dispatcher: `enforce_sandbox_profile` handler now calls `SandboxProfileEnforcer.bind(dispatch_target, profile)`
- [ ] Document that full namespace/process isolation is deferred to a post-MVP-v2 milestone

### Outputs

- `SandboxProfileEnforcer` with real seccomp profile binding (not empty placeholder)
- `SAF-001` partially met in M13

### Done criteria

- [ ] `enforcement.py` is no longer an empty placeholder
- [ ] Subprocess tool execution has seccomp profile applied
- [ ] `enforce_sandbox_profile` obligation handler calls real enforcer

---

## M13 Exit Criteria

- [ ] All six WPs above are marked done
- [ ] LangGraph `StateGraph` is the active orchestration engine in production
- [ ] Project spaces are created automatically; PM-default routing works
- [ ] Domain Leader active as a backend-routed virtual agent
- [ ] H-3 snapshot split-brain fixed
- [ ] Loop caps enforced on all inter-agent hops
- [ ] No `InMemory` placeholder used in any new orchestration path

## References

- `design/v2/adr/ADR-0005-LangGraph-State-Machine-Adoption.md`
- `design/v2/architecture/M13-ProjectSpaceAndOrchestrationModuleDesign-v2.md`
- `design/v2/components/OrchestratorComponentDelta-v2.md`
- `spec/orchestration/communication/ProjectSpaceBindingModel.md`
- `spec/orchestration/communication/AgentLoopControls.md`
- `spec/state-machines/TaskStateMachine.md`
