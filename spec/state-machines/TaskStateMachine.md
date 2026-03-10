# OpenQilin - Task State Machine Specification

## 1. Scope
- Canonical task execution lifecycle state machine.
- Must stay consistent with `spec/orchestration/control/TaskOrchestrator.md`.

## 2. States
- `created`
- `queued`
- `authorized`
- `dispatched`
- `running`
- `completed` (terminal)
- `failed` (terminal)
- `cancelled` (terminal)
- `blocked` (terminal for denied/unsupported conditions)

## 3. Transitions
| From | Event | Guard | Action | To |
| --- | --- | --- | --- | --- |
| created | enqueue | request valid | emit enqueue event | queued |
| queued | authorize | policy decision=`allow\|allow_with_obligations` | store decision metadata | authorized |
| queued | authorize | policy decision=`deny` or evaluation error | emit deny event | blocked |
| authorized | reserve_budget | reservation success | attach reservation reference | dispatched |
| authorized | reserve_budget | reservation fail/hard breach | emit budget enforcement event | blocked |
| dispatched | start_execution | execution slot acquired | emit start event | running |
| running | complete | execution success | persist outputs/summary | completed |
| running | fail | unrecoverable error | emit failure event | failed |
| queued/authorized/dispatched/running | cancel | authorized cancel request | emit cancel event | cancelled |

## 4. Conformance Tests
- Task MUST enter `created` before `queued`.
- Denied authorization cannot transition to dispatched.
- Budget reservation failure cannot transition to `dispatched`.
- Any policy or budget evaluation error transitions to `blocked` (fail-closed).
- Terminal states (`completed`, `failed`, `cancelled`, `blocked`) do not transition further.
