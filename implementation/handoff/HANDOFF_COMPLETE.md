# Handoff Complete: M15-WP2 — Token-Based Cost Model

**Completed by:** CodeX (engineer)
**Date:** 2026-03-19
**Branch:** `feat/127-m15-wp2-token-cost-model`
**Draft PR:** _Not opened in this run_
**Implements:** `implementation/handoff/current.md`

---

## Summary

Implemented the WP2 token-based budget cost model with a new `TokenCostEvaluator`, removed the character-count estimator, and rewired PostgreSQL budget settlement to resolve active reservations by `task_id`. Integrated settlement into `LlmGatewayDispatchAdapter` for served LLM responses and updated DI wiring plus protocol/repository contracts accordingly. Added the requested WP2 unit coverage and updated existing tests for the new budget client signatures.

---

## Completed Tasks

| Task | Status | Notes |
|---|---|---|
| Add `src/openqilin/budget_runtime/cost_evaluator.py` | ✅ Done | Added constants, routing-tier mapping, `CostEstimate`, `ActualCost`, `TokenCostEvaluator.estimate()`, `TokenCostEvaluator.settle()` |
| Update `BudgetReservationInput` and budget protocol signatures | ✅ Done | Added `model_class` default; changed `settle()`/`release()` to task-id based protocol with actual token/USD fields |
| Update `PostgresBudgetRuntimeClient` | ✅ Done | Added evaluator dependency, removed `_COST_UNIT_TO_USD`, switched reserve computation to evaluator, task-id-based `settle()`/`release()`, and event insertion on settle |
| Update `PostgresBudgetLedgerRepository` | ✅ Done | Added `find_active_reservation_id(task_id)`, removed unused `actual_units` from `settle_reservation()` |
| Update `BudgetReservationService` | ✅ Done | Removed `estimate_cost_units`; now uses fixed token estimate constant and `model_class="interactive_fast"` |
| Wire settle in LLM dispatch adapter | ✅ Done | Added optional `budget_client` dependency and `settle()` call for served/fallback-served LLM responses |
| Update task-service and dependency wiring | ✅ Done | Passed `budget_client` into `LlmGatewayDispatchAdapter`; injected `TokenCostEvaluator()` into `PostgresBudgetRuntimeClient` construction |
| Remove legacy estimator module | ✅ Done | Deleted `src/openqilin/budget_runtime/threshold_evaluator.py` |
| Add WP2 evaluator unit tests | ✅ Done | Added `tests/unit/budget_runtime/test_m15_wp2_token_cost_evaluator.py` with all requested scenarios |
| Add WP2 postgres settle unit tests | ✅ Done | Added `tests/unit/budget_runtime/test_m15_wp2_postgres_budget_settle.py` with all requested scenarios |
| Update existing tests for new signatures/removals | ✅ Done | Updated `tests/unit/test_m1_wp4_budget_runtime.py` and `tests/unit/test_m15_wp1_postgres_budget_ledger.py` |

---

## Validation Results

```
InMemory gate:    PASS
estimate_cost_units grep: PASS
_COST_UNIT_TO_USD grep: PASS
threshold_evaluator deleted: PASS
ruff check:       PASS
ruff format:      PASS
mypy:             PASS
pytest unit+component: PASS (717 passed, 0 failed)
```

Commands executed:
- `grep -r --exclude-dir=.venv --include="*.py" -l "class InMemory" . | grep -v "/testing/" | grep -v "tests/"`
- `grep -r --exclude-dir=.venv --include="*.py" "estimate_cost_units" .`
- `grep -r --exclude-dir=.venv --include="*.py" "_COST_UNIT_TO_USD" .`
- `test ! -f src/openqilin/budget_runtime/threshold_evaluator.py && echo "PASS"`
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

- Draft PR creation/push workflow was not executed in this run.

---

## Notes

- In this environment, `uv run mypy .` and `uv run pytest ...` executable shims were unavailable; equivalent validated commands were run via `uv run python -m mypy .` and `uv run python -m pytest ...`.
