# OpenQilin - Agent Authority Graph Specification

## 1. Scope
- Defines authority types, role-to-authority mapping, constraints, and escalation primitives.
- Source of truth alignment: `spec/governance/GovernanceArchitecture.md` sections 3.7, 4.1, 4.4, 4.5, 4.6.

## 2. Canonical Authorities
- Decision, Command, Execution, Review, Advisory, Oversight, Workforce
- Emergency authority is modeled as a conditional intervention power bound to governance roles.

## 3. Authority Matrix
| Role | Decision | Command | Execution | Review | Advisory | Oversight | Workforce |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Admin | - | - | - | - | - | Y | - |
| Auditor | - | - | - | - | - | Y | - |
| CEO | Y | Y | - | - | - | - | - |
| CWO | - | Y | - | - | - | - | Y |
| CSO | Y | - | - | - | Y | - | - |
| PM | Y | Y | - | - | - | - | Y |
| DL | - | - | - | Y | Y | - | - |
| Specialist | - | - | Y | - | - | - | - |

## 4. Hard Constraints
- Governance agents cannot participate in project execution.
- Executive agents cannot override Auditor or Administrator actions.
- Only the CWO may manage system-level agent creation or termination.
- Project Managers may create specialist agents only within project scope and budget.
- All emergency actions must be recorded in immutable execution logs.

## 5. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| AUTH-001 | Actions outside authority matrix MUST be denied. | critical | Policy Engine |
| AUTH-002 | Governance enforcement actions MUST NOT be overridden by executive or operational roles. | critical | Policy Engine |
| AUTH-003 | System-level workforce lifecycle actions MUST be restricted to CWO authority. | critical | Policy Engine |
| AUTH-004 | Emergency actions MUST emit immutable audit records with trace context. | high | Observability |

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
- Non-CWO system-level agent creation/termination attempts are denied.
- Emergency actions without audit metadata fail validation.
