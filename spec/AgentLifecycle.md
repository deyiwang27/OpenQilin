# OpenQilin - Agent Lifecycle Specification

## 1. Scope
- Defines lifecycle states, transitions, and guards for institutional, project, and specialist agents.

## 2. Lifecycle Classes
- Institutional: `Administrator`, `Auditor`, `CEO`, `CWO`, `CSO`
- Project: `ProjectManager`, `DomainLead`
- Specialist: task/project bound

## 3. State Machine (Specialist)
### States
- `created`, `active`, `paused`, `retired`, `archived`

### Transitions
| From | Event | Guard | Action | To |
| --- | --- | --- | --- | --- |
| created | activate | authorization=allow | emit lifecycle event | active |
| active | pause | governance or PM request | persist checkpoint | paused |
| paused | resume | budget ok and authorization=allow | restore checkpoint | active |
| active | retire | task complete | freeze mutable state | retired |
| retired | archive | retention period elapsed | move to cold storage | archived |

## 4. Invariants
- LIF-001: `archived` agents MUST be read-only.
- LIF-002: Institutional agents MUST NOT transition to `retired` in normal operation.
- LIF-003: Deletion of operational records MUST NOT occur.

## 5. Conformance Tests
- Invalid transition `archived -> active` is rejected.
- Pause/resume preserves task context.
- Retirement emits immutable audit event.

