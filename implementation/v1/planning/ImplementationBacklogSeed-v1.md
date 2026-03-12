# OpenQilin v1 - Implementation Backlog Seed

## 1. Scope
- Seed implementation work from Define and Design artifacts.
- Organize work in dependency order for governance-core first delivery.
- Extend backlog structure from completed M0-M4 foundation into MVP v0.1 completion milestones.

## 2. Tracking Rule
- `design/TODO.txt` is the design-stage historical tracker and is not reused as implementation live tracking.
- GitHub Issues/PRs/Project are the authoritative implementation execution tracker.
- `implementation/v1/planning/ImplementationProgress-v1.md` is the in-repo milestone/status mirror.
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

### 3.7 Governance Domain Persistence
- implement persistent `agents` / `projects` / `tasks` / `execution_logs` schemas
- replace placeholder governance repository/service surfaces
- enforce lifecycle constraints for project and agent domain states
- enforce canonical project lifecycle without standalone rejected state:
  - `proposed -> approved -> active -> paused -> completed -> terminated -> archived`

### 3.8 Recovery and Runtime Continuity
- persist runtime task/communication state beyond in-memory shells
- implement startup rehydration for runtime services and idempotency indexes
- harden append-only log policy and persistence-boundary constraints

### 3.9 External Owner Adapter
- implement Discord adapter boundary mapping to canonical owner-command envelope
- lock command-family contracts (`run_task*`, `llm_*`, `msg_*`, status queries)
- produce end-to-end MVP acceptance matrix and evidence pack

### 3.10 Proposal and Workforce Governance
- implement proposal discussion/approval path (`owner`, `ceo`, `cwo`)
- implement CWO project initialization (scope/objective/budget/metrics)
- implement template-based workforce creation (`project_manager` active, `domain_leader` declared-disabled)

### 3.11 Project Documentation Governance
- store runtime-generated project docs under `${OPENQILIN_SYSTEM_ROOT}/projects/<project_id>/`
- enforce allowed document types and per-type document caps
- persist DB pointer/hash metadata and fail closed on mismatch

### 3.12 Project Manager/Specialist Operating Constraints
- codify Project Manager mandatory operations template (milestones/tasks/assignment/reporting)
- enforce specialist touchability (`project_manager`-only, Domain Leader path disabled for first MVP)
- enforce owner non-direct-specialist interaction contract

## 4. Suggested Delivery Order
1. lock project lifecycle/transition guards (`proposed -> approved -> active -> paused -> completed -> terminated -> archived`)
2. implement proposal discussion + approval governance APIs (`owner`, `ceo`, `cwo`)
3. implement CWO project initialization and workforce templating contracts
4. implement canonical system-root project file storage and DB pointer/hash synchronization
5. enforce approved document types + per-type caps (fail-closed)
6. enforce specialist touchability (`project_manager`-only direct path) and owner non-direct-specialist policy
7. implement Project Manager mandatory-operations template enforcement
8. persist governance/runtime state adapters and startup recovery
9. harden append-only audit persistence behavior and integrity checks
10. implement Discord adapter with role/channel constraints
11. run MVP acceptance matrix and publish closeout evidence pack

## 5. Acceptance Gates
- governance-core conformance passes
- end-to-end task admission path works fail-closed
- idempotent retries do not duplicate side effects
- critical alerts and audit events are visible
