# M12 Work Packages — Infrastructure Wiring, Security Hardening, and CSO Activation

Milestone: `M12`
Status: `in_progress`
Entry gate: M11 complete
Design ref: `design/v2/architecture/M12-InfrastructureWiringAndSecurityModuleDesign-v2.md`, `design/v2/adr/ADR-0004`, `design/v2/adr/ADR-0006`, `design/v2/components/PolicyRuntimeComponentDelta-v2.md`, `design/v2/components/ObservabilityAndDashboardDelta-v2.md`

---

## Milestone Goal

Wire all real infrastructure backends: OPA as the live policy decision point, PostgreSQL as the runtime source of truth, Redis for idempotency, and OTel for observability export. Apply all security fixes that touch identity and access. Fix the five critical runtime bugs (H-1 through H-6). Activate CSO after real policy enforcement is in place.

This milestone is the foundation that makes all subsequent milestones trustworthy.

---

## WP M12-01 — OPA Policy Runtime Wiring

**Goal:** Replace `InMemoryPolicyRuntimeClient` with a live OPA HTTP client. OPA container is already in `compose.yml` but is never contacted by the application.

**Bug ref:** C-1 | **Design ref:** `design/v2/adr/ADR-0004-OPA-HTTP-Client-Integration.md`, `design/v2/components/PolicyRuntimeComponentDelta-v2.md §1.1, §1.4`

**Entry criteria:** OPA container running and reachable; constitution YAML files exist in `constitution/core/`.

### Tasks

- [x] Implement `OPAPolicyRuntimeClient` in `src/openqilin/policy_runtime_integration/client.py` using `httpx` sync:
  - POST to `http://opa:8181/v1/data/openqilin/policy/decide`
  - 150ms timeout budget
  - Fail-closed: any error (network, timeout, non-200) returns `deny` with `POL-003`
- [x] Move `InMemoryPolicyRuntimeClient` to `src/openqilin/policy_runtime_integration/testing/in_memory_client.py` — test use only
- [x] Create `src/openqilin/policy_runtime_integration/rego/` bundle:
  - `policy.rego` — Rego package implementing all 12 rules from `constitution/core/PolicyRules.yaml`
  - `data/authority_matrix.json` — generated from `AuthorityMatrix.yaml` at build time
  - `data/obligation_policy.json` — generated from `ObligationPolicy.yaml` at build time
- [x] Update `compose.yml` OPA service to mount the Rego bundle: `command: ["run", "--server", "--bundle", "/bundle"]`; volume-mount `src/openqilin/policy_runtime_integration/rego:/bundle`
- [x] Implement `verify_opa_bundle_loaded()` in `src/openqilin/shared_kernel/startup_validation.py`; add `health_check()` and `get_active_policy_version()` to `OPAPolicyRuntimeClient`
- [x] Call startup validation in app lifespan before accepting traffic
- [x] Wire `OPAPolicyRuntimeClient` in `src/openqilin/control_plane/api/dependencies.py`

### Outputs

- `OPAPolicyRuntimeClient` as the active production policy client
- Rego bundle loaded and serving the constitution
- Startup refuses if OPA is unreachable or bundle version mismatches

### Done criteria

- [x] OPA returns a real `PolicyDecision` for a known-allow request
- [x] OPA fail-closed: OPA returns 500 → `PolicyDecision(decision="deny", rule_ids=["POL-003"])`
- [x] OPA fail-closed: timeout → same deny result
- [x] Startup validation: OPA unreachable at startup → app refuses to start with clear error
- [x] `InMemoryPolicyRuntimeClient` removed from all production code paths

---

## WP M12-02 — Obligation Application

**Goal:** Replace the empty `obligations.py` placeholder with a real `ObligationDispatcher`. `allow_with_obligations` decisions currently pass as unconditional allows.

**Bug ref:** C-2 | **Design ref:** `design/v2/components/PolicyRuntimeComponentDelta-v2.md §1.2`

**Entry criteria:** WP M12-01 complete (OPA returns real decisions including obligations).

### Tasks

- [x] Implement `ObligationDispatcher` in `src/openqilin/policy_runtime_integration/obligations.py`:
  - Deterministic order: `emit_audit_event → require_owner_approval → reserve_budget → enforce_sandbox_profile`
  - Each obligation has a dedicated handler; unsatisfied obligation returns `satisfied=False` and blocks task
