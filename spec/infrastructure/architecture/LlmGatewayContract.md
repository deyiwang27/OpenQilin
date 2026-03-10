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
- `budget_context`
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
- Soft/hard budget signals are enforced before or during dispatch based on policy.
- Response includes normalized usage and estimated cost metadata.

## 6. Response Contract
Minimum response fields:
- `request_id`
- `trace_id`
- `decision` (`served|fallback_served|denied`)
- `model_selected`
- `usage` (`input_tokens`, `output_tokens`, `total_tokens`)
- `estimated_cost`
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
