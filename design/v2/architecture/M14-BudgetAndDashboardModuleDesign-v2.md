# OpenQilin v2 — M14 Module Design: Budget Persistence, Real Cost Model, and Grafana Dashboard

Milestone: `M14 — Budget Persistence, Real Cost Model, and Grafana Dashboard`
References: `design/v2/adr/ADR-0007-Grafana-Single-Dashboard-Strategy.md`, `design/v2/components/BudgetRuntimeComponentDelta-v2.md`, `spec/constitution/BudgetEngineContract.md`, `spec/observability/OperatorDashboardModel.md`

---

## 1. Scope

- Wire budget runtime to PostgreSQL (replace in-memory integer counter).
- Implement real token-based cost model from LLM response metadata.
- Wire `reserve_budget` obligation through the policy path [C-2 budget arm].
- Fix budget check silently skipped when client is `None` [M-4].
- Fix agent registry bootstrap idempotency [M-5].
- Build and provision Grafana dashboard as the single operator visibility surface.
- Configure Grafana alerting to Discord webhook.
- Pin Grafana dashboard link in `leadership_council`.

Prerequisite: M12 must be complete (PostgreSQL repos, OTel wired, OPA active); M13 must be complete (project spaces, LangGraph active).

---

## 2. Package Layout

### New and modified files

```text
src/openqilin/
  budget_runtime/
    client.py                      ← PostgresBudgetRuntimeClient (replace InMemoryBudgetRuntimeClient)
    cost_evaluator.py              ← TokenCostEvaluator: estimate + settle
    models.py                      ← CostEstimate, ActualCost, ReservationResult, BudgetAllocation

  data_access/repositories/postgres/
    budget_repository.py           ← PostgresBudgetLedgerRepository (budget_allocations, budget_reservations, budget_events)

  execution_sandbox/tools/
    write_tools.py                 ← fix M-4: raise BudgetConfigurationError when client is None

  data_access/repositories/postgres/
    agent_registry_repository.py   ← fix M-5: idempotency check in bootstrap_institutional_agents()

ops/grafana/
  provisioning/
    datasources/
      postgresql.yaml              ← PostgreSQL data source (business panels)
      prometheus.yaml              ← Prometheus data source (runtime metrics)
      tempo.yaml                   ← Tempo data source (traces)
    dashboards/
      dashboard.yaml               ← dashboard provisioning config
    alerting/
      contact_points.yaml          ← Discord webhook contact point
      notification_policy.yaml     ← routing: threshold alerts → Discord
      rules.yaml                   ← alert rules: budget breach, error rate, agent liveness
  dashboards/
    operator-main.json             ← provisioned Grafana dashboard definition
```

### Alembic migrations required

```text
alembic/versions/
  0008_create_budget_allocations_table.py
  0009_create_budget_reservations_table.py
  0010_create_budget_events_table.py
```

### compose.yml changes

```yaml
grafana:
  volumes:
    - ./ops/grafana/provisioning:/etc/grafana/provisioning
    - ./ops/grafana/dashboards:/var/lib/grafana/dashboards
  environment:
    GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_ADMIN_PASSWORD:-admin}
    GF_ALERTING_ENABLED: "true"
```

---

## 3. Runtime Responsibilities

### `budget_runtime/client.py` — `PostgresBudgetRuntimeClient`

Replaces `InMemoryBudgetRuntimeClient` (integer counter, character-count cost, no persistence).

**Atomic reservation (BUD-002):**
```python
async def reserve(self, task_id: str, project_id: str, estimate: CostEstimate) -> ReservationResult:
    async with self._session.begin():
        allocation = await self._session.execute(
            select(BudgetAllocation)
            .where(BudgetAllocation.project_id == project_id)
            .with_for_update()
        )
        spent = await self._session.execute(
            select(func.sum(BudgetReservation.reserved_usd))
            .where(BudgetReservation.project_id == project_id)
            .where(BudgetReservation.status == "reserved")
        )
        if spent + estimate.estimated_usd > allocation.currency_limit_usd:
            return ReservationResult(decision="hard_breach")
        await self._session.execute(
            insert(BudgetReservation).values(task_id=task_id, ...)
        )
    return ReservationResult(decision="ok")
```

