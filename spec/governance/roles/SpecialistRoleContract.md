# OpenQilin - Specialist Role Contract Specification

## 1. Scope
- Defines runtime contract for `specialist`.

## 2. Role Identity
- `role_id`: `specialist`
- `display_name`: `Specialist`
- `role_layer`: `specialist`
- `reports_to`: `project_manager`
- `informs`: `project_manager`, `domain_leader`

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
- Request technical clarification from `domain_leader` (activated in M13-WP5) when clarification criteria below are met.
- Governance/safety concerns must escalate via defined policy channels.

**DL clarification criteria:** Specialist may route to `domain_leader` for clarification only when:
1. Task requirements are internally contradictory.
2. Required resource is outside task scope as defined by PM.
3. Tool access required for the task is ambiguous or undocumented.

Specialist must first mark task as `clarification_needed` before routing to DL. DL responds within the same trace. If DL cannot resolve, DL escalates to PM. Specialist does not block a task without first requesting clarification.

Interaction policy:

- `project_manager` dispatches Specialist agents; `domain_leader` may interact with Specialist via governed review and clarification paths (activated in M13-WP5).

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