- [x] Implement `emit_audit_event` handler — writes to `InMemoryAuditWriter` (upgraded to Postgres in M12-WP5); mandatory for all `allow_with_obligations` decisions
- [x] Implement `require_owner_approval` handler — transitions task to `blocked` with `approval_required` reason; blocking
- [x] Implement `reserve_budget` handler — calls `BudgetReservationService.reserve_with_fail_closed()`; M12 stub (replaced in M14-WP1)
- [x] Implement `enforce_sandbox_profile` handler — validation hook only; non-blocking in M12 (full enforcement in M13-WP6)
- [x] Wire `ObligationDispatcher` into the task orchestration path after policy decision is received

### Outputs

- `ObligationDispatcher` active on all `allow_with_obligations` decisions
- `emit_audit_event` obligation fires on every policy decision

### Done criteria

- [x] `allow_with_obligations` result now triggers obligation application (not silently allowed)
- [x] `emit_audit_event` fires before any other obligation
- [x] `require_owner_approval` transitions task to `blocked`; owner receives notification
- [x] Obligation order is deterministic and matches the documented sequence

---

## WP M12-03 — PostgreSQL Repository Migration

**Goal:** Replace all 8 `InMemory*` repositories with real PostgreSQL-backed implementations. SQLAlchemy 2.x async ORM is already in `pyproject.toml`.

**Design ref:** `design/v2/adr/ADR-0006-PostgreSQL-Repository-Migration.md`

**Entry criteria:** PostgreSQL container running; `alembic.ini` exists; SQLAlchemy session factory scaffolded.

### Tasks

- [x] Implement SQLAlchemy session factory: `build_session_factory(engine)` (sync); expose as `get_db_session()` FastAPI dependency via `sessionmaker`
- [x] Write Alembic migrations for all 6 base table groups:
  - `20260315_0002_create_tasks_table.py`
  - `20260315_0003_create_agent_registry_table.py`
  - `20260315_0004_create_audit_events_table.py`
  - `20260315_0005_create_identity_mappings_table.py`
  - `20260315_0006_create_projects_table.py`
  - `20260315_0007_create_governance_artifacts_table.py` (artifacts + messages + dead_letters)
- [x] Implement `PostgresTaskRepository` in `data_access/repositories/postgres/task_repository.py`
- [x] Implement `PostgresAgentRegistryRepository` in `data_access/repositories/postgres/agent_registry_repository.py`
- [x] Implement `PostgresAuditEventRepository` in `data_access/repositories/postgres/audit_event_repository.py`
- [x] Implement `PostgresIdentityMappingRepository` in `data_access/repositories/postgres/identity_repository.py`
- [x] Implement `PostgresProjectRepository` in `data_access/repositories/postgres/project_repository.py`
- [x] Implement `PostgresGovernanceArtifactRepository` in `data_access/repositories/postgres/governance_artifact_repository.py`
- [x] Implement `PostgresCommunicationRepository` in `data_access/repositories/postgres/communication_repository.py`
- [x] Fix H-4 (dual RuntimeServices): `get_runtime_services()` raises `RuntimeError` when not pre-initialized; no lazy init fallback
- [x] Fix H-5 (idempotency re-claim): during startup recovery, only `queued`, `dispatched`, `running`, and `blocked` tasks hold idempotency claims
- [x] Fix H-6 (`dispatched` miscounted as terminal): terminal states = `completed`, `failed`, `cancelled`, `blocked` only
- [x] Wire all Postgres repos in `dependencies.py` behind `settings.database_url`; InMemory retained for empty URL (local/test)
- [x] Add `database_url: str = ""` to `RuntimeSettings`; populated by `OPENQILIN_DATABASE_URL` env (already set in compose)

### Outputs

- All repositories backed by PostgreSQL when `OPENQILIN_DATABASE_URL` is set
- Alembic migrations runnable on a clean DB (6 migration files extending existing baseline)
- H-4, H-5, H-6 bugs fixed
- 32 new unit tests covering H-4/H-5/H-6 and all Postgres repo interfaces

### Done criteria

- [x] H-4: exactly one `RuntimeServices` instance exists per process; lazy init raises instead of creating second instance
- [x] H-5: failed/cancelled tasks do not permanently block idempotency keys during recovery
- [x] H-6: startup recovery correctly counts only terminal tasks (dispatched excluded)
- [ ] All repositories read/write to PostgreSQL in a full compose stack
- [ ] Restarting the stack does not lose task or agent registry state

---

## WP M12-04 — Redis Idempotency Wiring

**Goal:** Replace `InMemoryIdempotencyCacheStore` with `RedisIdempotencyCacheStore`. Redis container is already in `compose.yml`.

**Design ref:** `design/v2/adr/ADR-0006-PostgreSQL-Repository-Migration.md §Redis`

**Entry criteria:** Redis container running and reachable.

### Tasks

