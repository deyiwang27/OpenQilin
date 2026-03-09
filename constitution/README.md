# Constitution Layer

Purpose: runtime constitutional source of truth for policy enforcement.

## How Agents Should Use This Folder
1. Load `core/PolicyManifest.yaml` first.
2. Validate required policy files listed in manifest.
3. Apply rules using the single global active policy version.
4. If any required file is missing/invalid, fail closed (`deny`).

## Canonical Runtime Policy Files (YAML)
### Core
- `core/PolicyManifest.yaml`
- `core/AuthorityMatrix.yaml`
- `core/PolicyRules.yaml`
- `core/ObligationPolicy.yaml`

### Domain
- `domain/EscalationPolicy.yaml`
- `domain/BudgetPolicy.yaml`
- `domain/SafetyPolicy.yaml`
- `domain/OperationsPolicy.yaml`

## Supporting Governance Docs (Human-readable)
- `governance/Charter.md`
- `governance/ChangeControl.md`

## Templates
- `templates/DomainPolicyTemplate.yaml`

## Runtime Decision Metadata (Required)
Every governance-critical decision should include:
- `policy_version`
- `policy_hash`
- `rule_ids`
- `trace_id`

## Versioning
Snapshot each approved release in `constitution/versions/`.
