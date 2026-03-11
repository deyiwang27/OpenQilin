# OpenQilin - Budget Engine Contract Specification

## 1. Scope
- Defines budget thresholds, reservations, and enforcement outcomes.
- Defines how budget control integrates with Policy Engine and governance enforcement.

## 2. Core Parameters
- currency_soft_threshold_percent
- currency_hard_threshold_percent
- daily_guardrail_percent
- quota_daily_request_cap
- quota_daily_token_cap
- quota_per_minute_request_cap (optional)
- quota_per_minute_token_cap (optional)
- allocation_mode (`absolute|ratio|hybrid`)
- project_share_ratio (when allocation mode uses ratio)
- project_currency_floor_usd (optional)
- project_currency_cap_usd (optional)
- project_quota_floor (`request_units`, `token_units`) (optional)
- project_quota_cap (`request_units`, `token_units`) (optional)
- Source of parameter values: `constitution/domain/BudgetPolicy.yaml`.

## 3. Budget Control Model (v1)
- Dual budget dimensions are mandatory:
  - currency budget (USD-denominated)
  - quota budget (request/token units in defined windows)
- Threshold values are read from YAML policy artifacts only.
- Checks occur at:
  - pre-dispatch (reservation)
  - in-flight update (consumption accounting)
  - post-completion reconciliation
- Concurrent spending uses atomic reservation semantics.
- Free-tier model posture:
  - currency usage MAY be `0`
  - quota usage MUST still be tracked and enforced

Quota limit source model:
- Quota enforcement inputs must use this precedence:
  1. policy-configured internal guardrails (authoritative runtime caps)
  2. provider quota configuration (project/model settings)
  3. provider runtime signals (`429`, `RESOURCE_EXHAUSTED`, rate-limit headers)
- Runtime must store observed provider-limit signals for operator visibility, but must not exceed policy-configured internal guardrails.

Project allocation model:
- Project budget allocation supports:
  - `absolute`: fixed per-project budgets
  - `ratio`: per-project share of total budget
  - `hybrid`: ratio with floor/cap constraints
- Recommended default is `hybrid`.
- Hybrid effective allocation per project is:
  - `effective_budget = min(max_cap, max(min_floor, share_ratio * total_available_budget))`
- The same allocation mode applies independently to both dimensions:
  - currency budget
  - quota budget
- Rebalance cadence must be explicit (for example daily window rollover) and auditable.

## 4. Decision and Enforcement Outputs
- `ok`: execution may proceed; no hard breach in either dimension.
- `soft_breach`: execution may proceed with alerts (`cwo`, `ceo`) when soft thresholds are crossed.
- `hard_breach`: execution blocked; emit enforcement event for governance action when any hard threshold is crossed.
- `reconciliation_error`: usage/cost reconciliation failed; block governed continuation until resolved.
- `allocation_violation`: project exceeded effective allocated share/cap; block governed continuation until next allocation window or approved override.

Hard breach governance behavior (aligned to governance specs):
- `auditor` performs independent enforcement.
- Project may be paused.
- `owner` is escalated; `ceo` is informed for remediation planning.

## 5. Budget Event Contract
Required fields:
- `event_id`
- `trace_id`
- `project_id`
- `budget_before`
- `budget_after`
- `currency_before_usd`
- `currency_after_usd`
- `quota_before` (`request_units`, `token_units`)
- `quota_after` (`request_units`, `token_units`)
- `cost_source` (`provider_reported|catalog_estimated|none`)
- `reservation_id`
- `allocation_mode`
- `project_share_ratio` (when applicable)
- `effective_currency_budget_usd`
- `effective_quota_budget` (`request_units`, `token_units`)
- `quota_limit_source` (`policy_guardrail|provider_config|provider_signal`)
- `threshold_state`
- `policy_version`
- `policy_hash`
- `rule_ids`

## 6. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| BUD-001 | Hard-threshold breaches MUST block or pause execution. | critical | Budget Engine |
| BUD-002 | Concurrent spend MUST use atomic reservation. | high | Budget Engine |
| BUD-003 | Threshold values MUST be sourced from active YAML budget policy. | high | Budget Engine |
| BUD-004 | Hard-breach events MUST trigger governance escalation metadata for `auditor`/`owner`/`ceo` flow. | critical | Budget Engine |
| BUD-005 | Budget decisions MUST include policy version/hash context. | high | Budget Engine |
| BUD-006 | Free-tier model traffic MUST still be enforced by quota thresholds even when currency impact is zero. | critical | Budget Engine |
| BUD-007 | Reservation and reconciliation MUST support both currency and quota dimensions. | high | Budget Engine |
| BUD-008 | Unknown/missing usage for governed actions MUST fail closed via reconciliation error handling. | critical | Budget Engine |
| BUD-009 | Quota limit evaluation MUST follow source precedence (`policy_guardrail` > `provider_config` > `provider_signal`). | high | Budget Engine |
| BUD-010 | Project allocation mode MUST support `absolute`, `ratio`, and `hybrid`; `hybrid` formula MUST be deterministic and auditable. | high | Budget Engine |
| BUD-011 | Allocation policy changes and rebalance executions MUST emit audit-linked evidence with policy version/hash context. | high | Budget Engine |

## 7. Conformance Tests
- Parallel requests cannot exceed reserved budget.
- Soft threshold breach emits alert event without automatic shutdown.
- Hard threshold breach emits block + enforcement event with escalation metadata.
- Budget evaluation under same inputs/policy version is deterministic.
- Free-tier request with `cost=0` still increments quota counters and enforces quota hard limits.
- Reconciliation mismatch or missing usage data emits `reconciliation_error` and blocks governed continuation.
- Quota decisions use source precedence deterministically when policy caps and provider limits differ.
- Hybrid allocation computes deterministic effective budget from ratio/floor/cap and blocks on allocation violations.
