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
- `agent_registry`
- `execution_logs`
- `metrics_store`
- `messages`
- `dimension_project_state`
- `dimension_agent_state`
- `dimension_tools`
- `lookup_roles`
- `lookup_memory_levels`

## 4. Entity Contracts (Required Fields)
### 4.1 `project_container`
- `project_id` (PK)
- `state`
- `budget_allocation`
- `constitution_policy_version`
- `created_at`
- `updated_at`

### 4.2 `agent_registry`
- `agent_id` (PK)
- `project_id` (FK, nullable for global roles)
- `role_type`
- `state`
- `base_model`
- `tool_bindings`
- `memory_scope`
- `autonomy_level`
- `budget_limit`
- `created_at`

### 4.3 `execution_logs` (append-only)
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

### 4.4 `metrics_store`
- `metric_id` (PK)
- `project_id` (FK)
- `agent_id` (FK)
- `token_usage`
- `api_calls`
- `execution_duration`
- `review_loops`
- `timestamp`

### 4.5 `messages`
- `message_id` (PK)
- `sender_id`
- `recipient_ids`
- `project_id` (nullable)
- `message_type`
- `priority`
- `content`
- `timestamp`
- `delivery_status`

## 5. State Dimensions
- `dimension_project_state`: proposed, approved, active, paused, completed, terminated, archived
- `dimension_agent_state`: created, active, paused, retired, archived

## 6. Schema and Consistency Requirements
- Authoritative state lives in relational store.
- Derived memory/vector layers must remain consistent with source records via change propagation.
- Every mutable entity update must include `updated_at` and actor provenance.

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
