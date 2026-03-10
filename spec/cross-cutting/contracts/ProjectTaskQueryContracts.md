# OpenQilin - Project and Task Query Contracts Specification

## 1. Scope
- Defines governed query and mutation contracts for project/milestone/task context access.
- Prevents arbitrary database access paths by runtime agents.

## 2. Design Principles
- Queries are contract-based, not ad hoc SQL.
- Role and scope constraints apply before query execution.
- Sensitive query classes require audit emission.

## 3. Canonical Read Contracts
- `get_project_snapshot(project_id)`
  - returns project state, key metrics, milestone summary, risk summary
- `get_milestone_plan(milestone_id)`
  - returns milestone state, dependencies, task summary, linked artifacts
- `get_task_brief(task_id)`
  - returns task requirements, acceptance criteria, dependencies, linked artifacts
- `get_task_runtime_context(task_id)`
  - returns task + project policy context and latest execution status
- `search_project_artifacts(project_id, query, filters)`
  - returns artifact versions and references under project scope

## 4. Canonical Write Contracts
- `append_task_note(task_id, content_md, trace_id)`
- `create_or_update_artifact(scope_type, scope_id, artifact_type, content_md, trace_id)`
- `request_task_state_transition(task_id, event, reason, trace_id)`
- `request_milestone_state_transition(milestone_id, event, reason, trace_id)`

## 5. Access Control
- Contract execution requires identity resolution and role authorization.
- Cross-project access is denied unless explicit policy authorization exists.
- High-impact write contracts require policy + budget gate checks where applicable.

## 6. Response Envelope
Minimum response fields:
- `trace_id`
- `contract_name`
- `status` (`ok|denied|error`)
- `policy_version`
- `policy_hash`
- `rule_ids`
- `data` or `error`

## 7. Operational Guarantees
- Idempotent writes for repeated calls with same `idempotency_key`.
- Deterministic paging/sorting for list/search contracts.
- Contract-level timeout and retry policy with no duplicate side effects.

## 8. Conformance Tests
- Calls without required scope are denied.
- Sensitive read/write contracts emit required audit metadata.
- Repeated idempotent write call does not duplicate side effects.
- Unauthorized state transition requests are rejected before mutation.
