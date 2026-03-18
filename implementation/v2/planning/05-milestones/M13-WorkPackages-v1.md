# M13 Work Packages — Project Space Binding, Routing, Orchestration, and Agent Spec Fixes

Milestone: `M13`
Status: `planned`
Entry gate: M12 complete (OPA live, PostgreSQL wired, role self-assertion fixed)
Design ref: `design/v2/architecture/M13-ProjectSpaceAndOrchestrationModuleDesign-v2.md`, `design/v2/adr/ADR-0005`, `design/v2/components/OrchestratorComponentDelta-v2.md`

---

## Milestone Goal

Adopt LangGraph as the real orchestration engine, replacing the linear HTTP-handler call chain. Introduce project-space binding and PM-default routing. Activate Domain Leader as a backend-routed virtual agent. Fix the snapshot split-brain bug. Begin real sandbox enforcement. Fix the CSO implementation (M12 built CSO as a generic governance gate; spec defines CSO as Chief Strategy Officer). Align Secretary with its spec contract (registry registration, runtime data access).

---

## WP M13-01 — LangGraph Orchestration Adoption

**Goal:** Replace the linear synchronous call chain inside the HTTP request handler with a real LangGraph StateGraph running in an async worker loop.

**Bug ref:** C-9 | **Design ref:** `design/v2/adr/ADR-0005-LangGraph-State-Machine-Adoption.md`, `design/v2/components/OrchestratorComponentDelta-v2.md §1.1, §1.5`

**Entry criteria:** M12 complete; PostgreSQL task queue available; OPA and obligation dispatcher wired.

### Tasks

- [x] Add `langgraph>=0.2` and `langchain-core>=0.2` to `pyproject.toml`
- [x] Create `src/openqilin/task_orchestrator/workflow/state_models.py` — `TaskState` TypedDict: `task_id`, `project_id`, `principal_role`, `command`, `policy_decision`, `obligation_result`, `budget_reservation`, `final_state`, `loop_state`
- [x] Implement `workflow/nodes.py` — four async node functions:
  - `policy_evaluation_node(state)` — calls `OPAPolicyRuntimeClient.evaluate()`; returns updated state with `policy_decision`
  - `obligation_check_node(state)` — calls `ObligationDispatcher.apply()`; returns updated state with `obligation_result`
  - `budget_reservation_node(state)` — calls budget client reserve (M14 completes this; M13 wires the stub that will be swapped)
  - `dispatch_node(state)` — dispatches to execution sandbox; writes final status
- [x] Implement `workflow/graph.py` — `build_task_graph()` returns a compiled `StateGraph` connecting the four nodes with conditional edges for `blocked` and `failed` outcomes; replace the existing one-line placeholder
- [x] Implement `state/state_machine.py` — graph compilation and transition enforcement using `transition_guard`; replace the existing one-line placeholder
- [x] Implement `apps/orchestrator_worker.py` as real async polling loop:
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
- [x] Update HTTP command handler to be admission-only: insert task as `queued` → return `accepted {task_id}` immediately; remove all orchestration logic from HTTP handler

### Outputs

- LangGraph `StateGraph` active as the real orchestration engine
- `orchestrator_worker` is a real async processing loop
- HTTP handler is admission-only

### Done criteria

- [x] End-to-end test: `queued` task progresses through all four nodes to `completed` via real LangGraph graph
- [x] OPA deny in `policy_evaluation_node` → task transitions to `blocked` without reaching dispatch
- [x] HTTP handler returns `202 accepted` immediately; task result visible only via status poll
- [x] `InMemory` task state machine placeholder replaced

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

**Entry criteria:** WP M13-01 (LangGraph active), WP M13-03 (project-space routing active), WP M13-07 (CSO rewritten as Chief Strategy Officer — required so DL escalation path does not inherit the broken CSO governance gate), M12 OPA wired.

### Tasks

