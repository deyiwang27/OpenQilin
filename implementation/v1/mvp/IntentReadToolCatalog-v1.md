# OpenQilin Intent-Level Read Tool Catalog v1

Status: proposed implementation catalog
Last updated: 2026-03-13

## 1. Purpose

Define a complete set of intent-level **read-only** tools for grounded agent responses in MVP-aligned workflows.

These tools are the source-of-truth interface for LLM reasoning:
- primary truth: governed runtime DB/repositories
- secondary truth: governed project docs (`project_artifact*`)
- no free-form external facts for project/runtime questions

## 2. Grounding Contract (All Tools)

Every read tool must:
- enforce actor-role + scope checks before returning data
- fail closed on unauthorized or ambiguous access
- return deterministic source metadata for citations
- be traceable (trace_id, tool_call_id, request_id)

Standard response envelope:
- `decision`: `ok|denied`
- `error_code`: nullable
- `data`: tool-specific payload
- `sources`: array of source descriptors
  - `source_id` (citation key, for example `project:project_1`)
  - `source_kind` (`project_record|artifact|task|budget|audit|runtime`)
  - `version` or `updated_at`

## 3. MVP Use Case Matrix to Tool Families

### 3.1 Governance and Lifecycle (owner, ceo, cwo, auditor)
1. `get_project_lifecycle_state(project_id)`
- Returns current state, legal next transitions, and last transition metadata.

2. `get_project_transition_history(project_id, limit)`
- Returns append-only lifecycle transition records.

3. `get_proposal_discussion_thread(project_id, limit)`
- Returns proposal messages for `proposed` stage triad discussion.

4. `get_proposal_approval_matrix(project_id)`
- Returns triad approval status (`owner`, `ceo`, `cwo`) and missing approvers.

5. `get_completion_gate_status(project_id)`
- Returns completion prerequisites: report present, `cwo` approval, `ceo` approval, owner-notification evidence.

6. `get_project_activation_baseline_status(project_id)`
- Returns required baseline docs presence/hash status (`project_charter`, `scope_statement`, `budget_plan`, `success_metrics`, `workforce_plan`, `execution_plan`).

### 3.2 Budget and Risk Governance (owner, ceo, cwo, auditor)
1. `get_project_budget_snapshot(project_id)`
- Returns currency/quota totals, used, remaining, soft/hard threshold status.

2. `get_project_budget_burn_trend(project_id, window)`
- Returns time-bucket burn trend and threshold crossing markers.

3. `get_budget_alerts(project_id, status_filter, limit)`
- Returns active/recent budget alerts and remediation status.

4. `get_project_risk_register(project_id, limit)`
- Returns latest risk entries from governed risk artifacts and normalized DB risk views.

5. `get_project_risk_summary(project_id)`
- Returns severity distribution, top open risks, overdue mitigations.

### 3.3 Delivery and Execution (project_manager, ceo, cwo)
1. `get_project_execution_plan(project_id)`
- Returns latest execution plan artifact metadata + digest.

2. `get_project_milestone_status(project_id)`
- Returns milestone list, completion %, blocked milestones, due-date risk flags.

3. `get_project_task_board(project_id, status_filter, assignee_filter, limit)`
- Returns governed task queue summary (`queued|authorized|dispatched|blocked|completed|failed|cancelled`).

4. `get_task_details(task_id)`
- Returns task command/target/status/outcome details and dispatch metadata.

5. `get_project_progress_reports(project_id, limit)`
- Returns append-only progress report entries and latest delta summary.

6. `get_project_decision_log(project_id, limit)`
- Returns append-only decision log entries with actor and rationale.

7. `get_project_workforce_snapshot(project_id)`
- Returns active workforce bindings and mandatory-operation template status.

### 3.4 Document and Knowledge Access (all governed roles with policy scope)
1. `search_project_docs(project_id, query, artifact_types, limit)`
- Semantic/keyword search over governed project docs with scoped hits.

