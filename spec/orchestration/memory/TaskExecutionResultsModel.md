# OpenQilin - Task Execution Results Model Specification

## 1. Scope
- Defines task-scoped output records produced by `specialist` agents during task execution.
- Distinct from project-level `ProjectArtifactModel` artifacts: task execution results are ephemeral task outputs, not governed project documentation.
- Resolves the Specialist write-path conflict: Specialist writes `task_execution_results`, NOT project artifact types (see `ProjectArtifactModel §6`).

## 2. Design Intent
- Specialist agents produce task outputs that need to be traceable and readable by PM and DL.
- These outputs must not enter the project artifact lifecycle (no versioning, no state machine, no per-type caps).
- PM reads and synthesizes `task_execution_results` into project artifact types (e.g. `progress_report`, `decision_log`) as part of PM's write authority.

## 3. Schema

Canonical table: `task_execution_results`

| Field | Type | Description |
| --- | --- | --- |
| `result_id` | uuid | Primary key |
| `task_id` | uuid | FK → `tasks.task_id` |
| `project_id` | uuid | FK → `projects.project_id` |
| `specialist_agent_id` | uuid | FK → `agent_registry.agent_id` |
| `output_type` | varchar | Enum: `analysis`, `draft`, `data`, `code`, `recommendation`, `summary`, `other` |
| `content` | text | Execution output content (markdown or structured text) |
| `content_hash` | varchar(64) | SHA-256 of content at write time |
| `trace_id` | uuid | Originating trace |
| `created_at` | timestamptz | Write timestamp |
| `finalized_at` | timestamptz | Null until task completes; set on task terminal transition |

## 4. Immutability and Lifecycle

- `task_execution_results` records are **immutable after task completion** (`finalized_at` is set on task terminal state transition: `completed` or `failed`).
- Before task completion, Specialist may append new result records for the same task (one record per execution step); in-place update of existing records is not permitted.
- When the parent project reaches `completed`, `terminated`, or `archived` state, all associated `task_execution_results` become read-only permanently.

## 5. Access Control

| Role | Read | Write |
| --- | --- | --- |
| `specialist` | own task only | own task only (before finalization) |
| `domain_leader` | scoped project tasks | — |
| `project_manager` | all project tasks | — |
| `auditor` | all | — |
| `owner` | all | — |
| `ceo`, `cwo`, `cso` | summary views only | — |
| `administrator` | all (integrity ops) | — |

## 6. PM Synthesis Path

- PM reads `task_execution_results` for completed tasks within the project and synthesizes findings into project artifact types:
  - `progress_report` — aggregates task completion summaries
  - `decision_log` — records PM decisions made in response to task outputs
  - `risk_register` — updates domain risks identified in task results
- PM must cite source `result_id` values in the artifact `change_reason` field when synthesizing.
- Synthesis is PM's responsibility; DL may provide review input before PM finalizes the synthesis.

## 7. Behavioral Violation Path

- If a `task_execution_results` record contains content that violates scope, policy, or behavioral constraints, PM or DL flags it for Auditor review.
- Auditor may attach a `behavioral_violation` finding to the `result_id` in `audit_events`.
- Specialist behavioral violations follow the ESC-008 path if PM is involved in the violation.

## 8. Normative Rule Bindings
- `AUTH-001`: Specialist write is bounded to own task only.
- `ORCH-001`, `ORCH-002`
- `AUD-001`: All writes include `trace_id`.
- `ESC-008`: PM violation path bypasses PM.

## 9. Conformance Tests
- Specialist cannot write `task_execution_results` for a task not assigned to it.
- Specialist cannot update a finalized result record.
- PM can read all task execution results within its project scope.
- Auditor can attach behavioral violation findings to result records.
- Content hash mismatch between stored record and computed hash is treated as integrity failure.
