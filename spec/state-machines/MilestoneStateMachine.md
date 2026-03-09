# OpenQilin - Milestone State Machine Specification

## 1. Scope
- Canonical lifecycle state machine for milestones under a project.
- Aligns project-level governance and task-level execution flow.

## 2. States
- `planned`
- `active`
- `paused`
- `blocked`
- `completed` (terminal)
- `cancelled` (terminal)
- `archived` (terminal)

## 3. Transitions
| From | Event | Guard | Action | To |
| --- | --- | --- | --- | --- |
| planned | start | parent project state=`active` and milestone authorized | emit milestone-start event | active |
| active | pause | parent project paused or containment action triggered | emit pause event | paused |
| paused | resume | parent project returned to active and remediation complete | emit resume event | active |
| active | block | unresolved dependency/critical failure | emit blocked event | blocked |
| blocked | unblock | dependency resolved and authorization=`allow` | emit unblock event | active |
| active | complete | all required tasks terminal-success | emit completion event | completed |
| planned/active/paused/blocked | cancel | authorized cancellation decision | emit cancellation event | cancelled |
| completed/cancelled | archive | retention elapsed | persist milestone snapshot | archived |

## 4. Illegal Transitions
- `planned` -> `completed` directly.
- `paused` -> `completed` without returning `active`.
- `blocked` -> `completed` directly.
- `completed` -> `active`.
- `archived` -> any state.

## 5. Alignment Constraints
- Milestones cannot be `active` when parent project is `paused`, `terminated`, or `archived`.
- Project completion requires all required milestones in `completed` state.
- Task assignment requires parent milestone not in terminal state.

## 6. Conformance Tests
- Milestone start is denied when parent project is not `active`.
- Completing milestone with non-terminal required tasks is denied.
- Paused project forces active milestone into `paused`.
- Archived milestone rejects any mutation event.
