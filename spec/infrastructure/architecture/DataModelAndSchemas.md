# OpenQilin - Data Model and Schemas Specification

## 1. Scope
- Defines canonical entities and event envelope schemas.
- Defines minimum relational data substrate and reference dimensions for deterministic runtime behavior.

## 2. Canonical Event Envelope
```json
{
  "schema_version": "string",
  "event_id": "uuid",
  "event_type": "string",
  "timestamp": "RFC3339",
  "trace_id": "uuid",
  "policy_version": "string",
  "policy_hash": "string",
  "rule_ids": ["string"],
  "payload": {}
}
```

## 3. Canonical Relational Entities (Minimum v1)
- `project_container`
- `milestone`
- `task`
- `task_assignment`
- `task_requirement`
- `agent_registry`
- `execution_logs`
- `metrics_store`
- `messages`
- `project_artifact`
- `project_artifact_version`
- `knowledge_document`
- `knowledge_chunk`
- `knowledge_embedding`
- `outbox_events`
- `sync_checkpoint`
- `dimension_project_state`
- `dimension_milestone_state`
- `dimension_task_state`
- `dimension_agent_state`
- `dimension_tools`
- `lookup_roles`
- `lookup_memory_levels`

## 4. Entity Contracts (Required Fields)
### 4.1 `project_container`
- `project_id` (PK)
- `state`
- `proposal_revision_no`
- `budget_allocation`
- `budget_currency_total`
- `budget_quota_total`
- `budget_currency_used`
- `budget_quota_used`
- `charter_storage_uri`
- `charter_content_hash`
- `metric_plan_storage_uri`
- `metric_plan_content_hash`
- `constitution_policy_version`
- `created_at`
- `updated_at`

### 4.2 `milestone`
- `milestone_id` (PK)
- `project_id` (FK)
- `state`
- `sequence_no`
- `due_at` (nullable)
- `created_at`
- `updated_at`

### 4.3 `agent_registry`
- `agent_id` (PK)
- `project_id` (FK, nullable for global roles)
- `role_type`
- `state`
- `base_model`
- `template_id`
- `template_version`
- `system_prompt_ref`
- `enabled`
- `tool_bindings`
- `memory_scope`
- `autonomy_level`
- `budget_limit`
- `created_at`

### 4.4 `task`
- `task_id` (PK)
- `project_id` (FK)
- `milestone_id` (FK, nullable)
- `state`
- `priority`
- `requested_by`
- `assigned_agent_id` (nullable)
- `idempotency_key`
- `created_at`
- `updated_at`

### 4.5 `task_assignment`
- `assignment_id` (PK)
- `task_id` (FK)
- `agent_id` (FK)
- `assigned_by`
- `assigned_at`
- `status`

### 4.6 `task_requirement`
- `requirement_id` (PK)
- `task_id` (FK)
- `requirement_type`
- `requirement_value`
- `is_mandatory`
- `created_at`
- `updated_at`

### 4.7 `execution_logs` (append-only)
- `log_id` (PK)
- `project_id` (FK)
- `agent_id` (FK)
- `trace_id`
- `intent`
- `decision_reasoning`
- `authority_source`
- `tool_call`
- `result`
- `outcome_evaluation`
- `budget_impact`
- `previous_state`
- `next_state`
- `timestamp`
- `checksum`

### 4.8 `metrics_store`
- `metric_id` (PK)
- `project_id` (FK)
- `agent_id` (FK)
- `token_usage`
- `api_calls`
- `execution_duration`
- `review_loops`
- `timestamp`

### 4.9 `messages`
- `message_id` (PK)
- `trace_id`
- `sender_id`
- `recipient_ids`
- `project_id` (nullable)
- `message_type`
- `priority`
- `content`
- `idempotency_key`
- `protocol` (`a2a|acp`)
- `channel_id`
- `channel_type`
- `trust_level`
- `policy_version`
- `policy_hash`
- `rule_ids`
- `attempt`
- `max_attempts`
- `dead_lettered` (boolean)
- `timestamp`
- `delivery_status`

### 4.10 `project_artifact`
- `artifact_id` (PK)
- `artifact_type`
- `scope_type` (`project|milestone|task`)
- `scope_id`
- `current_version`
- `status`
- `storage_uri`
- `content_hash`
- `created_at`
- `updated_at`

### 4.11 `project_artifact_version`
- `artifact_id` (FK)
- `version_no`
- `content_md`
- `summary_structured`
- `author_role`
- `author_agent_id`
- `change_reason`
- `trace_id`
- `created_at`

## 5. State Dimensions
- `dimension_project_state`: proposed, approved, active, paused, completed, terminated, archived
- `dimension_milestone_state`: planned, active, paused, blocked, completed, cancelled, archived
- `dimension_task_state`: created, queued, authorized, dispatched, running, completed, failed, cancelled, blocked
- `dimension_agent_state`: created, active, paused, retired, archived

## 6. Schema and Consistency Requirements
- Authoritative state lives in relational store.
- Derived memory/vector layers must remain consistent with source records via change propagation.
- Every mutable entity update must include `updated_at` and actor provenance.
- File/document ingestion and relational CDC are distinct pipelines; only relational changes are treated as CDC streams.
- Milestone and task states should use canonical values from their state-machine specs.
- Project rich-text documentation is file-backed under canonical system root; relational store tracks authoritative pointers and hashes.
- Runtime must fail closed on pointer/hash mismatch between relational metadata and file-backed project docs.

## 7. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| SCHEMA-001 | Every schema MUST carry explicit schema_version. | critical | Runtime |
| SCHEMA-002 | Execution logs MUST be append-only and checksum-verifiable. | critical | Observability |
| SCHEMA-003 | Project and agent states MUST map to canonical state dimensions. | high | Runtime |
| SCHEMA-004 | Runtime events and persistent records MUST be correlated via trace_id. | high | Runtime |
| SCHEMA-005 | Source-of-truth relational data and derived memory indexes MUST maintain consistency guarantees. | high | Infrastructure |

## 8. Conformance Tests
- Events missing schema_version are rejected.
- Writes missing required entity fields fail validation.
- Execution log mutation attempts are rejected.
- State values outside canonical dimensions are rejected.
- Records lacking trace correlation for governed actions fail validation.
