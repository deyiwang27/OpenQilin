# OpenQilin - Constitution Management Specification

## 1. Scope
- Defines constitutional governance assets, ownership, and operating model.
- Defines who can propose, approve, publish, and audit constitutional policy at early stage.

## 2. Constitutional Assets
- Charter: `constitution/governance/Charter.md`
- Authority matrix: `constitution/core/AuthorityMatrix.yaml`
- Policy rule catalog: `constitution/core/PolicyRules.yaml`
- Obligation policy: `constitution/core/ObligationPolicy.yaml`
- Runtime policy manifest: `constitution/core/PolicyManifest.yaml`
- Escalation policy: `constitution/domain/EscalationPolicy.yaml`
- Budget policy: `constitution/domain/BudgetPolicy.yaml`
- Safety policy: `constitution/domain/SafetyPolicy.yaml`
- Operations policy: `constitution/domain/OperationsPolicy.yaml`
- Change control policy: `constitution/governance/ChangeControl.md`
- Release snapshot record: `constitution/versions/<version>/ReleaseRecord.yaml`

## 3. Ownership and Approval Model (v1)
- owner:
  - sole approval authority for policy changes
  - final authority for emergency constitutional decisions
- ceo:
  - may propose policy changes to owner
  - cannot approve or publish policy changes
- administrator:
  - executes approved publish/snapshot operations
  - cannot alter policy semantics
- auditor:
  - verifies policy usage and enforcement traceability
  - cannot approve policy changes

## 4. Canonical Runtime Roles (v1)
- owner
- secretary
- administrator
- auditor
- ceo
- cwo
- cso
- project_manager
- domain_leader
- specialist

Unknown roles MUST be treated as unauthorized.

Secretary role model:
- `secretary` display role: Secretary.
- Formal contract: read-only advisory + triage router.
- `secretary` may read relevant dashboard, alert, and owner chat data for onboarding and status interpretation.
- `secretary` cannot command, execute, or perform workforce actions.

## 5. Runtime Policy Posture
- Policy format: YAML only.
- Active policy mode: single global active version.
- Policy enforcement mode: fail-closed.
- Runtime artifact membership source: `policy_bundle.required_files` from `PolicyManifest.yaml`.

## 6. Publish Artifact Model
- Runtime policy operation uses `constitution/core/PolicyManifest.yaml` and required YAML policy files.
- Snapshot governance uses `constitution/versions/<version>/ReleaseRecord.yaml` for publish metadata (`published_at`, publisher/approver role, artifact hashes, change summary).
- Runtime manifest and release record must agree on `policy_version` and `bundle_hash`.

## 7. Audit Strategy (Safety vs Cost)
- All policy decisions MUST emit immutable audit events.
- Event detail levels:
  - `allow`: compact envelope (decision summary + hashes + rule IDs)
  - `deny`: full context envelope
  - `allow_with_obligations`: full context envelope
  - emergency/governance actions: full context envelope
- Retention profile:
  - hot storage window for rapid diagnostics
  - compressed cold archival for long-term traceability

## 8. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| CONS-001 | Constitutional assets MUST be versioned and auditable. | critical | Observability |
| CONS-002 | `owner` MUST be the sole approver for policy changes in v1. | critical | Change Control |
| CONS-003 | Runtime policy source MUST be YAML-only in v1. | high | Constitution Binding |
| CONS-004 | Runtime policy mode MUST use a single globally active policy version. | high | Constitution Binding |
| CONS-005 | Unknown runtime roles MUST be denied by default. | critical | Policy Engine |

## 9. Conformance Tests
- Policy loads include version and hash metadata.
- Policy change requests without `owner` approval are rejected.
- Runtime requests with unknown roles are denied.
- Decision audit events match compact/full detail policy by decision type.
- Snapshot publish includes `ReleaseRecord.yaml` with matching `policy_version`/`bundle_hash`.
