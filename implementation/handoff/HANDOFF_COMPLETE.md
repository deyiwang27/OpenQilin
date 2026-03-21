# Handoff Complete: M15-WP4 — Bug Fixes: M-4 and M-5

**Completed by:** CodeX (engineer)
**Date:** 2026-03-21
**Branch:** `feat/133-m15-wp4-m4-m5-bug-fixes`
**Draft PR:** #134
**Implements:** `implementation/handoff/current.md`

---

## Summary

Implemented both scoped bug fixes from the handoff. `GovernedWriteToolService` now fails closed with `BudgetConfigurationError` when no budget runtime client is configured, and `PostgresAgentRegistryRepository.bootstrap_institutional_agents()` is now strictly additive (no status overwrite of existing agents). Added a dedicated M15-WP4 unit test file and adjusted one existing security-hardening test helper to inject an allow-budget client so prior access-control assertions remain valid under the new fail-closed behavior.

---

## Completed Tasks

| Task | Status | Notes |
|---|---|---|
| Add `BudgetConfigurationError` exception class in `budget_runtime/models.py` | ✅ Done | Added module-level exception class before `DEFAULT_BUDGET_PROJECT_ID` |
| Replace silent skip in `_reserve_budget_if_configured` with hard raise | ✅ Done | Replaced `return None` for `budget_runtime_client is None` with `BudgetConfigurationError(...)` |
| Remove status-overwrite UPDATE branch from `bootstrap_institutional_agents` | ✅ Done | Deleted `elif existing.status != "active"` branch entirely |
| Add M-4 tests | ✅ Done | Added 3 tests for None-client raise, no-handler progression, and allow-client normal progression |
| Add M-5 tests | ✅ Done | Added 3 tests for idempotent second bootstrap, non-overwrite behavior, and insert-on-missing |
| Keep existing suites green | ✅ Done | Updated `tests/unit/test_m12_wp6_security_hardening.py` helper to provide allow-budget client |

---

## Validation Results

```
InMemory gate:    PASS (src scope)
BudgetConfigurationError grep: PASS
budget_runtime_client None branch grep: PASS
bootstrap UPDATE grep: PASS
ruff check:       PASS
ruff format:      PASS
mypy:             PASS
pytest unit+component: PASS (731 passed, 0 failed)
```

Commands executed:
- `grep -r --include="*.py" -l "class InMemory" src | grep -v "/testing/"`
- `grep "class BudgetConfigurationError" src/openqilin/budget_runtime/models.py`
- `grep -n "budget_runtime_client is None" src/openqilin/execution_sandbox/tools/write_tools.py`
- `grep -n "UPDATE agents SET status" src/openqilin/data_access/repositories/postgres/agent_registry_repository.py`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run python -m mypy .`
- `uv run python -m pytest tests/unit tests/component -x`

---

## REVIEW_NOTEs for Architect

| File | Line | Note |
|---|---|---|

---

## Spec Change Requests

| Conflict | Docs involved | Blocking question |
|---|---|---|

---

## What Was Skipped

- None.

---

## Notes

- The literal governance gate command from the handoff (`grep -r ... .`) includes `.venv` third-party packages in this environment and produces non-repo matches. The production-code gate was therefore run against `src/` scope to validate repository compliance.
