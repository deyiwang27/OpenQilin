# OpenQilin v1 - Implementation Backlog Seed

## 1. Scope
- Seed implementation work from Define and Design artifacts.
- Organize work in dependency order for governance-core first delivery.

## 2. Workstreams
### 2.1 Runtime Core
- implement `policy_runtime` adapter and decision client
- implement `task_orchestrator` admission/state machine shell
- implement `budget_engine` reservation path
- implement `execution_sandbox` dispatch boundary

### 2.2 API and Identity
- implement owner ingress envelope validation
- implement Discord identity mapping and replay controls
- implement control-plane query/mutation endpoints

### 2.3 Communication
- implement A2A envelope validation
- implement ACP send/ack/nack/dead-letter pipeline
- implement idempotency key dedupe and message ledger writes

### 2.4 Intelligence
- implement `llm_gateway` wrapper with routing profile support
- configure `dev_gemini_free` for local/CI
- integrate governed retrieval path with pgvector-backed search

### 2.5 Data
- create PostgreSQL schema packages and migrations
- create Redis keyspace and TTL policy
- implement outbox and checkpoint-based CDC consumers

### 2.6 Observability
- instrument required spans and events
- stand up OTel collector pipeline
- provision minimum Grafana dashboards and alert rules

## 3. Suggested Delivery Order
1. schema + migrations + outbox primitives
2. policy runtime + orchestrator admission flow
3. control plane ingress and identity mapping
4. sandbox and llm gateway execution targets
5. communication gateway reliability path
6. observability and alerting hardening

## 4. Acceptance Gates
- governance-core conformance passes
- end-to-end task admission path works fail-closed
- idempotent retries do not duplicate side effects
- critical alerts and audit events are visible
