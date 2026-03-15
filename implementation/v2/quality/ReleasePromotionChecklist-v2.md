# OpenQilin v2 - Release Promotion Checklist

Adapts `implementation/v1/quality/ReleasePromotionChecklist-v1.md` for v2. Same decision-point structure.

---

## 1. Scope

Operator-facing promotion checklist for v2 release candidate handoff. Each decision point must be explicitly passed before promotion proceeds.

---

## 2. Required Inputs

- release version tag candidate (e.g. `0.2.0-rc1`)
- target git commit hash
- CI run URL with all required checks passing
- non-local secret readiness proof (`OPENQILIN_CONNECTOR_SHARED_SECRET` override confirmation)
- `oq-doctor` clean-pass evidence on a fresh compose stack
- Alembic migration forward-apply evidence
- rollback drill evidence reference
- release-gate matrix evidence reference

**[v2] Additional required inputs:**
- Rego bundle version confirmed matching `settings.expected_constitution_version`
- All M11–M16 WP exit criteria confirmed met (or applicable milestone exit criteria for the release scope)
- Grafana dashboard confirmed populated with real data (if M14+ scope)

---

## 3. Decision Points

### D1 — CI and Quality Gates

- **Owner role:** `administrator`
- **Decision:** Are CI and mandatory quality gates green on the release candidate commit?
- **Pass criteria:** All required CI checks pass (`ruff`, `mypy`, test suites, conformance checks, migration forward-apply, Rego bundle lint).
- **[v2] Pass criteria addition:** No `InMemory*` class instantiation in any production code path detected by lint/grep check.
- **Fail action:** Block promotion; open remediation issue.
- **Rollback hook:** No deployment started; keep current production version unchanged.

### D2 — Release Candidate Gate Matrix

- **Owner role:** `auditor`
- **Decision:** Do release-candidate gate matrix outputs confirm smoke + conformance readiness?
- **Pass criteria:** `ops/scripts/run_release_gate_matrix.py --scope release-candidate` completes with no failed step.
- **[v2] Pass criteria addition:** `oq-doctor` reports all blocking checks as `pass` on a clean compose stack.
- **Fail action:** Mark release candidate non-promotable; return to engineering remediation.
- **Rollback hook:** If deployment started, roll back application to last compatible release build.

### D3 — Migration and Rollback Readiness

- **Owner role:** `owner`
- **Decision:** Are migration forward-apply and rollback drill records complete?
- **Pass criteria:** Migration/rollback checks pass; evidence includes operator, reason, and version.
- **[v2] Pass criteria addition:** All Alembic migration files have been applied and verified on a clean PostgreSQL instance.
- **Fail action:** Stop promotion until missing migration/rollback evidence is remediated.
- **Rollback hook:** Execute restore-mode rollback using recorded backup/snapshot reference.

### D4 — Manual Go/No-Go

- **Owner role:** `ceo`
- **Decision:** Final promotion go/no-go.
- **Pass criteria:** `owner`, `auditor`, and `administrator` sign-off recorded.
- **[v2] Pass criteria addition:** All WPs in scope for this release have exit criteria confirmed; no open C-series or H-series bugs from `ArchitecturalReviewFindings-v2.md` remain unaddressed in the release scope.
- **Fail action:** Reject release candidate; retain existing production baseline.
- **Rollback hook:** Trigger incident rollback protocol if post-promotion instability appears.

---

## 4. Approval Record

- `administrator`: `pending`
- `auditor`: `pending`
- `owner`: `pending`
- `ceo`: `pending`

---

## 5. Promotion Output Record

- promoted version: `pending`
- promoted commit: `pending`
- promotion timestamp UTC: `pending`
- rollback fallback version: `pending`
- Rego bundle version at promotion: `pending`
- Alembic migration head at promotion: `pending`

---

## 6. Related References

- `implementation/v2/quality/QualityAndDelivery-v2.md`
- `implementation/v2/quality/ReleaseVersioningAndRollback-v2.md`
- `implementation/v2/planning/05-milestones/MvpV2MilestonePlan-v1.md`
- `implementation/v2/planning/00-direction/ArchitecturalReviewFindings-v2.md`