**Settle after LLM completion:**
```python
async def settle(self, task_id: str, actual_cost: ActualCost) -> None:
    # Update reservation status to 'settled'; insert budget_event row
```

### `budget_runtime/cost_evaluator.py` — `TokenCostEvaluator`

Replaces character-count heuristic with real token-based cost:
```python
COST_PER_1K_TOKENS = {
    "gemini_flash_free": 0.0,
    "gemini_flash": 0.000035,
    "gemini_pro": 0.00125,
}

def estimate(self, model_class: str, estimated_input_tokens: int) -> CostEstimate:
    rate = self.COST_PER_1K_TOKENS.get(model_class, 0.001)
    estimated_tokens = estimated_input_tokens * 2  # rough output multiplier
    return CostEstimate(
        estimated_tokens=estimated_tokens,
        estimated_usd=Decimal(str(rate * estimated_tokens / 1000)),
    )

def settle(self, response_metadata: LlmResponseMetadata) -> ActualCost:
    return ActualCost(
        actual_tokens=response_metadata.total_tokens,
        actual_usd=response_metadata.cost_usd or Decimal("0"),
    )
```

### M-4 fix: fail-closed when budget client is None

```python
# execution_sandbox/tools/write_tools.py — GovernedWriteToolService
# Before (silent skip):
if self._budget_runtime_client is None:
    return None

# After (fail-closed):
if self._budget_runtime_client is None:
    raise BudgetConfigurationError(
        "budget_runtime_client is required for governed write tools"
    )
```

### M-5 fix: agent registry bootstrap idempotency

```python
# data_access/repositories/postgres/agent_registry_repository.py
async def bootstrap_institutional_agents(self) -> None:
    for role in INSTITUTIONAL_ROLES:
        exists = await self.get_by_role(role)
        if exists is None:
            await self.create(AgentRecord(role=role, status="active", ...))
        # If exists: leave unchanged (idempotent, not overwrite)
```

### Grafana dashboard provisioning

Six required panels (per `spec/observability/OperatorDashboardModel.md`):

| Panel | Data Source | Key Queries |
|---|---|---|
| Owner Inbox | PostgreSQL | Pending approvals, escalations, proposals from `tasks`, `governance_artifacts` |
| Projects Overview | PostgreSQL | All projects: status, blockers, lifecycle state |
| Project Detail | PostgreSQL | Per-project activity, task counts, cost, health |
| Budget and Cost | PostgreSQL | `budget_events` by project, by role, over time; active reservations |
| System and Runtime Health | Prometheus / Tempo | Agent liveness, LLM latency, error rates, span traces |
| Audit and Governance Events | PostgreSQL | `audit_events` table: event_type, principal, policy_version, rule_ids |

**Grafana alerting → Discord:**
- `contact_points.yaml`: Discord webhook URL from env var `${DISCORD_ALERT_WEBHOOK_URL}`.
- `rules.yaml`: rules for budget hard breach, error rate spike, agent liveness failure.
- Alerts route to `#leadership_council` webhook; not to individual DMs.

**Dashboard link pinning:**
- At startup, `discord_automator.py` pins the Grafana dashboard URL in `leadership_council` channel topic/pinned message.
- URL sourced from `settings.grafana_public_url`.

---

## 4. Key Interfaces

