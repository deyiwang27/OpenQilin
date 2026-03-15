# OpenQilin - Owner Interaction Model Specification

## 1. Scope
- Defines owner-to-agent interaction patterns, channels, message types, alerts, and monitoring views.
- Covers human-facing interaction semantics only; policy enforcement remains in constitution/runtime components.
- Discord security profile is defined in `spec/cross-cutting/security/DiscordOwnerChannelIdentityHardening.md`.

## 2. Interaction Channels
- Direct Message (owner <-> single agent)
- Leadership Council Chat
- Project Chat (owner + scoped project agents)
- Executive Chat (owner + ceo/cwo/cso + secretary)
- Governance Chat (owner + auditor/administrator + secretary)

Channel names are stable interface classes; effective memberships by runtime profile are defined in Section 2.1.

Platform posture (v1):
- Primary external channel: Discord.
- Additional external channels are deferred until Discord baseline is hardened.
- Communication protocol posture remains `A2A + ACP`.

Allowed direct access (system-level target):
- owner may direct-message: `administrator`, `auditor`, `ceo`, `cwo`, `cso`, `secretary` (pending activation).
- owner direct-message access to `project_manager`, `domain_leader`, and `specialist` is denied.
- owner may join only contract-defined governance/executive/project channels.

## 2.1 Discord Chat Governance Contract
Channel classes are fixed and policy-governed; free-style owner group creation is out of scope.

System-level target profile:
- `leadership_council`: `owner`, `administrator`, `auditor`, `ceo`, `cwo`, `cso`, `secretary` (pending activation)
- `governance`: `owner`, `administrator`, `auditor`, `secretary` (pending activation)
- `executive`: `owner`, `ceo`, `cwo`, `cso`, `secretary` (pending activation)
- `project` channel name: `<project_name>`
  - `proposed`: `owner`, `ceo`, `cwo`, `cso`, `secretary` (pending activation)
  - `approved|active|paused`: `owner`, `ceo`, `cwo`, `cso`, `project_manager`, `domain_leader`, `secretary` (pending activation)
  - `completed|terminated`: same membership, read-only
  - `archived`: locked for new messages

MVP v1 active profile (simplified first activation):
- `cso` and `domain_leader` are schema-declared but runtime-disabled.
- `secretary` chat participation is system-defined but pending/inactive in v1.
- Allowed owner direct messages: `administrator`, `auditor`, `ceo`, `cwo`.
- `leadership_council`: `owner`, `administrator`, `auditor`, `ceo`, `cwo`
- `governance`: `owner`, `administrator`, `auditor`
- `executive`: `owner`, `ceo`, `cwo`
- `project` channel name: `<project_name>`
  - `proposed`: `owner`, `ceo`, `cwo`
  - `approved|active|paused`: `owner`, `ceo`, `cwo`, `project_manager`
  - `completed|terminated`: same membership, read-only
  - `archived`: locked for new messages

MVP v1 governance posture:
- Proposal discussion path is `owner <-> ceo <-> cwo` with optional joint discussion channel.
- owner may communicate with selected non-specialist agents by policy scope.
- owner direct interaction with `specialist` is prohibited; specialist communication routes through `project_manager`.
- `domain_leader` may be declared in schema but remains disabled in v1 runtime activation.
- v1 operational role set: `ceo`, `cwo`, `auditor`, `administrator`, `project_manager`, `specialist`.

