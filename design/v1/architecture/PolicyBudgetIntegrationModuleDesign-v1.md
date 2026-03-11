# OpenQilin v1 - Policy and Budget Integration Module Design

## 1. Scope
- Define the implementation modules for `policy_runtime_integration` and `budget_runtime`.
- Lock the v1 hosting model: both modules run inside `orchestrator_worker`.

## 2. Package Layout
```text
src/openqilin/policy_runtime_integration/
  client.py
  normalizer.py
  obligations.py
  fail_closed.py
  models.py

src/openqilin/budget_runtime/
  client.py
  reservation_service.py
  ledger_adapter.py
  threshold_evaluator.py
  models.py
```

## 3. Hosting Model
- `policy_runtime_integration` is a reusable module imported by runtime services.
- `budget_runtime` is a reusable module imported by `orchestrator_worker`.
- Neither is a standalone v1 process.
- OPA remains a separate runtime dependency; budget logic remains an internal application module backed by PostgreSQL.

## 4. Key Interfaces
- `PolicyClient.evaluate(normalized_request)`
- `ObligationExecutor.apply(decision, task_context)`
- `FailClosedGuard.raise_or_block(error, context)`
- `BudgetReservationService.reserve(reservation_request)` (currency + quota dimensions)
- `BudgetReservationService.reconcile(reservation_id, actual_usage)` (post-execution accounting)
- `ThresholdEvaluator.evaluate(ledger_state)`
- `QuotaLimitResolver.resolve(policy_guardrail, provider_config, provider_signal)`
- `ProjectAllocationEvaluator.compute(total_budget, project_policy)` (`absolute|ratio|hybrid`)

Hybrid allocation formula:
- `effective_budget = min(max_cap, max(min_floor, share_ratio * total_available_budget))`
- Applied independently to currency and quota dimensions for each allocation window.

## 5. Failure Rules
- policy uncertainty returns deny-equivalent result
- budget uncertainty blocks costed execution
- budget reconciliation mismatch or missing usage metadata blocks governed continuation
- no automatic retries on uncertain policy or budget outcomes
- version/hash metadata must be propagated unchanged to audit and response layers
- free-tier `cost=0` flows still enforce quota thresholds
- policy guardrails override provider-reported quota limits when conflicts exist
- provider `429`/limit signals are captured for observability and future policy tuning, but do not bypass guardrails

## 6. Testing Focus
- normalized request shape stability
- fail-closed wrappers
- reservation ledger idempotency
- hard and soft breach evaluation
- dual-budget reservation/reconciliation consistency (currency + quota)
- free-tier quota enforcement with zero-currency cost
