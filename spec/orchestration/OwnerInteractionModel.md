# OpenQilin - Owner Interaction Model Specification

## 1. Scope
- Defines owner-to-agent interaction patterns, channels, message types, alerts, and monitoring views.
- Covers human-facing interaction semantics only; policy enforcement remains in constitution/runtime components.

## 2. Interaction Channels
- Direct Message (owner <-> single agent)
- Group/Project Chat (owner + scoped project agents)
- Executive Chat (owner + ceo/cwo/cso)
- Governance Chat (owner + auditor/administrator)

Allowed direct access (v1):
- owner may direct-message: administrator, auditor, ceo, cwo, cso, `concierge_bootstrap`, `concierge_passive`.
- owner may join project and executive channels as observer/commander according to policy.

## 3. Message Types
- `command`
- `query`
- `info`
- `discussion`
- `alert`
- `system_event`

Every owner interaction message should include:
- `message_id`
- `trace_id`
- `sender`
- `recipients`
- `message_type`
- `priority`
- `timestamp`
- `content`
- optional `project_id`

## 4. Alerts and Notification Model
Alert classes:
- `critical`: immediate owner attention required.
- `warning`: high-priority risk signal, may trigger automated correction.
- `informational`: periodic updates and summaries.

Canonical examples:
- critical: legal risk, hard budget breach, deadlock, safety mode activation
- warning: repeated execution failures, nearing budget limit
- informational: milestones, periodic health summaries

## 5. Dashboard Views (v1)
- Agent status
- Project progress
- Budget usage
- Governance and safety events
- Periodic reports (daily/weekly/monthly/quarterly/yearly)

## 6. Governance and Safety Constraints
- owner interaction must not bypass policy authorization for execution actions.
- High-impact actions triggered by owner messages must still pass policy and budget gates.
- All critical owner interactions must produce immutable audit events.

## 7. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| OIM-001 | owner-issued commands MUST pass policy authorization before execution. | critical | Policy Engine |
| OIM-002 | Critical owner interaction events MUST generate immutable audit records. | high | Observability |
| OIM-003 | owner channel access MUST respect role and project scope constraints. | high | Task Orchestrator |
| OIM-004 | Alert severity mapping MUST follow constitutional safety/escalation policies. | high | Observability |

## 8. Conformance Tests
- Unauthorized owner-issued execution requests are denied by policy engine.
- Critical owner interactions produce immutable audit events with trace metadata.
- owner cannot access out-of-scope restricted project channels without authorization.
- Alert classification and routing match constitutional policy definitions.