- [ ] Create `src/openqilin/agents/domain_leader/` package: `agent.py`, `escalation_handler.py`, `prompts.py`, `models.py`
- [ ] Implement `DomainLeaderAgent.handle_escalation(request)` — receives PM escalation; produces domain response; does NOT reply directly to Discord channel
- [ ] Implement `DomainLeaderAgent.review_specialist_output(task_id, output)` — DL `review: allow` authority; assesses specialist output for correctness/quality; returns review outcome with rework recommendations if needed (spec §3)
- [ ] Implement `EscalationHandler` — PM calls DL; DL produces `DLResponse`; PM synthesizes response for channel reply
- [ ] Wire DL → PM material domain risk escalation (spec §6): when domain risk cannot be resolved, DL escalates to PM; PM is responsible for further escalation to CWO through the project governance path (EscalationModel: "specialist → domain_leader → project_manager → cwo → ceo"); DL does not route directly to CWO
- [ ] Wire Specialist → DL technical clarification path: `DomainLeaderAgent.handle_clarification_request(specialist_id, question, task_id)` — DL spec §6 declares this path active in MVP-v2; response returned to Specialist via PM synthesis (not direct)
- [ ] Bind DL to project context: DL always requires `project_id` in request; rejected without it
- [ ] Enforce `command: deny` for DL — DL cannot issue commands to specialists directly; all specialist interactions must route through PM
- [ ] Confirm DL is NOT a default Discord channel participant; NOT accessible by direct owner mention (no DM surface)
- [ ] Add integration test: PM escalates to DL; DL response returned to PM; channel receives PM-synthesized reply (not raw DL response)
- [ ] Add unit test: DL `command: deny` — attempt to dispatch task to specialist from DL is rejected

### Outputs

- `DomainLeaderAgent` active as backend-routed virtual agent
- DL surfaced only through PM escalation path
- DL reviews specialist outputs (review=allow) and escalates domain risk to CWO
- Specialist → DL clarification path wired

### Done criteria

- [ ] PM escalation to DL produces DL domain response
- [ ] DL response NOT sent directly to Discord channel
- [ ] DL invocation without `project_id` is rejected
- [ ] DL not accessible via direct owner message or DM
- [ ] DL specialist output review returns structured review outcome with rework recommendations when quality fails
- [ ] DL material domain risk escalation routes to PM (not directly to CWO); PM is accountable for further escalation to CWO
- [ ] DL command=deny enforced: DL cannot dispatch tasks directly to specialists
- [ ] Specialist → DL clarification request returns DL response via PM synthesis

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

---

## WP M13-07 — CSO Rewrite: Chief Strategy Officer

**Goal:** Rewrite `CSOAgent` to match its spec contract (`spec/governance/roles/CsoRoleContract.md`): portfolio strategy advisor, CWO proposal reviewer, cross-project risk analyst. Remove the erroneous OPA governance gate and `assert_opa_client_required` startup guard introduced in M12-WP8.

**Design ref:** `spec/governance/roles/CsoRoleContract.md`, `spec/governance/architecture/DecisionReviewGates.md`

**Entry criteria:** M12 complete. This WP corrects the M12-WP8 implementation.

### Tasks

- [ ] Remove `assert_opa_client_required` import and call from `src/openqilin/control_plane/api/dependencies.py`; remove `_cso_opa_required` flag; CSO no longer requires OPA
- [ ] Rewrite `src/openqilin/agents/cso/models.py`:
  - Replace `principal_role: str` with `proposal_id: str | None` and `portfolio_context: str | None`
  - Replace `CSOPolicyError` with `CSOConflictFlag` (not an exception — a structured advisory outcome, not a gate block)
  - Rename `governance_note` → `strategic_note` on `CSOResponse`
- [ ] Rewrite `src/openqilin/agents/cso/prompts.py`:
  - `STRATEGIC_SYSTEM_PROMPT` — CSO as portfolio strategist and long-horizon risk analyst; reviews for strategic alignment and opportunity cost
  - `PROPOSAL_REVIEW_TEMPLATE` — when `proposal_id` present; inputs: proposal summary, portfolio context; outputs: strategic review outcome (`Aligned` / `Needs Revision` / `Strategic Conflict`) with rationale
  - `CROSS_PROJECT_ADVISORY_TEMPLATE` — for `DISCUSSION`/`QUERY` intents without a specific proposal; provides cross-project insight and strategic perspective
- [ ] Rewrite `src/openqilin/agents/cso/agent.py`:
  - Remove all OPA evaluation (`_evaluate_governance`, `PolicyEvaluationInput`, `policy_client` dependency)
  - `CSOAgent.__init__(self, llm_gateway, project_artifact_repo, governance_repo)` — takes data access repos instead of policy client
  - `handle(request: CSORequest) -> CSOResponse`: for all intent classes; reads portfolio context from repos when `proposal_id` present; generates strategic advisory; sets `CSOConflictFlag` when strategic conflict detected
  - `_read_portfolio_context(proposal_id, project_id)` — reads relevant project artifacts, cross-project metrics, and task status to inform advisory
  - Returns `CSOResponse` with `advisory_text`, `strategic_note`, optional `conflict_flag: CSOConflictFlag | None`
  - On `Strategic Conflict`: escalate to `ceo` (primary path); on material strategic risk, route escalation event to `owner` per governance policy (EscalationModel strategic chain: `cso → ceo → owner`)
