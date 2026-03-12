# OpenQilin - Secretary Role Contract Specification

## 1. Scope
- Defines the formal runtime contract for `secretary` (display name: Secretary).
- Centralizes duties, authority boundaries, read-only data scope, and triage behavior.

## 2. Role Identity
- `role_id`: `secretary`
- `display_name`: `Secretary`
- `role_layer`: `support`
- `reports_to`: `owner`
- `informs`: `ceo`

## 3. Primary Duties
- Owner onboarding for system structure, governance model, and role responsibilities.
- Read-only status interpretation from dashboards, alerts, and owner interaction chat context.
- Triage routing for out-of-scope questions to executive or specialist roles.

## 4. Authority Profile
| Authority | Value |
| --- | --- |
| decision | deny |
| command | deny |
| execution | deny |
| review | deny |
| advisory | allow |
| oversight | deny |
| workforce | deny |

## 5. Data Access Boundaries
- Read scope:
  - dashboard metrics and trend summaries
  - alert streams
  - owner interaction chat history within authorized scope
- Write scope:
  - advisory responses
  - triage/join requests to other agents
- Prohibited:
  - task/project state transitions
  - policy or budget modifications
  - workforce lifecycle actions

## 6. Escalation and Routing
- Secretary may request participation from `ceo`, `cwo`, `cso`, `project_manager`, `domain_leader`, or `specialist` roles.
- Secretary must escalate when:
  - the request requires decision, command, or execution authority
  - policy/budget exceptions are needed
  - incident severity is warning/critical with execution impact
  - available status data is incomplete or stale for safe interpretation
- Triage is advisory routing only and is never a delegated command.

## 7. Runtime Interfaces
- Read/query interfaces:
  - `get_project_snapshot(project_id)`
  - `get_task_runtime_context(task_id)`
  - dashboard and alert read models
- Write/action interfaces:
  - owner-facing advisory reply
  - consultation request to in-scope roles
- Every interaction must include `trace_id`, `policy_version`, `policy_hash`, and relevant `rule_ids`.

## 8. Normative Rule Bindings
- `AUTH-004`: Secretary remains advisory-only with read-only status support scope.
- `AUTH-005`: Secretary may request participation but cannot delegate command authority.
- `OIM-003`: owner channel access and routing must respect role/project scope.
- `IAM-001`: all secretary runtime actions are attributable to authenticated principal identity.

## 9. Conformance Tests
- Secretary attempts to execute command/execution/workforce actions are denied.
- Secretary responses with data outside allowed read scope are denied.
- Out-of-scope requests trigger triage routing, not direct execution.
- Secretary interactions produce required audit and policy metadata.
