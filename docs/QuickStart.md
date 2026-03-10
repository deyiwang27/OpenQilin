# Quick Start

## 1. Read Architecture
- Overview: `docs/SystemOverview.md`
- Governance model: `docs/GovernanceGuide.md`

## 2. Read Implementation Specs
- Runtime: `spec/infrastructure/architecture/RuntimeArchitecture.md`
- Governance: `spec/governance/architecture/GovernanceArchitecture.md`

## 3. Load Constitutional Policies
- Runtime manifest first: `constitution/core/PolicyManifest.yaml`
- Charter: `constitution/governance/Charter.md`
- Rule catalog: `constitution/core/PolicyRules.yaml`
- Authority matrix: `constitution/core/AuthorityMatrix.yaml`
- Validate required files in `policy_bundle.required_files`
- Verify runtime `policy_version` + `bundle_hash` against snapshot in `constitution/versions/` when releasing

## 4. Build Against Contracts
- Use rule IDs and policy versions in runtime events.
