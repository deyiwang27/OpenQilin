# OpenQilin - LLM Model Routing Profile v1 Specification

## 1. Scope
- Defines v1 model catalog and routing profiles used by `llm_gateway`.
- Defines environment-specific provider/model selection policy.
- Defines initial local/CI testing posture using free-tier Gemini models.

## 2. Design Principles
- `llm_gateway` is the only governed runtime path for provider access.
- Routing behavior is deterministic for the same `routing_profile + model_class`.
- Provider/model identifiers are referenced by aliases in config, not hardcoded in runtime logic.
- Profile changes follow normal change control and must be auditable.
- Routing-profile budget guardrails define model-route safety caps, not per-project allocation shares.

## 3. Routing Contract
Each routing profile must define:
- `profile_id`
- `environments` (`local_dev|ci|staging|production`)
- `model_class_map` (`model_class -> provider_model_alias[]` in priority order)
- `fallback_policy` (`max_fallback_hops`, retry posture)
- `budget_guardrails`:
  - `currency_caps` (`per_request_usd_cap`, optional windowed caps)
  - `quota_caps` (`per_request_token_cap`, `window_request_cap`, `window_token_cap`)
- project-level ratio/floor/cap allocation is governed by Budget Engine policy, then intersected with these route guardrails
- `status` (`active|inactive`)

## 4. v1 Model Classes
- `interactive_fast`
- `reasoning_general`
- `embedding_text`

Notes:
- v1 may keep `embedding_text` disabled in a profile if embeddings are sourced from a separate governed path.
- New classes require policy/routing profile updates before runtime use.

## 5. v1 Routing Profiles
### 5.1 `dev_gemini_free`
Purpose:
- default profile for initial stage testing in `local_dev` and `ci`.

Environments:
- `local_dev`
- `ci`

Model class mapping:
- `interactive_fast` -> `google_gemini_free_primary`, `google_gemini_free_fallback`
- `reasoning_general` -> `google_gemini_free_primary`, `google_gemini_free_fallback`
- `embedding_text` -> `disabled`

Fallback policy:
- `max_fallback_hops`: `1`
- provider timeout/retry policy follows `LlmGatewayContract` runtime handling

Budget/cost posture:
- target is near-zero provider cost for early-stage validation
- requests exceeding configured free-tier-safe limits are denied or truncated by policy
- free-tier profile MUST define active quota caps even when currency caps are effectively zero

### 5.2 `prod_controlled`
Purpose:
- controlled staging/production profile managed by owner-approved change control.

Environments:
- `staging`
- `production`

Model class mapping:
- defined by approved runtime configuration and policy bundle
- may include paid provider aliases as approved

Fallback policy:
- bounded, explicit, and audit-emitting for every fallback decision

## 6. Provider Alias Requirements
Provider/model aliases are deployment configuration values. Required aliases for `dev_gemini_free`:
- `google_gemini_free_primary`
- `google_gemini_free_fallback`

Alias rules:
- aliases must resolve to available free-tier Gemini-capable endpoints in the running environment
- unresolved aliases fail closed for governed actions
- alias target changes require audit event and review record

## 7. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| LLM-001 | All governed model requests MUST use an active routing profile. | critical | llm_gateway |
| LLM-002 | Unknown or inactive `routing_profile` MUST be denied (fail-closed). | critical | llm_gateway |
| LLM-003 | `dev_gemini_free` MUST be the default profile for `local_dev` and `ci` in v1 initial testing. | high | platform config |
| LLM-004 | Fallback decisions MUST emit trace-correlated audit metadata. | high | llm_gateway |
| LLM-005 | Provider/model alias changes MUST be auditable and change-controlled. | high | administrator |
| LLM-006 | Free-tier routing profiles MUST include enforceable quota caps for request/token usage. | critical | llm_gateway |

## 8. Conformance Tests
- `local_dev` and `ci` requests default to `dev_gemini_free` unless explicitly overridden by approved config.
- Unknown profile id is denied with deterministic error code.
- Deterministic input/profile returns deterministic route class selection.
- Fallback events include `trace_id`, selected alias, and reason metadata.
- Unresolved Gemini alias fails closed for governed actions.
- `dev_gemini_free` enforces quota caps even when computed currency impact is `0`.
