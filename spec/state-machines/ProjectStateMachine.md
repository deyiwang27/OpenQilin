# OpenQilin - Project State Machine Specification

## 1. Scope
- Canonical state machine for project governance and execution lifecycle.
- Must align with decision-review and escalation governance specs.

## 2. States
- `proposed`
- `approved`
- `active`
- `paused`
- `completed`
- `terminated`
- `archived` (terminal)

## 3. Transitions
| From | Event | Guard | Action | To |
| --- | --- | --- | --- | --- |
| proposed | approve | review gates passed and decision=`approved` | emit approval event | approved |
| proposed | reject | decision=`rejected` | emit rejection event | terminated |
| approved | start | budget reservation + policy authorization succeed | emit project-start event | active |
| active | pause | budget hard breach or safety containment triggered | emit pause + escalation event | paused |
| paused | resume | remediation complete and authorization=`allow` | emit resume event | active |
| active | complete | all required milestones=`completed` and required tasks terminal-success | emit completion event | completed |
| active | terminate | owner/governance termination decision | emit termination event | terminated |
| paused | terminate | owner/governance termination decision | emit termination event | terminated |
| completed | archive | retention elapsed | persist completion snapshot | archived |
| terminated | archive | retention elapsed | persist termination snapshot | archived |

## 4. Illegal Transitions
- `proposed` -> `active` without `approved`.
- `paused` -> `completed` directly.
- `completed` -> `active`.
- `archived` -> any state.

## 5. Conformance Tests
- Hard budget breach transitions project to `paused` with enforcement metadata.
- Resuming a paused project without remediation evidence is denied.
- Project start requires both policy approval and budget reservation.
- Project completion is denied when any required milestone is not `completed`.
- Archived projects reject further mutation events.
