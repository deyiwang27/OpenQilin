# OpenQilin v2 — M12 Module Design: Infrastructure Wiring, Security Hardening, and CSO Activation

Milestone: `M12 — Infrastructure Wiring, Security Hardening, and CSO Activation`
References: `design/v2/adr/ADR-0004-OPA-HTTP-Client-Integration.md`, `design/v2/adr/ADR-0006-PostgreSQL-Repository-Migration.md`, `design/v2/components/ControlPlaneComponentDelta-v2.md`, `design/v2/components/PolicyRuntimeComponentDelta-v2.md`, `design/v2/components/ObservabilityAndDashboardDelta-v2.md`

---

## 1. Scope

This is the foundational infrastructure milestone. All subsequent milestones build on the real backends wired here.

- Wire OPA as the real policy decision point [C-1].
- Implement obligation application [C-2].
- Wire PostgreSQL for all runtime repositories (8 InMemory → Postgres).
- Wire Redis for idempotency and retry state.
- Wire OTel export from audit writer, tracer, and metric recorder [C-5].
- Security fix [C-6]: role derived from identity mapping, not HTTP header.
- Security fix [C-8]: fix write tool access check (inverted principal/recipient).
- Fix fail-open dispatch fallback [H-1].
- Fix task status transition guard [H-2].
- Fix dual `RuntimeServices` initialization [H-4].
- Fix idempotency key re-claim [H-5].
- Fix `dispatched` miscounted as terminal [H-6].
- Connect PostgreSQL as Grafana data source.
- Activate `cso` after OPA is live and role self-assertion is fixed.

---

## 2. Package Layout

### New files

```text
src/openqilin/
  policy_runtime_integration/
    client.py                      ← OPAPolicyRuntimeClient (replace InMemory)
    obligations.py                 ← ObligationDispatcher (was empty placeholder)
    rego/
      policy.rego                  ← Rego package for 12 constitution rules
      data/
        authority_matrix.json      ← generated from AuthorityMatrix.yaml at build
        obligation_policy.json     ← generated from ObligationPolicy.yaml at build

  data_access/repositories/
    postgres/
      task_repository.py           ← PostgresTaskRepository
      agent_registry_repository.py ← PostgresAgentRegistryRepository
      audit_event_repository.py    ← PostgresAuditEventRepository
      identity_repository.py       ← PostgresIdentityMappingRepository
      project_repository.py        ← PostgresProjectRepository
      governance_artifact_repository.py
      idempotency_cache_store.py   ← RedisIdempotencyCacheStore
      conversation_store.py        ← PostgresConversationStore (scaffold; complete in M15)

  observability/
    audit/
      audit_writer.py              ← OTelAuditWriter (dual write: OTel + PostgreSQL)
    tracing/
      tracer.py                    ← configure_tracer(otlp_endpoint)
    metrics/
      recorder.py                  ← configure_metrics(otlp_endpoint)

  shared_kernel/
    startup_validation.py          ← verify_opa_bundle_loaded(), verify_db_connection()

  agents/
    cso/
      __init__.py
      agent.py                     ← CSO advisory governance gate
      prompts.py
      models.py

  execution_sandbox/tools/
    write_tools.py                 ← fix C-8: check principal_role not recipient_role

  task_orchestrator/services/
    task_service.py                ← fix H-1: fail-closed unknown dispatch target

  data_access/repositories/
    runtime_state.py               ← fix H-2: add transition guard; fix H-3 (M13); fix H-4, H-5, H-6

  control_plane/
    api/
      dependencies.py              ← fix H-4: single RuntimeServices init; wire all Postgres repos
    identity/
      principal_resolver.py        ← fix C-6: role from DB mapping, not header
```

### Alembic migrations required before activation

```text
alembic/versions/
  0001_create_tasks_table.py
  0002_create_agent_registry_table.py
  0003_create_audit_events_table.py
  0004_create_identity_mappings_table.py
  0005_create_projects_table.py
  0006_create_governance_artifacts_table.py
```

