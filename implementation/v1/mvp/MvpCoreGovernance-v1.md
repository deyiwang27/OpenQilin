# OpenQilin MVP v0.1 - Core Governance Runtime (Final)

Status: finalized for MVP definition discussion
Last updated: 2026-03-12

## 1. Purpose

This document defines the first executable MVP boundary for OpenQilin.

The MVP must prove a governance-first multi-agent runtime that can:
- Instantiate persistent institutional agents
- Accept owner commands through one governed ingress path
- Enforce authority and budget controls before execution
- Dispatch to sandbox, LLM, and communication execution boundaries
- Persist immutable audit evidence for every decision path
- Execute proposal-to-project activation workflow with explicit approval gates

## 2. Scope

Included:
- Institutional agents: `ceo`, `cwo`, `auditor`, `administrator`
- Project roles: `pm` plus up to 2 `specialist` agents per project
- `domain_lead` role declared in schema but disabled in first MVP runtime
- Hybrid runtime: in-memory workers plus PostgreSQL authoritative state
- Dual budget control: currency (`usd`) and quota (`units`)
- Discord as owner-facing command adapter
- Tool execution only through governed dispatch boundaries
- Hard-block governance file-path controls
- Project documentation policy with file-type caps and governed storage root

Excluded:
- CSO and Domain Lead role systems
- Portfolio optimization across multiple projects
- Autonomous governance-policy editing by operational agents
- External swarm orchestration

## 3. Runtime Architecture

Authoritative flow:

`owner ingress -> envelope validation -> principal resolution -> admission/idempotency -> policy gate -> budget gate -> dispatch -> audit/metrics`

Core runtime components:
- Agent registry
- Project registry
- Runtime task-state repository
- Authority and policy middleware
- Budget engine
- Dispatch gateways (`sandbox`, `llm`, `communication`)
- Immutable audit log and metrics/tracing layer

## 4. Role and Authority Model

`ceo`:
- Approves project objectives and lifecycle transitions
- Cannot bypass `auditor` hard-budget pause without explicit owner action

`cwo`:
- Creates project workforce (`pm`, `specialist`, and `domain_lead` declaration when needed)
- Cannot change governance policy or budget engine rules
- Attaches template + llm profile + system prompt package when initializing workforce

`auditor`:
- Enforces budget and governance containment
- Can pause project execution on hard-threshold breach
- Does not execute delivery tasks

`administrator`:
- Enforces lifecycle integrity and operational controls
- Maintains runtime availability and audit-path integrity

`pm`:
- Coordinates project execution under approved budget
- Delegates scoped execution tasks to specialists
- Must execute mandatory operations from PM template (milestones, decomposition, assignment, reporting)

`specialist`:
- Executes bounded delivery tasks only
- Cannot create agents or modify governance controls
- Is touchable only by `pm` in first MVP (domain-lead path reserved but disabled)

## 5. Budget Governance

Budget model is dual-track:
- Currency budget (`usd`): estimated and actual spend
- Quota budget (`units`): provider-free-tier or internal execution allowance

Default thresholds for MVP:
- Soft threshold: `90%`
- Hard threshold: `100%`

Threshold behavior:
- At soft threshold: emit alerts and continue with elevated visibility
- At hard threshold: block new execution and pause project until explicit owner-approved increase and `ceo` reactivation

Free-tier providers (for example Gemini free plans) are tracked by quota usage even when currency cost is `0`.

## 6. Lifecycle Model

Project lifecycle states:
- `proposed -> approved -> active -> paused -> completed -> terminated -> archived`

Project lifecycle constraints:
- no standalone `rejected` state in first MVP
- proposals remain `proposed` until approved
- `terminated` allowed only from `active|paused`
- `archived` allowed only from `completed|terminated`

Project completion governance chain:
- PM submits completion report to `cwo`.
- `cwo` and `ceo` co-approve completion decision.
- owner is notified after completion decision is recorded.

Task/runtime lifecycle states (canonical in current implementation):
- `queued -> authorized -> dispatched`
- Fail-closed path: `blocked`
- Terminal callbacks: `completed | failed | cancelled`

Terminal states are immutable.

## 7. Command and Dispatch Model

Owner command families in MVP:
- `run_task*` -> `sandbox` dispatch
- `llm_*` -> `llm` dispatch
- `msg_*` -> `communication` dispatch
- Read-only status queries are allowed through owner ingress

Owner commands do not mutate runtime state directly. They always execute through the governed pipeline.

Owner interaction constraints:
- Proposal discussion path is `owner`, `ceo`, and `cwo`.
- owner may communicate with selected non-specialist agents under policy scope.
- owner cannot directly command `specialist`; specialist communication routes through `pm`.

## 8. Governance Boundaries

Protected paths for MVP governance guard:
- `implementation/v1/spec/`
- `implementation/v1/design/`
- `implementation/v1/mvp/`
- `src/openqilin/budget_runtime/`
- `src/openqilin/control_plane/identity/`

Any unauthorized modification attempt is blocked and audited.

## 8.1 Project Documentation Governance

Storage strategy:
- Rich-text project docs live under `${OPENQILIN_SYSTEM_ROOT}/projects/<project_id>/` (outside repo tree).
- DB remains authoritative for state/control metadata and file pointer/hash references.

MVP policy:
- Only approved artifact types may be created.
- Each artifact type has max active-document caps to control file volume.
- Over-cap document creation is denied fail-closed and audited.

## 9. Logging and Audit

Every governed step emits append-only evidence including:
- timestamp, trace ID, request ID, task ID
- actor and role
- decision source and outcome
- budget deltas (currency and quota)
- error code, reason code, and escalation markers

Append-only policy for logs means no in-place edits or deletes in runtime APIs.

## 10. Definition of Done for MVP

MVP v0.1 is complete when:
- Governed ingress and fail-closed execution paths are operational
- Role authority and budget controls are enforced in runtime flow
- Immutable audit evidence is generated for accept/block/replay/callback paths
- Discord owner adapter can submit valid owner commands through the same governed path
