# OpenQilin MVP v0.1 - Architecture Roadmap

Status: governance hardening complete (`M8`), real Discord runtime validation pending (`M9`)
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

M5..M7 implementation status:
- proposal/approval/initialization/workforce governance path is implemented
- project-document policy and specialist-touchability constraints are implemented
- runtime recovery, Discord ingress governance, Docker full-profile runtime cutover, and Gemini provider-path activation are implemented
- MVP acceptance matrix and evidence pack are implemented

Blocking gaps before MVP closeout:
1. Real Discord runtime connection is not yet implemented as a live bot worker in Docker `full` profile.

Gap-to-milestone mapping:
- `M8` (issues `#48`..`#52`): completed governance hardening, lifecycle API completion, and acceptance/doc alignment.
- `M9` (issues `#49`, `#53`..`#56`): real Discord bot runtime, Docker integration + secret hardening, live end-to-end acceptance evidence.

## 4. Target MVP Runtime Shape

Execution chain:

`discord/http ingress -> envelope/identity -> policy gate -> budget gate -> governance path guard -> dispatch boundary -> callbacks -> immutable audit/log`

Core persistent domains:
- `agents`: institutional + project agents with lifecycle states
- `projects`: lifecycle, objective, budget caps and usage counters
- `tasks`: governed execution records and terminal outcomes
- `execution_logs`: append-only governed audit records
- `project_artifact*`: file-backed rich-text docs with runtime pointer/hash metadata

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
- implement hybrid runtime-metadata + file project documentation model and role-touchability rules

Work packages:
1. `M6-WP1`: implement canonical project file root under `${OPENQILIN_SYSTEM_ROOT}/projects/<project_id>/` with runtime pointer/hash synchronization
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

## M8 - Governance Surface Hardening (Completed)
Objective:
- close governance-critical MVP gaps exposed by post-M7 review

Work packages:
1. `M8-WP1`: enforce connector signature/idempotency/actor parity on governance and proposal-discussion routes
2. `M8-WP2`: add governed lifecycle APIs for `pause`, `resume`, `terminate`, `archive` with audit evidence
3. `M8-WP3`: refactor acceptance to API-only lifecycle transitions and align planning docs to runtime-authoritative persistence wording

Exit criteria:
- header spoofing is fail-closed on governance mutation routes
- lifecycle transitions are API-driven and audited end-to-end
- acceptance/conformance paths no longer mutate lifecycle via repository internals
- milestone/spec/planning persistence semantics are consistent

## M9 - Real Discord Runtime and Live MVP Validation
Objective:
- run an actually connected Discord instance in Docker and validate live MVP use cases

Work packages:
1. `M9-WP1`: implement real Discord bot worker runtime (`discord gateway -> /v1/connectors/discord/messages -> governed response bridge`)
2. `M9-WP2`: integrate Discord worker into Docker `full` profile and enforce non-local secret hardening
3. `M9-WP3`: execute live Discord acceptance checklist across proposal/approval/activation/execution/completion flows
4. `M9-WP4`: publish live-instance MVP evidence pack and closeout checklist

Exit criteria:
- real Discord bot receives and replies through governed runtime paths
- Docker `full` profile runs API + workers + Discord bot together
- non-local runtime denies unsafe/missing connector secret configuration
- live evidence demonstrates MVP lifecycle use cases through real Discord

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
