# OpenQilin - Metrics and Alerts Specification

## 1. Scope
- Defines operational and governance metrics, alert routing, and alert ownership.

## 2. Core Metrics
- authorization deny rate
- budget breach count (`soft`, `hard`)
- task failure rate
- mean time to containment
- dead-letter message rate
- policy evaluation error rate

## 3. Alert Ownership Matrix
| Alert Type | Source owner | Primary Escalation | Secondary/Fallback |
| --- | --- | --- | --- |
| budget_hard_breach | `auditor` | `owner` | `ceo` (notify) |
| governance_violation | `auditor` | `owner` | `ceo` (notify) |
| safety_critical_incident | `auditor` | `owner` | `ceo` |
| infrastructure_failure | `administrator` | `owner` | `ceo` |
| orchestration_deadlock | `project_manager` | `cwo` | `ceo` |
| communication_dead_letter_spike | `administrator` | `cwo` | `ceo` |

Fallback rule:
- If source owner is unavailable or ambiguous, route to `ceo` as default operational owner and emit owner-resolution audit event.

## 4. Alert Event Requirements
- required fields: `event_id`, `trace_id`, `alert_type`, `severity`, `source_owner_role`, `next_owner_role`, `rule_ids`, `timestamp`
- all critical alerts MUST include linked policy and escalation metadata.

## 5. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| MET-001 | Critical incidents MUST trigger alerts to governance channels. | critical | observability |
| MET-002 | Every alert MUST resolve a source owner role before escalation. | high | observability |
| MET-003 | Ambiguous-owner alerts MUST default-route to `ceo` with audit metadata. | high | observability |
| MET-004 | Alert events MUST include required escalation metadata fields. | high | observability |

## 6. Conformance Tests
- Critical incident classes emit alerts with complete required fields.
- Ambiguous owner scenario routes to `ceo` and emits resolution event.
- Budget hard breach alert routes through `auditor` enforcement path.
