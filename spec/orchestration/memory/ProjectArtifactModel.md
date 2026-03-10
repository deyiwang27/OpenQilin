# OpenQilin - Project Artifact Model Specification

## 1. Scope
- Defines project/milestone/task narrative artifacts used alongside structured runtime state.
- Defines artifact taxonomy, ownership, lifecycle, and write/read boundaries for agents.

## 2. Design Intent
- Structured status/state remains authoritative in relational tables.
- Artifacts carry narrative context, rationale, and working notes.
- Artifacts are versioned and trace-linked to runtime events.

## 3. Canonical Artifact Types
| Artifact Type | Primary Owner | Scope | Purpose |
| --- | --- | --- | --- |
| `project_charter` | `owner`, `ceo`, `cwo`, `cso` | project | objectives, pathways, risks, success metrics |
| `project_strategy` | `project_manager` | project | plan updates, execution strategy |
| `project_risk_register` | `cso`, `domain_lead` | project | risk tracking and mitigations |
| `project_metric_plan` | `ceo`, `project_manager` | project | KPI/metric definitions and targets |
| `milestone_plan` | `project_manager`, `domain_lead` | milestone | milestone-specific deliverables and sequencing |
| `task_brief` | `project_manager`, `domain_lead` | task | requirements, acceptance criteria, dependencies |
| `task_execution_notes` | `specialist` | task | execution notes, findings, blockers |
| `task_handover_report` | `specialist` | task | completion summary and handoff context |
| `project_retrospective` | `project_manager`, `ceo` | project | closure review and lessons learned |

## 4. Artifact Data Contract
Minimum artifact record:
- canonical table: `project_artifact`
- `artifact_id`
- `artifact_type`
- `scope_type` (`project|milestone|task`)
- `scope_id`
- `current_version`
- `status`
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

## 7. Synchronization Semantics
- Artifact updates may produce structured extractions (objectives/risks/requirements/metrics).
- Structured extraction output updates normalized relational tables.
- On extraction conflicts, relational state-machine fields remain authoritative.

## 8. Conformance Tests
- Unauthorized role cannot create or update restricted artifact types.
- Every artifact version write includes `trace_id`.
- Project/task archived state enforces artifact read-only behavior.
- Artifact update does not directly perform illegal project/task state transitions.
