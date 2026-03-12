# OpenQilin v1 - Quality and Delivery

## 1. Scope
- Consolidate test strategy, CI/CD quality gates, and merge/release expectations.

## 2. Test Strategy
Test layers:
- `unit`
- `component`
- `contract`
- `integration`
- `conformance`

Minimum expectations:
- changed modules require unit tests
- contract-touching changes require contract tests
- governance-core path changes require integration or conformance coverage
- critical bug fixes require regression coverage

Local execution:
```bash
uv run pytest tests/unit tests/component
uv run pytest tests/contract tests/integration
uv run pytest tests/conformance
uv run python ops/scripts/run_release_gate_matrix.py --scope ci
uv run python ops/scripts/run_release_gate_matrix.py --scope release-candidate --dry-run
uv run python ops/scripts/check_release_artifact_package.py
uv run python ops/scripts/run_release_artifact_packager.py --release-version 0.1.0-rc1 --git-commit <commit>
```

Fixture rules:
- deterministic IDs and timestamps where practical
- canonical roles, policy metadata, and task states represented in fixtures
- isolated databases/containers for infrastructure-backed tests

## 3. CI Workflow
Recommended branch workflow:
- follow `implementation/v1/workflow/GitHubOperationsManagementGuide-v1.md` as canonical branch policy
- short-lived branches only, created from latest `main`
- PR into protected `main` (or documented procedural equivalent) using squash merge
- no direct commits to `main` for implementation code

Mandatory PR checks:
- locked dependency sync with `uv`
- lint
- format check
- type check
- unit tests
- component tests
- contract tests
- spec/conformance integrity checks
- release-gate matrix checks (`ops/scripts/check_release_gate_matrix.py`)
- release artifact package checks (`ops/scripts/check_release_artifact_package.py`)

Additional checks when relevant:
- integration tests for runtime-flow changes
- migration validation for schema changes
- conformance smoke tests for governance-core behavior changes
- docs/spec drift checks for contract changes
- repository consistency/governance check for structure or policy/documentation refactors (see `implementation/v1/workflow/RepositoryConsistencyAndGovernanceCheck-v1.md`)

## 4. Quality Gates
Merge blocked when:
- lint/format/type checks fail
- required tests fail
- lockfile drift is detected
- critical conformance checks fail
- migration forward-apply validation fails

Release blocked when:
- critical conformance checks fail
- restore/recovery evidence is missing
- unresolved high-priority implementation blockers remain
- unresolved high-risk governance drift or unaddressed folder-fit/duplication conflicts remain
- non-local environments use default connector signing secret (`OPENQILIN_CONNECTOR_SHARED_SECRET=dev-openqilin-secret`)

## 5. Delivery Posture
Initial v1 posture:
- CI required immediately
- CD may remain manual and promotion-gated during local-first development

Manual promotion gates:
- passing CI
- migration plan available
- config/secret readiness confirmed
- connector signing secret override is confirmed for non-local environments (`OPENQILIN_CONNECTOR_SHARED_SECRET` must not remain default)
- rollback path documented
- release-candidate matrix gate run includes smoke + conformance checks (`ops/scripts/run_release_gate_matrix.py --scope release-candidate`)
- smoke evidence scope is explicitly recorded (M4 validates `admin bootstrap --smoke-in-process`; api/worker placeholder containers are out of current promotion scope)
- promotion checklist completed and artifact index references verified (`implementation/v1/quality/ReleasePromotionChecklist-v1.md`, `implementation/v1/planning/ReleaseArtifactIndex-v1.md`)

## 6. Artifact Policy
- build definitions must be reproducible from the repo
- build metadata must include provenance references
- release artifacts must map back to code and config baseline

## 7. Related Follow-Ups
- implementation architecture lives in `design/v1/architecture/ImplementationArchitecture-v1.md`
- foundation/bootstrap details live in `design/v1/foundation/ImplementationFoundation-v1.md`
- GitHub issue/PR/release operations live in `implementation/v1/workflow/GitHubOperationsManagementGuide-v1.md`
- repository consistency/governance check process lives in `implementation/v1/workflow/RepositoryConsistencyAndGovernanceCheck-v1.md`
