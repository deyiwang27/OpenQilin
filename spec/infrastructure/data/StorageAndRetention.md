# OpenQilin - Storage and Retention Specification

## 1. Scope
- Defines storage classes, retention windows, archival policy, and retrieval constraints.
- Defines deterministic retention lifecycle for logs, memory artifacts, and derived summaries.

## 2. Storage Classes
- operational, audit, archive

Project documentation storage boundary (v1):
- runtime-generated project files must be stored outside repository source tree
- canonical root: `${OPENQILIN_SYSTEM_ROOT}/projects/<project_id>/`
- DB is authoritative for project state/control fields; file store is authoritative for rich-text project content
- governed writes require DB pointer/hash synchronization (`storage_uri`, `content_hash`)
- deterministic file path pattern:
  - `${OPENQILIN_SYSTEM_ROOT}/projects/<project_id>/docs/<artifact_type>/<artifact_type>--v<revision_no>.md`

## 3. Retention Defaults (v1)
| Data Class | Tier | TTL Default | Compression | Read-Only |
| --- | --- | --- | --- | --- |
| Active task/project context | operational/hot | 24 hours | No | No |
| Summarized historical context | operational/warm | 30 days | Yes | No |
| Historical snapshots and archived logs | archive/cold | 365 days | Yes | Yes |
| Audit events | audit | policy-defined long retention | Optional | Yes (append-only) |

## 4. Retention and Deletion Policy
- Snapshot-before-compression is mandatory for warm/cold compaction.
- Retention transitions must preserve traceability links (`source_ref`, `snapshot_id`, `policy_version`).
- Purge/deletion behavior:
  - automatic retention transitions are allowed by policy.
  - destructive deletion override requires explicit owner approval.
- Cross-project isolation is mandatory in all storage queries and archive retrieval.

## 5. Operational Workflow
1. Ingest operational records.
2. Perform scheduled compaction/summarization.
3. Create snapshot artifact.
4. Transition to next retention tier.
5. Record transition event in immutable audit log.

Project documentation workflow:
1. Validate artifact type against allowed project document policy.
2. Validate per-type cap and project total active-document cap before file create.
3. Validate role/stage write permissions.
4. Write file revision under canonical project path convention.
5. Persist/update DB metadata pointer + `sha256` content hash atomically.
6. Emit immutable audit event for create/update/archive actions.

Integrity-failure behavior:
- write/update/archive operations fail closed.
- reads may serve last verified version when latest integrity check fails.
- every integrity denial emits immutable audit evidence.

## 6. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| STR-001 | Audit data MUST be immutable and retained per policy. | critical | administrator |
| STR-002 | Snapshot artifacts MUST exist before compression or archival compaction. | high | administrator |
| STR-003 | Retention transitions MUST preserve traceability metadata. | high | Observability |
| STR-004 | Destructive deletion overrides MUST require owner approval. | critical | Change Control |
| STR-005 | Storage access MUST enforce project isolation boundaries. | critical | Policy Engine |
| STR-006 | Runtime-generated project files MUST live under the canonical system root outside repository source tree. | high | administrator |
| STR-007 | Project document create/update MUST fail closed when pointer/hash sync validation fails. | critical | Runtime |
| STR-008 | Project document creates MUST fail closed when per-type or total active-document cap is exceeded. | critical | Runtime |
| STR-009 | Project document writes MUST use deterministic typed path conventions under canonical root. | high | administrator |
| STR-010 | On integrity failure, writes MUST be denied and immutable audit evidence MUST be emitted; reads MAY return last verified version. | high | auditor |

## 7. Conformance Tests
- Expired operational data follows retention transition policy.
- Compression attempts without snapshot references are rejected.
- Deletion override without owner approval is rejected.
- Cross-project storage retrieval without authorization is denied.
- Project-file writes outside canonical system root are denied.
- Pointer/hash mismatch between DB metadata and file content is denied.
- Over-cap project document create attempts are denied (per-type and total cap).
- Integrity-failure read path returns last verified version with audit evidence.
