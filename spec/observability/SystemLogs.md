# OpenQilin - System Logs Specification

## 1. Scope
- Defines required system log streams and structured fields.
- Defines compact and full-detail logging profiles aligned with constitutional audit policy.

## 2. Logging Profiles
- Compact profile: default for normal `allow` paths.
- Full profile: required for `deny`, `allow_with_obligations`, and governance/emergency actions.

## 3. Required Fields
Compact profile required fields:
- `timestamp`
- `level`
- `component`
- `trace_id`
- `event_id`
- `message`
- `context`

Full profile additional required fields:
- `agent_id`
- `intent`
- `decision_reasoning`
- `authority_source`
- `tool_call`
- `result`
- `outcome_evaluation`
- `budget_impact`
- `previous_state`
- `next_state`

## 4. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| LOG-001 | Critical actions MUST emit structured logs with trace_id. | high | Observability |
| LOG-002 | Full profile logging MUST be used for deny, allow_with_obligations, and governance/emergency actions. | high | Observability |
| LOG-003 | Structured log records MUST preserve policy metadata (`policy_version`, `policy_hash`, `rule_ids`) for governed actions. | high | Observability |

## 5. Conformance Tests
- Logs missing trace_id fail validation where required.
- Full-profile-required events missing extended fields fail validation.
- Governed actions missing policy metadata fail validation.
