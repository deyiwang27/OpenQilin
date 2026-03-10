# SEQ-0002: Fail-Closed and Timeout Branches

## Actors
- `control_plane_api`
- `task_orchestrator`
- `policy_runtime`
- `budget_engine`
- `execution_sandbox`
- `audit_ledger`

## Preconditions
- Task request passed API envelope validation.
- `trace_id` is established and propagated.

## Sequence
```mermaid
sequenceDiagram
    autonumber
    participant API as control_plane_api
    participant ORCH as task_orchestrator
    participant OPA as policy_runtime
    participant BUD as budget_engine
    participant SBX as execution_sandbox
    participant AUD as audit_ledger

    API->>ORCH: submit(task)
    ORCH->>OPA: evaluate(timeout=150ms)

    alt policy timeout/load/eval error
        ORCH->>AUD: append fail-closed policy event
        ORCH-->>API: blocked(EVAL_INTERNAL_ERROR|POLICY_LOAD_ERROR)
    else policy deny
        ORCH->>AUD: append deny event(rule_ids)
        ORCH-->>API: blocked(UNAUTHORIZED_ACTION)
    else policy allow path
        ORCH->>BUD: reserve(timeout=200ms)
        alt budget error/timeout/hard breach
            ORCH->>AUD: append budget enforcement event
            ORCH-->>API: blocked(BUDGET_RESERVATION_FAILED|BUDGET_HARD_THRESHOLD)
        else budget ok
            ORCH->>SBX: dispatch(timeout=1s)
            alt sandbox reject/timeout
                ORCH->>AUD: append dispatch-failure event
                ORCH-->>API: blocked(EXECUTION_DISPATCH_FAILED)
            else dispatch accepted
                ORCH-->>API: accepted(task_id, trace_id)
            end
        end
    end
```

## Notes
- State-changing governed actions are fail-closed when uncertainty exists.
- Export failures after durable audit append are non-blocking.
- Read-only query flows may return degraded responses with no state mutation.
