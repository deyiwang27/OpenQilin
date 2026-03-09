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
4. Policy bundle version incremented and published.
5. Global active version switched atomically.
6. Snapshot stored in `constitution/versions/`.
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
