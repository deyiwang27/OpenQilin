# OpenQilin - Constitution Management Specification

## 1. Scope
- Defines constitutional governance assets, ownership, and operating model.
- Defines who can propose, approve, publish, and audit constitutional policy at early stage.

## 2. Constitutional Assets
- Charter: `constitution/governance/Charter.md`
- Authority matrix: `constitution/core/AuthorityMatrix.yaml`
- Policy rule catalog: `constitution/core/PolicyRules.yaml`
- Obligation policy: `constitution/core/ObligationPolicy.yaml`
- Policy manifest: `constitution/core/PolicyManifest.yaml`
- Escalation policy: `constitution/domain/EscalationPolicy.yaml`
- Budget policy: `constitution/domain/BudgetPolicy.yaml`
- Safety policy: `constitution/domain/SafetyPolicy.yaml`
- Change control policy: `constitution/governance/ChangeControl.md`

## 3. Ownership and Approval Model (v1)
- Owner:
  - sole approval authority for policy changes
  - final authority for emergency constitutional decisions
- CEO:
  - may propose policy changes to Owner
  - cannot approve or publish policy changes
- Administrator:
  - executes approved publish/snapshot operations
  - cannot alter policy semantics
- Auditor:
  - verifies policy usage and enforcement traceability
  - cannot approve policy changes

## 4. Canonical Runtime Roles (v1)
- Owner
- concierge_bootstrap
- concierge_passive
- Administrator
- Auditor
- CEO
- CWO
- CSO
- ProjectManager
- DomainLead
- Specialist

Unknown roles MUST be treated as unauthorized.

Concierge phase model:
- `concierge_bootstrap`: initialization-only role with limited advisory/workforce capability.
- `concierge_passive`: post-handoff advisory-only role.
- Transition from passive back to bootstrap requires explicit Owner approval.

## 5. Runtime Policy Posture
- Policy format: YAML only.
- Active policy mode: single global active version.
- Policy enforcement mode: fail-closed.

## 6. Audit Strategy (Safety vs Cost)
- All policy decisions MUST emit immutable audit events.
- Event detail levels:
  - `allow`: compact envelope (decision summary + hashes + rule IDs)
  - `deny`: full context envelope
  - `allow_with_obligations`: full context envelope
  - emergency/governance actions: full context envelope
- Retention profile:
  - hot storage window for rapid diagnostics
  - compressed cold archival for long-term traceability

## 7. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| CONS-001 | Constitutional assets MUST be versioned and auditable. | critical | Observability |
| CONS-002 | Owner MUST be the sole approver for policy changes in v1. | critical | Change Control |
| CONS-003 | Runtime policy source MUST be YAML-only in v1. | high | Constitution Binding |
| CONS-004 | Runtime policy mode MUST use a single globally active policy version. | high | Constitution Binding |
| CONS-005 | Unknown runtime roles MUST be denied by default. | critical | Policy Engine |

## 8. Conformance Tests
- Policy loads include version and hash metadata.
- Policy change requests without Owner approval are rejected.
- Runtime requests with unknown roles are denied.
- Decision audit events match compact/full detail policy by decision type.