- [x] Add `redis[asyncio]>=5.0` to `pyproject.toml` if not already present
- [x] Implement `RedisIdempotencyCacheStore` in `data_access/repositories/postgres/idempotency_cache_store.py`:
  - Key format: `idempotency:{namespace}:{key}` (namespace separation addresses M-3, completed fully in M15)
  - `claim()` via `SET NX EX`
  - `release()` via `DEL`
- [x] Wire as the active idempotency store in `dependencies.py`

### Outputs

- `RedisIdempotencyCacheStore` active in production
- Idempotency state survives process restart (backed by Redis)

### Done criteria

- [x] Duplicate ingress request with same idempotency key rejected as replay
- [ ] Idempotency claim persists across process restart (verified in compose stack)

---

## WP M12-05 — OTel Export Wiring

**Goal:** Wire real OTel export from all three observability modules. OTel collector, Prometheus, Tempo, and Grafana containers exist in `compose.yml` but receive nothing from the application.

**Bug ref:** C-5 | **Design ref:** `design/v2/components/ObservabilityAndDashboardDelta-v2.md §1.1`

**Entry criteria:** OTel collector container reachable; observability modules exist in `src/openqilin/observability/`.

### Tasks

- [x] Add to `pyproject.toml`: `opentelemetry-sdk>=1.20`, `opentelemetry-exporter-otlp-proto-grpc>=1.20`, `opentelemetry-instrumentation-fastapi>=0.40`
- [x] Implement `configure_tracer(otlp_endpoint)` in `src/openqilin/observability/tracing/tracer.py` using `TracerProvider` + `BatchSpanProcessor(OTLPSpanExporter(...))`
- [x] Implement `configure_metrics(otlp_endpoint)` in `src/openqilin/observability/metrics/recorder.py` using `MeterProvider` + `PeriodicExportingMetricReader(OTLPMetricExporter(...))`
- [x] Implement `OTelAuditWriter` in `src/openqilin/observability/audit/audit_writer.py`:
  - Dual write: OTel log record (streaming) AND PostgreSQL `audit_events` row (durable)
  - PostgreSQL write failure propagates error; OTel collector failure logs locally and continues
- [x] Call `configure_tracer()` and `configure_metrics()` in app lifespan startup
- [x] Wire `OTelAuditWriter` as the active audit writer in `dependencies.py`
- [x] Add Grafana volume mounts for provisioning directory in `compose.yml`; add `datasources/postgresql.yaml`, `datasources/prometheus.yaml`, `datasources/tempo.yaml` under `ops/grafana/provisioning/datasources/`

### Outputs

- OTel traces, metrics, and audit logs exported to OTel collector
- Grafana data sources connected to Prometheus, Tempo, and PostgreSQL
- `AUD-001` compliance: immutable audit records in PostgreSQL

### Done criteria

- [x] OTel collector receives spans and metrics from the running application
- [x] Audit event creates both an OTel log record AND a PostgreSQL `audit_events` row
- [x] OTel collector unreachable → runtime continues; PostgreSQL audit row still written
- [x] PostgreSQL audit write fails → error propagated; runtime does NOT continue silently
- [ ] Grafana data sources connected and queryable (verified in compose stack)

---

## WP M12-06 — Security Hardening: Role Self-Assertion and Write Tool Access

**Goal:** Fix two security vulnerabilities that must be closed before any new agent is trusted with real authority.

**Bug refs:** C-6, C-8 | **Design ref:** `design/v2/components/ControlPlaneComponentDelta-v2.md §1.1`

**Entry criteria:** WP M12-03 complete (PostgreSQL identity mapping repository available).

### Tasks

**C-6 — Role self-assertion fix:**
- [x] In `src/openqilin/control_plane/identity/principal_resolver.py`: replace header-based role with DB lookup:
  - `resolve_principal` accepts optional `identity_repo`; when provided and `connector != "internal"`, actor must have a verified DB mapping; role from `mapping.principal_role`
  - Internal connector bypasses DB check (trusted system boundary)
- [x] Remove all code that reads `x-openqilin-actor-role` header for role assignment on the critical Discord ingress path (`owner_commands.py` now passes `identity_repo`); header used only as fallback for internal/legacy admin paths
- [x] Add `principal_role` column to `identity_channels` table (migration 20260315_0008); InMemory and Postgres repos updated with `get_by_connector_actor` lookup method
- [x] Add unit test: valid connector secret + unverified identity → PrincipalResolutionError; verified identity → correct role from DB (not from header value)

**C-8 — Write tool access check fix:**
- [x] In `src/openqilin/execution_sandbox/tools/write_tools.py` `GovernedWriteToolService`: replace `context.recipient_role` with `context.principal_role` in access check; added `principal_role` to `ToolCallContext`, `LlmDispatchRequest`, propagated from `task.principal_role`
- [x] Add unit test: requester with insufficient `principal_role` is denied; correct `principal_role` is allowed (regardless of `recipient_role`)

