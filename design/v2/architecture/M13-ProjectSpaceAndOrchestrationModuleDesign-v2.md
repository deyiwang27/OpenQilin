# OpenQilin v2 — M13 Module Design: Project Space Binding, Routing, and Orchestration Foundation

Milestone: `M13 — Project Space Binding, Routing, and Orchestration Foundation`
References: `design/v2/adr/ADR-0005-LangGraph-State-Machine-Adoption.md`, `design/v2/components/OrchestratorComponentDelta-v2.md`, `spec/orchestration/communication/ProjectSpaceBindingModel.md`, `spec/orchestration/communication/AgentLoopControls.md`

---

## 1. Scope

- Introduce LangGraph as the real orchestration engine [C-9].
- Implement project-space binding persistence, automation, and PM-default routing.
- Replace project-scoped multi-bot assumptions with virtual workforce routing.
- Activate `domain_leader` as a backend-routed virtual agent scoped to project context.
- Fix snapshot write failure split-brain [H-3].
- Begin sandbox enforcement implementation [C-10].

Prerequisite: M12 must be complete (OPA live, PostgreSQL repos wired, role self-assertion fixed).

---

## 2. Package Layout

### New packages and files

```text
src/openqilin/
  task_orchestrator/
    workflow/
      graph.py              ← LangGraph StateGraph definition (replace placeholder)
      nodes.py              ← node functions: policy_gate, obligation_gate, budget_gate, dispatch
      state_models.py       ← TaskState TypedDict for LangGraph
    state/
      state_machine.py      ← LangGraph graph compilation and transition enforcement (replace placeholder)
      transition_guard.py   ← LEGAL_TRANSITIONS dict + assert_legal_transition()
    loop_control.py         ← LoopState dataclass, check_and_increment_hop/pair

  project_spaces/
    __init__.py
    binding_service.py      ← ProjectSpaceBindingService: create, bind, lifecycle transitions
    binding_repository.py   ← PostgresProjectSpaceBindingRepository
    routing_resolver.py     ← resolve Discord channel → project_id + default_recipient
    discord_automator.py    ← create/archive/lock Discord channels and threads
    models.py               ← ProjectSpaceBinding, BindingState enum, LifecycleEvent

  agents/
    domain_leader/
      __init__.py
      agent.py              ← DomainLeader virtual agent: backend-routed, project-scoped
      escalation_handler.py ← handle PM escalation → DL response → PM synthesis
      prompts.py
      models.py             ← DLRequest, DLResponse

  execution_sandbox/
    profiles/
      enforcement.py        ← begin C-10: process isolation scaffolding (replace placeholder)
      seccomp_profiles/
        default.json        ← seccomp profile for sandboxed tool execution

apps/
  orchestrator_worker.py    ← real async polling loop (replace HTTP-handler-only)
```

### Alembic migrations required

```text
alembic/versions/
  0007_create_project_space_bindings_table.py
```

### pyproject.toml additions

```toml
[tool.poetry.dependencies]
langgraph = ">=0.2"
langchain-core = ">=0.2"
```

---

## 3. Runtime Responsibilities

### LangGraph orchestration [C-9]

The `orchestrator_worker` becomes a real async loop that polls the PostgreSQL task queue. The HTTP command handler becomes admission-only: it inserts a task as `queued` and returns `accepted` immediately.

The `task_graph` (LangGraph `StateGraph`) executes the governance pipeline:
```
policy_evaluation → obligation_check → budget_reservation → dispatch
```

Each node is an async function that reads/writes `TaskState` and may transition the task to `blocked` or `failed`.

### `workflow/state_models.py`
```python
class TaskState(TypedDict):
    task_id: str
    project_id: str
    principal_role: str
    command: dict
    policy_decision: PolicyDecision | None
    obligation_result: ObligationResult | None
    budget_reservation: ReservationResult | None
    final_state: str
    loop_state: LoopState
```

### `state/transition_guard.py`
```python
LEGAL_TRANSITIONS = {
    "queued": {"policy_evaluation"},
    "policy_evaluation": {"obligation_check", "blocked"},
    "obligation_check": {"budget_reservation", "blocked"},
    "budget_reservation": {"dispatched", "blocked"},
    "dispatched": {"running", "failed"},
    "running": {"completed", "failed", "blocked"},
    "blocked": {"queued"},
    "completed": set(),
    "failed": set(),
    "cancelled": set(),
}

def assert_legal_transition(current: str, next_state: str) -> None:
    if next_state not in LEGAL_TRANSITIONS.get(current, set()):
        raise InvalidStateTransitionError(current, next_state)
```

### `loop_control.py`
- `check_and_increment_hop(state, limit=5)`: increments `hop_count`; raises `LoopCapBreachError` if exceeded.
- `check_and_increment_pair(state, sender, recipient, limit=2)`: per-pair tracking in `pair_rounds` dict.
- On `LoopCapBreachError`: emit audit event → task transitions to `blocked` → owner notified.

### Project-space binding (`project_spaces/`)

