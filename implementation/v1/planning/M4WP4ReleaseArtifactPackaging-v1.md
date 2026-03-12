# OpenQilin v1 - M4-WP4 Release Artifact and Promotion Checklist Packaging

Date: `2026-03-12`  
Milestone: `M4 Hardening and Release Readiness`  
Work package issue: `#25`

## 1. Scope
- Package release-candidate artifacts for operator handoff.
- Publish explicit promotion decision points with rollback hooks.
- Provide traceable artifact index and packaging commands.

## 2. Implemented Artifacts
- `src/openqilin/release_readiness/artifact_packaging.py`
  - release artifact bundle schema
  - artifact inventory and promotion decision-point contracts
  - checklist markdown renderer and contract validator
- `ops/scripts/run_release_artifact_packager.py`
  - emits release artifact bundle JSON + rendered checklist markdown
- `ops/scripts/check_release_artifact_package.py`
  - validates required WP4 docs and decision/rollback coverage
- `implementation/v1/quality/ReleasePromotionChecklist-v1.md`
  - operator-facing go/no-go checklist with explicit rollback hooks
- `implementation/v1/planning/ReleaseArtifactIndex-v1.md`
  - artifact inventory with traceability links

## 3. Promotion and Rollback Decision Coverage
- `D1_ci_and_quality_gates`: CI hard gate pass/fail and non-promotion fallback.
- `D2_release_candidate_gate_matrix`: smoke+conformance gate result and rollback to last compatible build.
- `D3_migration_and_rollback_readiness`: migration evidence gate and restore-mode rollback hook.
- `D4_manual_go_no_go`: final approval record and post-promotion incident rollback protocol.

## 4. Validation Commands
- `uv run ruff check src/openqilin/release_readiness/artifact_packaging.py ops/scripts/run_release_artifact_packager.py ops/scripts/check_release_artifact_package.py tests/unit/test_m4_wp4_release_artifact_packaging.py tests/conformance/test_m4_wp4_release_artifact_package_conformance.py`
- `uv run mypy src/openqilin/release_readiness/artifact_packaging.py ops/scripts/check_release_artifact_package.py ops/scripts/run_release_artifact_packager.py`
- `uv run pytest tests/unit/test_m4_wp4_release_artifact_packaging.py tests/conformance/test_m4_wp4_release_artifact_package_conformance.py`
- `uv run python ops/scripts/check_release_artifact_package.py`
- `uv run pytest tests/unit tests/component tests/integration tests/contract tests/conformance`
