# OpenQilin - Task Orchestrator Specification

## 1. Scope
- Plans, dispatches, tracks, and closes tasks under policy and budget constraints.
- Source alignment:
  - `spec/governance/AgentAuthorityGraph.md`
  - `spec/governance/EscalationModel.md`
  - `spec/constitution/PolicyEngineContract.md`
  - `spec/constitution/BudgetEngineContract.md`
  - `constitution/core/PolicyManifest.yaml`

## 2. Responsibilities
- Accept task creation requests from authorized roles.
- Evaluate dispatch readiness using policy + budget controls.
- Route tasks to execution environments (internal/external) after authorization.
- Track task state until terminal outcome.
- Emit traceable and auditable events for each critical transition.
- Trigger escalation events when incidents match escalation policy.

## 3. Non-Responsibilities
- Does not override Policy Engine decisions.
- Does not override governance enforcement actions (auditor/administrator).
- Does not mutate constitutional policy artifacts.

## 4. Task Lifecycle
- `created`
- `queued`
- `authorized`
- `dispatched`
- `running`
- `completed` (terminal)
- `failed` (terminal)
- `cancelled` (terminal)
- `blocked` (terminal for denied/unsupported conditions)

## 5. State Transitions
| From | Event | Guard | Action | To |
| --- | --- | --- | --- | --- |
| created | enqueue | request valid | emit enqueue event | queued |
| queued | authorize | policy decision=`allow|allow_with_obligations` | store decision metadata | authorized |
| queued | authorize | policy decision=`deny` or evaluation error | emit deny event | blocked |
| authorized | reserve_budget | reservation success | attach reservation reference | dispatched |
| authorized | reserve_budget | reservation fail/hard breach | emit budget enforcement event | blocked |
| dispatched | start_execution | execution slot acquired | emit start event | running |
| running | complete | execution success | persist outputs/summary | completed |
| running | fail | unrecoverable error | emit failure event | failed |
| queued/authorized/dispatched/running | cancel | authorized cancel request | emit cancel event | cancelled |

## 6. Dispatch Pipeline
1. Validate task envelope and requester identity.
2. Build policy request context (`project_id`, `budget_state`, `incident_level`, capabilities).
3. Call Policy Engine.
4. If `deny`, stop and transition to `blocked`.
5. If `allow_with_obligations`, execute obligations in deterministic order.
6. Perform budget reservation before execution dispatch.
7. Dispatch task to execution target with `trace_id` and policy metadata.
8. Track runtime updates until terminal state.

## 7. Obligation Handling
Supported obligations:
- `emit_audit_event`
- `reserve_budget`
- `enforce_sandbox_profile`
- `require_owner_approval`

Deterministic obligation order:
1. `emit_audit_event`
2. `require_owner_approval` (if present)
3. `reserve_budget` (if present)
4. `enforce_sandbox_profile` (if present)

If any required obligation cannot be satisfied, transition to `blocked` (fail-closed).

## 8. Budget and Concurrency Controls
- All costed tasks must reserve budget prior to dispatch.
- Concurrent dispatches must honor atomic reservation semantics.
- Hard threshold behavior:
  - block new execution
  - emit governance enforcement metadata for auditor path
  - preserve auditable trace context

## 9. Failure and Retry Behavior
- Policy evaluation error -> deny (`blocked`) (fail-closed).
- Budget engine unavailability -> block dispatch (fail-closed).
- Idempotency:
  - repeated task creation with same idempotency key must not duplicate side effects.
- Retry policy:
  - transient dispatch failures may retry with bounded attempts and backoff.
  - safety-critical failures do not auto-retry before containment.

Communication reliability profile lock (A2A + ACP):
- Orchestrator must enforce OpenQilin reliability profile v1 for message dispatch:
  - `ack_deadline_ms`: `30000`
  - `max_attempts`: `5`
  - retry trigger: ack timeout or retryable nack
  - retry backoff: bounded exponential with jitter (`500ms`, `1s`, `2s`, `4s`, `8s`, cap `10s`)
  - dead-letter trigger: non-retryable nack or retry exhaustion
- Command/event dispatch without `idempotency_key` is invalid and must fail closed.

## 10. Escalation Integration
- Escalation paths follow `constitution/domain/EscalationPolicy.yaml`.
- Operational failures use operational path.
- Budget hard breaches include auditor enforcement path and owner escalation with ceo notification.
- Behavioral/infrastructure incidents emit escalation events with required fields:
  - `event_id`, `trace_id`, `incident_type`, `severity`, `current_owner_role`, `next_owner_role`, `rule_ids`

## 11. Task Envelope Contract
Minimum task input:
```json
{
  "task_id": "uuid",
  "trace_id": "uuid",
  "project_id": "string",
  "requested_by": {"actor_id": "string", "actor_role": "string"},
  "action": "string",
  "target": "string",
  "priority": "low|normal|high|critical",
  "idempotency_key": "string",
  "context": {}
}
```

Minimum task status output:
```json
{
  "task_id": "uuid",
  "trace_id": "uuid",
  "state": "created|queued|authorized|dispatched|running|completed|failed|cancelled|blocked",
  "policy_version": "string",
  "policy_hash": "string",
  "rule_ids": ["string"],
  "updated_at": "RFC3339"
}
```

## 12. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| ORCH-001 | Task MUST pass Policy Engine before dispatch. | critical | Task Orchestrator |
| ORCH-002 | Task MUST reserve budget before dispatch. | critical | Task Orchestrator |
| ORCH-003 | Policy or budget evaluation errors MUST fail closed and block dispatch. | critical | Task Orchestrator |
| ORCH-004 | Orchestrator MUST execute required obligations for `allow_with_obligations` decisions before dispatch. | high | Task Orchestrator |
| ORCH-005 | Governance enforcement actions MUST NOT be overridden by orchestrator logic. | critical | Task Orchestrator |
| ORCH-006 | Task state transitions MUST emit traceable events with immutable audit references. | high | Task Orchestrator |
| ORCH-007 | Duplicate requests with same idempotency key MUST be side-effect safe. | high | Task Orchestrator |

## 13. Conformance Tests
- Unauthorized tasks are not dispatched.
- Policy Engine deny transitions task to `blocked`.
- Policy Engine unavailability transitions task to `blocked` (fail-closed).
- Budget reservation failure prevents dispatch.
- `allow_with_obligations` path enforces required obligations in deterministic order.
- Hard budget breach emits enforcement metadata for auditor/owner/ceo escalation flow.
- Duplicate task requests do not duplicate side effects.