### compose.yml changes

```yaml
# Grafana datasource provisioning
ops/grafana/provisioning/datasources/postgresql.yaml    ← new
ops/grafana/provisioning/datasources/prometheus.yaml    ← new
ops/grafana/provisioning/datasources/tempo.yaml         ← new
```

---

## 3. Runtime Responsibilities

### `OPAPolicyRuntimeClient` [C-1]
- Sends `PolicyRequest` to `http://opa:8181/v1/data/openqilin/policy/decide` via httpx async.
- 150ms timeout budget.
- Fail-closed: any error (network, timeout, non-200) returns `deny` with `POL-003`.
- Startup check: `verify_opa_bundle_loaded()` must pass before accepting traffic.

### `ObligationDispatcher` [C-2]
- Applies obligations in deterministic order: `emit_audit_event → require_owner_approval → reserve_budget → enforce_sandbox_profile`.
- Each obligation has a dedicated handler; any unsatisfied obligation returns `satisfied=False` and blocks the task.
- `emit_audit_event` is mandatory for all policy decisions (fires even on deny).

### PostgreSQL repository migration [ADR-0006]
- 8 InMemory repositories replaced; see `design/v2/adr/ADR-0006-PostgreSQL-Repository-Migration.md` for full scope.
- SQLAlchemy 2.x async ORM with `async_sessionmaker(engine, expire_on_commit=False)`.
- Session injected via FastAPI dependency; no module-level connection state.

### Redis idempotency store
- `RedisIdempotencyCacheStore` with namespace prefix `idempotency:{namespace}:{key}`.
- Namespace separation between ingress-level and communication-level keys (fixes M-3-data, addressed fully in M15).

### OTel export wiring [C-5]
- `configure_tracer(otlp_endpoint)` and `configure_metrics(otlp_endpoint)` called at app startup.
- `OTelAuditWriter`: dual write — OTel log record (streaming) + PostgreSQL `audit_events` row (durable).
- PostgreSQL write failure propagates error; OTel collector failure logs locally and continues.

### Security fix [C-6]: role from identity mapping
```python
# principal_resolver.py — role from DB, not header
mapping = await self.identity_repo.get_by_external_id(channel, actor_external_id)
if mapping is None or mapping.state != "verified":
    raise AuthorizationError("unknown_or_unverified_identity")
return PrincipalContext(
    principal_id=mapping.principal_id,
    principal_role=mapping.role,  # from DB
    trust_domain=mapping.trust_domain,
)
```

### Security fix [C-8]: write tool access check
```python
# write_tools.py — check principal_role (requester), not recipient_role
if not self._access_policy.allows(context.principal_role, tool_name):
    raise AccessDeniedError(context.principal_role, tool_name)
```

### Fixes H-1, H-2, H-4, H-5, H-6
- H-1: Unknown dispatch target → `DispatchTargetError` → task `failed`.
- H-2: `transition_guard.assert_legal_transition()` called before every `update_task_status`.
- H-4: `build_runtime_services()` called once at startup; `get_runtime_services()` returns the same instance.
- H-5: During startup recovery, `failed` and `cancelled` tasks release their idempotency keys (not block).
- H-6: `dispatched` removed from terminal state set in startup recovery counting.

### CSO activation (gated on OPA + C-6 fix)
```python
# dependencies.py — startup check
if not isinstance(policy_client, OPAPolicyRuntimeClient):
    raise RuntimeError("CSO must not be activated without real OPA client")
```
CSO uses real OPA policy evaluation; advisory governance gate role in shared channels.

---

## 4. Key Interfaces

