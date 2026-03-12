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

State clarification:
- `proposed` is the only pre-approval state in v1.
- Proposal revisions remain in `proposed` until explicit approval.

## 3. Transitions
| From | Event | Guard | Action | To |
| --- | --- | --- | --- | --- |
| proposed | amend | proposal requires clarification/revision | persist revision + emit proposal-update event | proposed |
| proposed | approve | review gates passed and decision=`approved` | emit approval event | approved |
| approved | start | budget reservation + policy authorization succeed | emit project-start event | active |
| active | pause | budget hard breach or safety containment triggered | emit pause + escalation event | paused |
| paused | resume | remediation complete and authorization=`allow` | emit resume event | active |
| active | complete | all required milestones=`completed`, required tasks terminal-success, PM completion report submitted, and `cwo+ceo` completion approval recorded | emit completion event + owner notification event | completed |
| active | terminate | owner/governance termination decision | emit termination event | terminated |
| paused | terminate | owner/governance termination decision | emit termination event | terminated |
| completed | archive | retention elapsed | persist completion snapshot | archived |
| terminated | archive | retention elapsed | persist termination snapshot | archived |

## 4. Illegal Transitions
- `proposed` -> `active` without `approved`.
- `proposed` -> `terminated`.
- `approved` -> `terminated` before `active`.
- `paused` -> `completed` directly.
- `completed` -> `active`.
- `completed` -> `terminated`.
- `terminated` -> `active`.
- `archived` -> any state.

## 5. Conformance Tests
- Hard budget breach transitions project to `paused` with enforcement metadata.
- Resuming a paused project without remediation evidence is denied.
- Project start requires both policy approval and budget reservation.
- Proposals remain in `proposed` state until explicit approval.
- Project completion is denied without PM completion report and `cwo+ceo` approval evidence.
- Project completion is denied when any required milestone is not `completed`.
- Archived projects reject further mutation events.
