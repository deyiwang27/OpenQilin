# OpenQilin - Agent Memory Model Specification

## 1. Scope
- Defines memory tiers, access scopes, and retrieval/write constraints.
- Source alignment:
  - `constitution/domain/SafetyPolicy.yaml`
  - `spec/infrastructure/StorageAndRetention.md`
  - `spec/governance/GovernanceArchitecture.md`

## 2. Tiers
- Hot, Warm, Cold

## 3. Tier Definitions and Defaults
| Tier | Purpose | TTL Default | Compression | Read-Only |
| --- | --- | --- | --- | --- |
| Hot | Active task/project working context | 24 hours | No | No |
| Warm | Summarized project and preference memory | 30 days | Yes | No |
| Cold | Archived historical memory snapshots | 365 days | Yes | Yes |

## 4. Memory Lifecycle Policies
- Snapshot-before-compression: required for warm/cold promotion.
- Cross-project isolation: memory retrieval must be scope-filtered by project.
- Deletion and purge:
  - routine TTL expiry follows retention transition rules.
  - destructive deletion override requires explicit Owner approval.
- Consistency:
  - operational source of truth remains structured stores; vectorized memory is a derived retrieval layer.

## 5. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| MEM-001 | Immutable execution logs MUST be append-only. | critical | Observability |
| MEM-002 | Memory tier transitions MUST follow configured TTL and lifecycle policies. | high | Administrator |
| MEM-003 | Cross-project memory isolation MUST be enforced for all reads and writes. | critical | Policy Engine |
| MEM-004 | Deletion overrides outside normal retention flow MUST require Owner approval. | critical | Change Control |
| MEM-005 | Snapshot artifacts MUST be created before compression or archival compaction. | high | Administrator |

## 6. Conformance Tests
- Unauthorized memory access is denied and logged.
- Hot memory expires or transitions after default TTL.
- Warm memory transitions to cold/archive with snapshot reference.
- Cross-project retrieval attempts without scope authorization are denied.
- Deletion override requests without Owner approval are rejected.
