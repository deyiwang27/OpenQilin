# OpenQilin v1 - Release Artifact Index

Date: `2026-03-12`  
Scope: `M4-WP4` release artifact packaging and promotion handoff.

## 1. Artifact Inventory
| Artifact ID | Path | Purpose | Traceability |
| --- | --- | --- | --- |
| `compose_full_profile` | `compose.yml` | runtime topology and full-profile smoke baseline | `M2-WP4`, `M4-WP3` |
| `dependency_lock` | `uv.lock` | reproducible dependency set for RC build | CI frozen sync |
| `migration_contract` | `migrations/versions/20260311_0001_pgvector_baseline_contract.py` | schema baseline + pgvector contract | `M2-WP4` |
| `rollback_drill_contract` | `implementation/v1/planning/M4WP2MigrationRollbackDrill-v1.md` | rollback drill and evidence contract | `M4-WP2` |
| `release_gate_matrix_contract` | `implementation/v1/planning/M4WP3ReleaseGateHardening-v1.md` | deterministic release-gate matrix | `M4-WP3` |
| `observability_baseline` | `implementation/v1/planning/M4WP1ObservabilityBaseline-v1.md` | release-readiness dashboards/alerts | `M4-WP1` |
| `promotion_checklist` | `implementation/v1/quality/ReleasePromotionChecklist-v1.md` | go/no-go + rollback decision checklist | `M4-WP4` |
| `artifact_package_contract` | `src/openqilin/release_readiness/artifact_packaging.py` | bundle schema + decision point model | `M4-WP4` |

## 2. Evidence Index
- Parent issue (M4): https://github.com/deyiwang27/OpenQilin/issues/21
- `M4-WP1` evidence: https://github.com/deyiwang27/OpenQilin/issues/22#issuecomment-4043213775
- `M4-WP2` evidence: https://github.com/deyiwang27/OpenQilin/issues/23#issuecomment-4043581589
- `M4-WP3` evidence: https://github.com/deyiwang27/OpenQilin/issues/24#issuecomment-4043616599
- `M4-WP4` evidence: pending issue `#25` closeout comment

## 3. Packaging Commands
```bash
uv run python ops/scripts/check_release_artifact_package.py
uv run python ops/scripts/run_release_artifact_packager.py --release-version 0.1.0-rc1 --git-commit <commit>
```

Outputs:
- `implementation/v1/planning/artifacts/release_candidate_bundle_latest.json`
- `implementation/v1/planning/artifacts/release_promotion_checklist_latest.md`
