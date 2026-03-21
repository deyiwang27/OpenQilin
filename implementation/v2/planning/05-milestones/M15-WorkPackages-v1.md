# M15 Work Packages — Budget Persistence, Real Cost Model, and Grafana Dashboard

Milestone: `M15`
Status: `planned`
Entry gate: M14 complete (all agents active, DecisionReviewGates flow wired, PostgreSQL stable)
Design ref: `design/v2/architecture/M14-BudgetAndDashboardModuleDesign-v2.md`, `design/v2/adr/ADR-0007`, `design/v2/components/BudgetRuntimeComponentDelta-v2.md`, `design/v2/components/ObservabilityAndDashboardDelta-v2.md`

---

## Milestone Goal

Replace the in-memory integer budget counter with a real PostgreSQL-backed budget ledger with atomic reservation. Implement real token-based cost accounting from LLM response metadata. Wire budget obligation enforcement through the policy path. Build and provision the Grafana operator dashboard as the single visibility surface.

---

## WP M15-01 — PostgreSQL Budget Ledger

**Goal:** Replace `InMemoryBudgetRuntimeClient` (integer counter, character-count cost, no persistence, no atomicity) with `PostgresBudgetRuntimeClient` backed by three PostgreSQL tables.

**Bug ref:** C-3 | **Design ref:** `design/v2/components/BudgetRuntimeComponentDelta-v2.md §1.1, §1.3`

**Entry criteria:** M12 PostgreSQL session factory active; M13 LangGraph budget reservation node stub in place.

### Tasks

- [x] Write and run Alembic migrations:
  - `0008_create_budget_allocations_table.py` — `(id, project_id, currency_limit_usd, quota_limit_tokens, window_type, created_at, updated_at)`
  - `0009_create_budget_reservations_table.py` — `(id, task_id, project_id, reserved_usd, reserved_tokens, status, created_at, settled_at)`
  - `0010_create_budget_events_table.py` — `(id, task_id, project_id, role, model_class, actual_tokens, actual_cost_usd, created_at)`
- [x] Implement `src/openqilin/data_access/repositories/postgres/budget_repository.py` — `PostgresBudgetLedgerRepository`:
  - `get_allocation(project_id)`, `insert_reservation()`, `settle_reservation()`, `release_reservation()`, `insert_event()`, `get_spent(project_id, status)`
- [x] Implement `src/openqilin/budget_runtime/client.py` — `PostgresBudgetRuntimeClient`:
  - `reserve(task_id, project_id, estimate)` — atomic `SELECT ... FOR UPDATE` on allocation row; check `spent + estimate ≤ limit`; insert reservation on success; return `hard_breach` on limit exceeded
  - `settle(task_id, actual_cost)` — update reservation to `settled`; insert `budget_events` row
  - `release(task_id)` — update reservation to `released` on task cancellation
- [x] Wire `PostgresBudgetRuntimeClient` in `dependencies.py`; remove `InMemoryBudgetRuntimeClient` from production
- [x] Populate a default `budget_allocations` row on first startup for the default project (or via seeding script)

### Outputs

- Budget ledger in PostgreSQL; state survives process restart
- Atomic reservation via `SELECT ... FOR UPDATE`
- `BUD-002` (atomic reservation) met

### Done criteria

- [x] Concurrent reservation: two tasks race near budget limit; only one succeeds
- [x] Reservation persists across process restart
- [x] `hard_breach` returned when `spent + estimate > currency_limit_usd`
- [x] PostgreSQL unavailable during reservation → returns `uncertain` → task blocked

---

## WP M15-02 — Token-Based Cost Model

**Goal:** Replace character-count cost heuristic with real token usage from LLM response metadata.

**Design ref:** `design/v2/components/BudgetRuntimeComponentDelta-v2.md §1.2`

**Entry criteria:** WP M15-01 complete (budget ledger and `settle()` method available).

### Tasks

- [x] Implement `src/openqilin/budget_runtime/cost_evaluator.py` — `TokenCostEvaluator`:
  - `estimate(model_class, estimated_input_tokens)` — returns `CostEstimate(usd_estimate, quota_tokens_estimate)` using `COST_PER_1K_TOKENS` lookup; rough output multiplier 2×; **both currency and quota dimensions required** (TaskOrchestrator ORCH-002: dual-dimension budget)
  - `settle(response_metadata)` — returns `ActualCost(usd_actual, quota_tokens_actual)` using `response_metadata.total_tokens` and `response_metadata.cost_usd`
  - `COST_PER_1K_TOKENS = {"gemini_flash_free": 0.0, "gemini_flash": 0.000035, "gemini_pro": 0.00125}`
  - Free-tier models (`gemini_flash_free`): `usd_estimate=0.0` but `quota_tokens_estimate` is still non-zero and enforced (ORCH-002: free-tier is still budget-governed through quota limits)
