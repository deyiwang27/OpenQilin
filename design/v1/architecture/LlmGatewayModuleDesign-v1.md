# OpenQilin v1 - LLM Gateway Module Design

## 1. Scope
- Translate the LLM gateway component design into implementation modules under `src/openqilin/llm_gateway/`.

## 2. Package Layout
```text
src/openqilin/llm_gateway/
  routing/
    profile_resolver.py
    model_selector.py
  providers/
    base.py
    litellm_adapter.py
  policy/
    request_guard.py
  accounting/
    usage_recorder.py
    cost_estimator.py
    quota_source_resolver.py
    allocation_context_normalizer.py
  schemas/
    requests.py
    responses.py
```

## 3. Key Interfaces
- `ProfileResolver.resolve(routing_profile, model_class)`
- `ModelSelector.select(route_plan)`
- `LiteLLMAdapter.complete(request)`
- `RequestGuard.validate(governed_request)`
- `UsageRecorder.record(response_metadata)`
- `CostEstimator.estimate(request, usage)` with explicit `cost_source`
- `BudgetUsageNormalizer.normalize(usage, cost)` for currency + quota attribution
- `QuotaSourceResolver.resolve(policy_guardrail, provider_config, provider_signal)`
- `AllocationContextNormalizer.normalize(project_allocation_context)`

## 4. Routing Rules
- local and CI default to `dev_gemini_free`
- routing resolution is deterministic for the same profile and model class
- fallback count is profile bounded
- unresolved alias or inactive profile denies fail-closed

## 5. Hosting Model
- `llm_gateway` is an internal module used by runtime services
- external provider interaction is mediated through the `litellm` container/service
- no direct provider SDK use in feature modules

## 6. Testing Focus
- profile resolution
- Gemini free-tier default wiring
- fallback behavior
- usage and cost metadata persistence
- free-tier path enforcement where `cost=0` but quota usage is non-zero
- reservation/reconciliation compatibility with budget runtime dual-budget model
- hybrid allocation (`ratio + floor/cap`) context propagation to budget reservation/reconciliation
