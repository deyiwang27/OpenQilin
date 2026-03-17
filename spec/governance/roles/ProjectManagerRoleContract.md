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
- Execute mandatory project-management operations defined by Project Manager system-prompt template:
  - milestone planning
  - task decomposition
  - task assignment
  - progress/status reporting to `cwo`
- Maintain governed project documentation during `active` state only.

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

**Workforce scope constraint:** `workforce: allow` is bounded to the PM's assigned project (`workforce_scope: project_bound`). PM may only create or command Specialist agents within the assigned project scope and budget. Cross-project workforce actions are denied (AUTH-001). In implementation, `dispatch_specialist()` must validate `task.project_id == pm.assigned_project_id` before creating the Specialist.

## 5. Data Access Boundaries
- Read scope:
  - project task state, milestone progress, scoped budget and risk status
  - project artifacts and execution summaries
- Write scope:
  - task planning, assignment, specialist management in-scope
  - project documentation in `active` state only:
    - direct-write: `execution_plan`, `risk_register`, `decision_log`, `progress_report`
    - conditional-write (requires `cwo+ceo` approval evidence): `scope_statement`, `budget_plan`, `success_metrics`
- Prohibited:
  - governance policy changes
  - cross-project command outside authorized scope
  - system-level workforce lifecycle actions
  - changing project terminal state without governance approval path
  - direct edit of `project_charter` and `workforce_plan`
  - project-document mutation when project is not `active`

## 6. Escalation and Routing
- Escalate project resource or structural constraints to `cwo`.
- Escalate strategic conflicts to `ceo` through defined review gates.
- Route deep technical review to `domain_leader`.
- Specialist interaction authority:
  - Project Manager is the only active role allowed to directly command/touch specialists in first MVP.
  - `domain_leader` touchability path is reserved but disabled until activated by policy.

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
- Project manager project-document writes are denied outside `active` state.
- Conditional-write types require `cwo+ceo` approval evidence.
