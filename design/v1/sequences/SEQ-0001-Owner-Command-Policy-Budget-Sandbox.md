# SEQ-0001: Owner Command -> Policy -> Budget -> Sandbox

## Actors
- `owner_channel_adapter`
- `control_plane_api`
- `task_orchestrator`
- `policy_runtime`
- `budget_engine`
- `execution_sandbox`
- `audit_ledger`

## Preconditions
- Active policy version and hash are available.
- Request has valid actor identity and idempotency key.
- Project/task scope is resolvable.

## Normal Path
```mermaid
sequenceDiagram
    autonumber
    participant OWNER as owner_channel_adapter
    participant API as control_plane_api
    participant ORCH as task_orchestrator
    participant OPA as policy_runtime
    participant BUD as budget_engine
    participant SBX as execution_sandbox
    participant AUD as audit_ledger

    OWNER->>API: command(request envelope)
    API->>ORCH: submit(task_id, trace_id)
    ORCH->>OPA: evaluate(policy request)
    OPA-->>ORCH: allow / allow_with_obligations
    ORCH->>AUD: append audit/obligation event
    ORCH->>BUD: reserve budget
    BUD-->>ORCH: reservation ok
    ORCH->>SBX: dispatch(task envelope)
    SBX-->>ORCH: accepted(run_id)
    ORCH-->>API: accepted(task_id, trace_id)
    SBX-->>ORCH: async progress + terminal status
```

## Failure Branches
- Policy deny or policy error: transition task to `blocked`, append deny audit event, return denial code.
- Budget reservation failure/hard threshold: transition to `blocked`, append enforcement event.
- Sandbox dispatch reject/timeout: transition to `blocked`, append dispatch-failure event.

## Expected Outputs
- Task state transitions in source-of-record.
- Immutable audit events with policy metadata.
- Trace continuity across all hops.