```python
# budget_runtime/client.py
class PostgresBudgetRuntimeClient:
    async def reserve(self, task_id: str, project_id: str, estimate: CostEstimate) -> ReservationResult: ...
    async def settle(self, task_id: str, actual_cost: ActualCost) -> None: ...
    async def release(self, task_id: str) -> None: ...  # on task cancellation

# budget_runtime/cost_evaluator.py
class TokenCostEvaluator:
    def estimate(self, model_class: str, estimated_input_tokens: int) -> CostEstimate: ...
    def settle(self, response_metadata: LlmResponseMetadata) -> ActualCost: ...

# data_access/repositories/postgres/budget_repository.py
class PostgresBudgetLedgerRepository:
    async def get_allocation(self, project_id: str) -> BudgetAllocation | None: ...
    async def insert_reservation(self, reservation: BudgetReservation) -> None: ...
    async def settle_reservation(self, task_id: str, actual_cost: ActualCost) -> None: ...
    async def insert_event(self, event: BudgetEvent) -> None: ...
    async def get_spent(self, project_id: str, status: str = "reserved") -> Decimal: ...
```

### PostgreSQL budget tables

```sql
CREATE TABLE budget_allocations (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id),
    currency_limit_usd NUMERIC(12, 6),
    quota_limit_tokens BIGINT,
    window_type VARCHAR(20),  -- 'daily' | 'weekly' | 'per_project'
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);

CREATE TABLE budget_reservations (
    id UUID PRIMARY KEY,
    task_id UUID REFERENCES tasks(id),
    project_id UUID REFERENCES projects(id),
    reserved_usd NUMERIC(12, 6),
    reserved_tokens BIGINT,
    status VARCHAR(20),  -- 'reserved' | 'settled' | 'released'
    created_at TIMESTAMPTZ,
    settled_at TIMESTAMPTZ
);

CREATE TABLE budget_events (
    id UUID PRIMARY KEY,
    task_id UUID REFERENCES tasks(id),
    project_id UUID REFERENCES projects(id),
    role VARCHAR(50),
    model_class VARCHAR(50),
    actual_tokens BIGINT,
    actual_cost_usd NUMERIC(12, 6),
    created_at TIMESTAMPTZ
);
```

---

## 5. Dependency Rules

- `PostgresBudgetRuntimeClient` depends on `data_access/repositories/postgres/budget_repository.py` — no direct SQLAlchemy in `budget_runtime/`.
- `TokenCostEvaluator` has no external dependencies; it is a pure calculation utility.
- `budget_runtime/client.py` is injected into `ObligationDispatcher` (wired in M12) via dependency injection — no direct import of obligation logic in budget module.
- `LlmGatewayService` calls `budget_runtime_client.settle()` after every LLM response with actual token metadata.
- `ops/grafana/` is configuration-as-code only — no Python application code depends on it; it is mounted as a Docker volume.
- Dashboard link pinning uses the existing `discord_automator.py` (new in M13) — M14 adds the pinning call at startup.

---

## 6. Testing Focus

| Test | Assertion |
|---|---|
| Concurrent reservation: two tasks near limit | Only one succeeds; second returns `hard_breach` |
| Token cost model: `settle()` uses actual response tokens | `actual_tokens` from response metadata, not character count |
| Budget persistence: process restart | Reservation survives restart (read from PostgreSQL) |
| M-4 fix: `budget_runtime_client` is None | `BudgetConfigurationError` raised; not silent skip |
| M-5 fix: bootstrap twice | No duplicate agent records created |
| Hard breach: task blocked | Task status = `blocked`; owner notification emitted; budget alert fired |
| PostgreSQL unavailable during reservation | Returns `uncertain`; task blocked |
| Grafana datasource: Owner Inbox panel | Returns non-empty results after test data insertion |
| Alert routing: budget breach | Grafana alert fires; reaches Discord webhook |
| Dashboard link: startup | Grafana URL pinned in `leadership_council` channel |

---

## 7. Related References

- `design/v2/adr/ADR-0007-Grafana-Single-Dashboard-Strategy.md`
- `design/v2/components/BudgetRuntimeComponentDelta-v2.md`
- `spec/constitution/BudgetEngineContract.md`
- `spec/observability/OperatorDashboardModel.md`
- `spec/architecture/ArchitectureBaseline-v1.md`
