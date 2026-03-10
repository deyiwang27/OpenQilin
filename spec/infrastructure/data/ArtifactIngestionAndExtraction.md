# OpenQilin - Artifact Ingestion and Extraction Specification

## 1. Scope
- Defines ingestion of project artifacts (including Markdown documents) into relational storage.
- Defines extraction of structured fields from artifact content for deterministic runtime usage.
- Defines failure/replay behavior for ingestion and extraction pipelines.

## 2. Pipeline Separation
- `document_ingest` pipeline:
  - source: file/git/document updates
  - target: artifact and knowledge tables in relational store
  - note: not database CDC
- `relational_cdc` pipeline:
  - source: relational transaction log / outbox events
  - target: derived stores (vector index cache invalidation, optional external memory sync)

## 3. Ingestion Contract
Input envelope:
- `source_type` (`git|api|system`)
- `source_ref`
- `artifact_type`
- `scope_type`
- `scope_id`
- `content_md`
- `author_role`
- `author_agent_id`
- `trace_id`
- `ingested_at`

Output artifacts:
- upsert `project_artifact` record
- insert `project_artifact_version` record
- append ingestion event (`status_event` or outbox record)

## 4. Extraction Contract
Target extraction blocks:
- objectives
- pathways
- risks
- metrics
- requirements
- acceptance criteria
- dependency references

Extraction behavior:
- map extracted fields into normalized relational tables.
- keep extraction deterministic for same input version.
- persist extraction metadata (`extractor_version`, `schema_version`, `confidence`).

## 5. Conflict and Authority Rules
- State-machine fields in relational tables are authoritative for lifecycle control.
- Artifact narrative fields are authoritative for rationale/context narrative.
- If extraction conflicts with protected state transitions, transition change is rejected and event is emitted.

## 6. Idempotency and Replay
- Re-processing the same `artifact_id + version_no` must be idempotent.
- Consumers must checkpoint offsets for deterministic replay.
- Recovery after failure resumes from last valid checkpoint.

## 7. Failure Behavior
- parse failure: reject artifact version and emit validation event.
- extraction failure: keep artifact version, mark extraction status failed, retry with backoff.
- persistent pipeline failure: pause pipeline and escalate per governance policy.

## 8. Security and Compliance
- sanitize and classify sensitive content before indexing.
- apply project-scope isolation on all extraction writes.
- log immutable audit metadata for governance-relevant artifact changes.

## 9. Conformance Tests
- Duplicate ingest of same artifact version does not duplicate writes.
- Invalid artifact payload fails validation deterministically.
- Extraction output is consistent for same input and extractor version.
- Cross-project artifact ingestion attempt is denied without authorization.
