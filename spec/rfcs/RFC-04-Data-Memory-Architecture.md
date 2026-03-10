# OpenQilin - RFC 04: Data and Memory Architecture

## 1. Scope
Domains in this RFC:
- PostgreSQL as authoritative system-of-record for runtime/governance entities
- Markdown corpus role in memory architecture
- pgvector + RAG retrieval over document and memory content
- Redis role for hot-path caching, idempotency, and bounded queueing
- Mem0 role as optional memory optimization layer
- Change propagation model: document ingestion + relational CDC + replay/rebuild

## 2. Investigation Questions
- Should PostgreSQL own logs, project/agent/task/event state, registries, authority dimensions, and constitution snapshots in v1?
- Is Markdown a correct "hot memory" source, or should it be treated as governed document knowledge input?
- How should pgvector + RAG over Markdown and operational memory be structured for deterministic retrieval?
- Is "CDC from files to PostgreSQL" the correct model, or should file changes use document-ingestion events and DB CDC be reserved for relational changes?
- What should Redis own for v1 (cache, idempotency, stream queue), and what should it explicitly not own?
- How should Mem0 be integrated without creating a second source-of-truth?
- How should agents query PostgreSQL safely for structured retrieval during execution?

## 3. Candidate Evaluation Matrix
| Domain | Candidate | Decision | Confidence | Conformance Impact | Notes |
| --- | --- | --- | --- | --- | --- |
| source-of-record db | PostgreSQL | adopt (v1 authoritative) | high | strong positive | ACID, relational integrity, RLS, and partitioning support governance and audit requirements. |
| document memory source | Markdown files | adopt as governed knowledge corpus, not hot memory store | high | positive | Keep docs human-governed; ingest to relational + vector layers for runtime retrieval. |
| vector index | pgvector | adopt (v1 default) | high | positive | Vector search in Postgres with exact and ANN index options (HNSW/IVFFlat). |
| cache/queue/coordination | Redis | adopt (bounded role) | high | positive | Use for TTL cache, idempotency keys, and optional stream-based async workers. |
| memory optimizer | Mem0 | adopt_later (optional overlay) | medium | neutral-positive | Valuable layered/graph memory; keep Postgres + pgvector authoritative in v1. |
| consistency pipeline | dual pipeline: doc_ingest + relational CDC | adopt | high | strong positive | File changes ingest into DB events; DB CDC streams derived updates and replay. |
| data lifecycle | retention/deletion with replayable derivation | adopt | high | strong positive | Derived stores rebuildable from source data and checkpoints. |

## 4. Required Deliverables
- Canonical data/memory reference model with authoritative and derived boundaries.
- Revised interpretation of Markdown and CDC in architecture terms.
- Read/write contracts including agent read access to PostgreSQL under governance.
- Redis and Mem0 boundary decisions with anti-patterns.
- Adopt/defer/adopt_later decisions and migration notes.

## 5. Your Proposed Model: Assessment
| Proposed idea | Assessment | Adjustment |
| --- | --- | --- |
| PostgreSQL as main DB for logs, state, registry, dimensions, constitution data | correct | Keep this as authoritative system-of-record. |
| Markdown files as hot memory source | partially correct | Treat Markdown as governed source documents, not runtime hot memory. |
| pgvector + RAG for warm memory on Markdown | correct | Use chunked document tables + embeddings in Postgres/pgvector. |
| CDC from files to PostgreSQL as cold memory transition | incorrect terminology | Use document-ingestion events for files; reserve CDC for DB log-based change streaming. |
| Redis + Mem0 for cache/retrieval optimization | correct with boundaries | Redis in v1; Mem0 optional overlay after baseline stability. |
| Agents query PostgreSQL for required data | correct | Enforce query boundary with role-scoped views/RLS and audited query classes. |

## 6. Recommended Technical Solution (v1)

### 6.1 Data Ownership and Tiers
- Authoritative (`postgresql`):
  - project, agent, task, event, message, policy snapshot, authority mappings
  - append-only execution/audit logs
  - canonical memory facts and document metadata
- Derived:
  - pgvector embeddings/indexes
  - Redis cache keys, idempotency windows, optional stream queues
  - optional Mem0 stores (if enabled)

Tier semantics:
- hot: Redis + in-flight runtime context (short TTL)
- warm: Postgres + pgvector retrieval layer
- cold: partitioned/archive Postgres history and snapshots

### 6.2 Markdown and Document Memory
Use Markdown as a governed knowledge corpus:
- constitution and governance text
- SOP/runbooks
- curated project knowledge

Ingestion flow:
1. File/Git change detected.
2. Parser creates normalized `knowledge_document` + `knowledge_chunk` rows in Postgres.
3. Embeddings computed and written to `knowledge_embedding` (`pgvector`).
4. `document_ingest_event` appended for observability and replay.

Why:
- Runtime "hot" memory needs low-latency, scoped, high-churn storage.
- Markdown files are excellent human-editable sources but not ideal as concurrent hot runtime state.

