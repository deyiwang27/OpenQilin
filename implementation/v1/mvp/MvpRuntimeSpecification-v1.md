# OpenQilin Runtime Specification v0.1 (Final)

Status: finalized implementation contract for MVP v0.1
Last updated: 2026-03-12

## 1. Purpose

This document defines the implementation-level contracts for MVP v0.1.
It is intentionally aligned with current runtime semantics and naming.

## 2. Canonical Runtime Constants

- Budget soft-threshold default: `0.90`
- Budget hard-threshold default: `1.00`
- Communication retry `max_attempts`: `3`
- Project workforce cap: `1 project_manager + up to 2 specialist`
- Canonical project file root: `${OPENQILIN_SYSTEM_ROOT}/projects/<project_id>/`
- Project documentation total active-document cap: `20`

Canonical role naming:
- Administrator -> `administrator`
- Auditor -> `auditor`
- CEO -> `ceo`
- CWO -> `cwo`
- CSO -> `cso`
- Project Manager -> `project_manager`
- Domain Leader -> `domain_leader`
- Specialist -> `specialist`

Budget thresholds are configurable per environment, but these are the MVP defaults.

## 3. Data Model Contracts

## 3.1 `agents`

Columns:
- `id` (uuid, pk)
- `role` (text: `ceo|cwo|auditor|administrator|project_manager|specialist|domain_leader`)
- `autonomy_level` (int)
- `authority_flags` (jsonb)
- `lifecycle_state` (text: `created|active|paused|retired`)
- `project_id` (uuid, nullable)
- `created_at` (timestamp)
- `updated_at` (timestamp)

MVP activation note:
- `domain_leader` role is schema-declared for forward compatibility but runtime-disabled in first MVP.

## 3.2 `projects`

Columns:
- `id` (uuid, pk)
- `name` (text)
- `objective` (text)
- `status` (text: `proposed|approved|active|paused|completed|terminated|archived`)
- `budget_currency_total` (numeric)
- `budget_quota_total` (numeric)
- `budget_currency_used` (numeric)
- `budget_quota_used` (numeric)
- `charter_storage_uri` (text)
- `charter_content_hash` (text)
- `metric_plan_storage_uri` (text)
- `metric_plan_content_hash` (text)
- `created_at` (timestamp)
- `updated_at` (timestamp)

## 3.3 `tasks` (runtime-state)

Columns:
- `task_id` (uuid, pk)
- `request_id` (uuid/string)
- `trace_id` (string)
- `principal_id` (string)
- `command` (text)
- `target` (text)
- `project_id` (uuid, nullable)
- `status` (text: `queued|authorized|dispatched|blocked|completed|failed|cancelled`)
- `outcome_source` (text, nullable)
- `outcome_error_code` (text, nullable; lower snake-case)
- `dispatch_target` (text, nullable)
- `dispatch_id` (text, nullable)
- `created_at` (timestamp)

## 3.4 `execution_logs` (append-only)

Columns:
- `id` (bigserial, pk)
- `timestamp` (timestamp)
- `trace_id` (text)
- `request_id` (text)
- `task_id` (text)
- `agent_id` (text/uuid)
- `role` (text)
- `action_type` (text)
- `target` (text)
- `currency_delta` (numeric)
- `quota_delta` (numeric)
- `result_status` (text: `success|failure|blocked|replayed|ignored_terminal`)
- `escalation_flag` (boolean)

Enforcement contract:
- Runtime write path is append-only
- No update/delete API for log records
- Database roles for runtime writers must deny direct update/delete

## 3.5 `project_artifact` + `project_artifact_version`

Minimum `project_artifact` fields:
- `artifact_id` (uuid, pk)
- `project_id` (uuid)
- `artifact_type` (text)
- `scope_type` (`project` in MVP v0.1)
- `scope_id` (text/uuid)
- `current_version` (int)
- `status` (`draft|active|superseded|archived`)
- `storage_uri` (text; under canonical project file root)
- `content_hash` (text; `sha256`)

