# OpenQilin v1 - Task Orchestrator Component Design

## 1. Scope
- Define the v1 `task_orchestrator` runtime component.
- Specify state handling, admission flow, lifecycle transitions, and downstream interfaces.
- Translate orchestration contracts into implementation-facing component boundaries.

## 2. Component Boundary
Component: `task_orchestrator` (LangGraph-backed worker)

Responsibilities:
- accept task submissions from `control_plane_api`
- enforce canonical task state machine transitions
- coordinate policy, budget, llm gateway, communication gateway, and sandbox dispatch
- emit lifecycle, escalation, and audit-linked events
- ensure idempotent task admission and side-effect safety

Non-responsibilities:
- does not make policy decisions
- does not override governance enforcement
- does not access providers or tools directly outside governed component boundaries

## 3. Inputs and Outputs
### 3.1 Inputs
- task envelope from `control_plane_api`
- lifecycle events from `execution_sandbox`
- ack/nack delivery outcomes from `communication_gateway`
- governance action requests

### 3.2 Outputs
- task status updates
- budget reservation requests
- sandbox dispatch requests
- llm gateway calls
- A2A/ACP publish requests
- audit and escalation events

## 4. Admission and Dispatch Flow
1. validate task envelope and current idempotency status
2. persist `created -> queued`
3. build policy request context
4. call `policy_runtime`
5. execute obligations in deterministic order
6. reserve budget when applicable
7. choose execution target:
- `execution_sandbox` for tool/code/runtime actions
- `llm_gateway` for model-serving requests
- `communication_gateway` for inter-agent messages
8. persist and emit task transition events until terminal state

## 5. State Management
Authoritative task states:
- `created`
- `queued`
- `authorized`
- `dispatched`
- `running`
- `completed`
- `failed`
- `cancelled`
- `blocked`

Rules:
- state transitions are validated against `TaskStateMachine`
- terminal states are immutable
- `blocked` is used for deny/fail-closed paths

## 6. Downstream Interface Contracts
### 6.1 Policy Runtime
- synchronous decision call
- required outputs: `decision`, `rule_ids`, `obligations`, `policy_version`, `policy_hash`

### 6.2 Budget Engine
- synchronous reservation call before costed dispatch
- hard breach or unavailability blocks dispatch

### 6.3 Execution Sandbox
- synchronous dispatch-accept gate
- asynchronous runtime progress and terminal event callbacks

### 6.4 LLM Gateway
- all governed model requests route through `llm_gateway`
- orchestrator passes `model_class`, `routing_profile`, `budget_context`, and `policy_context`

### 6.5 Communication Gateway
- publish command/event/escalation envelopes with mandatory `idempotency_key`
- consume delivery outcomes asynchronously

## 7. Idempotency and Retry
- task admission dedupe key: `task_id` or upstream idempotency key binding
- duplicate task submission with same semantic payload returns prior admission result
- policy and budget are not auto-retried
- dispatch retries are bounded and target-specific

## 8. Failure Modes
| Failure | Behavior |
| --- | --- |
| policy deny/error | transition to `blocked` |
| budget failure/hard breach | transition to `blocked` |
| sandbox dispatch reject | transition to `blocked` or `failed` by target semantics |
| communication dead-letter | attach delivery failure and escalate if required |
| duplicate submission | no duplicate side effects |

## 9. Observability
- required spans:
  - `task_orchestration`
  - `task_state_transition`
  - `task_dispatch_target_select`
- required event fields:
  - `task_id`, `trace_id`, `project_id`, `state`, `policy_version`, `policy_hash`, `rule_ids`

## 10. Related `spec/` References
- `spec/orchestration/control/TaskOrchestrator.md`
- `spec/state-machines/TaskStateMachine.md`
- `spec/governance/architecture/EscalationModel.md`
- `spec/constitution/PolicyEngineContract.md`
- `spec/constitution/BudgetEngineContract.md`
- `spec/infrastructure/architecture/LlmGatewayContract.md`
- `spec/orchestration/communication/AgentCommunicationA2A.md`
- `spec/orchestration/communication/AgentCommunicationACP.md`