- [x] Update `PostgresBudgetRuntimeClient.reserve()` to enforce both currency AND quota dimensions atomically: check `spent_usd + estimate_usd ≤ currency_limit_usd` AND `spent_tokens + estimate_tokens ≤ quota_limit_tokens`; return `hard_breach` if either dimension exceeded
- [x] Add `quota_spent_tokens` and `quota_limit_tokens` columns to `budget_allocations` table via Alembic migration (if not already present from M15-WP1)
- [x] Update `LlmGatewayService` to call `TokenCostEvaluator.estimate()` before dispatch and `settle()` after LLM response is received; call `budget_client.settle()` with actual cost (both dimensions)
- [x] Remove the character-count cost formula from all code paths
- [x] Add unit tests:
  - `estimate()` returns `CostEstimate` with both USD and token quota dimensions
  - `settle()` uses `response_metadata.total_tokens`, not character count
  - Free-tier model: `usd=0` but `quota_tokens > 0`; quota breach still returns `hard_breach`
  - Unknown model class uses default rate `0.001`

### Outputs

- Real token-based cost model active for all LLM calls; both currency and quota dimensions tracked
- Actual cost settled from LLM response metadata after every call
- Free-tier LLM calls quota-governed even at zero currency cost

### Done criteria

- [x] `settle()` uses `total_tokens` from LLM response, not character count
- [x] Character-count formula no longer present in any code path
- [x] Budget ledger `budget_events` rows contain real token and USD values
- [x] Free-tier dispatch with `cost_usd=0` still enforces quota limit before dispatch (ORCH-002)
- [x] `reserve()` checks both currency and quota dimensions; either breach returns `hard_breach`

---

## WP M15-03 — Budget Obligation Enforcement

**Goal:** Wire `reserve_budget` obligation through the policy path. Budget reservation must be triggered by a policy obligation, not unconditionally applied regardless of policy outcome.

**Bug ref:** C-2 budget arm | **Design ref:** `design/v2/components/PolicyRuntimeComponentDelta-v2.md §1.2`

**Entry criteria:** WP M12-02 (obligation dispatcher active), WP M15-01 (budget ledger active).

### Tasks

- [x] Replace the M12 `reserve_budget` stub handler in `ObligationDispatcher` with the real handler: calls `PostgresBudgetRuntimeClient.reserve()`; fails closed if `uncertain`
- [x] Confirm obligation order: `reserve_budget` fires only after `emit_audit_event` and `require_owner_approval`
- [x] Add integration test: task with policy decision `allow` (no `reserve_budget` obligation) → budget NOT reserved; task with obligation → budget IS reserved
- [x] Add integration test: budget `uncertain` result → task blocked; obligation chain stops

### Outputs

- Budget reservation conditioned on policy obligations (not always-applied)
- `reserve_budget` handler is the real PostgreSQL-backed implementation

### Done criteria

- [x] Budget reserved only when `reserve_budget` appears in the obligations list from OPA
- [x] Budget NOT reserved for tasks with plain `allow` decision
- [x] `uncertain` from budget → task blocked

---

## WP M15-04 — Bug Fixes: M-4 and M-5

**Goal:** Fix budget client `None` silent skip and agent registry bootstrap overwrite.

**Bug refs:** M-4, M-5 | **Design ref:** `design/v2/components/BudgetRuntimeComponentDelta-v2.md §1.4, §1.5`

**Entry criteria:** WP M15-01 complete (budget client is now always non-None in production; M-4 is defensive coding).

### Tasks

**M-4 — Budget client None fail-closed:**
- [x] In `GovernedWriteToolService` (`execution_sandbox/tools/write_tools.py`): replace silent `return None` when `budget_runtime_client is None` with `raise BudgetConfigurationError("budget_runtime_client is required for governed write tools")`
- [x] Add unit test: `budget_runtime_client=None` → `BudgetConfigurationError` raised; tool call does not proceed

**M-5 — Agent registry bootstrap idempotency:**
- [x] In `PostgresAgentRegistryRepository.bootstrap_institutional_agents()`: check `get_by_role(role)` before creating; skip if exists (do not overwrite)
- [x] Add unit test: running bootstrap twice does not duplicate or overwrite any agent record

### Outputs

- Budget check fails closed when client is missing
- Agent registry bootstrap is idempotent

### Done criteria

- [x] M-4: `budget_runtime_client=None` raises `BudgetConfigurationError`, not silent skip
- [x] M-5: running `bootstrap_institutional_agents()` twice produces exactly one record per role

---

## WP M15-05 — Grafana Dashboard Build

**Goal:** Build and provision the Grafana operator dashboard as the single visibility surface for business and ops data.

**Design ref:** `design/v2/adr/ADR-0007-Grafana-Single-Dashboard-Strategy.md`, `spec/observability/OperatorDashboardModel.md`

