# OpenQilin - Agent Authority Graph Specification

## 1. Scope
- Defines authority types, role-to-authority mapping, constraints, and escalation primitives.
- Source of truth alignment: `spec/governance/GovernanceArchitecture.md` sections 3.7, 4.1, 4.4, 4.5, 4.6.
- Runtime authority values MUST align with `constitution/core/AuthorityMatrix.yaml`.

## 2. Canonical Authorities
- Decision, Command, Execution, Review, Advisory, Oversight, Workforce
- Emergency authority is modeled as a conditional intervention power bound to governance roles.

## 3. Authority Matrix
| Role | Decision | Command | Execution | Review | Advisory | Oversight | Workforce |
| --- | --- | --- | --- | --- | --- | --- | --- |
| owner | Y | Y | - | Y | Y | Y | Y |
| concierge_bootstrap | - | - | - | - | Y | - | Y |
| concierge_passive | - | - | - | - | Y | - | - |
| administrator | - | - | - | - | - | Y | - |
| auditor | - | - | - | - | - | Y | - |
| ceo | Y | Y | - | - | - | - | - |
| cwo | - | Y | - | - | - | - | Y |
| cso | Y | - | - | - | Y | - | - |
| project_manager | Y | Y | - | - | - | - | Y |
| domain_lead | - | - | - | Y | Y | - | - |
| specialist | - | - | Y | - | - | - | - |

Notes:
- `concierge_bootstrap` is initialization-only and can be active only before system initialization and `ceo` handoff completion.
- `concierge_passive` is post-handoff advisory-only and cannot perform workforce actions.
- Reactivation from `concierge_passive` to `concierge_bootstrap` requires explicit `owner` approval.

## 4. Hard Constraints
- Governance agents cannot participate in project execution.
- Executive agents cannot override `auditor` or `administrator` actions.
- Only the `cwo` may manage system-level agent creation or termination.
- `project_manager` may create `specialist` agents only within project scope and budget.
- All emergency actions must be recorded in immutable execution logs.

## 5. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| AUTH-001 | Actions outside authority matrix MUST be denied. | critical | Policy Engine |
| AUTH-002 | Governance enforcement actions MUST NOT be overridden by executive or operational roles. | critical | Policy Engine |
| AUTH-003 | System-level workforce lifecycle actions MUST be restricted to `cwo` authority. | critical | Policy Engine |
| AUTH-004 | `concierge_bootstrap` role MUST only be active pre-initialization and before `ceo` handoff completion. | critical | Policy Engine |
| AUTH-005 | Reactivating `concierge_bootstrap` from `concierge_passive` MUST require explicit `owner` approval. | critical | Policy Engine |
| AUD-001 | Emergency actions MUST emit immutable audit records with trace context. | high | Observability |

## 6. Data Contract
- Authority check request/response schema references PolicyEngine contract.
- Required authority check inputs:
  - actor role
  - intended authority type
  - action and target
  - project scope and budget context (when applicable)

## 7. Conformance Tests
- Invalid role-action-target triplets are denied.
- Executive override attempts against governance actions are denied.
- Non-`cwo` system-level agent creation/termination attempts are denied.
- `concierge_bootstrap` is denied when used after handoff-complete state.
- `concierge_passive` workforce actions are denied.
- Emergency actions without audit metadata fail validation.
