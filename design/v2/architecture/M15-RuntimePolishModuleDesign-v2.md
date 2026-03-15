# OpenQilin v2 — M15 Module Design: Onboarding, Diagnostics, and Runtime Polish

Milestone: `M15 — Onboarding, Diagnostics, and Runtime Polish`
References: `design/v2/adr/ADR-0006-PostgreSQL-Repository-Migration.md`, `spec/architecture/ArchitectureBaseline-v1.md`

---

## 1. Scope

- Fix multiple independent `RuntimeSettings()` instantiations [M-1]: consolidate to single injected instance.
- Implement conversation history persistence [M-2]: wire `PostgresConversationStore`.
- Fix idempotency namespace separation [M-3-data]: prevent key collision between ingress and communication layers.
- Reduce setup pain: guided validation/doctor flows, startup diagnostics.
- Enforce loop controls in production paths (validate LOOP-001 through LOOP-005 specs are fully met).
- Tighten token/cost discipline: minimize unnecessary LLM calls.

Prerequisite: M11–M14 complete. All infrastructure wired, budget live, dashboard visible.

---

## 2. Package Layout

### Modified files

```text
src/openqilin/
  shared_kernel/
    settings.py                    ← fix M-1: RuntimeSettings as singleton; expose via DI only
    startup_validation.py          ← add doctor/diagnostics: check all required infra connections
    doctor.py                      ← new: operator-facing diagnostic CLI (oq-doctor)

  data_access/repositories/postgres/
    conversation_store.py          ← PostgresConversationStore (scaffold in M12; complete here)
    idempotency_cache_store.py     ← fix M-3-data: enforce namespace prefix on all key operations

  control_plane/api/
    dependencies.py                ← fix M-1: inject single RuntimeSettings instance everywhere
    lifespan.py                    ← add doctor checks to startup lifespan

  task_orchestrator/
    loop_control.py                ← verify loop controls are enforced in all LangGraph nodes

apps/
  oq_doctor.py                    ← standalone diagnostic entrypoint (docker run oq-doctor)
```

### compose.yml additions

```yaml
# Optional doctor service for operator diagnostics
oq_doctor:
  build: .
  command: ["python", "-m", "apps.oq_doctor"]
  profiles: ["doctor"]
  depends_on:
    - postgres
    - redis
    - opa
    - otel_collector
```

---

## 3. Runtime Responsibilities

### M-1 fix: `RuntimeSettings` singleton

**Problem:** At least four separate `RuntimeSettings()` instances exist within a single request lifecycle across `llm_gateway/service.py`, `task_service.py`, and `LlmGatewayDispatchAdapter`. Each instance reads from environment at construction.

**Fix:**
```python
# shared_kernel/settings.py
_settings_instance: RuntimeSettings | None = None

def get_settings() -> RuntimeSettings:
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = RuntimeSettings()
    return _settings_instance
```

All service constructors accept `settings: RuntimeSettings` as an injected parameter. `dependencies.py` wires `Annotated[RuntimeSettings, Depends(get_settings)]`. No `RuntimeSettings()` construction outside of `get_settings()`.

### M-2 fix: conversation history persistence

**Problem:** `InMemoryConversationStore` created fresh at app startup. All conversation context lost on restart even when `runtime_persistence_enabled=True`.

**Fix:** `PostgresConversationStore` (scaffolded in M12 migration, completed here):

```python
class PostgresConversationStore:
    async def get(self, conversation_id: str) -> ConversationHistory | None: ...
    async def append(self, conversation_id: str, message: Message) -> None: ...
    async def clear(self, conversation_id: str) -> None: ...
```

PostgreSQL table: `conversation_messages(id, conversation_id, role, content, created_at)`.

`InMemoryConversationStore` is moved to `testing/` and used only in tests.

### M-3-data fix: idempotency namespace separation

**Problem:** Ingress-level and communication-level idempotency stores share the same Redis key space. A task idempotency key can silently collide with a delivery idempotency key.

**Fix:** Enforce namespace prefix on all key operations in `RedisIdempotencyCacheStore`:

```python
class RedisIdempotencyCacheStore:
    def __init__(self, redis: Redis, namespace: str):
        self._namespace = namespace  # e.g. "ingress" or "communication"

    def _key(self, key: str) -> str:
        return f"idempotency:{self._namespace}:{key}"

    async def claim(self, key: str, payload_hash: str) -> ClaimResult:
        return await self._redis.set(
            self._key(key), payload_hash, nx=True, ex=self._ttl_seconds
        )
```

Two separate `RedisIdempotencyCacheStore` instances wired in `dependencies.py`:
- `ingress_idempotency_store = RedisIdempotencyCacheStore(redis, namespace="ingress")`
- `communication_idempotency_store = RedisIdempotencyCacheStore(redis, namespace="communication")`