`ProjectSpaceBindingService`:
- Creates Discord channel/thread for each project on project creation.
- Persists binding: `project_id → (guild_id, channel_id, binding_state, default_recipient)`.
- Transitions binding state per `LifecycleEvent`: `proposed → pending_approval → active → archived → locked`.
- Archives/locks Discord channel as project state changes.

`ProjectSpaceRoutingResolver`:
- Resolves inbound message from Discord channel → `project_id` and `default_recipient`.
- Default recipient is `project_manager` per PSB-004.
- Falls back to fail-closed if channel is not bound to any project.

### Domain Leader activation (`agents/domain_leader/`)
- Backend-routed virtual agent: no Discord bot identity, no DM surface.
- Invoked only through PM escalation path or governed review path.
- Not a default participant in project channels.
- `EscalationHandler`: PM calls DL → DL produces domain response → PM synthesizes for channel reply.

### H-3 fix: snapshot split-brain (`data_access/repositories/runtime_state.py`)
```python
async def update_task_status(self, task_id: str, status: str) -> None:
    assert_legal_transition(self._tasks[task_id].status, status)  # guard first
    await self._pg_repo.update_status(task_id, status)   # durable write first
    self._tasks[task_id].status = status                  # cache update after durable write
```
I/O errors on the PostgreSQL write propagate before in-memory state is mutated.

### C-10 scaffolding: sandbox enforcement (`execution_sandbox/profiles/enforcement.py`)
- Replace empty placeholder with real enforcement class.
- M13 scope: apply `seccomp` profile to subprocess execution via `subprocess.Popen` with security options.
- Full namespace/process isolation deferred to a later milestone.
- `SAF-001` compliance is partial in M13; complete in M15+.

---

## 4. Key Interfaces

```python
# task_orchestrator/workflow/graph.py
def build_task_graph() -> CompiledGraph: ...

# task_orchestrator/state/transition_guard.py
def assert_legal_transition(current: str, next_state: str) -> None: ...

# task_orchestrator/loop_control.py
@dataclass
class LoopState:
    hop_count: int = 0
    pair_rounds: dict[tuple[str, str], int] = field(default_factory=dict)

def check_and_increment_hop(state: LoopState, limit: int = 5) -> None: ...
def check_and_increment_pair(state: LoopState, sender: str, recipient: str, limit: int = 2) -> None: ...

# project_spaces/binding_service.py
class ProjectSpaceBindingService:
    async def create_and_bind(self, project_id: str) -> ProjectSpaceBinding: ...
    async def transition(self, project_id: str, event: LifecycleEvent) -> ProjectSpaceBinding: ...

# project_spaces/routing_resolver.py
class ProjectSpaceRoutingResolver:
    async def resolve(self, guild_id: str, channel_id: str) -> RoutingContext | None: ...

# agents/domain_leader/agent.py
class DomainLeaderAgent:
    async def handle_escalation(self, request: DLRequest) -> DLResponse: ...
```

---

## 5. Dependency Rules

- `task_orchestrator/workflow/` depends on `policy_runtime_integration/`, `budget_runtime/`, `execution_sandbox/` — all must be M12-wired before this milestone.
- `loop_control.py` has no external dependencies; it operates on `TaskState` only.
- `project_spaces/` depends on `data_access/` (PostgreSQL repos) and `discord_runtime/` (channel creation) — no dependency on `task_orchestrator/`.
- `agents/domain_leader/` depends on `policy_runtime_integration/` (policy profile enforcement) and `task_orchestrator/loop_control` (hop tracking for DL escalations).
- `orchestrator_worker.py` (app entrypoint) depends on `task_orchestrator/workflow/graph.py` — decoupled from HTTP handler.
- LangGraph must be in `pyproject.toml` before any code in `workflow/` is importable.

---

## 6. Testing Focus

| Test | Assertion |
|---|---|
| Legal state transition: `queued → policy_evaluation` | Succeeds |
| Illegal state transition: `queued → dispatched` | `InvalidStateTransitionError` |
| Loop cap: 6th hop | `LoopCapBreachError`; task blocked; audit event emitted |
| Loop cap: 3rd pair round same sender/recipient | `LoopCapBreachError` |
| LangGraph end-to-end: `queued → completed` | Task progresses through all nodes without error |
| LangGraph fail-closed: OPA deny | Task transitions to `blocked` after `policy_evaluation` node |
| Worker processing: real queue poll | Worker picks up queued task; invokes LangGraph graph |
| H-3 fix: DB write fails | In-memory state NOT updated; error propagated to caller |
| Project-space binding: project created | Discord channel created; binding persisted to PostgreSQL |
| Project-space routing: known channel | Resolves to correct `project_id` and `project_manager` |
| Project-space routing: unknown channel | Returns `None`; fail-closed |
| DL escalation: PM invokes DL | DL response returned; PM synthesizes; DL not surfaced in channel |

---

## 7. Related References

- `design/v2/adr/ADR-0005-LangGraph-State-Machine-Adoption.md`
- `design/v2/components/OrchestratorComponentDelta-v2.md`
- `spec/orchestration/communication/ProjectSpaceBindingModel.md`
- `spec/orchestration/communication/AgentLoopControls.md`
- `spec/state-machines/TaskStateMachine.md`
- `spec/orchestration/control/TaskOrchestrator.md`
