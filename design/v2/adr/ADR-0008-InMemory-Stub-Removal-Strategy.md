# ADR-0008: InMemory Stub Removal and Test Infrastructure Hardening

## Status
Accepted (2026-03-17)

## Context

- `CLAUDE.md` governance constraint (CI and merge gate): _"No `InMemory*` in production: `InMemory*` stubs are test-only. Production code paths must use real clients (PostgreSQL, Redis, OPA)."_
- Enforcement grep: `grep -r --include="*.py" -l "class InMemory" src/ | grep -v "/testing/" | grep -v "tests/"` — must return zero results.
- As of M13-WP1, the gate returns **26 matching files** in production `src/`.
- M12 wired real PostgreSQL repositories and Redis idempotency (ADR-0006). The `InMemory*` classes in `data_access/` and `cache/` were not deleted at that time; `dependencies.py` kept them as fallbacks when `DATABASE_URL` / `REDIS_URL` / `OPA_URL` are absent.
- Result: `create_control_plane_app()` silently starts in InMemory mode in any environment where env vars are not set, including CI. Unit and component tests pass against Python-dict stores rather than real infrastructure — masking real behaviour.
- Governance check run after M13-WP1 close surfaced this as a `pass_with_followups` finding. User decision (2026-03-17): remove the stubs, test against real infrastructure.

### Why InMemory tests give false confidence

OpenQilin enforces policy decisions, records immutable audit trails, coordinates idempotency across restarts, and gates task dispatch behind OPA. Python-dict stubs cannot model:
- Postgres ACID guarantees (concurrent writes, row locking for budget)
- Redis TTL semantics and key expiry for idempotency
- OPA bundle evaluation for real policy rules
- Cross-restart state recovery (InMemory always starts empty)

A test suite that passes against InMemory but not against real infra delivers false assurance for a correctness-critical system.

---

## Decision

### Three-group removal strategy

The 26 InMemory classes fall into three groups with different treatment:

#### Group 1 — Infrastructure stubs (real counterpart exists today): DELETE

These classes substitute for Postgres, Redis, or OPA. The real implementations exist and were wired in M12. The InMemory fallback in `dependencies.py` must be replaced with a startup guard that raises `RuntimeError` when the env var is absent.

| Class | File | Replace with |
|---|---|---|
| `InMemoryRuntimeStateRepository` | `data_access/repositories/runtime_state.py` | `PostgresTaskRepository` |
| `InMemoryCommunicationRepository` | `data_access/repositories/communication.py` | `PostgresCommunicationRepository` |
| `InMemoryAgentRegistryRepository` | `data_access/repositories/agent_registry.py` | `PostgresAgentRegistryRepository` |
| `InMemoryProjectArtifactRepository` | `data_access/repositories/artifacts.py` | `PostgresProjectArtifactRepository` |
| `InMemoryGovernanceRepository` | `data_access/repositories/governance.py` | `PostgresGovernanceRepository` |
| `InMemoryIdentityChannelRepository` | `data_access/repositories/identity_channels.py` | `PostgresIdentityChannelRepository` |
| `InMemoryIdempotencyCacheStore` | `data_access/cache/idempotency_store.py` | `RedisIdempotencyCacheStore` |
| `InMemoryArtifactSearchReadModel` | `data_access/read_models/artifact_search.py` | `PostgresArtifactSearchReadModel` |

Startup guard pattern in `dependencies.py`:
```python
if not settings.database_url:
    raise RuntimeError(
        "OPENQILIN_DATABASE_URL is required. "
        "Run: docker compose --profile core up -d"
    )
```

Same pattern for `redis_url` and `opa_url`.

#### Group 2 — Simulation stubs (no real transport counterpart yet): RENAME

These classes substitute for Discord/ACP transport, an LLM provider, a budget service, and a process-scoped deduplication store. No real external service is available for these in CI. The `InMemory` prefix is misleading (they are not "in-memory versions of a real service" — they are the only implementation for that interface in the test pipeline). **Rename** to remove the `InMemory` prefix and make the in-process nature explicit.

| Current class | New name | Location |
|---|---|---|
| `InMemoryDeliveryPublisher` | `LocalDeliveryPublisher` | `communication_gateway/delivery/publisher.py` |
| `InMemoryDeadLetterWriter` | `LocalDeadLetterWriter` | `communication_gateway/delivery/dlq_writer.py` |
| `InMemoryMessageLedger` | `LocalMessageLedger` | `communication_gateway/storage/message_ledger.py` |
| `InMemoryCommunicationIdempotencyStore` | `LocalCommunicationIdempotencyStore` | `communication_gateway/storage/idempotency_store.py` |
| `InMemoryAcpClient` | `LocalAcpClient` | `communication_gateway/transport/acp_client.py` |
| `InMemoryOrderingValidator` | `LocalOrderingValidator` | `communication_gateway/validators/ordering_validator.py` |
| `InMemoryCommunicationDispatchAdapter` | `LocalCommunicationDispatchAdapter` | `task_orchestrator/dispatch/communication_dispatch.py` |
| `InMemorySandboxExecutionAdapter` | `LocalSandboxExecutionAdapter` | `task_orchestrator/dispatch/sandbox_dispatch.py` |
| `InMemoryConversationStore` | `LocalConversationStore` | `task_orchestrator/dispatch/llm_dispatch.py` |
| `InMemoryLiteLLMAdapter` | `LocalLiteLLMAdapter` | `llm_gateway/providers/litellm_adapter.py` |
| `InMemoryBudgetRuntimeClient` | `AlwaysAllowBudgetRuntimeClient` | `budget_runtime/client.py` |
| `InMemoryIngressDedupe` | `IngressDedupeStore` | `control_plane/idempotency/ingress_dedupe.py` |
| `InMemorySandboxEventCallbackProcessor` | `LocalSandboxEventCallbackProcessor` | `task_orchestrator/callbacks/sandbox_events.py` |
| `InMemoryDeliveryEventCallbackProcessor` | `LocalDeliveryEventCallbackProcessor` | `task_orchestrator/callbacks/delivery_events.py` |