2. `get_project_doc_latest(project_id, artifact_type)`
- Returns latest version pointer/hash and content excerpt.

3. `get_project_doc_version_history(project_id, artifact_type, limit)`
- Returns version chain, authorship, timestamps, hashes.

4. `verify_project_doc_integrity(project_id, artifact_type)`
- Returns pointer/hash/file verification result.

5. `get_project_doc_policy_status(project_id)`
- Returns per-type cap usage, total cap usage, and writeability by lifecycle stage.

### 3.5 Communication and Channel Governance (owner, administrator, auditor)
1. `get_chat_class_policy(chat_class, project_id)`
- Returns allowed roles, read/write mode, lock state.

2. `get_channel_membership_effective(guild_id, channel_id, project_id)`
- Returns effective role membership for current lifecycle state.

3. `get_identity_channel_mapping(actor_external_id, guild_id, channel_id)`
- Returns mapping status (`pending|verified|revoked`) and trust metadata.

4. `get_specialist_touchability_status(project_id)`
- Returns whether specialist direct-touch is allowed (expected deny in MVP).

### 3.6 Audit, Compliance, and Evidence (auditor, administrator, owner)
1. `get_audit_event_stream(project_id, event_types, limit)`
- Returns immutable audit events with trace and actor context.

2. `get_trace_timeline(trace_id)`
- Returns span timeline (`owner_ingress`, `task_orchestration`, `policy_evaluation`, etc.).

3. `get_policy_decision_evidence(task_id)`
- Returns policy version/hash/rule_ids and decision outcome payload.

4. `get_budget_decision_evidence(task_id)`
- Returns budget decision codes, budget version, threshold context.

5. `get_dispatch_denial_evidence(task_id)`
- Returns deny source/error_code/retryability/dead-letter linkage.

6. `get_mvp_acceptance_evidence_index(project_id)`
- Returns linked artifact paths/check results for acceptance workflows.

### 3.7 Runtime and Operations (administrator, owner read-only)
1. `get_runtime_health_snapshot()`
- Returns service health (`api_app`, workers, bot worker), startup validation status.

2. `get_runtime_recovery_snapshot()`
- Returns restored task counts, idempotency reconstruction summary, institutional-agent bootstrap summary.

3. `get_llm_provider_runtime_status()`
- Returns active provider backend, model aliases, retry config, recent failure counters.

4. `get_dead_letter_summary(window)`
- Returns communication dead-letter counts and top failure codes.

## 4. Minimum Tool Set for Immediate Grounded LLM Quality

Implement first (priority order):
1. `get_project_lifecycle_state`
2. `get_project_budget_snapshot`
3. `get_project_milestone_status`
4. `get_project_task_board`
5. `search_project_docs`
6. `get_project_doc_latest`
7. `get_completion_gate_status`
8. `get_project_workforce_snapshot`
9. `get_audit_event_stream`
10. `get_dispatch_denial_evidence`

## 5. Role-to-Tool Access Baseline (MVP)

- `owner`: broad read access except internal secrets; no direct specialist command mutation
- `ceo`: strategic, portfolio, lifecycle, budget, delivery reads
- `cwo`: workforce, delivery, lifecycle, completion-chain reads
- `auditor`: full audit/compliance/budget evidence reads
- `administrator`: runtime/ops/integrity/audit reads
- `project_manager`: project-scoped delivery/docs/workforce reads only

All access remains policy-evaluated and fail-closed.

## 6. Tool Invocation Policy for LLM

For project/runtime factual questions:
1. call relevant read tools first
2. synthesize only from returned `data` + `sources`
3. attach citations using `source_id`
4. if no sufficient evidence: respond `INSUFFICIENT_EVIDENCE` with best available source references

## 7. Non-Goals

- No direct SQL generation by LLM
- No unrestricted repository traversal by LLM
- No write/mutation operations in this read-tool catalog
