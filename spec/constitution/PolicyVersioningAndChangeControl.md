# OpenQilin - Policy Versioning and Change Control Specification

## 1. Scope
- Defines policy lifecycle, approval, rollout, and rollback controls.
- Source alignment: constitutional assets under `constitution/`.

## 2. Versioning Rules
- Policy bundle versioning uses semantic versioning: `MAJOR.MINOR.PATCH`.
- Backward-incompatible policy behavior changes require `MAJOR` bump.
- New rules or non-breaking defaults require `MINOR` bump.
- Metadata-only fixes require `PATCH` bump.

## 3. Active Version Model (v1)
- Exactly one global policy version is active at any time.
- All runtime policy decisions resolve against this active version.
- No per-task/per-project policy pinning in v1.

## 4. Change Authority (v1)
- `ceo` may propose policy updates.
- `owner` is sole policy approver.
- `administrator` publishes approved policy bundle.
- `auditor` verifies post-publish enforcement and audit integrity.

## 5. Change Control Workflow
1. Propose change (`ceo` or `owner`).
2. Run impact review (scope, affected rule IDs, enforcement impact).
3. `owner` approval decision.
4. Publish approved bundle.
5. Atomically switch global active version.
6. Snapshot bundle to `constitution/versions/`.
7. Emit change audit event and release note.

## 6. Bundle Manifest Contract
Minimum manifest fields:
- `policy_version`
- `published_at`
- `approved_by`
- `bundle_hash`
- `artifact_hashes` (per YAML artifact)
- `change_summary`

## 7. Rollback Rules
- Rollback target must be a previously published immutable snapshot.
- Rollback requires `owner` approval.
- Rollback action must emit auditable change event with rationale.

## 8. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| PVC-001 | Runtime decisions MUST include policy version and hash. | critical | Policy Engine |
| PVC-002 | Policy activation MUST be atomic to prevent mixed-version decisions. | critical | Constitution Binding |
| PVC-003 | Policy publication without `owner` approval MUST be rejected. | critical | Change Control |
| PVC-004 | Rollback operations MUST target immutable snapshots only. | high | Change Control |

## 9. Conformance Tests
- Rollback to prior policy version preserves decision reproducibility.
- Concurrent decision requests never observe mixed policy versions during switch.
- Publish attempt without `owner` approval fails.
- Manifest hash mismatch causes publish rejection.