### Outputs

- Role no longer self-assertable via HTTP header
- Write tool access checks the actual requester role

### Done criteria

- [x] Caller with valid connector secret but unrecognized external identity → PrincipalResolutionError (principal_identity_unverified)
- [x] Caller cannot escalate role by sending `x-openqilin-actor-role: owner` in header (header ignored on external connector path with identity_repo)
- [x] Write tool access denied when `principal_role` lacks permission; allowed when it has permission

---

## WP M12-07 — Critical Runtime Bug Fixes (H-1, H-2)

**Goal:** Fix the two orchestration bugs that create silent fail-open and invalid state transitions.

**Bug refs:** H-1, H-2 (H-4, H-5, H-6 addressed in WP M12-03)

**Design ref:** `design/v2/components/OrchestratorComponentDelta-v2.md §1.2, §1.3`

**Entry criteria:** WP M12-03 complete (PostgreSQL task repository active).

### Tasks

**H-1 — Fail-open dispatch fallback:**
- [ ] In `src/openqilin/task_orchestrator/services/task_service.py`: replace silent `dispatched` assignment for unknown target with `raise DispatchTargetError(f"unknown dispatch target: {target}")` → task transitions to `failed`
- [ ] Add unit test: unknown dispatch target → task status = `failed`; no `dispatched` record

**H-2 — State transition guard:**
- [ ] Create `src/openqilin/task_orchestrator/state/transition_guard.py` with `LEGAL_TRANSITIONS` dict and `assert_legal_transition(current, next_state)` that raises `InvalidStateTransitionError` on illegal transitions
- [ ] Call `assert_legal_transition()` before every `update_task_status()` call in `runtime_state.py` and `task_service.py`
- [ ] Add unit test: `queued → dispatched` raises `InvalidStateTransitionError`; `queued → policy_evaluation` succeeds

### Outputs

- Unknown dispatch targets fail closed
- All state transitions validated against the legal transition graph

### Done criteria

- [ ] H-1: unknown dispatch target produces `failed` task status, not `dispatched`
- [ ] H-2: any illegal state transition raises `InvalidStateTransitionError`; task not updated

---

## WP M12-08 — CSO Activation

**Goal:** Activate CSO as a real advisory governance gate, gated on OPA being live and role self-assertion being fixed.

**Design ref:** `design/v2/components/ControlPlaneComponentDelta-v2.md §1.6`

**Entry criteria:** WP M12-01 (OPA live), WP M12-06 (C-6 role fix) both complete.

### Tasks

- [ ] Create `src/openqilin/agents/cso/` package: `agent.py`, `prompts.py`, `models.py`
- [ ] Implement `CSOAgent` — advisory governance gate; uses real OPA policy evaluation; present in institutional channels
- [ ] Add startup guard in `dependencies.py`:
  ```python
  if not isinstance(policy_client, OPAPolicyRuntimeClient):
      raise RuntimeError("CSO must not be activated without real OPA client")
  ```
- [ ] Wire CSO as active participant in institutional shared channels per `OwnerInteractionModel.md` MVP v2 active profile
- [ ] Add integration test: CSO governance gate rejects a request that violates a Rego rule; CSO NOT activated when `InMemoryPolicyRuntimeClient` is detected

### Outputs

- CSO active as a real governance gate
- Startup guard prevents CSO activation without real OPA client

### Done criteria

- [ ] CSO governance gate calls real OPA; denial is based on actual Rego rule evaluation
- [ ] CSO NOT activated if OPA is not wired — startup fails with clear error
- [ ] CSO activated only in correct channels; not in project channels

---

## M12 Exit Criteria

- [ ] All eight WPs above are marked done
- [ ] OPA, PostgreSQL, Redis, OTel all wired and receiving real traffic
- [ ] All C-series bugs from §5 of the milestone plan for M12 are closed
- [ ] All H-series bugs assigned to M12 are closed
- [ ] CSO active as a real governance gate
- [ ] No `InMemory*` implementation used in any production code path
- [ ] Full compose stack starts cleanly and passes startup validation

## References

- `design/v2/adr/ADR-0004-OPA-HTTP-Client-Integration.md`
- `design/v2/adr/ADR-0006-PostgreSQL-Repository-Migration.md`
- `design/v2/architecture/M12-InfrastructureWiringAndSecurityModuleDesign-v2.md`
- `design/v2/components/ControlPlaneComponentDelta-v2.md`
- `design/v2/components/PolicyRuntimeComponentDelta-v2.md`
- `design/v2/components/ObservabilityAndDashboardDelta-v2.md`
