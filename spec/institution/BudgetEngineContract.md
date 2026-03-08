# OpenQilin - Budget Engine Contract Specification

## 1. Scope
- Defines budget thresholds, reservations, and enforcement outcomes.
- Defines how budget control integrates with Policy Engine and governance enforcement.

## 2. Core Parameters
- soft_threshold_percent
- hard_threshold_percent
- daily_guardrail_percent
- Source of parameter values: `constitution/BudgetPolicy.yaml`.

## 3. Budget Control Model (v1)
- Threshold values are read from YAML policy artifacts only.
- Checks occur at:
  - pre-dispatch (reservation)
  - in-flight update (consumption accounting)
  - post-completion reconciliation
- Concurrent spending uses atomic reservation semantics.

## 4. Decision and Enforcement Outputs
- `ok`: execution may proceed.
- `soft_breach`: execution may proceed with alerts (`CWO`, `CEO`).
- `hard_breach`: execution blocked; emit enforcement event for governance action.

Hard breach governance behavior (aligned to governance specs):
- Auditor performs independent enforcement.
- Project may be paused.
- Owner is escalated; CEO is informed for remediation planning.

## 5. Budget Event Contract
Required fields:
- `event_id`
- `trace_id`
- `project_id`
- `budget_before`
- `budget_after`
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
| BUD-004 | Hard-breach events MUST trigger governance escalation metadata for Auditor/Owner/CEO flow. | critical | Budget Engine |
| BUD-005 | Budget decisions MUST include policy version/hash context. | high | Budget Engine |

## 7. Conformance Tests
- Parallel requests cannot exceed reserved budget.
- Soft threshold breach emits alert event without automatic shutdown.
- Hard threshold breach emits block + enforcement event with escalation metadata.
- Budget evaluation under same inputs/policy version is deterministic.
