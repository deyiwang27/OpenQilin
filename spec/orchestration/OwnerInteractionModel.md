# OpenQilin - Owner Interaction Model Specification

## 1. Scope
- Defines Owner-to-agent interaction patterns, channels, message types, alerts, and monitoring views.
- Covers human-facing interaction semantics only; policy enforcement remains in constitution/runtime components.

## 2. Interaction Channels
- Direct Message (Owner <-> single agent)
- Group/Project Chat (Owner + scoped project agents)
- Executive Chat (Owner + CEO/CWO/CSO)
- Governance Chat (Owner + Auditor/Administrator)

Allowed direct access (v1):
- Owner may direct-message: Administrator, Auditor, CEO, CWO, CSO, Concierge roles.
- Owner may join project and executive channels as observer/commander according to policy.

## 3. Message Types
- `command`
- `query`
- `info`
- `discussion`
- `alert`
- `system_event`

Every Owner interaction message should include:
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
- `critical`: immediate Owner attention required.
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
- Owner interaction must not bypass policy authorization for execution actions.
- High-impact actions triggered by Owner messages must still pass policy and budget gates.
- All critical Owner interactions must produce immutable audit events.

## 7. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| OIM-001 | Owner-issued commands MUST pass policy authorization before execution. | critical | Policy Engine |
| OIM-002 | Critical Owner interaction events MUST generate immutable audit records. | high | Observability |
| OIM-003 | Owner channel access MUST respect role and project scope constraints. | high | Task Orchestrator |
| OIM-004 | Alert severity mapping MUST follow constitutional safety/escalation policies. | high | Observability |

## 8. Conformance Tests
- Unauthorized Owner-issued execution requests are denied by policy engine.
- Critical Owner interactions produce immutable audit events with trace metadata.
- Owner cannot access out-of-scope restricted project channels without authorization.
- Alert classification and routing match constitutional policy definitions.

