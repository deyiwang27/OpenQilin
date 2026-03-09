# OpenQilin - RFC 04: Data and Memory Architecture

## 1. Scope
Domains in this RFC:
- PostgreSQL as source-of-record
- Redis for cache/queue/coordination
- pgvector for vector indexing in Postgres
- Mem0 as optional memory layer
- CDC, replay, and index rebuild strategy

## 2. Investigation Questions
- What data ownership model should separate authoritative records from derived memory/indexes?
- How should PostgreSQL, Redis, and pgvector be combined for consistency, performance, and operational simplicity?
- What should Redis own in v1: cache only, queue only, coordination only, or a bounded combination?
- Where should Mem0 sit in the architecture: optional personalization layer, or core memory dependency?
- What is the required write/read path for deterministic behavior under retries, restarts, and partial failures?
- What retention, deletion, and PII controls are required across source data and derived memory stores?

## 3. Candidate Evaluation Matrix
| Domain | Candidate | Decision | Confidence | Conformance Impact | Notes |
| --- | --- | --- | --- | --- | --- |
| source-of-record db | PostgreSQL | pending | pending | pending | pending |
| cache/queue/coordination | Redis | pending | pending | pending | pending |
| vector index | pgvector | pending | pending | pending | pending |
| memory layer | Mem0 | pending | pending | pending | pending |
| consistency pipeline | CDC and replay model | pending | pending | pending | pending |
| data lifecycle | retention/deletion model | pending | pending | pending | pending |

## 4. Required Deliverables
- Canonical data/memory reference model: authoritative stores vs derived stores.
- Write/read path contract with idempotency and failure recovery behavior.
- Role of Redis in v1 with explicit anti-patterns and boundaries.
- Mem0 integration decision (adopt/defer/adopt_later) with policy and PII constraints.
- Adopt/defer decision per domain.
