# OpenQilin v1 - Implementation Backlog Seed

## 1. Scope
- Seed implementation work from Define and Design artifacts.
- Organize work in dependency order for governance-core first delivery.

## 2. Tracking Rule
- `design/TODO.txt` is the authoritative live tracker for open and completed design-stage work.
- This document is the stable workstream reference and should be updated only when backlog structure materially changes.

## 3. Workstreams
### 3.1 Runtime Core
- implement `policy_runtime` adapter and decision client
- implement `task_orchestrator` admission/state machine shell
- implement `budget_runtime` reservation path inside `orchestrator_worker`
- implement `execution_sandbox` dispatch boundary

### 3.2 API and Identity
- implement owner ingress envelope validation
- implement Discord identity mapping and replay controls
- implement control-plane query and mutation endpoints

### 3.3 Communication
- implement A2A envelope validation
- implement ACP send/ack/nack/dead-letter pipeline
- implement idempotency key dedupe and message ledger writes

### 3.4 Intelligence
- implement `llm_gateway` wrapper with routing profile support
- configure `dev_gemini_free` for local and CI
- integrate governed retrieval path with pgvector-backed search

### 3.5 Data
- create PostgreSQL schema packages and migrations
- create Redis keyspace and TTL policy
- implement outbox and checkpoint-based CDC consumers

### 3.6 Observability
- instrument required spans and events
- stand up OTel collector pipeline
- provision minimum Grafana dashboards and alert rules

## 4. Suggested Delivery Order
1. schema, migrations, and outbox primitives
2. control-plane ingress and identity mapping
3. policy runtime and orchestrator admission flow
4. budget reservation path inside `orchestrator_worker`
5. sandbox and llm gateway execution targets
6. communication gateway reliability path
7. observability and alerting hardening

## 5. Acceptance Gates
- governance-core conformance passes
- end-to-end task admission path works fail-closed
- idempotent retries do not duplicate side effects
- critical alerts and audit events are visible