Minimum `project_artifact_version` fields:
- `artifact_id` (uuid)
- `version_no` (int)
- `author_role` (text)
- `trace_id` (text)
- `created_at` (timestamp)

## 4. Owner Command Ingress Contract

Primary endpoint:
- `POST /v1/owner/commands`

Envelope requirements:
- canonical sender/recipient metadata
- connector metadata (idempotency key, signature payload hash, external message id)
- command action + target + payload args
- trace ID

Command-family routing:
- `llm_*` -> `llm`
- `msg_*` -> `communication`
- all others -> `sandbox`

Owner interaction policy:
- Proposal discussions are constrained to `owner`, `ceo`, and `cwo`.
- owner cannot directly command `specialist` in first MVP.
- Specialist command path is via `project_manager`.

## 5. Governance Middleware Pipeline

Required synchronous pipeline:

`request -> authority validation -> policy validation -> budget validation -> governance path guard -> dispatch -> audit append -> response`

Fail-closed rules:
- policy uncertainty or policy runtime error -> `blocked`
- budget uncertainty or budget runtime error -> `blocked`
- dispatch adapter failure -> `blocked`
- project-document policy violation (type/cap/path/hash mismatch) -> `blocked`

## 6. Budget Engine Contract

Dual-budget enforcement dimensions:
- `currency_usd` (estimated + actual)
- `quota_units` (token/request/provider quota abstraction)

Threshold behavior:
- soft (`>=90%`): alert and continue
- hard (`>=100%`): pause project and block new dispatches

Provider notes:
- Free-tier LLMs may report `actual_cost_usd=0`
- Quota accounting still applies and is mandatory for governance control
- Provider quota limits are configured operationally; runtime does not auto-discover all external quota policies

Project allocation model:
- Runtime enforcement uses absolute per-project caps
- Optional ratio planning is allowed upstream but must resolve to absolute caps before runtime execution

## 7. Lifecycle and Replay Contracts

Project state contracts:
- proposal revisions stay in `proposed`
- `proposed -> approved -> active -> paused -> completed|terminated -> archived`
- `terminated` allowed only from `active|paused`
- `archived` allowed only from `completed|terminated`
- project completion requires:
  - Project Manager completion report persisted
  - `cwo` + `ceo` approval evidence persisted
  - owner notification event emitted

Task state contracts:
- admission creates `queued`
- policy allow transitions to `authorized`
- accepted dispatch transitions to `dispatched`
- denied/rejected/fail-closed transitions to `blocked`

Callback update rules:
- Callback processor may rewrite communication outcomes to `dispatched` or `blocked`
- Terminal task states `completed|failed|cancelled` are immutable

Idempotency/replay rules:
- idempotency key is bound to principal identity
- replay returns the persisted prior outcome and does not re-run policy/budget/dispatch side effects

## 8. Governance Path Guard Contract

Protected directories (MVP baseline):
- `implementation/v1/spec/`
- `implementation/v1/design/`
- `implementation/v1/mvp/`
- `src/openqilin/budget_runtime/`
- `src/openqilin/control_plane/identity/`

Unauthorized write attempts must return blocked outcome with audit evidence.

## 8.1 Project Documentation Policy Contract

Storage location:
- Project-generated rich-text docs must be stored under `${OPENQILIN_SYSTEM_ROOT}/projects/<project_id>/`.
- Writes outside canonical project root are denied.
- Deterministic file convention:
  - `${OPENQILIN_SYSTEM_ROOT}/projects/<project_id>/docs/<artifact_type>/<artifact_type>--v<revision_no>.md`

Policy constraints:
- Only approved doc types may be created (MVP strict enum):
  - `project_charter`
  - `scope_statement`
  - `budget_plan`
  - `success_metrics`
  - `workforce_plan`
  - `execution_plan`
  - `decision_log`
  - `risk_register`
  - `progress_report`
  - `completion_report`