`AlwaysAllowBudgetRuntimeClient` explicitly signals its semantics: it always approves budget reservation. It will be replaced by a real budget service in M14.

`IngressDedupeStore` is intentionally process-scoped (resets on restart); no external persistence is required by spec.

#### Group 3 — Observability introspection stubs: MOVE to `testing/`

These stubs provide `.get_events()`, `.get_spans()`, `.get_counter_value()` methods used by component and integration tests to assert on emitted telemetry. They cannot be deleted because the production `OTelAuditWriter` and OTel tracer do not expose in-process query methods. They must not exist in production module files.

**Move to `src/openqilin/observability/testing/stubs.py`** (file already partially exists). Inject into the test app via a conftest fixture after `create_control_plane_app()` returns.

| Class | Destination |
|---|---|
| `InMemoryAuditWriter` | `observability/testing/stubs.py` |
| `InMemoryTracer` + `InMemorySpan` | `observability/testing/stubs.py` |
| `InMemoryMetricRecorder` | `observability/testing/stubs.py` |
| `InMemoryAlertEmitter` | `observability/testing/stubs.py` |

Conftest injection pattern (`tests/component/conftest.py`, `tests/integration/conftest.py`):
```python
@pytest.fixture(autouse=True)
def inject_test_observability(app):
    from openqilin.observability.testing.stubs import (
        InMemoryAuditWriter, InMemoryTracer, InMemoryMetricRecorder
    )
    app.state.runtime_services.audit_writer = InMemoryAuditWriter()
    app.state.runtime_services.tracer = InMemoryTracer()
    app.state.runtime_services.metric_recorder = InMemoryMetricRecorder()
```

---

### Test infrastructure changes

#### Compose required for all non-pure-logic tests

After Group 1 deletion, `create_control_plane_app()` raises `RuntimeError` without env vars. Every test that calls it requires the compose stack.

Compose services needed: `postgres:5432`, `redis:6379`, `opa:8181`.

#### `@pytest.mark.no_infra` for pure-logic unit tests

Pure-logic unit tests (grammar parsers, routing tables, state machine guards, schema validators) have no I/O and need no compose. Mark them `@pytest.mark.no_infra` so CI can run them without the stack:

```bash
# Fast gate — no compose required
uv run pytest -m no_infra tests/unit/

# Full gate — compose required
docker compose --profile core up -d
uv run pytest tests/unit tests/component tests/contract tests/integration tests/conformance
```

#### Database cleanup between tests

Add a session-scoped `autouse` fixture in `tests/component/conftest.py` and `tests/integration/conftest.py` that truncates test-relevant tables between test functions to prevent cross-test state leakage.

#### Tests that tested the InMemory fallback path: delete or rewrite

Three unit tests explicitly assert "when env var is empty → InMemory class is selected":
- `test_build_runtime_services_uses_inmemory_when_no_redis_url`
- `test_build_runtime_services_uses_inmemory_when_no_database_url`
- `test_build_runtime_services_uses_inmemory_when_no_opa_url`

These tests must be rewritten to assert that `RuntimeError` is raised when the env var is absent (the new correct behaviour).

---

## Consequences

**Positive:**
- CI merge gate passes. `grep` check returns zero results.
- Test suite validates real Postgres, Redis, and OPA behaviour.
- False-assurance test results eliminated.
- Production `build_runtime_services()` fails fast on misconfiguration instead of silently degrading.
- `RuntimeServices` union types narrow to concrete types only.

**Tradeoffs:**
- Compose stack required for component/integration tests. Local development requires `docker compose --profile core up -d` before running tests.
- Pure-logic unit tests still run fast without infra (`@pytest.mark.no_infra`).
- Observability introspection stubs remain in `testing/` — tests that call `.get_events()` still use in-process stubs injected via conftest. Full OTel query support (reading from Postgres) is deferred to M14+ observability milestone.
- `AlwaysAllowBudgetRuntimeClient` and `Local*` simulation stubs remain in production files until their respective real service implementations are wired (M14 for budget; Discord transport already exists as an external service but is not injectable in CI).

## Alternatives Considered

1. **Move all InMemory classes to `testing/` subpackages and keep them importable from production code.**
   - Rejected: production code importing from `testing/` subpackages is an architectural smell and does not enforce the spirit of the governance constraint, only its letter.

2. **Add `@pytest.mark.infra` to integration tests only; keep InMemory for unit/component.**
   - Rejected: component tests are really integration tests. Calling them "component" while using dict-backed stores gives false confidence at the most-run test tier.

3. **Keep InMemory fallbacks, document them as "dev mode" intentional behaviour.**
   - Rejected: the spec and governance constraints are explicit. The system must fail closed when real infrastructure is absent, not silently degrade.

## Related References

- `CLAUDE.md` — governance constraint and CI grep gate
- `design/v2/adr/ADR-0006-PostgreSQL-Repository-Migration.md` — established real Postgres repos in M12
- `implementation/v2/planning/05-milestones/M13-WorkPackages-v1.md` — WP M13-09 implements this ADR
- `implementation/v2/planning/ImplementationProgress-v2.md` — tracking
