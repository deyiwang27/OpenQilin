# OpenQilin - Audit Events Specification

## 1. Scope
- Defines immutable governance/audit event taxonomy.
- Defines required audit event schema and detail profile behavior.

## 2. Event Categories
- policy_decision
- escalation
- enforcement
- lifecycle_transition
- budget_violation
- policy_change
- agent_pause_report

## 3. Audit Event Contract
Required fields:
- `event_id`
- `event_type`
- `timestamp`
- `trace_id`
- `actor_id`
- `actor_role`
- `policy_version`
- `policy_hash`
- `rule_ids`
- `payload`

Detail profile:
- compact: normal `allow` decision path
- full: `deny`, `allow_with_obligations`, governance/emergency, policy changes

For `agent_pause_report`, payload must include:
- `paused_agent_id`
- `initiated_by`
- `reason`
- `critical_impact`
- `ceo_notified`
- `owner_alerted`

## 4. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| AUD-001 | Governance-critical actions MUST emit immutable audit events. | critical | Observability |
| AUD-002 | Audit events MUST include policy metadata (`policy_version`, `policy_hash`, `rule_ids`) for governed actions. | critical | Observability |
| AUD-003 | Agent pause events MUST generate audit records including ceo notification and owner alert status when critical impact is true. | high | Observability |

## 5. Conformance Tests
- Audit events include policy_version, policy_hash, and rule_ids.
- Governance/emergency events use full detail profile.
- Agent pause events missing required payload fields fail validation.
