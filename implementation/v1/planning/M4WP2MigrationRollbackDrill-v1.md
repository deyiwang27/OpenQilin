# OpenQilin v1 - M4-WP2 Migration Validation and Rollback Drill

Date: `2026-03-12`  
Milestone: `M4 Hardening and Release Readiness`  
Work package issue: `#23`

## 1. Scope
- Add deterministic migration-validation + rollback-drill command flow.
- Emit structured drill evidence for operator auditability.
- Gate CI on rollback-readiness policy/checklist integrity.

## 2. Implemented Artifacts
- `src/openqilin/apps/admin_cli.py`
  - added `rollback-drill` command with two modes:
    - `restore`: forward migration validation plus required `--restore-reference` evidence
    - `downgrade`: downgrade/upgrade round-trip drill for disposable environments (guarded by explicit `--allow-downgrade-destructive`)
  - added migration contract checks for:
    - `pgvector` extension availability
    - `knowledge_embedding` table availability
  - added deterministic JSON evidence payload/write helpers.
- `ops/scripts/run_migration_rollback_drill.py`
  - script entrypoint for rollout operators and automation wrappers.
  - mirrors downgrade safety guard via `--allow-downgrade-destructive`.
- `ops/scripts/check_migration_rollback_readiness.py`
  - CI integrity checks for migration files, rollback policy snippets, and gate wiring.
- `.github/workflows/ci.yml`
  - added `Migration rollback readiness checks` step.
- `implementation/v1/quality/ReleaseVersioningAndRollback-v1.md`
  - added rollback-drill command matrix and CI gate requirement.
- `migrations/README.md`
  - documented migration/rollback drill command usage.

## 3. Drill Evidence Output Contract
- default output file:
  - `implementation/v1/planning/artifacts/migration_rollback_drill_latest.json`
- required fields:
  - `timestamp_utc`, `release_version`, `operator`, `reason`
  - `rollback_mode`, `rollback_revision` or `restore_reference`
  - masked `database_url`
  - `steps[]` with deterministic pass/fail detail
  - `overall_success`

## 4. Validation Commands
- `uv run ruff check src/openqilin/apps/admin_cli.py ops/scripts/run_migration_rollback_drill.py ops/scripts/check_migration_rollback_readiness.py tests/unit/test_m4_wp2_migration_rollback_drill.py`
- `uv run mypy src/openqilin/apps/admin_cli.py`
- `uv run pytest tests/unit/test_m4_wp2_migration_rollback_drill.py`
- `uv run python ops/scripts/check_migration_rollback_readiness.py`
