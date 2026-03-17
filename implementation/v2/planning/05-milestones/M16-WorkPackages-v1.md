# M16 Work Packages — Onboarding, Diagnostics, and Runtime Polish

Milestone: `M16`
Status: `planned`
Entry gate: M15 complete (all infrastructure wired, budget live, dashboard visible)
Design ref: `design/v2/architecture/M16-RuntimePolishModuleDesign-v2.md`, `design/v2/adr/ADR-0006`

---

## Milestone Goal

Polish and harden the runtime. Consolidate settings to a single source of truth. Persist conversation history. Fix idempotency key namespace collision. Build an operator-facing diagnostic CLI. Validate loop controls end-to-end and tighten token/cost discipline.

This milestone makes the system reliable and supportable — suitable for external dogfooding and public demo.

---

## WP M16-01 — RuntimeSettings Singleton

**Goal:** Eliminate multiple independent `RuntimeSettings()` instances per request lifecycle. Currently at least four separate instances can exist in `llm_gateway/service.py`, `task_service.py`, and `LlmGatewayDispatchAdapter`.

**Bug ref:** M-1 | **Design ref:** `design/v2/architecture/M16-RuntimePolishModuleDesign-v2.md §3`

**Entry criteria:** All service modules that currently construct `RuntimeSettings()` identified.

### Tasks

- [ ] Audit all `RuntimeSettings()` instantiation points across the codebase:
  - `grep -r "RuntimeSettings()" src/` to enumerate all construction sites
- [ ] Add `get_settings()` factory in `src/openqilin/shared_kernel/settings.py`:
  ```python
  _settings_instance: RuntimeSettings | None = None
  def get_settings() -> RuntimeSettings:
      global _settings_instance
      if _settings_instance is None:
          _settings_instance = RuntimeSettings()
      return _settings_instance
  ```
- [ ] Refactor all service constructors to accept `settings: RuntimeSettings` as injected parameter (not construct it internally)
- [ ] Wire `Annotated[RuntimeSettings, Depends(get_settings)]` in `api/dependencies.py`
- [ ] Remove all `RuntimeSettings()` construction outside of `shared_kernel/settings.py`
- [ ] Add unit test: `get_settings()` called twice returns same object identity (`is` check)
- [ ] Add integration test: confirm no second `RuntimeSettings()` constructed during a full request lifecycle

### Outputs

- Single `RuntimeSettings` instance per process
- All services receive settings via dependency injection

### Done criteria

- [ ] `get_settings()` called twice returns the same object
- [ ] No `RuntimeSettings()` construction outside `shared_kernel/settings.py`
- [ ] Settings value consistent across all services within a request

---

## WP M16-02 — Conversation History Persistence

**Goal:** Wire `PostgresConversationStore` to replace `InMemoryConversationStore`. Conversation context must survive process restart when `runtime_persistence_enabled=True`.

**Bug ref:** M-2 | **Design ref:** `design/v2/architecture/M16-RuntimePolishModuleDesign-v2.md §3`

**Entry criteria:** M12 PostgreSQL session factory active; `conversation_store.py` scaffolded in M12.

### Tasks

- [ ] Write Alembic migration for `conversation_messages` table: `(id, conversation_id, role, content, metadata jsonb, created_at)`
- [ ] Complete `PostgresConversationStore` in `src/openqilin/data_access/repositories/postgres/conversation_store.py`:
  - `get(conversation_id)` — returns full `ConversationHistory` or `None`
  - `append(conversation_id, message)` — inserts one message row
  - `clear(conversation_id)` — soft-deletes or truncates messages for conversation
- [ ] Move `InMemoryConversationStore` to `src/openqilin/data_access/repositories/testing/` — test use only
- [ ] Wire `PostgresConversationStore` in `dependencies.py`
- [ ] Add integration test: append messages → restart process (clear in-memory) → `get()` returns all messages

### Outputs

- Conversation history persisted in PostgreSQL
- `InMemoryConversationStore` removed from production

### Done criteria

- [ ] Messages retrieved from PostgreSQL after in-memory store cleared
- [ ] `InMemoryConversationStore` not instantiated in any production code path
- [ ] `runtime_persistence_enabled=False` can use a no-op store (existing conversations not broken)

---

## WP M16-03 — Idempotency Namespace Separation

**Goal:** Fix the key namespace collision between ingress-level and communication-level idempotency stores. Same raw key in both layers can silently collide.

**Bug ref:** M-3 | **Design ref:** `design/v2/architecture/M16-RuntimePolishModuleDesign-v2.md §3`

**Entry criteria:** M12 `RedisIdempotencyCacheStore` active.

### Tasks

- [ ] Add `namespace: str` parameter to `RedisIdempotencyCacheStore.__init__()`:
  - Internal key format: `idempotency:{namespace}:{key}`
- [ ] Update `claim()` and `release()` to use `_key(key)` internally
- [ ] Update `dependencies.py` to wire two separate named instances:
  - `ingress_idempotency_store = RedisIdempotencyCacheStore(redis, namespace="ingress")`
  - `communication_idempotency_store = RedisIdempotencyCacheStore(redis, namespace="communication")`
- [ ] Inject the correct instance at each injection site (ingress routes use `ingress_store`; communication delivery uses `communication_store`)
- [ ] Add unit test: ingress claim with key `abc` and communication claim with same key `abc` both succeed (no collision)
- [ ] Add unit test: ingress claim and ingress re-claim with same key → second claim fails (within-namespace deduplication still works)