### 6.3 CDC and Replay Model
Use two separate mechanisms:
- Document ingestion pipeline (file changes -> DB writes): not WAL CDC.
- Relational CDC (DB changes -> downstream sync): logical decoding/connector path.

Recommended pattern:
- Transactional writes to business tables + `outbox_events`.
- CDC consumers update derived stores (Redis invalidation, optional Mem0 sync).
- Consumers are idempotent and replayable via sequence/LSN checkpoints.

### 6.4 Query Model for Agents
- Agents may query PostgreSQL, but through governed access profiles:
  - approved read views/materialized views by role
  - row-level security for project isolation
  - predeclared query classes for high-risk entities
  - full audit for sensitive query categories

Default retrieval order:
1. Structured PostgreSQL query (state, authority, budget, registry).
2. pgvector retrieval for unstructured context.
3. Optional Mem0 retrieval augmentation (if enabled).

### 6.5 Redis and Mem0 Boundaries
Redis (v1 adopt):
- cache-aside for expensive reads
- idempotency/replay suppression keys
- short-lived workflow coordination and optional streams workers

Redis anti-patterns:
- do not treat Redis as long-term source-of-record
- do not store governance-critical immutable audit as Redis-only

Mem0 (adopt_later):
- use for personalization/episodic/graph augmentation
- keep writes filtered by policy and PII controls
- no authoritative decision state in Mem0

## 7. Reference Schema Extensions (v1)
Add to relational model:
- `knowledge_document` (`document_id`, `source_path`, `source_version`, `hash`, `scope`, `ingested_at`)
- `knowledge_chunk` (`chunk_id`, `document_id`, `chunk_index`, `content`, `token_count`)
- `knowledge_embedding` (`chunk_id`, `embedding vector(n)`, `embedding_model`, `created_at`)
- `outbox_events` (`event_id`, `aggregate_type`, `aggregate_id`, `payload`, `created_at`)
- `sync_checkpoint` (`consumer_name`, `lsn_or_offset`, `updated_at`)

## 8. Risks and Mitigations
- Risk: ambiguous CDC scope causes inconsistent pipelines.
- Mitigation: enforce terminology and architecture split (`document_ingest` vs `relational_cdc`).

- Risk: duplicated side effects after crash/restart.
- Mitigation: idempotency keys and replay checkpoints (LSN/offset) in consumers.

- Risk: cross-project data leakage in agent queries.
- Mitigation: RLS + policy-scoped views + audited sensitive query classes.

- Risk: memory drift between source and derived indexes.
- Mitigation: rebuildable derived indexes and periodic reconciliation jobs.

## 9. Recommendation Summary
Adopt now:
- PostgreSQL as authoritative source-of-record
- Markdown as governed input corpus (not hot memory)
- pgvector in Postgres for vector retrieval
- Redis with bounded operational role
- dual pipeline model: `document_ingest` + `relational_cdc`

Adopt later / optional:
- Mem0 as augmentation layer after v1 data contracts stabilize

Defer:
- Any architecture where Redis/Mem0 become independent authorities for governance-critical state

## 10. Sources (Primary)
- PostgreSQL row security: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
- PostgreSQL logical decoding concepts: https://www.postgresql.org/docs/current/logicaldecoding-explanation.html
- PostgreSQL partitioning: https://www.postgresql.org/docs/current/ddl-partitioning.html
- PostgreSQL JSONB indexing: https://www.postgresql.org/docs/16/datatype-json.html
- PostgreSQL GIN index operator classes: https://www.postgresql.org/docs/current/gin.html
- PostgreSQL text search functions/operators: https://www.postgresql.org/docs/current/functions-textsearch.html

- Debezium PostgreSQL connector (stable): https://debezium.io/documentation/reference/stable/connectors/postgresql.html
- Debezium outbox event router: https://debezium.io/documentation/reference/stable/transformations/outbox-event-router.html

- pgvector repository/README: https://github.com/pgvector/pgvector

- Redis key eviction policies: https://redis.io/docs/latest/develop/reference/eviction/
- Redis persistence: https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/
- Redis streams intro: https://redis.io/docs/latest/develop/data-types/streams/
- Redis `XREADGROUP`: https://redis.io/docs/latest/commands/xreadgroup/
- Redis `XACK`: https://redis.io/docs/latest/commands/xack/

- Mem0 memory types: https://docs.mem0.ai/core-concepts/memory-types
- Mem0 entity-scoped memory: https://docs.mem0.ai/platform/features/entity-scoped-memory
- Mem0 graph memory: https://docs.mem0.ai/platform/features/graph-memory

## 11. Evidence Strength Notes
- High confidence: PostgreSQL/pgvector/Redis core boundaries, CDC semantics, and RLS-based isolation.
- Medium confidence: exact adoption timing and ROI for Mem0 in your v1/v1.1 path.
- Inference note: the recommendation to classify Markdown as governed source (not hot runtime state) is an architecture inference based on consistency, concurrency, and replay requirements from the cited database/streaming capabilities.
