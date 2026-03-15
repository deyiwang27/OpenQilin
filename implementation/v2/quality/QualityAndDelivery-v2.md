# OpenQilin v2 - Quality and Delivery

Adapts `implementation/v1/quality/QualityAndDelivery-v1.md` for v2. Same rules apply unless marked **[v2]**.

---

## 1. Scope

Consolidate test strategy, CI/CD quality gates, and merge/release expectations for MVP-v2 delivery.

---

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

**[v2] Additional test requirements by area:**

| Area | Minimum test requirement |
|---|---|
| OPA policy client (C-1) | Integration test: real OPA container; fail-closed on timeout and 500 |
| Obligation dispatcher (C-2) | Integration test: obligation order verified; audit event fires first |
| PostgreSQL repos (ADR-0006) | Integration test: writes verified; reads consistent after restart |
| LangGraph orchestration (C-9) | End-to-end test: task progresses `queued → completed` through real graph |
| Budget reservation (C-3) | Concurrent integration test: `SELECT FOR UPDATE` prevents double-spend |
| OTel export (C-5) | Smoke test: collector receives spans/metrics; audit row also written to PostgreSQL |
| Loop controls | Integration test: cap breach produces audit event + `blocked` + owner notification |
| Alembic migrations | Forward-apply test: clean DB + `alembic upgrade head` succeeds |

Local execution:
```bash
uv run pytest tests/unit tests/component
uv run pytest tests/contract tests/integration
uv run pytest tests/conformance
# v2: run with real compose stack for integration and conformance
docker compose up -d
uv run pytest tests/integration -m "requires_compose"
uv run python ops/scripts/run_release_gate_matrix.py --scope ci
uv run python ops/scripts/run_release_gate_matrix.py --scope release-candidate --dry-run
```

**[v2] Doctor check:**
```bash
docker compose --profile doctor run oq_doctor
```

Fixture rules:
- deterministic IDs and timestamps where practical
- canonical roles, policy metadata, and task states represented in fixtures
- isolated databases/containers for infrastructure-backed tests
- **[v2]** InMemory stubs are test-only; integration tests must use real infra (OPA container, PostgreSQL, Redis)

---

## 3. CI Workflow

Recommended branch workflow:
- follow `implementation/v2/workflow/GitHubOperationsManagementGuide-v2.md` as canonical branch policy
- short-lived branches only, created from latest `main`
- PR into protected `main` using squash merge
- no direct commits to `main` for implementation code

Mandatory PR checks:
- locked dependency sync with `uv`
- lint (`ruff`)
- format check (`ruff format`)
- type check (`mypy`)
- unit tests
- component tests
- contract tests
- spec/conformance integrity checks
- **[v2]** migration forward-apply check for any PR touching Alembic migrations
- **[v2]** OPA Rego bundle lint for any PR touching `policy_runtime_integration/rego/`

Additional checks when relevant:
- integration tests for governed-path or orchestration changes
- migration validation for schema changes
- conformance smoke tests for governance-core behavior changes
- docs/spec drift checks for contract changes
- repository consistency/governance check for structure or policy/documentation refactors

---

## 4. Quality Gates

Merge blocked when:
- lint/format/type checks fail
- required tests fail
- lockfile drift is detected
- critical conformance checks fail
- migration forward-apply validation fails
- **[v2]** a new `InMemory*` class is introduced in a production code path (not under `testing/`)
- **[v2]** OPA Rego bundle fails to load against the constitution YAML files
- **[v2]** a WP task checklist item is closed without corresponding test coverage for a C-series or H-series bug fix

Release blocked when:
- critical conformance checks fail
- restore/recovery evidence is missing
- unresolved high-priority WP blockers remain
- **[v2]** any WP done-criteria are not demonstrably met in the real compose stack (not InMemory)
- non-local environments use default connector signing secret (`OPENQILIN_CONNECTOR_SHARED_SECRET=dev-openqilin-secret`)

---

## 5. Delivery Posture

v2 posture:
- CI required immediately
- CD remains manual and WP-completion-gated
- each milestone (M11–M16) requires exit criteria pass before the next milestone begins

**[v2] WP completion gate:**
- all task checkboxes in the WP document are checked
- done-criteria verified in full compose stack
- no InMemory substitute in any production code path in the completed WP
- integration tests covering the critical path added in the WP are green

Manual promotion gates (same as v1 plus):
- passing CI
- migration plan available
- config/secret readiness confirmed
- connector signing secret override confirmed
- rollback path documented
- **[v2]** `oq-doctor` passes all blocking checks on a clean stack
- **[v2]** Grafana dashboard panels confirmed populated with real data (M14+)
- release promotion checklist completed: `implementation/v2/quality/ReleasePromotionChecklist-v2.md`

---

## 6. Artifact Policy

- build definitions must be reproducible from the repo
- build metadata must include provenance references
- release artifacts must map back to code and config baseline
- **[v2]** Rego bundle version must be recorded in each release artifact index

---

## 7. Related References

- `implementation/v2/workflow/GitHubOperationsManagementGuide-v2.md`
- `implementation/v2/workflow/RepositoryConsistencyAndGovernanceCheck-v2.md`
- `implementation/v2/quality/ReleasePromotionChecklist-v2.md`
- `implementation/v2/quality/ReleaseVersioningAndRollback-v2.md`
- `design/v2/README.md`
- `implementation/v2/planning/05-milestones/MvpV2MilestonePlan-v1.md`