- [ ] Implement `CSOReviewRecord` write: after every proposal review, persist a governance record to `governance_artifacts` table with `proposal_id`, `review_outcome`, `cso_advisory_text`, `trace_id`, `created_at` — required by GATE-006 before proposal can advance to CEO+CWO review
- [ ] Remove `assert_opa_client_required` function from `agent.py`
- [ ] Update `dependencies.py`: `CSOAgent(llm_gateway=llm_gateway, project_artifact_repo=project_artifact_repo, governance_repo=governance_repo)`
- [ ] Update unit tests in `tests/unit/test_m12_wp8_cso_activation.py` to reflect new interface; remove OPA guard tests; add strategic advisory and proposal review tests; add GATE-006 governance record persistence test

### Outputs

- `CSOAgent` is a strategic advisor; no OPA dependency
- Proposal review returns structured `CSOConflictFlag` when strategic conflict detected
- CSO reads portfolio/proposal artifacts to inform advisory
- GATE-006 compliance: CSO review outcome persisted to governance record before proposal advances

### Done criteria

- [ ] `CSOAgent` has no reference to `PolicyRuntimeClient` or `OPAPolicyRuntimeClient`
- [ ] CSO handles `proposal_id` in request — reads proposal artifacts and returns `Aligned`/`Needs Revision`/`Strategic Conflict` outcome
- [ ] CSO review outcome persisted to `governance_artifacts` with `trace_id` before proposal advances (GATE-006)
- [ ] `Strategic Conflict` triggers escalation event to CEO; material strategic risk routes escalation to owner
- [ ] CSO handles cross-project advisory requests without proposal context
- [ ] All unit tests pass; no OPA mock required to test CSO

---

## WP M13-08 — Secretary and Routing Spec Alignment

**Goal:** Register Secretary in `_INSTITUTIONAL_ROLES`; add CSO as a routing target in executive and leadership_council channels; add Secretary runtime data access interfaces (project snapshot, task context).

**Design ref:** `spec/governance/roles/SecretaryRoleContract.md §7`, `spec/orchestration/communication/OwnerInteractionModel.md §2.1`

**Entry criteria:** WP M13-07 complete (CSO has stable interface before it is added to routing).

### Tasks

- [ ] Add `"secretary"` to `_INSTITUTIONAL_ROLES` in `src/openqilin/data_access/repositories/agent_registry.py`
- [ ] Add `"secretary"` to `_INSTITUTIONAL_ROLES` in `src/openqilin/data_access/repositories/postgres/agent_registry_repository.py`
- [ ] Update `src/openqilin/control_plane/grammar/free_text_router.py`: in `executive` and `leadership_council` channels, route `MUTATION`/`ADMIN` intents to `cso`; keep `DISCUSSION`/`QUERY` routed to `secretary` (CSO reviews governed actions; Secretary handles general queries)
- [ ] Implement `src/openqilin/agents/secretary/data_access.py` — `SecretaryDataAccessService`:
  - `get_project_snapshot(project_id) -> ProjectSnapshot | None` — reads project status, task counts, blockers from PostgreSQL
  - `get_task_runtime_context(task_id) -> TaskRuntimeContext | None` — reads task state, logs, outcome
  - `get_dashboard_summary() -> DashboardSummary` — reads alert counts and key metrics for status interpretation
- [ ] Wire `SecretaryDataAccessService` into `SecretaryAgent.__init__`; use it in `_generate_advisory()` to include live project/task context in LLM prompt when relevant
- [ ] Update `dependencies.py`: `SecretaryAgent(llm_gateway=llm_gateway, data_access=secretary_data_access)`
- [ ] Add `policy_version`, `policy_hash`, and `rule_ids` fields to `SecretaryResponse` (spec §7: every interaction must include these) — wire with `policy_version="v2"`, `policy_hash="secretary-advisory-v1"`, `rule_ids=("AUTH-004", "AUTH-005")`
- [ ] Add authority-profile validation in `bootstrap_institutional_agents()` for `secretary` registration: validate that secretary is registered with advisory-only capability profile; reject if non-advisory authority or mutating data capabilities requested (AgentRegistry spec §3)
- [ ] Update `dependencies.py`: `SecretaryAgent(llm_gateway=llm_gateway, data_access=secretary_data_access)`
- [ ] Add unit tests for routing table changes (MUTATION in executive → cso; DISCUSSION in executive → secretary)
- [ ] Add unit tests for data access (project snapshot enriches advisory context)
- [ ] Add unit test: secretary registration with command capability → rejected by registry bootstrap