### Doctor / diagnostics (`shared_kernel/doctor.py`, `apps/oq_doctor.py`)

Operator-facing startup diagnostic tool. Checks:
1. PostgreSQL: reachable, migrations up-to-date, all required tables exist.
2. Redis: reachable, namespace separation working.
3. OPA: reachable, constitution bundle loaded, version matches `settings.expected_constitution_version`.
4. OTel collector: reachable (non-blocking; warns but does not fail).
5. Discord: bot token valid, required channels exist.
6. Grafana: reachable (non-blocking; warns but does not fail).
7. Agent registry: institutional agents bootstrapped.

Output: structured pass/warn/fail table for operator debugging and CI smoke checks.

### Loop control production validation

- Verify all LangGraph graph nodes call `check_and_increment_hop()` before processing.
- Verify `check_and_increment_pair()` is called for all A2A delegation hops.
- Add integration test: assert hop count is reset per task trace, not shared across tasks.
- Verify `LoopCapBreachError` is handled in graph exception handler: audit event + `blocked` transition + owner notification.

### Token/cost discipline

- Audit all LLM calls for unnecessary invocations: intent classifier, secretary response, DL escalation.
- Introduce lightweight classification cache: if the same message was classified in the last 60 seconds, reuse result.
- Add metric counter: `llm_calls_total{purpose="intent_classification"}` to Prometheus to detect cost overruns.

---

## 4. Key Interfaces

```python
# shared_kernel/settings.py
def get_settings() -> RuntimeSettings: ...

# data_access/repositories/postgres/conversation_store.py
class PostgresConversationStore:
    async def get(self, conversation_id: str) -> ConversationHistory | None: ...
    async def append(self, conversation_id: str, message: Message) -> None: ...
    async def clear(self, conversation_id: str) -> None: ...

# data_access/repositories/postgres/idempotency_cache_store.py
class RedisIdempotencyCacheStore:
    def __init__(self, redis: Redis, namespace: str): ...
    async def claim(self, key: str, payload_hash: str) -> ClaimResult: ...
    async def release(self, key: str) -> None: ...

# shared_kernel/doctor.py
class SystemDoctor:
    async def run(self) -> DoctorReport: ...

@dataclass
class DoctorReport:
    checks: list[DoctorCheck]
    def all_passed(self) -> bool: ...
    def has_failures(self) -> bool: ...

@dataclass
class DoctorCheck:
    name: str
    status: Literal["pass", "warn", "fail"]
    detail: str
```

---

## 5. Dependency Rules

- `get_settings()` is the only allowed construction path for `RuntimeSettings`. Any `RuntimeSettings()` call outside of `shared_kernel/settings.py` is a bug.
- `PostgresConversationStore` depends on the same `async_sessionmaker` factory wired in M12 — no new DB connection handling.
- `RedisIdempotencyCacheStore` requires `namespace` at construction; `dependencies.py` creates two named instances and injects the correct one at each injection site.
- `SystemDoctor` depends on all infrastructure clients but has no dependency on service layer classes — it checks connectivity only.
- `oq_doctor.py` is an independent entrypoint; it must not import from `apps/orchestrator_worker.py` or `apps/control_plane_api.py`.

---

## 6. Testing Focus

| Test | Assertion |
|---|---|
| M-1: `get_settings()` called twice | Returns same object instance |
| M-1: all services receive same instance | No second `RuntimeSettings()` constructed in service layer |
| M-2: conversation persists across restart | Messages retrieved after in-memory store cleared |
| M-3: ingress vs communication key collision | Separate namespace prevents collision |
| M-3: ingress claim does not block communication claim for same raw key | Both claims succeed in respective namespaces |
| Doctor: all infra up | `DoctorReport.all_passed() == True` |
| Doctor: PostgreSQL down | Check status = `fail`; report includes actionable detail |
| Doctor: OTel collector down | Check status = `warn` (non-blocking); report continues |
| Loop controls: hop count resets per task | Separate tasks have independent `LoopState` |
| Loop controls: `LoopCapBreachError` in graph | Audit event emitted; task blocked; owner notified |
| Cost discipline: repeated intent classification | Cache hit returns reused result; no second LLM call |

---

## 7. Related References

- `design/v2/adr/ADR-0006-PostgreSQL-Repository-Migration.md`
- `design/v2/architecture/M12-InfrastructureWiringAndSecurityModuleDesign-v2.md`
- `design/v2/architecture/M13-ProjectSpaceAndOrchestrationModuleDesign-v2.md`
- `spec/orchestration/communication/AgentLoopControls.md`
- `spec/architecture/ArchitectureBaseline-v1.md`
