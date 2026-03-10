# OpenQilin - Data and Memory Operations Playbooks Specification

## 1. Scope
- Defines operational playbooks for data and memory continuity workflows.
- Covers documentation-grade procedures for replay, backfill, extraction failure handling, and core datastore recovery.

## 2. Playbook Catalog
- `PB-01` CDC replay and offset recovery
- `PB-02` Historical backfill and reindex
- `PB-03` Artifact extraction failure handling
- `PB-04` PostgreSQL recovery drill
- `PB-05` Redis recovery drill

## 3. PB-01 CDC Replay and Offset Recovery
Trigger:
- CDC consumer outage, offset corruption, or consistency gap.

Procedure:
1. Pause downstream derived writers.
2. Validate authoritative source checkpoint.
3. Restore last valid offset/checkpoint.
4. Replay in bounded batches with idempotency checks.
5. Reconcile row counts and integrity hashes.
6. Resume downstream consumers.

Exit criteria:
- No missing sequence windows.
- Replay idempotency verified.
- Reconciliation report attached to audit record.

## 4. PB-02 Historical Backfill and Reindex
Trigger:
- schema evolution, embedding version change, or derived index rebuild.

Procedure:
1. Freeze write-sensitive reindex targets.
2. Snapshot source tables and artifact versions.
3. Execute deterministic backfill by ordered windows.
4. Validate sample queries against baseline.
5. Promote rebuilt index and release freeze.

Exit criteria:
- Versioned index metadata updated.
- Query parity checks pass.
- Rollback pointer is retained.

## 5. PB-03 Artifact Extraction Failure Handling
Trigger:
- parse failure or repeated extraction failure from artifact pipeline.

Procedure:
1. Mark extraction status as failed with reason code.
2. Keep artifact version persisted.
3. Apply bounded retry with backoff.
4. Escalate if retries exceed threshold.
5. Record remediation outcome and extractor version.

Exit criteria:
- Failure is resolved or escalated with owner/ceo visibility per policy.
- No unauthorized state transition occurred from extraction conflict.

## 6. PB-04 PostgreSQL Recovery Drill
Trigger:
- scheduled recovery validation or incident recovery exercise.

Procedure:
1. Select restore point and capture restore objective.
2. Restore to isolated recovery environment.
3. Validate policy, task, and audit integrity datasets.
4. Run deterministic snapshot parity checks.
5. Document RTO/RPO results and remediation items.

Exit criteria:
- Restore objective met.
- Core governance and runtime tables validated.
- Evidence archived with immutable audit reference.

## 7. PB-05 Redis Recovery Drill
Trigger:
- scheduled resiliency drill or Redis state loss incident.

Procedure:
1. Validate persistence configuration and snapshots.
2. Restore Redis from approved backup path.
3. Rebuild ephemeral caches from authoritative stores.
4. Reconcile idempotency and queue markers.
5. Resume queue/coordination services.

Exit criteria:
- No unreconciled idempotency keys for active windows.
- Queue and cache services stable under smoke checks.

## 8. Evidence Requirements
Each playbook execution must emit:
- `trace_id`
- `playbook_id`
- `policy_version`
- `policy_hash`
- referenced `rule_ids`
- outcome status and timestamps

## 9. Normative Rule Bindings
- `STR-002`: snapshot-before-compression/compaction.
- `STR-003`: retention/replay transitions preserve traceability.
- `STR-005`: project isolation on storage reads/writes.
- `FRM-003`: validated restart artifacts before recovery resume.
- `FRM-005`: recovery actions emit immutable audit events.

## 10. Conformance Tests
- Replay/backfill runs are idempotent and auditable.
- Extraction failures do not mutate protected lifecycle state.
- Postgres and Redis drills produce evidence with RTO/RPO results.
- Recovery procedures fail closed when validation checks fail.
