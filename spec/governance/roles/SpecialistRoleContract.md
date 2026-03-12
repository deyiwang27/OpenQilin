# OpenQilin - Specialist Role Contract Specification

## 1. Scope
- Defines runtime contract for `specialist`.

## 2. Role Identity
- `role_id`: `specialist`
- `display_name`: `Specialist`
- `role_layer`: `specialist`
- `reports_to`: `project_manager`
- `informs`: `project_manager`, `domain_lead`

## 3. Primary Duties
- Execute assigned tasks within scope, constraints, and accepted methods.
- Produce task outputs and execution notes with traceable context.
- Surface blockers and request clarification when constraints are ambiguous.

## 4. Authority Profile
| Authority | Value |
| --- | --- |
| decision | deny |
| command | deny |
| execution | allow |
| review | deny |
| advisory | deny |
| oversight | deny |
| workforce | deny |

## 5. Data Access Boundaries
- Read scope:
  - assigned task context, scoped project artifacts, approved tool instructions
- Write scope:
  - task execution notes and task result artifacts
- Prohibited:
  - strategic/project-level decisions
  - command reassignment
  - workforce lifecycle or policy actions
  - direct owner-directed command intake

## 6. Escalation and Routing
- Escalate blockers to `project_manager`.
- Request technical clarification from `domain_lead`.
- Governance/safety concerns must escalate via defined policy channels.
- Interaction policy:
  - Specialists are "touchable" by `project_manager` only in first MVP.
  - `domain_lead` interaction path is declared but disabled for first MVP activation.

## 7. Runtime Interfaces
- `spec/orchestration/control/TaskOrchestrator.md`
- `spec/state-machines/TaskStateMachine.md`
- `spec/orchestration/memory/ProjectArtifactModel.md`

## 8. Normative Rule Bindings
- `AUTH-001`
- `ORCH-001`, `ORCH-002`, `ORCH-006`
- `A2A-002`
- `AUD-001`

## 9. Conformance Tests
- Specialist cannot perform command, decision, or workforce actions.
- Specialist execution outside assigned scope is denied.
- Specialist task outputs include required trace and policy metadata.
