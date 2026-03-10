# OpenQilin - Agent Memory Model Specification

## 1. Scope
- Defines memory tiers, access scopes, lifecycle controls, and CDC synchronization behavior.
- Source alignment:
  - `constitution/domain/SafetyPolicy.yaml`
  - `spec/infrastructure/data/StorageAndRetention.md`
  - `spec/infrastructure/architecture/DataModelAndSchemas.md`

## 2. Design Principles
- Source of record is structured persistence (`postgresql`), not vector index.
- Vector index is a derived retrieval layer and must be reproducible from source of record.
- Memory operations must preserve policy, scope, and audit constraints.
- Markdown/constitution documents are governed source corpus inputs; they are ingested into structured memory layers and are not the runtime hot-memory store.

## 3. Tiers
- `hot`
- `warm`
- `cold`

## 4. Tier Definitions and Defaults
| Tier | Purpose | TTL Default | Compression | Read-Only |
| --- | --- | --- | --- | --- |
| hot | Active task/project working context | 24 hours | no | no |
| warm | Summarized project and preference memory | 30 days | yes | no |
| cold | Archived historical memory snapshots | 365 days | yes | yes |

## 5. Lifecycle Policies
- Snapshot-before-compression is mandatory for warm/cold promotion.
- Cross-project retrieval must be scope-filtered by project.
- Routine deletion follows retention policies.
- Destructive deletion override requires explicit `owner` approval.

## 6. Memory CDC Pipeline (v1)
- Pipeline split:
  - `document_ingest`: file/git document changes -> normalized relational document tables.
  - `relational_cdc`: append-only relational event/store -> derived indexes/caches.
- Ordering: apply changes by monotonic source sequence.
- Replay: consumers must support restartable replay from committed checkpoint.
- Idempotency: repeated CDC events with same source event id must not duplicate memory writes.
- Failure recovery:
  - transient index failure -> retry with backoff.
  - persistent index failure -> pause sync and escalate to `administrator`.
  - checkpoint corruption -> recover from last valid snapshot and replay forward.

## 7. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| MEM-001 | Immutable execution logs MUST be append-only. | critical | observability |
| MEM-002 | Memory tier transitions MUST follow configured TTL and lifecycle policies. | high | administrator |
| MEM-003 | Cross-project memory isolation MUST be enforced for all reads and writes. | critical | policy_engine |
| MEM-004 | Deletion overrides outside normal retention flow MUST require `owner` approval. | critical | change_control |
| MEM-005 | Snapshot artifacts MUST be created before compression or archival compaction. | high | administrator |
| MEM-006 | CDC application MUST be idempotent and ordered by source sequence. | critical | memory_sync_runtime |
| MEM-007 | CDC checkpoint recovery MUST be deterministic and auditable. | high | memory_sync_runtime |

## 8. Conformance Tests
- Unauthorized memory access is denied and logged.
- Hot memory expires or transitions after default TTL.
- Warm memory transitions to cold/archive with snapshot reference.
- Cross-project retrieval attempts without scope authorization are denied.
- Deletion override requests without `owner` approval are rejected.
- CDC replay does not duplicate indexed memory entries.
- CDC recovery from checkpoint restores deterministic derived state.
