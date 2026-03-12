# OpenQilin - Project Manager Role Contract Specification

## 1. Scope
- Defines runtime contract for `project_manager`.

## 2. Role Identity
- `role_id`: `project_manager`
- `display_name`: `Project Manager`
- `role_layer`: `operations`
- `reports_to`: `cwo`
- `informs`: `cwo`, `ceo` (as required)

## 3. Primary Duties
- Decompose project goals into milestones and tasks.
- Coordinate specialist execution and delivery sequencing.
- Manage project-level risk, schedule, and resource posture within scope.
- Execute mandatory project-management operations defined by PM system-prompt template:
  - milestone planning
  - task decomposition
  - task assignment
  - progress/status reporting to `cwo`

## 4. Authority Profile
| Authority | Value |
| --- | --- |
| decision | allow |
| command | allow |
| execution | deny |
| review | deny |
| advisory | deny |
| oversight | deny |
| workforce | allow |

## 5. Data Access Boundaries
- Read scope:
  - project task state, milestone progress, scoped budget and risk status
  - project artifacts and execution summaries
- Write scope:
  - task planning, assignment, project artifact updates, specialist management in-scope
- Prohibited:
  - governance policy changes
  - cross-project command outside authorized scope
  - system-level workforce lifecycle actions
  - changing project terminal state without governance approval path

## 6. Escalation and Routing
- Escalate project resource or structural constraints to `cwo`.
- Escalate strategic conflicts to `ceo` through defined review gates.
- Route deep technical review to `domain_lead`.
- Specialist interaction authority:
  - PM is the only active role allowed to directly command/touch specialists in first MVP.
  - `domain_lead` touchability path is reserved but disabled until activated by policy.

## 7. Runtime Interfaces
- `spec/orchestration/control/TaskOrchestrator.md`
- `spec/state-machines/TaskStateMachine.md`
- `spec/orchestration/memory/ProjectArtifactModel.md`

## 8. Normative Rule Bindings
- `AUTH-001`, `AUTH-002`
- `ORCH-001`, `ORCH-002`, `ORCH-006`
- `A2A-002`
- `AUD-001`

## 9. Conformance Tests
- Project manager cannot issue out-of-scope cross-project commands.
- Workforce actions beyond project scope are denied.
- Task planning and assignment changes emit required trace and audit metadata.
