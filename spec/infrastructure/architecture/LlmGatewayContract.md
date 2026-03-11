# OpenQilin - LLM Gateway Contract Specification

## 1. Scope
- Defines the authoritative LLM gateway contract for model access.
- Defines routing, fallback, budget attribution, and observability requirements.

## 2. Gateway Role
- All model calls are routed through the gateway.
- Direct provider calls from orchestrator/agents are not allowed in governed runtime paths.
- Gateway must propagate policy and trace context end-to-end.

## 3. Request Contract
Minimum request fields:
- `request_id`
- `trace_id`
- `project_id`
- `agent_id`
- `skill_id` (if skill-governed flow)
- `model_class`
- `routing_profile`
- `messages_or_prompt`
- `max_tokens`
- `temperature`
- `budget_context`:
  - currency + quota dimensions
  - reservation reference when present
  - allocation metadata (`allocation_mode`, `project_share_ratio`, `effective_budget_window`)
- `policy_context` (`policy_version`, `policy_hash`, `rule_ids`)

## 4. Routing and Fallback
- Model selection uses policy-approved model classes.
- Model-class to provider/model resolution MUST use an active routing profile.
- Routing profile authority: `spec/infrastructure/architecture/LlmModelRoutingProfile-v1.md`.
- v1 local/CI default profile: `dev_gemini_free` (free-tier Gemini path for initial testing).
- Fallback is bounded and explicit per routing profile.
- Retries and fallback decisions must emit decision metadata.

## 5. Budget and Cost Semantics
- Every request carries attribution dimensions (`project_id`, `agent_id`, `task_id` optional).
- Soft/hard budget signals are enforced before or during dispatch based on policy across dual dimensions:
  - currency budget (USD)
  - quota budget (request/token units)
- Gateway MUST support pre-call reservation and post-call reconciliation for budget accounting.
- Response includes normalized usage, cost metadata, and quota-attribution metadata.
- Free-tier model behavior:
  - `cost_usd` MAY be `0`
  - quota usage MUST still be recorded and enforced
- Quota limit handling must follow source precedence:
  - `policy_guardrail` (authoritative)
  - `provider_config`
  - `provider_signal` (`429`, `RESOURCE_EXHAUSTED`, rate-limit headers)
- Provider-limit signals must be captured in response metadata and observability streams.
- `cost_source` MUST be explicit:
  - `provider_reported`
  - `catalog_estimated`
  - `none` (for free-tier/no-price path)

## 6. Response Contract
Minimum response fields:
- `request_id`
- `trace_id`
- `decision` (`served|fallback_served|denied`)
- `model_selected`
- `usage` (`input_tokens`, `output_tokens`, `total_tokens`, `request_units`)
- `cost` (`estimated_cost_usd`, `actual_cost_usd` optional, `cost_source`)
- `budget_usage` (`currency_delta_usd`, `quota_delta` with `request_units`, `token_units`)
- `budget_context_effective` (`allocation_mode`, `project_share_ratio` optional, `effective_budget`)
- `quota_limit_source` (`policy_guardrail|provider_config|provider_signal`)
- `latency_ms`
- `policy_context`
- `route_metadata`

## 7. Security and Reliability
- Provider credentials are loaded from secret references only.
- Request/response payload handling must follow data classification policy.
- Gateway failure behavior for governed actions is fail-closed unless explicit downgrade path is policy-approved.

## 8. Conformance Tests
- Direct provider access path is blocked for governed runtime components.
- Same routing profile and input produce deterministic policy-compliant route class.
- Requests with unknown `routing_profile` are denied.
- Fallback path emits required trace and audit metadata.
- Budget attribution fields are present for all completed requests.
- Free-tier served responses include quota usage fields even when `cost.actual_cost_usd == 0`.
- Missing usage data for governed responses triggers deterministic deny/fail-closed handling.
- Quota-limit source and provider-limit signals are included for governed responses when available.