### Outputs

- Secretary registered as an institutional agent with `AgentRecord` in the registry
- CSO reachable from executive and leadership_council channels for governed actions
- Secretary advisory responses include live project/task context from PostgreSQL
- `SecretaryResponse` includes full audit metadata (`policy_version`, `policy_hash`, `rule_ids`)

### Done criteria

- [ ] `bootstrap_institutional_agents()` creates a `secretary` record
- [ ] MUTATION intent in executive/leadership_council channel → routed to `cso`
- [ ] DISCUSSION/QUERY intent in executive/leadership_council channel → routed to `secretary`
- [ ] Secretary advisory includes live project status when `project_id` context is available
- [ ] `SecretaryResponse` includes `policy_version`, `policy_hash`, and `rule_ids` fields (AUTH-004, AUTH-005)
- [ ] Secretary registration rejected if non-advisory capabilities are requested (AgentRegistry spec §3)

---

## WP M13-09 — InMemory Stub Removal and Test Infrastructure Hardening

**Goal:** Remove all `InMemory*` class definitions from production `src/` files. Replace infrastructure stubs with real Postgres/Redis/OPA implementations. Rename simulation stubs (no real transport counterpart) away from the `InMemory*` prefix. Move observability introspection stubs to `testing/`. Harden test infrastructure to require the compose stack for all non-pure-logic tests.

**Bug ref:** CI governance gate (`grep -r --include="*.py" -l "class InMemory" src/ | grep -v "/testing/"` returns 26 files)
**Design ref:** `design/v2/adr/ADR-0008-InMemory-Stub-Removal-Strategy.md`

**Entry criteria:** M13-WP1 complete (real LangGraph nodes wired; current test suite passing).

### Tasks

#### Phase 1 — Delete Group 1 (infra stubs with real Postgres/Redis/OPA counterparts)

- [x] Delete `InMemoryRuntimeStateRepository` from `data_access/repositories/runtime_state.py`
- [x] Delete `InMemoryCommunicationRepository` from `data_access/repositories/communication.py`
- [x] Delete `InMemoryAgentRegistryRepository` from `data_access/repositories/agent_registry.py`
- [x] Delete `InMemoryProjectArtifactRepository` from `data_access/repositories/artifacts.py`
- [x] Delete `InMemoryGovernanceRepository` from `data_access/repositories/governance.py`
- [x] Delete `InMemoryIdentityChannelRepository` from `data_access/repositories/identity_channels.py`
- [x] Delete `InMemoryIdempotencyCacheStore` from `data_access/cache/idempotency_store.py`
- [x] Delete `InMemoryArtifactSearchReadModel` from `data_access/read_models/artifact_search.py`
- [x] Replace the `else` fallback branches in `build_runtime_services()` with `RuntimeError` guards for `DATABASE_URL`, `REDIS_URL`, `OPA_URL`
- [x] Narrow `RuntimeServices` dataclass union types to concrete Postgres/Redis types only

#### Phase 2 — Rename Group 2 (simulation stubs with no real transport counterpart)

- [x] Rename `InMemoryDeliveryPublisher` → `LocalDeliveryPublisher`
- [x] Rename `InMemoryDeadLetterWriter` → `LocalDeadLetterWriter`
- [x] Rename `InMemoryMessageLedger` → `LocalMessageLedger`
- [x] Rename `InMemoryCommunicationIdempotencyStore` → `LocalCommunicationIdempotencyStore`
- [x] Rename `InMemoryAcpClient` → `LocalAcpClient`
- [x] Rename `InMemoryOrderingValidator` → `LocalOrderingValidator`
- [x] Rename `InMemoryCommunicationDispatchAdapter` → `LocalCommunicationDispatchAdapter`
- [x] Rename `InMemorySandboxExecutionAdapter` → `LocalSandboxExecutionAdapter`
- [x] Rename `InMemoryConversationStore` → `LocalConversationStore`
- [x] Rename `InMemoryLiteLLMAdapter` → `LocalLiteLLMAdapter`
- [x] Rename `InMemoryBudgetRuntimeClient` → `AlwaysAllowBudgetRuntimeClient`
- [x] Rename `InMemoryIngressDedupe` → `IngressDedupeStore`
- [x] Rename `InMemorySandboxEventCallbackProcessor` → `LocalSandboxEventCallbackProcessor`
- [x] Rename `InMemoryDeliveryEventCallbackProcessor` → `LocalDeliveryEventCallbackProcessor`
- [x] Update all callers and import sites for all renamed classes

