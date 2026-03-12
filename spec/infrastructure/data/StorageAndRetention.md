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
2. Validate per-type document cap before file create.
3. Write file revision under `${OPENQILIN_SYSTEM_ROOT}/projects/<project_id>/`.
4. Persist/update DB metadata pointer + hash atomically.
5. Emit immutable audit event for create/update/archive actions.

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

## 7. Conformance Tests
- Expired operational data follows retention transition policy.
- Compression attempts without snapshot references are rejected.
- Deletion override without owner approval is rejected.
- Cross-project storage retrieval without authorization is denied.
- Project-file writes outside canonical system root are denied.
- Pointer/hash mismatch between DB metadata and file content is denied.
