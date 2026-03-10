# OpenQilin v1 - Task Orchestrator Module Design

## 1. Scope
- Translate the task-orchestrator component design into implementation modules under `src/openqilin/task_orchestrator/`.

## 2. Package Layout
```text
src/openqilin/task_orchestrator/
  admission/
    service.py
    envelope_validator.py
    idempotency.py
  workflow/
    graph.py
    nodes.py
    transition_guard.py
  state/
    state_machine.py
    transition_service.py
  dispatch/
    target_selector.py
    sandbox_dispatch.py
    llm_dispatch.py
    communication_dispatch.py
  callbacks/
    sandbox_events.py
    delivery_events.py
  escalation/
    escalation_router.py
  services/
    task_service.py
    lifecycle_service.py
```

## 3. Core Flow Ownership
- `admission`: intake, dedupe, initial persistence
- `workflow`: orchestration graph and deterministic node order
- `state`: authoritative transition validation
- `dispatch`: target-specific adapter calls behind orchestrator-owned boundary
- `callbacks`: async runtime outcome handling
- `escalation`: containment and human escalation routing

## 4. Key Interfaces
- `AdmissionService.admit(task_envelope)`
- `TransitionService.transition(task_id, event)`
- `TargetSelector.select(task_context)`
- `SandboxDispatch.dispatch(task_context)`
- `LlmDispatch.dispatch(task_context)`
- `CommunicationDispatch.dispatch(task_context)`

## 5. Persistence Boundary
- task and lifecycle persistence goes through `data_access.runtime_state`
- outbox and audit-linked writes happen in the same transaction where required
- orchestrator owns durable task state; downstream components only return outcomes

## 6. Idempotency Rules
- intake dedupe is checked before new task creation
- callback handlers dedupe by external event id and task transition marker
- duplicate callbacks must be side-effect safe

## 7. Testing Focus
- admission dedupe
- state transition legality
- target selection rules
- blocked and fail-closed paths for policy, budget, sandbox, and communication failures