#### Phase 3 — Move Group 3 (observability introspection stubs) to `testing/`

- [x] Move `InMemoryAuditWriter` to `src/openqilin/observability/testing/stubs.py`
- [x] Move `InMemoryTracer` + `InMemorySpan` to `src/openqilin/observability/testing/stubs.py`
- [x] Move `InMemoryMetricRecorder` to `src/openqilin/observability/testing/stubs.py`
- [x] Move `InMemoryAlertEmitter` to `src/openqilin/observability/testing/stubs.py`
- [x] Update all import sites (tests, conftest files)

#### Phase 4 — Harden test infrastructure

- [x] Add `tests/component/conftest.py`:
  - `patch_build_runtime_services` autouse fixture: builds fully-wired in-memory `RuntimeServices` for component tests without compose stack
- [ ] Add `tests/integration/conftest.py` with database cleanup fixture (requires compose — deferred to integration test phase)
- [x] Add `@pytest.mark.no_infra` to all pure-logic unit tests via `tests/unit/conftest.py` (auto-applied to all except infra-requiring files)
- [x] Register `no_infra` marker in `pyproject.toml`
- [x] Rewrite the three tests that asserted "env var absent → InMemory selected" to assert `RuntimeError` is raised instead
- [ ] Update `CLAUDE.md` test command table to document `no_infra` and compose-required tiers

#### Phase 5 — Verify and gate

- [x] `grep -r --include="*.py" -l "class InMemory" src/ | grep -v "/testing/" | grep -v "tests/"` returns zero results
- [x] `uv run ruff check . && uv run mypy .` — clean
- [x] `uv run pytest -m no_infra tests/unit/` — passes without compose (413 tests)
- [ ] `uv run pytest tests/unit tests/component tests/contract tests/integration tests/conformance` — passes with compose stack (deferred)

### Outputs

- Zero `class InMemory` definitions in non-testing `src/` files
- CI governance grep gate passes
- `build_runtime_services()` fails fast on missing env vars instead of silently degrading to InMemory mode
- All simulation stubs renamed to `Local*` or semantically accurate names
- Observability stubs consolidated in `observability/testing/stubs.py`
- `@pytest.mark.no_infra` tier established for fast, compose-free logic tests

### Done criteria

- [x] `grep -r --include="*.py" -l "class InMemory" src/ | grep -v "/testing/" | grep -v "tests/"` returns zero
- [x] `build_runtime_services()` raises `RuntimeError` when `DATABASE_URL`, `REDIS_URL`, or `OPA_URL` is absent
- [ ] Full test suite passes against compose stack (unit+component pass without compose; contract/integration/conformance require compose)
- [x] `uv run pytest -m no_infra tests/unit/` passes without compose stack (413 tests, 2026-03-17)
- [x] `uv run ruff check . && uv run mypy .` — clean

---

## M13 Exit Criteria

- [ ] All nine WPs above are marked done
- [ ] LangGraph `StateGraph` is the active orchestration engine in production
- [ ] Project spaces are created automatically; PM-default routing works
- [ ] Domain Leader active as a backend-routed virtual agent
- [ ] H-3 snapshot split-brain fixed
- [ ] Loop caps enforced on all inter-agent hops
- [ ] CSO rewritten as Chief Strategy Officer; no OPA dependency; portfolio data access wired
- [ ] Secretary registered in agent registry; CSO routing active; Secretary data access wired
- [ ] No `InMemory` placeholder used in any new orchestration path

## References

- `design/v2/adr/ADR-0005-LangGraph-State-Machine-Adoption.md`
- `design/v2/adr/ADR-0008-InMemory-Stub-Removal-Strategy.md`
- `design/v2/architecture/M13-ProjectSpaceAndOrchestrationModuleDesign-v2.md`
- `design/v2/components/OrchestratorComponentDelta-v2.md`
- `spec/orchestration/communication/ProjectSpaceBindingModel.md`
- `spec/orchestration/communication/AgentLoopControls.md`
- `spec/state-machines/TaskStateMachine.md`
