# Change Control

## Scope
Defines how constitutional policy artifacts are modified.

## Approval Policy (v1)
- `ceo` may propose policy changes.
- Only the `owner` can approve policy changes.
- `administrator` publishes approved policy bundles.
- `auditor` verifies policy-change audit integrity.

## Change Workflow
1. Proposal created (`ceo` or `owner`).
2. Impact assessment prepared (affected rules, runtime effect, rollback plan).
3. `owner` approval decision recorded.
4. Policy bundle version incremented and runtime manifest published.
5. Global active version switched atomically.
6. Snapshot stored in `constitution/versions/<version>/` with `ReleaseRecord.yaml`.
7. Change event recorded in immutable audit log.

## Rollback Policy
- Rollback target must be a previously published immutable snapshot.
- Rollback requires `owner` approval.
- Rollback must emit audit event with rationale.

## Audit Requirement
All policy changes must log:
- proposer
- approver
- timestamp
- affected files
- policy version before/after
- change summary

## Snapshot Release Record
Each published snapshot must include `constitution/versions/<version>/ReleaseRecord.yaml` with:
- `policy_version`
- `published_at`
- `published_by_role`
- `approved_by_role`
- `bundle_hash`
- `artifact_hashes`
- `change_summary`

## Bundle Hash Rule
- `bundle_hash` must be deterministic and reproducible from required policy artifacts.
- v1 hash process:
  1. Compute SHA256 for each file in `policy_bundle.required_files` (from runtime manifest).
  2. Build canonical input lines `path:sha256` in required-files order.
  3. SHA256 that canonical input to produce final `bundle_hash`.
- Runtime manifest and snapshot release record must carry the same `bundle_hash`.