**Entry criteria:** M12 OTel and PostgreSQL data sources connected to Grafana; M13 project spaces active (data available for project panels); WP M15-01 budget data available.

### Tasks

- [x] Create `ops/grafana/provisioning/dashboards/dashboard.yaml` — dashboard provisioning config pointing to `ops/grafana/dashboards/`
- [x] Build `ops/grafana/dashboards/operator-main.json` with 6 required panels:
  - **Owner Inbox** — pending approvals, escalations, proposals from `tasks` and `governance_artifacts` (PostgreSQL)
  - **Projects Overview** — all projects: status, blockers, lifecycle state (PostgreSQL)
  - **Project Detail** — per-project activity, task counts, cost (PostgreSQL; project selector variable)
  - **Budget and Cost** — `budget_events` by project, by role, over time; active reservations (PostgreSQL)
  - **System and Runtime Health** — agent liveness, LLM call latency, error rates (Prometheus); span traces (Tempo)
  - **Audit and Governance Events** — `audit_events`: event_type, principal, policy_version, rule_ids (PostgreSQL)
- [x] Set dashboard refresh: 30s default; budget/audit panels configurable to 5m
- [x] Update `compose.yml` Grafana service: volume-mount `ops/grafana/provisioning` and `ops/grafana/dashboards`
- [x] Smoke test: all 6 panels return data after inserting test rows into PostgreSQL and emitting test spans

### Outputs

- `operator-main.json` — provisioned Grafana dashboard with 6 panels
- Dashboard loads automatically from provisioning config on Grafana startup

### Done criteria

- [x] All 6 panels render without errors after minimal test data insertion
- [x] Owner Inbox panel shows pending tasks from `tasks` table
- [x] Budget panel shows cost by project from `budget_events`
- [x] System Health panel shows metrics from Prometheus
- [x] Audit panel shows events from `audit_events`
- [x] Owner can identify blocked projects, pending decisions, budget risk, and system health in under 2 minutes

---

## WP M15-06 — Grafana Alerting and Discord Webhook

**Goal:** Configure Grafana alerting to route threshold alerts to Discord `#leadership_council` via webhook. Pin dashboard link in channel.

**Design ref:** `design/v2/adr/ADR-0007-Grafana-Single-Dashboard-Strategy.md §alerting`

**Entry criteria:** WP M15-05 complete (dashboard with panels); Discord webhook URL available.

### Tasks

- [x] Create `ops/grafana/provisioning/alerting/contact_points.yaml` — Discord webhook contact point; URL from `${DISCORD_ALERT_WEBHOOK_URL}` env var
- [x] Create `ops/grafana/provisioning/alerting/notification_policy.yaml` — route all threshold alerts to Discord contact point
- [x] Create `ops/grafana/provisioning/alerting/rules.yaml` — alert rules:
  - Budget hard breach: any `budget_reservations.status = 'hard_breach'` in last 5 min
  - Error rate spike: `rate(errors_total[5m]) > 0.1`
  - Agent liveness failure: no heartbeat in last 2 min
- [x] Add `DISCORD_ALERT_WEBHOOK_URL` to `.env.example`
- [x] Add dashboard link pinning: on app startup, `discord_automator.py` pins Grafana URL in `leadership_council` channel topic or pinned message; URL from `settings.grafana_public_url`
- [x] Add `GRAFANA_PUBLIC_URL` to `settings.py` and `.env.example`
- [x] Test alert routing: trigger a test alert rule; verify Discord webhook receives the message

### Outputs

- Grafana alerting configured as code in `ops/grafana/provisioning/alerting/`
- Three alert rules active: budget breach, error rate, agent liveness
- Dashboard URL pinned in `leadership_council`

### Done criteria

- [x] Budget breach alert fires and reaches `#leadership_council` Discord webhook
- [x] Grafana dashboard URL is pinned in `leadership_council` on app startup
- [x] Alert rules load from provisioning YAML (not manual Grafana UI configuration)
- [x] Alerts route to Discord only (not email or other channels)

---

## M15 Exit Criteria

- [x] All six WPs above are marked done
- [x] Budget ledger in PostgreSQL; reservation survives process restart
- [x] Token-based cost model active; character-count formula gone
- [x] Budget obligation conditioned on policy decision
- [x] M-4 and M-5 bugs closed
- [x] Grafana dashboard with 6 panels live and provisioned as code
- [x] Grafana alerting routes to Discord; dashboard URL pinned in `leadership_council`

## References

- `design/v2/adr/ADR-0007-Grafana-Single-Dashboard-Strategy.md`
- `design/v2/architecture/M14-BudgetAndDashboardModuleDesign-v2.md`
- `design/v2/components/BudgetRuntimeComponentDelta-v2.md`
- `design/v2/components/ObservabilityAndDashboardDelta-v2.md`
- `spec/constitution/BudgetEngineContract.md`
- `spec/observability/OperatorDashboardModel.md`