- Per-type active-document caps are enforced per project:
  - `project_charter`: 1
  - `scope_statement`: 1
  - `budget_plan`: 1
  - `success_metrics`: 1
  - `workforce_plan`: 1
  - `execution_plan`: 1
  - `decision_log`: 4
  - `risk_register`: 3
  - `progress_report`: 6
  - `completion_report`: 1
- Project-level total active-document cap is enforced: `20`.
- File create/update requires DB pointer (`storage_uri`) + hash (`content_hash`) synchronization.
- Pointer/hash mismatch is treated as integrity failure and denied fail-closed.

Mutability model:
- Versioned update: `project_charter`, `scope_statement`, `budget_plan`, `success_metrics`, `workforce_plan`, `execution_plan`, `risk_register`
- Append-only entries: `decision_log`, `progress_report`
- Append-only final report: `completion_report`

Lifecycle and stage write constraints:
- Writable states: `proposed|approved|active|paused`
- Read-only states: `completed|terminated|archived`
- `project_manager` may write only when project state is `active`.
- `project_manager` direct-write types in `active`: `execution_plan`, `risk_register`, `decision_log`, `progress_report`.
- `project_manager` writes to `scope_statement|budget_plan|success_metrics` require `cwo+ceo` approval evidence.
- Activation gate (`approved -> active`) requires initial finalized versions for:
  - `project_charter`, `scope_statement`, `budget_plan`, `success_metrics`, `workforce_plan`, `execution_plan`
- Initial baseline finalization is recorded during `proposed|approved` governance review and approved by `owner+ceo+cwo` before activation.

Integrity-failure behavior:
- write/update/archive operations are denied fail-closed.
- reads may return last verified version.
- immutable audit evidence is required for each denial.

## 9. Discord Adapter Contract

Allowed operations through owner ingress:
- `run_task*`
- `llm_*`
- `msg_*`
- status query commands (`query_project_status`, `query_agent_status`, `query_budget_status`)
- proposal discussion messages routed to governance discussion contracts (`owner`, `ceo`, `cwo`)

Adapter behavior:
- maps Discord message metadata to canonical owner-command envelope
- submits only through governed owner ingress endpoint
- does not bypass policy, budget, or authority middleware
- enforces specialist-touchability restriction for owner-originated commands

Discord chat governance contract:
- Chat classes are fixed: `direct`, `leadership_council`, `governance`, `executive`, `project`.
- Owner direct-message allowlist in MVP: `administrator`, `auditor`, `ceo`, `cwo`.
- Free-style owner group creation outside contract classes is denied.
- Project-channel (`<project_name>`) membership is state-driven in MVP:
  - `proposed`: `owner`, `ceo`, `cwo`
  - `approved|active|paused`: `owner`, `ceo`, `cwo`, `project_manager`
  - `completed|terminated`: read-only
  - `archived`: locked

System-level target profile (documented, deferred in MVP):
- Add `secretary` to owner direct-message allowlist and all chat classes (`leadership_council`, `governance`, `executive`, `project`) as pending activation.
- Add `cso` to `leadership_council`, `executive`, and `project` proposed-stage membership.
- Add `domain_leader` to `project` active-stage membership after role activation policy allows it.

## 10. Recovery Contract

Startup recovery sequence:
1. Load institutional agents from persistent state
2. Restore project states and budget counters
3. Restore runtime tasks and idempotency index
4. Rehydrate in-memory service state
5. Preserve paused/blocked constraints until explicit authorized transition

## 11. Non-Goals (MVP)

- Portfolio-level optimization and cross-project rebalancing
- Auto-discovery of all provider free-tier quota contracts
- Autonomous governance model mutation by project agents
- Runtime activation of `domain_leader` command path (declared but disabled)
