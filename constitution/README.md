# Constitution Layer

Purpose: runtime institutional source of truth that agents read and follow.

## Canonical Rule Files
- `Charter.md`
- `AuthorityMatrix.yaml`
- `PolicyRules.yaml`
- `EscalationPolicy.yaml`
- `BudgetPolicy.yaml`
- `SafetyPolicy.yaml`
- `ChangeControl.md`

## Runtime Requirement
Every governance-critical decision should include:
- `policy_version`
- `policy_hash`
- matched `rule_ids`

## Versioning
Snapshot each approved release in `constitution/versions/`.
