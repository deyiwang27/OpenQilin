# OpenQilin v1 - Release Promotion Checklist

## 1. Scope
- Provide operator-facing promotion checklist for release candidate handoff.
- Make promotion and rollback decision points explicit and auditable.

## 2. Required Inputs
- release version tag candidate (for example `0.1.0-rc1`)
- target git commit hash
- CI run URL with passing required checks
- rollback drill evidence reference from `M4-WP2`
- release-gate matrix evidence reference from `M4-WP3`

## 3. Decision Points
### D1_ci_and_quality_gates
- Owner Role: `administrator`
- Decision: Are CI and mandatory quality gates green on the release candidate commit?
- Pass Criteria: All required CI checks pass (`ruff`, `mypy`, test suites, integrity checks).
- Fail Action: Block promotion and open remediation issue.
- Rollback Hook: No rollback execution required; keep current production version unchanged because promotion is blocked.

### D2_release_candidate_gate_matrix
- Owner Role: `auditor`
- Decision: Do release-candidate gate matrix outputs confirm smoke + conformance readiness?
- Pass Criteria: `ops/scripts/run_release_gate_matrix.py --scope release-candidate` completes with no failed step.
- Fail Action: Mark release candidate non-promotable and return to engineering remediation.
- Rollback Hook: If deployment started, roll back application to last compatible release build.

### D3_migration_and_rollback_readiness
- Owner Role: `owner`
- Decision: Are migration forward-apply and rollback drill records complete?
- Pass Criteria: Migration/rollback checks pass and evidence includes operator, reason, and version.
- Fail Action: Stop promotion until missing migration/rollback evidence is remediated.
- Rollback Hook: Execute restore-mode rollback using recorded backup/snapshot reference.

### D4_manual_go_no_go
- Owner Role: `ceo`
- Decision: Final promotion go/no-go.
- Pass Criteria: Owner, auditor, and administrator sign-off recorded.
- Fail Action: Reject release candidate and retain existing production baseline.
- Rollback Hook: Trigger incident rollback protocol if post-promotion instability appears.

## 4. Approval Record
- `administrator`: `pending`
- `auditor`: `pending`
- `owner`: `pending`
- `ceo`: `pending`

## 5. Promotion Output Record
- promoted version: `pending`
- promoted commit: `pending`
- promotion timestamp UTC: `pending`
- rollback fallback version: `pending`
- evidence index reference: `implementation/v1/planning/ReleaseArtifactIndex-v1.md`