```python
# policy_runtime_integration/client.py
class OPAPolicyRuntimeClient:
    async def evaluate(self, request: PolicyRequest) -> PolicyDecision: ...
    async def health_check(self) -> OpaHealthResult: ...
    async def get_active_policy_version(self) -> str: ...

# policy_runtime_integration/obligations.py
class ObligationDispatcher:
    async def apply(
        self,
        obligations: list[str],
        context: ObligationContext,
    ) -> ObligationResult: ...

# shared_kernel/startup_validation.py
async def verify_opa_bundle_loaded(opa_client: OPAPolicyRuntimeClient) -> None: ...
async def verify_db_connection(session_factory: async_sessionmaker) -> None: ...

# observability/audit/audit_writer.py
class OTelAuditWriter:
    async def write(self, event: AuditEvent) -> None: ...  # dual write

# data_access/repositories/postgres/idempotency_cache_store.py
class RedisIdempotencyCacheStore:
    async def claim(self, namespace: str, key: str, payload_hash: str) -> ClaimResult: ...
    async def release(self, namespace: str, key: str) -> None: ...
```

---

## 5. Dependency Rules

- All new Postgres repositories depend on `data_access/` base classes — no direct SQLAlchemy in service layer.
- `OPAPolicyRuntimeClient` depends only on `httpx` (already in pyproject.toml) and `policy_runtime_integration/models.py`.
- `ObligationDispatcher` depends on: `audit_event_repository`, `budget_runtime_client`, `task_orchestrator/task_service` (for state transitions). No circular dependency: obligation dispatcher is called BY the orchestrator, not the reverse.
- OTel SDK imports (`opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-grpc`) must be added to `pyproject.toml`.
- CSO agent depends on `OPAPolicyRuntimeClient` — activation guard enforces this at startup.
- `startup_validation.py` is called from app lifespan context (`@asynccontextmanager`), not at module import time.

### pyproject.toml additions
```toml
[tool.poetry.dependencies]
opentelemetry-sdk = ">=1.20"
opentelemetry-exporter-otlp-proto-grpc = ">=1.20"
opentelemetry-instrumentation-fastapi = ">=0.40"
redis = {extras = ["asyncio"], version = ">=5.0"}
```

---

## 6. Testing Focus

| Test | Assertion |
|---|---|
| OPA fail-closed: OPA returns 500 | `PolicyDecision(decision="deny", rule_ids=["POL-003"])` |
| OPA fail-closed: network timeout | Same as above |
| OPA startup check: bundle not loaded | `RuntimeError` raised; app refuses to start |
| Obligation order: `emit_audit_event` fires before `reserve_budget` | Assert audit row inserted before budget reservation attempted |
| `require_owner_approval`: task blocked | Task transitions to `blocked`; owner notification emitted |
| C-6 fix: role from DB | Principal role matches DB mapping, not request header value |
| C-8 fix: write tool access check | Access checked against `principal_role`; wrong-role request denied |
| H-1: unknown dispatch target | Task status = `failed`; no `dispatched` record created |
| H-2: invalid state transition | `InvalidStateTransitionError` raised; task not updated |
| H-4: single RuntimeServices | One instance returned by both eager init and `get_runtime_services()` |
| H-5: idempotency re-claim after failure | Key released on `failed`; retry succeeds |
| H-6: dispatched not terminal | Startup recovery does not count `dispatched` tasks as terminal |
| OTel audit writer: dual write | OTel log record AND PostgreSQL row created for one audit event |
| OTel fail-safe: collector down | Runtime continues; PostgreSQL row still written |

---

## 7. Related References

- `design/v2/adr/ADR-0004-OPA-HTTP-Client-Integration.md`
- `design/v2/adr/ADR-0006-PostgreSQL-Repository-Migration.md`
- `design/v2/components/ControlPlaneComponentDelta-v2.md`
- `design/v2/components/PolicyRuntimeComponentDelta-v2.md`
- `design/v2/components/ObservabilityAndDashboardDelta-v2.md`
- `spec/constitution/PolicyEngineContract.md`
- `spec/cross-cutting/security/IdentityAndAccessModel.md`
- `spec/observability/AuditEvents.md`
