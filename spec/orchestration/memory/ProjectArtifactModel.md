# OpenQilin - Project Artifact Model Specification

## 1. Scope
- Defines project/milestone/task narrative artifacts used alongside structured runtime state.
- Defines artifact taxonomy, ownership, lifecycle, and write/read boundaries for agents.

## 2. Design Intent
- Structured status/state remains authoritative in relational tables.
- Artifacts carry narrative context, rationale, and working notes.
- Artifacts are versioned and trace-linked to runtime events.
- Rich-text project documentation is file-backed; governance and lifecycle control fields remain DB-authoritative.

## 2.1 Canonical Storage Root (v1)
- Project-generated files must not be stored in the source repository tree.
- Canonical runtime root:
  - `${OPENQILIN_SYSTEM_ROOT}/projects/<project_id>/`
- Recommended local default:
  - `${HOME}/.openqilin/projects/<project_id>/`
- DB metadata must track file-backed records using:
  - `storage_uri`
  - `content_hash`
  - `revision_no`

## 3. Canonical Artifact Types
| Artifact Type | Primary Owner | Scope | Purpose |
| --- | --- | --- | --- |
| `project_proposal` | `owner`, `ceo`, `cwo` | project | proposal discussion baseline prior to approval |
| `project_charter` | `owner`, `ceo`, `cwo` | project | approved scope, objectives, pathways, risks, success metrics |
| `workforce_plan` | `cwo` | project | PM/DL template selection, llm profile binding, staffing rationale |
| `project_strategy` | `project_manager` | project | plan updates, execution strategy |
| `project_risk_register` | `cwo`, `project_manager`, `domain_lead` | project | risk tracking and mitigations |
| `project_metric_plan` | `ceo`, `project_manager` | project | KPI/metric definitions and targets |
| `milestone_plan` | `project_manager`, `domain_lead` | milestone | milestone-specific deliverables and sequencing |
| `task_brief` | `project_manager`, `domain_lead` | task | requirements, acceptance criteria, dependencies |
| `task_execution_notes` | `specialist` | task | execution notes, findings, blockers |
| `task_handover_report` | `specialist` | task | completion summary and handoff context |
| `project_retrospective` | `project_manager`, `ceo` | project | closure review and lessons learned |

## 3.1 MVP Document Type Policy and Volume Caps
Per project, first-MVP limits:
- `project_proposal`: max 1 active document
- `project_charter`: max 1 active document
- `workforce_plan`: max 1 active document
- `project_metric_plan`: max 1 active document
- `project_risk_register`: max 1 active document
- `project_strategy`: max 1 active document
- `milestone_plan`: max 20 active documents
- `task_brief`: max 500 active documents
- `task_execution_notes`: max 2000 active documents
- `task_handover_report`: max 500 active documents
- `project_retrospective`: max 1 active document

Policy behavior:
- Creating documents beyond cap is denied fail-closed.
- Revisions increment `version_no` on existing documents instead of creating new active records.
- Archived projects are read-only for all project documentation types.

## 4. Artifact Data Contract
Minimum artifact record:
- canonical table: `project_artifact`
- `artifact_id`
- `artifact_type`
- `scope_type` (`project|milestone|task`)
- `scope_id`
- `current_version`
- `status`
- `storage_uri`
- `content_hash`
- `created_at`
- `updated_at`

Minimum artifact version record:
- canonical table: `project_artifact_version`
- `artifact_id`
- `version_no`
- `content_md`
- `summary_structured`
- `author_role`
- `author_agent_id`
- `change_reason`
- `trace_id`
- `created_at`

## 5. Lifecycle
Artifact states:
- `draft`
- `active`
- `superseded`
- `archived`

Lifecycle rules:
- New artifacts start at `draft`.
- A published working version moves artifact state to `active`.
- Newer accepted version marks previous version `superseded`.
- Artifacts for archived projects become `archived` and read-only.

## 6. Governance and Access
- Artifact writes must pass policy checks for role + scope.
- Artifact updates cannot bypass state-machine constraints for project/task transitions.
- Sensitive artifact reads/writes are auditable with `trace_id`.
- `specialist` write authority is limited to task-scoped artifact types only.
- owner cannot directly mutate specialist-owned task execution artifacts.

## 7. Synchronization Semantics
- Artifact updates may produce structured extractions (objectives/risks/requirements/metrics).
- Structured extraction output updates normalized relational tables.
- On extraction conflicts, relational state-machine fields remain authoritative.
- DB pointer (`storage_uri`) and file hash (`content_hash`) must remain synchronized atomically.
- Hash mismatch between DB and file-backed content is treated as integrity failure and blocks mutation until reconciled.

## 8. Conformance Tests
- Unauthorized role cannot create or update restricted artifact types.
- Every artifact version write includes `trace_id`.
- Document cap policy blocks over-limit create attempts.
- Project/task archived state enforces artifact read-only behavior.
- Artifact update does not directly perform illegal project/task state transitions.
- DB pointer/hash mismatch is detected and denied for governed writes.
