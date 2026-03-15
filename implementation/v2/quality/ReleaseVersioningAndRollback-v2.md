# OpenQilin v2 - Release, Versioning, and Rollback Workflow

Adapts `implementation/v1/quality/ReleaseVersioningAndRollback-v1.md` for v2. Same strategy; v2-specific additions marked **[v2]**.

---

## 1. Scope

Define release versioning, artifact strategy, and rollback rules for MVP-v2 delivery.

---

## 2. Versioning Strategy

- Use semantic versioning.
- MVP-v2 releases under `0.2.z`.
- Every release records:
  - application version
  - Git commit hash
  - Alembic migration head
  - constitution/policy bundle version and hash (`expected_constitution_version`)
  - **[v2]** OPA Rego bundle version and hash
  - **[v2]** LangGraph graph schema version (if graph structure changed)
  - routing-profile config version

---

## 3. Release Artifacts

Release candidate set:
- Docker images for `api`, `orchestrator_worker`, `communication_worker`, `admin`
- **[v2]** `oq_doctor` service image (for operator validation)
- `uv.lock`
- Alembic migration bundle (all migrations through release head)
- **[v2]** OPA Rego bundle (`src/openqilin/policy_runtime_integration/rego/`)
- **[v2]** Grafana provisioning files (`ops/grafana/provisioning/`)
- Compose definitions for local-first baseline
- release notes and conformance evidence links
- release artifact index + promotion checklist:
  - `implementation/v2/quality/ReleasePromotionChecklist-v2.md`

---

## 4. Promotion Rules

Promotion requires:
- passing CI (all mandatory checks)
- passing full-profile smoke and conformance checks
- Alembic migration forward-apply verification on a clean PostgreSQL instance
- rollback-drill verification gate
- release artifact package verification
- rollback plan documented for changed schema/config/runtime surfaces
- secrets/config readiness confirmed for target environment
- **[v2]** `oq-doctor` all blocking checks pass on a fresh stack
- **[v2]** OPA bundle version matches `settings.expected_constitution_version`
- **[v2]** No `InMemory*` class in any production code path (confirmed by static check)

---

## 5. Rollback Rules

Application rollback:
- allowed only to builds compatible with the deployed schema, config, and Rego bundle version
- release metadata must identify the last known compatible version

Schema rollback:
- do not rely on destructive down-migrations
- use forward fixes or restore-from-backup when a schema release is broken
- migrations must be reviewed for backward compatibility during rolling app rollback windows

**[v2] OPA bundle rollback:**
- rolling back the OPA bundle requires matching the constitution YAML versions in `constitution/core/`
- `expected_constitution_version` in settings must be updated in sync with bundle rollback
- incompatible Rego bundle rollback requires coordinated application rollback

**[v2] Budget ledger rollback:**
- budget table schema rollback is a restore-only operation (no destructive down-migration)
- active `reserved` budget reservations must be manually reconciled after rollback

Config rollback:
- routing-profile and provider alias changes must be versioned and auditable
- incompatible config changes require coordinated app rollback plan

---

## 5.1 Migration Validation and Rollback Drill Commands

```bash
# Forward-apply validation on clean DB
uv run python -m openqilin.apps.admin_cli rollback-drill \
  --rollback-mode restore \
  --restore-reference backup-<timestamp> \
  --release-version 0.2.0-rc1 \
  --operator release_manager

# [v2] Doctor check on fresh stack
docker compose --profile doctor run oq_doctor

# [v2] OPA bundle version check
curl http://localhost:8181/v1/data/openqilin/policy/version
```

---

## 6. Incident Response Linkage

- every rollback event emits audit metadata to PostgreSQL `audit_events` table
- **[v2]** rollback events are also exported via OTel and visible in Grafana Audit panel
- rollback execution must record operator, reason, affected version, and timestamp
- release promotion remains manual and WP-gated in MVP-v2

---

## 7. Related References

- `implementation/v2/quality/QualityAndDelivery-v2.md`
- `implementation/v2/quality/ReleasePromotionChecklist-v2.md`
- `design/v2/adr/ADR-0006-PostgreSQL-Repository-Migration.md`
- `design/v2/adr/ADR-0007-Grafana-Single-Dashboard-Strategy.md`
