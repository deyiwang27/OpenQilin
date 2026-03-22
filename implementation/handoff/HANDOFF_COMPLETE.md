# Handoff Complete: M16-WP3 — Idempotency Namespace Separation

**Completed by:** CodeX (engineer)
**Date:** 2026-03-22
**Branch:** `feat/147-m16-wp3-idempotency-namespace`
**Draft PR:** N/A (not opened in this environment)
**Implements:** `implementation/handoff/current.md`

---

## Summary

Implemented constructor-bound namespace enforcement for `RedisIdempotencyCacheStore` and removed per-call namespace arguments from its API. Runtime wiring now constructs two Redis-backed store instances (`ingress`, `communication`) from a shared Redis client and exposes both on `RuntimeServices`. Updated affected unit/component tests and added new M16-WP3 tests verifying namespaced key generation, cross-namespace isolation, within-namespace deduplication, and namespace-bound store attributes.

---

## Completed Tasks

| Task | Status | Notes |
|---|---|---|
| Add `namespace: str` to `RedisIdempotencyCacheStore.__init__` and bind keying to instance | ✅ Done | Added `namespace` constructor arg, persisted `self._namespace`, added `_key()`, removed per-call `namespace` from `claim`, `increment_attempt`, `complete`, `get`, `list_namespace`. |
| Keep module `_redis_key(namespace, key)` unchanged | ✅ Done | Function signature/body retained exactly; class now uses it via `self._key(key)`. |
| Wire two namespaced Redis stores in `build_runtime_services()` | ✅ Done | Added shared `redis_client`, `ingress_idempotency_store(namespace="ingress")`, `communication_idempotency_store(namespace="communication")`; updated `RuntimeServices` fields. |
| Remove unused `idempotency_cache_store` path from dispatch-service builder | ✅ Done | Removed dead parameter/import from `build_task_dispatch_service()` and removed call-site argument in `dependencies.py`. |
| Update existing Redis idempotency tests for new API shape | ✅ Done | `tests/unit/test_m12_wp4_redis_idempotency.py` updated to constructor namespace + namespace-free method calls; RuntimeServices type check updated for renamed/new fields. |
| Add M16-WP3 namespace tests | ✅ Done | Added `tests/unit/test_m16_wp3_idempotency_namespace.py` with all four required tests. |

---

## Validation Results

```
InMemory gate:   PASS (project files; command requires excluding .venv site-packages locally)
ruff check:      PASS
ruff format:     PASS
mypy:            PASS
pytest unit:     PASS
pytest component: PASS
```

Executed commands:
- `grep -r --include="*.py" -l "class InMemory" . | grep -v "/testing/" | grep -v "tests/" | grep -v "/.venv/"`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run python -m mypy .`
- `uv run python -m pytest tests/unit tests/component -x --tb=short -q` → `753 passed, 0 failed`

---

## REVIEW_NOTEs for Architect

| File | Line | Note |
|---|---|---|
| _None_ | - | No REVIEW_NOTEs added. |

---

## Spec Change Requests

| Conflict | Docs involved | Blocking question |
|---|---|---|
| Communication publisher idempotency store interface is not compatible with `RedisIdempotencyCacheStore` (`LocalCommunicationIdempotencyStore` has different methods/record type). WP3 requires namespaced Redis wiring but publisher migration is deferred. | `implementation/handoff/current.md` (Spec Gaps — Gap 1), `src/openqilin/communication_gateway/delivery/publisher.py`, `src/openqilin/communication_gateway/storage/idempotency_store.py` | Should a protocol adapter or a dedicated Redis-backed communication idempotency store interface be introduced in a follow-up WP before wiring `communication_idempotency_store` into publisher? |

---

## What Was Skipped

- Draft PR creation was not performed in this environment.

---

## Notes

- `uv run mypy .` and `uv run pytest ...` failed to spawn binaries in this local environment (`No such file or directory`), so equivalent module invocations were used (`uv run python -m mypy ...` and `uv run python -m pytest ...`).
- No changes were made to `communication_gateway/delivery/publisher.py` or `communication_gateway/storage/idempotency_store.py` (out of scope per handoff).
