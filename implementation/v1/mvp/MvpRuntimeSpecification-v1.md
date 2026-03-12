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
- Project workforce cap: `1 pm + up to 2 specialist`

Budget thresholds are configurable per environment, but these are the MVP defaults.

## 3. Data Model Contracts

## 3.1 `agents`

Columns:
- `id` (uuid, pk)
- `role` (text: `ceo|cwo|auditor|administrator|pm|specialist`)
- `autonomy_level` (int)
- `authority_flags` (jsonb)
- `lifecycle_state` (text: `created|active|paused|retired`)
- `project_id` (uuid, nullable)
- `created_at` (timestamp)
- `updated_at` (timestamp)

## 3.2 `projects`

Columns:
- `id` (uuid, pk)
- `name` (text)
- `objective` (text)
- `status` (text: `created|active|paused|completed|archived`)
- `budget_currency_total` (numeric)
- `budget_quota_total` (numeric)
- `budget_currency_used` (numeric)
- `budget_quota_used` (numeric)
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

## 5. Governance Middleware Pipeline

Required synchronous pipeline:

`request -> authority validation -> policy validation -> budget validation -> governance path guard -> dispatch -> audit append -> response`

Fail-closed rules:
- policy uncertainty or policy runtime error -> `blocked`
- budget uncertainty or budget runtime error -> `blocked`
- dispatch adapter failure -> `blocked`

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

## 9. Discord Adapter Contract

Allowed operations through owner ingress:
- `run_task*`
- `llm_*`
- `msg_*`
- status query commands (`query_project_status`, `query_agent_status`, `query_budget_status`)

Adapter behavior:
- maps Discord message metadata to canonical owner-command envelope
- submits only through governed owner ingress endpoint
- does not bypass policy, budget, or authority middleware

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

