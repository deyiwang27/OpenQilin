# OpenQilin v1 - M4 Evidence Pack

Date: `2026-03-12`  
Milestone: `M4 Hardening and Release Readiness`  
Primary issue: `#21` (`M4: Hardening and Release Readiness Kickoff`)  
WP closeout issue: `#26` (`M4-WP5: M4 evidence pack and milestone closeout validation`)

## 1. Scope
- Consolidate M4 release-readiness evidence for `M4-WP5`.
- Map M4 exit checklist criteria to concrete tests/checks and operational docs.
- Document milestone closeout linkage workflow (parent issue, PR, and merge closeout steps).

## 2. Validation Commands
- `uv run pytest tests/unit tests/component tests/integration tests/contract tests/conformance`
- `uv run ruff check .`
- `uv run mypy .`
- `uv run python ops/scripts/check_migration_rollback_readiness.py`
- `uv run python ops/scripts/check_release_gate_matrix.py`
- `uv run python ops/scripts/check_release_artifact_package.py`
- Latest baseline before WP5 commit: `156 passed` (`pytest`), `ruff` pass, `mypy` pass.
- Baseline commit before WP5 implementation: `0b4754e`.

## 3. Evidence Map by M4 Exit Checklist
### 3.1 Release-readiness dashboards and alerts are defined, runbook-linked, and validated
- Docs:
  - `implementation/v1/planning/M4WP1ObservabilityBaseline-v1.md`
  - `implementation/v1/quality/QualityAndDelivery-v1.md`
- Tests:
  - `tests/unit/test_m4_wp1_observability_release_readiness.py`

### 3.2 Migration and rollback drills are repeatable with recorded evidence
- Docs:
  - `implementation/v1/planning/M4WP2MigrationRollbackDrill-v1.md`
  - `implementation/v1/quality/ReleaseVersioningAndRollback-v1.md`
- Runtime/scripts:
  - `src/openqilin/apps/admin_cli.py` (`rollback-drill` command)
  - `ops/scripts/run_migration_rollback_drill.py`
  - `ops/scripts/check_migration_rollback_readiness.py`
- Tests:
  - `tests/unit/test_m4_wp2_migration_rollback_drill.py`

### 3.3 `full` profile smoke and conformance gates are deterministic promotion blockers
- Docs:
  - `implementation/v1/planning/M4WP3ReleaseGateHardening-v1.md`
- Runtime/scripts:
  - `src/openqilin/release_readiness/gate_matrix.py`
  - `ops/scripts/run_release_gate_matrix.py`
  - `ops/scripts/check_release_gate_matrix.py`
- Tests:
  - `tests/unit/test_m4_wp3_release_gate_matrix.py`
  - `tests/conformance/test_m4_wp3_release_gate_hardening_conformance.py`
- Scope boundary:
  - The M4 release-candidate smoke contract validates `admin bootstrap --smoke-in-process` under `compose --profile full`.
  - `api_app`, `orchestrator_worker`, and `communication_worker` compose services are placeholder containers in M4 and are excluded from M4 promotion evidence.

### 3.4 Release artifact and promotion checklist package is complete and operator-usable
- Docs:
  - `implementation/v1/planning/M4WP4ReleaseArtifactPackaging-v1.md`
  - `implementation/v1/planning/ReleaseArtifactIndex-v1.md`
  - `implementation/v1/quality/ReleasePromotionChecklist-v1.md`
- Runtime/scripts:
  - `src/openqilin/release_readiness/artifact_packaging.py`
  - `ops/scripts/run_release_artifact_packager.py`
  - `ops/scripts/check_release_artifact_package.py`
- Tests:
  - `tests/unit/test_m4_wp4_release_artifact_packaging.py`
  - `tests/conformance/test_m4_wp4_release_artifact_package_conformance.py`

### 3.5 Full quality and release gates pass for merged M4 scope
- Validation command group:
  - `uv run ruff check .`
  - `uv run mypy .`
  - `uv run pytest tests/unit tests/component tests/integration tests/contract tests/conformance`
- Gate-integrity checks:
  - `uv run python ops/scripts/check_migration_rollback_readiness.py`
  - `uv run python ops/scripts/check_release_gate_matrix.py`
  - `uv run python ops/scripts/check_release_artifact_package.py`

## 4. Acceptance Criteria Mapping (`#26`)
1. M4 evidence pack maps each exit criterion to concrete tests/checks.
- Covered by Section 3 with explicit doc/script/test mapping for each M4 exit checklist item.

2. Final validation results are posted on parent issue `#21`.
- WP-level evidence already synchronized for `#22`..`#25` and parent updates.
- Completed: final validation summary posted on `#21` and references this evidence pack (`https://github.com/deyiwang27/OpenQilin/issues/21#issuecomment-4044442744`).
- Completed: WP5 implementation evidence posted on `#26` (`https://github.com/deyiwang27/OpenQilin/issues/26#issuecomment-4044441059`).

3. Milestone closeout PR references and closure steps are documented.
- Closeout sequence for M4:
  - Open milestone closeout PR from `feat/21-m4-hardening-release-kickoff` to `main`.
  - In PR description, link parent issue `#21` and child issues `#22`..`#26`.
  - Re-run required gates (`ruff`, `mypy`, full `pytest`, release checks) on the closeout commit.
  - Merge PR; update `ImplementationProgress-v1.md` M4 row to `completed` and `100%`.
  - Close parent issue `#21` with merge commit and evidence links.

## 5. GitHub Issue Evidence Links
- Parent milestone issue: https://github.com/deyiwang27/OpenQilin/issues/21
- `M4-WP1` issue + evidence: https://github.com/deyiwang27/OpenQilin/issues/22, https://github.com/deyiwang27/OpenQilin/issues/22#issuecomment-4043213775
- `M4-WP2` issue + evidence: https://github.com/deyiwang27/OpenQilin/issues/23, https://github.com/deyiwang27/OpenQilin/issues/23#issuecomment-4043581589
- `M4-WP3` issue + evidence: https://github.com/deyiwang27/OpenQilin/issues/24, https://github.com/deyiwang27/OpenQilin/issues/24#issuecomment-4043616599
- `M4-WP4` issue + evidence: https://github.com/deyiwang27/OpenQilin/issues/25, https://github.com/deyiwang27/OpenQilin/issues/25#issuecomment-4044250483, https://github.com/deyiwang27/OpenQilin/issues/25#issuecomment-4044265685
- Parent progress updates: https://github.com/deyiwang27/OpenQilin/issues/21#issuecomment-4043167927, https://github.com/deyiwang27/OpenQilin/issues/21#issuecomment-4043618833, https://github.com/deyiwang27/OpenQilin/issues/21#issuecomment-4044266430, https://github.com/deyiwang27/OpenQilin/issues/21#issuecomment-4044442744
- `M4-WP5` issue + evidence: https://github.com/deyiwang27/OpenQilin/issues/26, https://github.com/deyiwang27/OpenQilin/issues/26#issuecomment-4044441059
