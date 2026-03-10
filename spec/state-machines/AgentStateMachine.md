# OpenQilin - Agent State Machine Specification

## 1. Scope
- Canonical lifecycle state machine for all runtime agents.
- This document is the normative source for lifecycle transitions.
- `spec/orchestration/control/AgentLifecycleManagement.md` defines orchestration enforcement behavior using this state machine.

## 2. States
- `created`
- `active`
- `paused`
- `retired`
- `archived` (terminal)

## 3. Transitions
| From | Event | Guard | Action | To |
| --- | --- | --- | --- | --- |
| created | activate | policy decision=`allow` and registration valid | emit activation event | active |
| created | activate | policy decision=`deny` | emit deny audit event | created |
| active | pause | governance/safety/manager request authorized | emit pause event + route escalation if needed | paused |
| paused | resume | policy decision=`allow` and containment cleared | emit resume event | active |
| active | retire | no running tasks and retirement approved | emit retire event | retired |
| paused | retire | retirement approved | emit retire event | retired |
| retired | archive | retention window elapsed | persist snapshot reference | archived |

## 4. Illegal Transitions
- `archived` -> any state.
- `retired` -> `active`.
- `created` -> `retired` without activation path.
- `active` -> `archived` without retirement + archive sequence.

## 5. Conformance Tests
- Activation denial does not transition out of `created`.
- Pause events include escalation metadata when `critical_impact=true`.
- Resume from `paused` fails when containment clearance is missing.
- Archived agents reject all further lifecycle events.
