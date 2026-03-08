# Constitution Layer

Purpose: runtime constitutional source of truth for policy enforcement.

## How Agents Should Use This Folder
1. Load `PolicyManifest.yaml` first.
2. Validate required policy files listed in manifest.
3. Apply rules using the single global active policy version.
4. If any required file is missing/invalid, fail closed (`deny`).

## Canonical Runtime Policy Files (YAML)
- `PolicyManifest.yaml`
- `AuthorityMatrix.yaml`
- `PolicyRules.yaml`
- `ObligationPolicy.yaml`
- `EscalationPolicy.yaml`
- `BudgetPolicy.yaml`
- `SafetyPolicy.yaml`

## Supporting Governance Docs (Human-readable)
- `Charter.md`
- `ChangeControl.md`

## Runtime Decision Metadata (Required)
Every governance-critical decision should include:
- `policy_version`
- `policy_hash`
- `rule_ids`
- `trace_id`

## Versioning
Snapshot each approved release in `constitution/versions/`.
