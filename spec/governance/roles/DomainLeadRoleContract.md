# OpenQilin - Domain Lead Role Contract Specification

## 1. Scope
- Defines runtime contract for `domain_lead`.
- First MVP posture: role is declared in schema for forward compatibility but runtime activation is disabled by policy.

## 2. Role Identity
- `role_id`: `domain_lead`
- `display_name`: `Domain Lead`
- `role_layer`: `operations`
- `reports_to`: `project_manager`
- `informs`: `project_manager`, `cwo` (risk escalation)

## 3. Primary Duties
- Provide domain methodology and technical design guidance.
- Review specialist outputs for correctness and quality.
- Identify domain risks and recommend remediation.

## 4. Authority Profile
| Authority | Value |
| --- | --- |
| decision | deny |
| command | deny |
| execution | deny |
| review | allow |
| advisory | allow |
| oversight | deny |
| workforce | deny |

## 5. Data Access Boundaries
- Read scope:
  - scoped project/task artifacts and technical execution notes
  - domain-relevant metrics and quality indicators
- Write scope:
  - review outcomes, rework recommendations, domain advisories
- Prohibited:
  - direct specialist command assignment
  - workforce lifecycle changes
  - governance policy actions

## 6. Escalation and Routing
- Escalate unresolved technical risk to `project_manager`.
- Escalate material domain risk to `cwo` through project governance path.
- Advisory output cannot be used as command delegation.

## 7. Runtime Interfaces
- `spec/orchestration/memory/ProjectArtifactModel.md`
- `spec/cross-cutting/contracts/ProjectTaskQueryContracts.md`
- `spec/state-machines/TaskStateMachine.md`

## 8. Normative Rule Bindings
- `AUTH-001`
- `AUTH-002`
- `OIM-003`
- `AUD-001`

## 9. Conformance Tests
- Domain lead cannot perform command/workforce/execution actions.
- Review actions are scoped to authorized project context.
- Rework recommendations are traceable and auditable.
