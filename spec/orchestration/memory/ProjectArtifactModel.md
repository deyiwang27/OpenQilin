# OpenQilin - Project Artifact Model Specification

## 1. Scope
- Defines governed project-level narrative artifacts used alongside structured runtime state.
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

## 3. Canonical Artifact Types (MVP-Strict Enum)
| Artifact Type | Primary Owner | Scope | Required For `approved -> active` | Per-Type Active Cap | Mutability Model |
| --- | --- | --- | --- | --- | --- |
| `project_charter` | `owner`, `ceo`, `cwo` | project | yes | 1 | versioned update |
| `scope_statement` | `owner`, `ceo`, `cwo` | project | yes | 1 | versioned update |
| `budget_plan` | `owner`, `ceo`, `cwo` | project | yes | 1 | versioned update |
| `success_metrics` | `owner`, `ceo`, `cwo` | project | yes | 1 | versioned update |
| `workforce_plan` | `cwo` | project | yes | 1 | versioned update |
| `execution_plan` | `project_manager` | project | yes | 1 | versioned update |
| `decision_log` | `project_manager`, `cwo`, `ceo` | project | no | 4 | append-only entries |
| `risk_register` | `project_manager` | project | no | 3 | versioned update |
| `progress_report` | `project_manager` | project | no | 6 | append-only entries |
| `completion_report` | `project_manager` | project | no | 1 | append-only final report |

MVP strictness:
- Only the above 10 `artifact_type` values are valid in first MVP.
- No per-project artifact-type overrides in MVP.

## 3.1 MVP Document Cap Policy
Per project caps:
- Per-type active-document caps are enforced as listed above.
- Total active-document cap per project: `20`.

Policy behavior:
- Creating documents beyond per-type or total cap is denied fail-closed.
- Cap checks apply to active artifact records, not historical versions.
- Revisions increment `version_no` on existing artifacts and remain trace-linked.
- `completed|terminated|archived` projects are read-only for all project documentation types.

## 3.2 Activation Baseline Requirement
Before `approved -> active` transition:
- Initial version (`version_no=1`) must exist and be finalized for:
  - `project_charter`
  - `scope_statement`
  - `budget_plan`
  - `success_metrics`
  - `workforce_plan`
  - `execution_plan`
- Finalization evidence is required in governance records prior to activation.

## 4. Artifact Data Contract
Minimum artifact record:
- canonical table: `project_artifact`
- `artifact_id`
- `artifact_type`
- `scope_type` (`project` in MVP v0.1)
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
- `completion_report` is immutable after publish (no in-place updates).

## 6. Governance and Access
- Artifact writes must pass policy checks for role + scope.
- Artifact updates cannot bypass state-machine constraints for project transitions.
- Sensitive artifact reads/writes are auditable with `trace_id`.
- Strict fixed access matrix is enforced in code/spec for MVP (no project-level overrides).
- Stage-aware write contract:
  - writable project states: `proposed|approved|active|paused`
  - read-only project states: `completed|terminated|archived`
- `project_manager` write contract:
  - write allowed only when project state is `active`
  - direct-write types in `active`: `execution_plan`, `risk_register`, `decision_log`, `progress_report`
  - conditional-write types in `active` require `cwo+ceo` approval evidence: `scope_statement`, `budget_plan`, `success_metrics`
  - cannot directly edit `project_charter` or `workforce_plan`
- `cwo` and `ceo` may approve and apply controlled updates in `proposed|approved|active|paused`.
- `specialist` has no direct write path for project documentation types in MVP.

## 7. Synchronization Semantics
- Artifact updates may produce structured extractions (objectives/risks/requirements/metrics).
- Structured extraction output updates normalized relational tables.
- On extraction conflicts, relational state-machine fields remain authoritative.
- DB pointer (`storage_uri`) and file hash (`content_hash`) must remain synchronized atomically.
- Hash mismatch between DB and file-backed content is treated as integrity failure and blocks mutation until reconciled.
- `content_hash` uses `sha256` for MVP.
- On integrity failure:
  - write/update/archive operations are denied fail-closed
  - reads may return last verified version metadata/content
  - runtime must emit immutable audit event with denial reason

## 8. Conformance Tests
- Unauthorized role cannot create or update restricted artifact types.
- Every artifact version write includes `trace_id`.
- Document cap policy blocks per-type and total-cap over-limit create attempts.
- Project archived state enforces artifact read-only behavior.
- Artifact update does not directly perform illegal project state transitions.
- DB pointer/hash mismatch is detected and denied for governed writes.