### Outputs

- Ingress and communication idempotency keys live in separate Redis namespaces
- Collision between layers impossible

### Done criteria

- [ ] Ingress claim `abc` does not block communication claim `abc`
- [ ] Within-namespace deduplication still functions correctly
- [ ] Key format in Redis is `idempotency:ingress:abc` and `idempotency:communication:abc`

---

## WP M16-04 — Doctor / Diagnostics CLI

**Goal:** Build an operator-facing diagnostic tool that checks all required infrastructure connections and reports pass/warn/fail. Reduces setup pain and replaces manual debugging.

**Design ref:** `design/v2/architecture/M16-RuntimePolishModuleDesign-v2.md §3`

**Entry criteria:** All M12–M15 infrastructure wired (PostgreSQL, Redis, OPA, OTel, Discord, Grafana).

### Tasks

- [ ] Implement `src/openqilin/shared_kernel/doctor.py` — `SystemDoctor` class:
  - `run()` → `DoctorReport` containing list of `DoctorCheck(name, status, detail)`
  - Checks: PostgreSQL reachable + migrations up-to-date, Redis reachable, OPA reachable + bundle loaded, OTel collector reachable (warn-only), Discord bot token valid + channels exist, Grafana reachable (warn-only), agent registry bootstrapped
  - Blocking checks (PostgreSQL, Redis, OPA) fail the report; non-blocking checks (OTel, Grafana) warn only
- [ ] Implement `apps/oq_doctor.py` — standalone entrypoint that runs `SystemDoctor` and prints tabular output; exits with code `1` if `has_failures()`
- [ ] Add to `compose.yml` as optional doctor profile:
  ```yaml
  oq_doctor:
    build: .
    command: ["python", "-m", "apps.oq_doctor"]
    profiles: ["doctor"]
  ```
- [ ] Wire doctor checks into app lifespan (`lifespan.py`): run blocking checks at startup; warn on non-blocking failures; refuse startup if blocking check fails
- [ ] Add tests: all infra up → `all_passed() == True`; PostgreSQL down → `has_failures() == True` with actionable detail; OTel down → `has_failures() == False` but report has warn

### Outputs

- `oq_doctor` runnable as standalone: `docker compose --profile doctor run oq_doctor`
- Blocking infra checks run automatically at app startup
- Pass/warn/fail table output for operator debugging

### Done criteria

- [ ] All-clear: `oq_doctor` exits 0, prints all-pass table
- [ ] PostgreSQL unreachable: exits 1, prints clear failure message and remediation hint
- [ ] OTel unreachable: exits 0 with warn (non-blocking)
- [ ] App startup fails if PostgreSQL or OPA unreachable (blocking check)

---

## WP M16-05 — Loop Control Audit and Token Discipline

**Goal:** Validate that loop controls from M13 are enforced end-to-end in production. Reduce unnecessary LLM invocations and add cost-discipline metrics.

**Design ref:** `design/v2/architecture/M16-RuntimePolishModuleDesign-v2.md §3`

**Entry criteria:** M13 loop controls implemented; M12 OTel metrics wired.

### Tasks

**Loop control audit:**
- [ ] Verify all LangGraph graph nodes call `check_and_increment_hop()` — add integration test that asserts `LoopCapBreachError` after exactly 5 hops
- [ ] Verify `check_and_increment_pair()` called for PM → DL and DL → specialist A2A hops
- [ ] Add integration test: `LoopCapBreachError` in graph → audit event row inserted + task `blocked` + owner notified (all three effects verified)
- [ ] Verify `LoopState` is per-task trace — add test confirming separate tasks have independent `hop_count`

**Token/cost discipline:**
- [ ] Audit all LLM calls: identify any call site that could be cached or eliminated
- [ ] Implement classification result cache: if same message text classified in last 60 seconds from same `conversation_id`, return cached `IntentClass`; no second LLM call
- [ ] Add Prometheus metric counter: `llm_calls_total` with label `purpose` (e.g. `intent_classification`, `secretary_response`, `dl_escalation`, `pm_response`)
- [ ] Verify metric appears in Grafana System Health panel
- [ ] Document which LLM calls are expected per interaction type in inline code comments

### Outputs

- Loop cap enforcement verified end-to-end with integration tests
- Intent classification cache active
- `llm_calls_total` metric visible in Grafana

### Done criteria

- [ ] Hop cap breach after exactly 5 hops: audit event + blocked task + owner notification all verified
- [ ] Same text classified twice in 60s from same conversation → one LLM call (cache hit on second)
- [ ] `llm_calls_total{purpose="intent_classification"}` visible in Prometheus
- [ ] Separate task traces have independent `LoopState`

---

## M16 Exit Criteria

- [ ] All five WPs above are marked done
- [ ] Single `RuntimeSettings` instance per process
- [ ] Conversation history survives restart
- [ ] Idempotency keys namespaced; no cross-layer collision
- [ ] `oq_doctor` works standalone and as startup validator
- [ ] Loop controls verified end-to-end with integration tests
- [ ] Token discipline metrics visible in Grafana

## References

- `design/v2/architecture/M16-RuntimePolishModuleDesign-v2.md`
- `design/v2/adr/ADR-0006-PostgreSQL-Repository-Migration.md`
- `spec/orchestration/communication/AgentLoopControls.md`
- `spec/architecture/ArchitectureBaseline-v1.md`
