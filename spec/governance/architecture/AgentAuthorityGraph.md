# OpenQilin - Agent Authority Graph Specification

## 1. Scope
- Defines authority types, role-to-authority mapping, constraints, and escalation primitives.
- Source of truth alignment: `spec/governance/architecture/GovernanceArchitecture.md` sections 3.7, 4.1, 4.4, 4.5, 4.6.
- Runtime authority values MUST align with `constitution/core/AuthorityMatrix.yaml`.

## 2. Canonical Authorities
- Decision, Command, Execution, Review, Advisory, Oversight, Workforce
- Emergency authority is modeled as a conditional intervention power bound to governance roles.

## 3. Authority Matrix
| Role | Decision | Command | Execution | Review | Advisory | Oversight | Workforce |
| --- | --- | --- | --- | --- | --- | --- | --- |
| owner | Y | Y | - | Y | Y | Y | Y |
| secretary | - | - | - | - | Y | - | - |
| administrator | - | - | - | - | - | Y | - |
| auditor | - | - | - | - | - | Y | - |
| ceo | Y | Y | - | - | - | - | - |
| cwo | - | Y | - | - | - | - | Y |
| cso | Y | - | - | - | Y | - | - |
| project_manager | Y | Y | - | - | - | - | Y |
| domain_leader | - | - | - | Y | Y | - | - |
| specialist | - | - | Y | - | - | - | - |

Notes:
- `secretary` is advisory-only and acts as onboarding guide + status interpreter + triage router.
- `secretary` has read-only access to relevant dashboard, alert, and owner chat data for basic analysis.
- `secretary` can invite executive/specialist participation for out-of-scope questions, but cannot command them.
- `cso` `decision: Y` means CSO may form and issue a strategic review opinion (Aligned / Needs Revision / Strategic Conflict). It does not confer approval or veto authority — CSO decisions are advisory and non-binding without CEO or owner endorsement. See `CsoRoleContract §4`.
- CEO `emergency_review` carve-out: CEO `review: -` applies to routine review. CEO retains bounded `emergency_review` authority for safety incidents and emergency project shutdown only. See `CeoRoleContract §4`.

## 4. Hard Constraints
- Governance agents cannot participate in project execution.
- Executive agents cannot override `auditor` or `administrator` actions.
- `cwo` manages system-level agent creation or termination in normal operations; `owner` exceptions require explicit constitutional override approval.
- `project_manager` may create `specialist` agents only within project scope and budget.
- All emergency actions must be recorded in immutable execution logs.

## 5. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| AUTH-001 | Actions outside authority matrix MUST be denied. | critical | Policy Engine |
| AUTH-002 | Governance enforcement actions MUST NOT be overridden by executive or operational roles. | critical | Policy Engine |
| AUTH-003 | System-level workforce lifecycle actions MUST be executed by `cwo` in normal operations; `owner` may authorize exceptions through constitutional override workflow. | critical | Policy Engine |
| AUTH-004 | `secretary` role MUST remain advisory-only and MAY access relevant dashboard, alert, and owner chat data in read-only mode for onboarding and status interpretation. | high | Policy Engine |
| AUTH-005 | `secretary` role MAY request executive or specialist participation for out-of-scope questions but MUST NOT delegate as command authority. | high | Policy Engine |
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
- Non-`cwo` system-level agent creation/termination attempts are denied unless an explicit `owner` override approval is present.
- `secretary` command/execution/workforce actions are denied.
- `secretary` status-analysis requests over allowed read scopes are denied.
- Emergency actions without audit metadata fail validation.
