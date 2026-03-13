# OpenQilin MVP v0.1 - Architecture Roadmap

Status: planning baseline
Last updated: 2026-03-12

## 1. Goal

Define the delivery architecture and milestone roadmap required to turn the
current post-M4 foundation into the first usable MVP runtime.

## 2. Current Implementation Baseline (Completed in M0-M4)

Implemented and validated:
- Governed owner-command ingress (`POST /v1/owner/commands`)
- Identity binding, connector signature validation, and idempotent replay
- Fail-closed policy and budget decision gates
- Dispatch routing for `sandbox`, `llm`, and `communication` targets
- Communication reliability path (A2A validation, ACP send/ack/nack, retries, dead-letter, callbacks)
- Retrieval query baseline (`POST /v1/projects/{project_id}/artifacts/search`)
- Observability and release-readiness gates (audit/metrics/tracing, CI gates, migration checks, release artifacts)

## 3. MVP Gap Assessment

Still missing or placeholder-heavy for MVP v0.1:
- Persistent governance domain model:
  - `data_access/repositories/governance.py` is placeholder
  - no concrete persistent agent/project registries with lifecycle constraints
- Runtime-state persistence:
  - task and communication repositories are primarily in-memory
  - restart recovery does not yet hydrate full runtime state from persistent storage
- Governance path guard enforcement:
  - policy exists in docs, but centralized runtime write-guard service is not yet implemented
- Append-only log enforcement at persistence boundary:
  - append-only behavior exists in runtime APIs, but DB-level roles/policies are not yet codified
- MVP control-plane surfaces:
  - owner discussion/governance routers are placeholders
  - project creation and project/agent/budget status contracts are not yet exposed as stable MVP API set
- Discord adapter:
  - transport assumptions exist, but adapter boundary that maps Discord payloads to canonical owner envelope is not yet a first-class runtime service
- Project proposal and approval governance flow:
  - explicit proposal revision/approval lifecycle contracts are not yet implemented end-to-end
- Project rich-text documentation policy:
  - canonical system root + file type/cap enforcement is not implemented yet
- Project Manager template and workforce bootstrapping contracts:
  - CWO-driven template/llm/system-prompt binding path is not implemented as governed runtime flow

## 4. Target MVP Runtime Shape

Execution chain:

`discord/http ingress -> envelope/identity -> policy gate -> budget gate -> governance path guard -> dispatch boundary -> callbacks -> immutable audit/log`

Core persistent domains:
- `agents`: institutional + project agents with lifecycle states
- `projects`: lifecycle, objective, budget caps and usage counters
- `tasks`: governed execution records and terminal outcomes
- `execution_logs`: append-only governed audit records
- `project_artifact*`: file-backed rich-text docs with DB pointer/hash metadata

## 5. Post-M4 Milestone Plan for MVP v0.1

## M5 - Proposal-to-Activation Governance Slice
Objective:
- implement explicit project proposal/approval lifecycle and governance discussion surfaces

Work packages:
1. `M5-WP1`: lock project lifecycle model (`proposed -> approved -> active -> paused -> completed -> terminated -> archived`) in runtime contracts
2. `M5-WP2`: implement proposal discussion/approval APIs (`owner`, `ceo`, `cwo`)
3. `M5-WP3`: implement CWO project initialization contract (scope/objective/budget/metrics persistence)
4. `M5-WP4`: implement CWO workforce creation from templates (`project_manager` + `domain_leader` declared, `domain_leader` disabled)

Exit criteria:
- proposal revisions remain in `proposed` until explicit approval
- activation requires approved proposal + policy/budget gates
- CWO initialization writes governed project metadata and workforce-plan evidence

## M6 - Project Documentation and Access Governance
Objective:
- implement hybrid DB+file project documentation model and role-touchability rules

Work packages:
1. `M6-WP1`: implement canonical project file root under `${OPENQILIN_SYSTEM_ROOT}/projects/<project_id>/` with DB pointer/hash synchronization
2. `M6-WP2`: enforce approved doc types, mixed per-type + project-total caps, and lifecycle/role write-governance policy
3. `M6-WP3`: enforce specialist touchability policy (Project Manager-only in first MVP)
4. `M6-WP4`: enforce Project Manager mandatory-operations template contract

Exit criteria:
- project docs persist outside repo tree with governed policy constraints
- approved-to-active initialization persists baseline artifacts (`project_charter`, `scope_statement`, `budget_plan`, `success_metrics`, `workforce_plan`, `execution_plan`) with verified pointer/hash metadata
- over-cap, out-of-policy, or role/stage unauthorized document writes are blocked and audited
- owner cannot directly command specialist in any governed channel path
- Project Manager template binding fails closed when mandatory operations are missing

## M7 - Persistence/Recovery + Discord Acceptance Closeout
Objective:
- complete runtime persistence/recovery hardening, Docker runtime cutover, real Gemini free-tier validation, and Discord-governed acceptance evidence

Work packages:
1. `M7-WP1`: persistent runtime-state adapters + startup recovery orchestration
2. `M7-WP2`: Discord ingress context + identity/channel mapping baseline (`guild_id`/`channel_id`/`channel_type`, connector verification, allowlist state model)
3. `M7-WP3`: Discord chat-governance enforcement (`direct`/`leadership_council`/`governance`/`executive`/`project`) + lifecycle-driven project-channel membership + specialist-access constraints
4. `M7-WP4`: Docker `full` profile runtime cutover (replace `api_app`/worker placeholder containers with real runtime entrypoints)
5. `M7-WP5`: Gemini Flash free-tier provider-path activation + quota accounting validation
6. `M7-WP6`: MVP acceptance matrix + evidence pack + closeout checklist (including Project Manager reporting, completion approval path, and full lifecycle E2E)

Exit criteria:
- restart/recovery preserves governance and idempotency invariants and restores institutional-agent state
- Docker `full` profile executes real runtime services (no placeholder app/worker containers)
- Gemini free-tier provider path is validated through governed dispatch with quota telemetry evidence
- Discord-to-governed-ingress path is executable end-to-end with specialist-access constraints
- Discord adapter enforces fixed chat classes (`direct`, `leadership_council`, `governance`, `executive`, `project`) and lifecycle-driven project-channel membership constraints, including deferred/pending `secretary` participation profile handling
- full project lifecycle (`proposed -> approved -> active -> paused -> completed -> terminated -> archived`) is validated via governed acceptance scenarios
- MVP v0.1 evidence pack is complete and traceable

## 6. Design Decisions Locked for MVP v0.1

- Budget defaults: soft `90%`, hard `100%`
- Communication retries: `max_attempts=3`
- Task terminal immutability: `completed|failed|cancelled` not rewritten by callbacks
- Error-code naming: lower snake-case
- Ratio-based budget planning allowed upstream only; runtime enforces absolute caps
- Project lifecycle lock: `proposed -> approved -> active -> paused -> completed -> terminated -> archived`
- No standalone `rejected` project state in first MVP
- `domain_leader` role declared but runtime-disabled for first MVP
- Project documentation uses strict 10-type enum with mixed per-type caps plus project total active-doc cap (`20`)
- Project documentation mutability is hybrid (versioned core plans + append-only logs/reports)
- `project_manager` project-document writes are `active`-only; controlled doc edits require `cwo+ceo` approval evidence