MVP v2 active profile (supersedes v1 profile above):
- `secretary` is active as an institutional front-desk agent: advisory-only, handles intent triage, routing assistance, and daily summaries. Activated in M11.
- `cso` is active as a real advisory governance gate enforced by live OPA policy evaluation. Activated in M12 (after OPA wiring and role self-assertion fix are complete).
- `domain_leader` is active as a backend-routed virtual agent scoped to project context. It is NOT a standalone Discord bot identity. Activated in M13 (after project-space binding is in place).
- Allowed owner direct messages (v2): `administrator`, `auditor`, `ceo`, `cwo`, `cso`, `secretary`.
- `leadership_council` (v2): `owner`, `administrator`, `auditor`, `ceo`, `cwo`, `cso`, `secretary`
- `governance` (v2): `owner`, `administrator`, `auditor`, `secretary`
- `executive` (v2): `owner`, `ceo`, `cwo`, `cso`, `secretary`
- `project` channel name: `<project_name>` (v2 — runtime-bound project space, see `ProjectSpaceBindingModel.md`)
  - `proposed`: `owner`, `ceo`, `cwo`, `cso`
  - `approved|active|paused`: `owner`, `ceo`, `cwo`, `cso`, `project_manager`
  - `completed|terminated`: same membership, read-only
  - `archived`: locked for new messages

MVP v2 governance posture:
- `project_manager` is the default responder in project spaces; routing is enforced by project-space binding, not by Discord bot identity.
- `domain_leader` responds only through PM escalation or governed review paths; it is not a default channel participant.
- Free-text and compact command interaction replaces JSON-shaped daily use. See `OwnerInteractionGrammar.md`.
- Agent loop controls (hop limits, pair-round caps) are enforced per trace. See `AgentLoopControls.md`.
- All governance prerequisites for role activation (OPA wiring, role self-assertion fix) MUST be satisfied before the v2 active profile is treated as live.

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

Connector-required metadata:
- `channel` (`discord|internal`)
- `external_message_id`
- `actor_external_id`
- `idempotency_key`
- `raw_payload_hash`

## 4. Connector Security and Reliability
- Incoming connector payloads must pass platform signature/token validation.
- External identity must be mapped to internal principal/role before policy checks.
- Replay window and idempotency controls are required for redelivery-safe processing.
- High-impact command handling must produce immutable accept/deny audit records.

## 5. Alerts and Notification Model
Alert classes:
- `critical`: immediate owner attention required.
- `warning`: high-priority risk signal, may trigger automated correction.
- `informational`: periodic updates and summaries.

Canonical examples:
- critical: legal risk, hard budget breach, deadlock, safety mode activation
- warning: repeated execution failures, nearing budget limit
- informational: milestones, periodic health summaries

## 6. Dashboard Views (v1)
- Agent status
- Project progress
- Budget usage
- Governance and safety events
- Periodic reports (daily/weekly/monthly/quarterly/yearly)

## 7. Governance and Safety Constraints
- owner interaction must not bypass policy authorization for execution actions.
- High-impact actions triggered by owner messages must still pass policy and budget gates.
- All critical owner interactions must produce immutable audit events.
- Discord chat class and membership must match the fixed contract in Section 2.1.
- Proposal approval state transitions are constrained by project state machine (`proposed -> approved -> active ...`).
- Specialist touchability policy is enforced at ingress + policy layers (owner cannot directly command specialist).

## 8. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| OIM-001 | owner-issued commands MUST pass policy authorization before execution. | critical | Policy Engine |
| OIM-002 | Critical owner interaction events MUST generate immutable audit records. | high | Observability |
| OIM-003 | owner channel access MUST respect fixed chat-class membership and project-scope constraints. | high | Task Orchestrator |
| OIM-004 | Alert severity mapping MUST follow constitutional safety/escalation policies. | high | Observability |
| OIM-005 | owner MUST NOT directly command specialist agents; specialist interactions route through `project_manager`. | critical | Policy Engine |

## 9. Conformance Tests
- Unauthorized owner-issued execution requests are denied by policy engine.
- Critical owner interactions produce immutable audit events with trace metadata.
- owner cannot access out-of-scope restricted project channels without authorization.
- ad hoc owner group chats outside Section 2.1 contract are denied.
- Alert classification and routing match constitutional policy definitions.
- Unsigned or replayed connector payloads are rejected before orchestration.
