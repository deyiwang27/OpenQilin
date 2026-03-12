# OpenQilin v1 - Release, Versioning, and Rollback Workflow

## 1. Scope
- Define release versioning, artifact strategy, and rollback rules for v1.

## 2. Versioning Strategy
- Use semantic versioning.
- v1 initial implementation may release under `0.y.z` until interface stability is proven.
- Every release records:
  - application version
  - Git commit
  - schema migration head
  - constitution/policy bundle version and hash
  - routing-profile config version

## 3. Release Artifacts
Release candidate set:
- Docker images for `api`, `orchestrator`, `communication`, and `admin`
- `uv.lock`
- migration bundle
- Compose definitions for local-first baseline
- release notes and conformance evidence links

## 4. Promotion Rules
Promotion requires:
- passing CI
- passing full-profile smoke and conformance checks
- migration forward-apply verification
- rollback-drill verification gate (`uv run python ops/scripts/check_migration_rollback_readiness.py`)
- rollback plan documented for changed schema/config/runtime surfaces
- secrets/config readiness confirmed for target environment

## 5. Rollback Rules
Application rollback:
- allowed only to builds compatible with the deployed schema and config version
- release metadata must identify the last known compatible version

Schema rollback:
- do not rely on destructive down-migrations in v1
- use forward fixes or restore-from-backup when a schema release is broken
- migrations must be reviewed for backward compatibility during rolling app rollback windows

## 5.1 Migration Validation and Rollback Drill Commands
Release and pre-release operators run one of:

```bash
# Policy-aligned path (production-like): validate forward migration + record restore reference
uv run python -m openqilin.apps.admin_cli rollback-drill \
  --rollback-mode restore \
  --restore-reference backup-2026-03-12T020000Z \
  --release-version 0.1.0-rc1 \
  --operator release_manager

# Disposable-environment drill: verify downgrade/upgrade round-trip deterministically
uv run python -m openqilin.apps.admin_cli rollback-drill \
  --rollback-mode downgrade \
  --rollback-revision -1 \
  --release-version 0.1.0-rc1 \
  --operator release_manager
```

Operational equivalent script entrypoint:

```bash
uv run python ops/scripts/run_migration_rollback_drill.py --help
```

Config rollback:
- routing-profile and provider alias changes must be versioned and auditable
- incompatible config changes require coordinated app rollback plan

## 6. Incident Response Linkage
- every rollback event emits audit metadata
- rollback execution must record operator, reason, affected version, and timestamp
- release promotion remains manual in the local-first phase

## 7. Related Design Artifacts
- `implementation/v1/quality/QualityAndDelivery-v1.md`
- `design/v1/architecture/ContainerizationAndLocalInfraTopology-v1.md`
- `design/v1/readiness/DesignReviewChecklistAndExitCriteria-v1.md`
