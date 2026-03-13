# OpenQilin v1 - Implementation Execution Plan

## 1. Scope
- Define the execution model for v1 implementation after design closeout.
- Lock milestone structure, feature grouping, tracking interfaces, and progress cadence.

## 2. Authority and Tracking Boundary
- `design/TODO.txt` remains the historical and design-stage tracker. It is not reused as the live implementation backlog.
- GitHub Issues/Project is the primary execution system for implementation tracking and day-to-day status.
- `implementation/v1/planning/ImplementationProgress-v1.md` is the in-repo mirror for milestone-level progress snapshots.
- `implementation/v1/planning/TODO.txt` is the implementation-stage working checklist mirror and must not override GitHub/Progress evidence.

## 3. Milestone Model
Milestone names and ordering match `implementation/v1/planning/ImplementationMilestones-v1.md`.

| Milestone | Goal | Feature Set | Exit Evidence |
| --- | --- | --- | --- |
| `M0 Foundation Scaffold` | establish runnable implementation baseline | `uv` project initialization, base package tree, Docker Compose baseline, CI skeleton (lint/type/unit) | baseline commands execute, scaffold and checks are wired, CI baseline is running |
| `M1 First Executable Slice` | deliver first governed end-to-end path | API ingress, task admission, policy check, budget reserve, sandbox/LLM dispatch stub, audit+trace emission | owner command accept/block path works and fail-closed behavior for policy/budget uncertainty is verified |
| `M2 Execution Targets` | replace stubs with real execution adapters | real sandbox dispatch, LiteLLM-backed `llm_gateway`, basic retrieval-backed query path | governed dispatch reaches sandbox or Gemini-backed path; usage/cost metadata and retrieval path are validated |
| `M3 Communication Reliability` | harden delivery lifecycle | A2A validation, ACP send/ack/nack, retries, dead-letter flow, orchestrator callback integration | deterministic at-least-once behavior, duplicate safety, and dead-letter alert/audit evidence |
| `M4 Hardening and Release Readiness` | complete release hardening gates | dashboards/alerts, migration and rollback validation, conformance+smoke suites, release artifact prep | `full` profile passes smoke and conformance gates and release candidate is promotable |
| `M5 MVP Proposal and Governance Activation` | implement proposal-to-activation governance contracts | project lifecycle lock, proposal/approval APIs, CWO initialization flow, workforce templating with declared-disabled `domain_leader` | proposal/approval/activation workflow is enforced with deterministic lifecycle guards and audit evidence |
| `M6 MVP Documentation and Access Governance` | implement hybrid project-doc governance and role-touchability controls | canonical system-root project docs, file type/cap policy, runtime pointer/hash integrity, Project Manager-only specialist touchability policy | project-document writes are policy-governed and specialist access constraints are enforced fail-closed |
| `M7 MVP Persistence, Adapter, and Acceptance` | close MVP with recovery hardening and constrained Discord adapter | persistent runtime recovery path, Discord adapter with role/channel constraints, MVP acceptance matrix and evidence pack | restart invariants and Discord-governed ingress constraints pass end-to-end acceptance evidence |
| `M8 MVP Governance Surface Hardening` | close governance-critical MVP gaps from post-M7 review | connector-auth parity for governance routes, governed lifecycle API completion, API-only lifecycle acceptance flow, planning doc alignment | governance mutation spoofing is fail-closed and lifecycle transitions are API-governed end-to-end |
| `M9 MVP Real Discord Runtime and Live Validation` | deliver real Discord-connected runtime and live MVP evidence | Discord bot worker runtime, Docker full-profile integration + secret hardening, live acceptance checklist, closeout evidence pack | real Discord use cases run on Docker runtime with traceable live acceptance evidence |

## 4. M1 Implementation Workplan (Kickoff on Issue `#4`)
### 4.1 Objective and Boundary
- Build the first governed owner-command path from API ingress to dispatch stub with fail-closed policy and budget enforcement.
- Produce testable accept/block outcomes plus trace and audit evidence for each outcome.
- Keep M2+ scope out of this slice (no real sandbox execution, no real LiteLLM provider wiring, no reliability hardening).

### 4.2 Ordered Work Packages
1. `M1-WP1` Owner command contract and ingress validation
- Target modules: `control_plane/schemas/owner_commands.py`, `control_plane/routers/owner_commands.py`, `control_plane/identity/principal_resolver.py`, `task_orchestrator/admission/envelope_validator.py`.
- Deliverables: request/response schema, identity binding shell, envelope validation with explicit rejection reasons.

2. `M1-WP2` Task admission and idempotency shell
- Target modules: `task_orchestrator/admission/service.py`, `task_orchestrator/admission/idempotency.py`, `control_plane/idempotency/ingress_dedupe.py`, `data_access/repositories/runtime_state.py`.
- Deliverables: admission service path that creates or reuses task state and returns deterministic idempotent results.

3. `M1-WP3` Policy decision path with fail-closed behavior
- Target modules: `policy_runtime_integration/normalizer.py`, `policy_runtime_integration/client.py`, `policy_runtime_integration/fail_closed.py`, `policy_runtime_integration/models.py`.
- Deliverables: normalized policy input, policy decision integration shell, uncertainty/error mapped to fail-closed block result.

4. `M1-WP4` Budget reservation path with fail-closed behavior
- Target modules: `budget_runtime/reservation_service.py`, `budget_runtime/client.py`, `budget_runtime/threshold_evaluator.py`, `budget_runtime/models.py`.
- Deliverables: reservation check shell, budget uncertainty/error mapped to fail-closed block result.

5. `M1-WP5` Dispatch stub and lifecycle wiring
- Target modules: `task_orchestrator/dispatch/target_selector.py`, `task_orchestrator/dispatch/sandbox_dispatch.py`, `task_orchestrator/services/lifecycle_service.py`, `task_orchestrator/services/task_service.py`.
- Deliverables: controlled dispatch stub path for accepted requests and deterministic blocked-path state transitions.

6. `M1-WP6` Observability evidence emission
- Target modules: `observability/tracing/spans.py`, `observability/tracing/tracer.py`, `observability/audit/audit_writer.py`, `observability/metrics/recorder.py`.
- Deliverables: correlation IDs propagated through M1 path, audit event written for accept/block, minimum counters for admission outcomes.

7. `M1-WP7` Admin CLI command implementation
- Target modules: `apps/admin_cli.py` plus supporting utilities in `data_access/db/*` and app entrypoints.
- Deliverables: non-placeholder behavior for `migrate`, `bootstrap`, `smoke`, and `diagnostics` commands with explicit success/failure exit semantics.

8. `M1-WP8` Test and evidence pack
- Target test slices: `tests/unit`, `tests/component`, `tests/integration`, `tests/contract`.
- Deliverables: fail-closed policy/budget tests, owner command accept/block tests, CLI command behavior tests, and issue evidence links to PR/test runs.

### 4.3 M1 Exit Evidence Checklist
- Owner command returns deterministic `accepted` or `blocked` result through governed path.
- Policy uncertainty and budget uncertainty both resolve to blocked outcome (fail-closed).
- Dispatch stub invoked only on accepted path.
- Trace and audit artifacts are emitted for both accepted and blocked outcomes.
- Admin CLI commands (`migrate`, `bootstrap`, `smoke`, `diagnostics`) run with non-placeholder behavior.

## 5. M2 Kickoff Workplan (Issue `#6`)
### 5.1 Objective and Boundary
- Replace M1 execution stubs with real adapter boundaries while preserving governed-path contracts and fail-closed behavior.
- Deliver incremental runtime integration in small work packages with independent evidence.
- Keep M3 reliability scope out of this kickoff slice (no retries/dead-letter semantics yet).

### 5.2 Ordered Work Packages
1. `M2-WP1` Sandbox adapter wiring (`issue #7`)
- Target modules: `task_orchestrator/dispatch/*`, `task_orchestrator/services/*`.
- Deliverables: accepted-path dispatch routed to sandbox adapter boundary with deterministic lifecycle/error mapping.

2. `M2-WP2` LiteLLM gateway integration (`issue #8`)
- Target modules: `llm_gateway/*`, execution integration boundaries.
- Deliverables: controlled model-call path through LiteLLM and normalized usage/cost metadata.

3. `M2-WP3` Retrieval-backed query baseline (`issue #9`)
- Target modules: retrieval runtime boundary modules and execution integration points.
- Deliverables: deterministic retrieval path integration with fail-closed tests for retrieval/runtime uncertainty.

4. `M2-WP4` PostgreSQL `pgvector` enablement + migration contract (`issue #10`)
- Target modules: `compose.yml`, `migrations/*`, `data_access/*`, env/bootstrap docs.
- Deliverables: extension-available bootstrap contract and deterministic migration path evidence.

5. `M2-WP5` M2 evidence pack and milestone exit validation (`issue #11`)
- Target slices: `tests/unit`, `tests/component`, `tests/integration`, `tests/contract`, `tests/conformance`.
- Deliverables: acceptance-criteria evidence mapping and milestone closeout links.

### 5.3 M2 Exit Evidence Checklist
- Accepted governed path executes through sandbox adapter boundary.
- LiteLLM gateway path runs through defined integration boundary with usage/cost metadata captured.
- Retrieval-backed baseline path is validated by deterministic integration tests.
- `pgvector` bootstrap+migration contract is validated and documented.
- Full quality gates pass for merged M2 scope (`ruff`, `mypy`, `pytest` suites).

## 6. M3 Kickoff Workplan (Issue `#13`)
### 6.1 Objective and Boundary
- Harden communication lifecycle reliability with deterministic delivery semantics and duplicate-safe processing.
- Deliver M3 in independently verifiable work packages with explicit contract/conformance evidence.
- Keep M4 hardening/release scope out of this slice (no release-gate packaging yet).

### 6.2 Ordered Work Packages
1. `M3-WP1` A2A envelope validation + ACP message-contract baseline (`issue #14`)
- Target modules: `communication_gateway/validators/*`, `communication_gateway/transport/route_resolver.py`.
- Deliverables: canonical envelope validation, ordering checks, and explicit deny reasons for malformed/out-of-policy inputs.

2. `M3-WP2` ACP send/ack/nack delivery pipeline (`issue #15`)
- Target modules: `communication_gateway/transport/acp_client.py`, `communication_gateway/delivery/publisher.py`, `communication_gateway/delivery/ack_handler.py`, `communication_gateway/storage/message_ledger.py`.
- Deliverables: deterministic send lifecycle with persisted state transitions for ack/nack outcomes.

3. `M3-WP3` Retry scheduler + duplicate-safe idempotency (`issue #16`)
- Target modules: `communication_gateway/delivery/retry_scheduler.py`, `communication_gateway/storage/idempotency_store.py`, `data_access/cache/idempotency_store.py`.
- Deliverables: deterministic retry policy enforcement and duplicate-delivery suppression without duplicate side effects.

4. `M3-WP4` Dead-letter flow + alert/audit emission (`issue #17`)
- Target modules: `communication_gateway/delivery/dlq_writer.py`, `data_access/repositories/communication.py`, observability integration points.
- Deliverables: retry-exhausted deterministic dead-letter routing with required audit and reliability signal emission.

5. `M3-WP5` Orchestrator callback integration + M3 evidence pack (`issue #18`)
- Target modules: `task_orchestrator/callbacks/*`, `communication_gateway/callbacks/outcome_notifier.py`, `implementation/v1/planning/M3EvidencePack-v1.md`.
- Deliverables: callback-driven lifecycle integration and milestone closeout evidence mapping for M3 acceptance criteria.

### 6.3 M3 Exit Evidence Checklist
- A2A envelope validation rejects malformed/invalid traffic deterministically with explicit reason codes.
- ACP send/ack/nack lifecycle is persisted and duplicate-safe under retry/replay conditions.
- Retry policy and dead-letter routing produce deterministic, auditable outcomes.
- Orchestrator callback handling preserves at-least-once semantics without duplicate side effects.
- Full quality gates pass for merged M3 scope (`ruff`, `mypy`, `pytest` suites including contract/conformance slices).

## 7. M4 Kickoff Workplan (Issue `#21`)
### 7.1 Objective and Boundary
- Complete hardening and release-readiness gates now that M3 is merged to `main`.
- Deliver M4 in independently verifiable work packages with explicit release evidence links.
- Focus on release reliability and operational promotion criteria; avoid net-new product-scope expansion.

### 7.2 Ordered Work Packages
1. `M4-WP1` Observability dashboards + release alert thresholds (`issue #22`)
- Target modules: `observability/*`, release monitoring docs/runbooks.
- Deliverables: release-readiness dashboard/alert contract, thresholds, and ownership/runbook linkage.

2. `M4-WP2` Migration validation + rollback drill automation (`issue #23`)
- Target modules: `migrations/*`, `ops/scripts/*`, rollout/rollback documentation.
- Deliverables: deterministic forward/backward migration verification and rollback drill evidence flow (`admin_cli rollback-drill`, `ops/scripts/run_migration_rollback_drill.py`, CI `check_migration_rollback_readiness.py` gate).

3. `M4-WP3` Full-profile smoke + conformance gate hardening (`issue #24`)
- Target modules: `compose.yml`, CI/release gate workflows, smoke/conformance suites.
- Deliverables: stable release-gate command matrix and deterministic pass/fail criteria for promotion (`release_readiness/gate_matrix.py`, `ops/scripts/run_release_gate_matrix.py`, CI `check_release_gate_matrix.py` gate, smoke/conformance conformance coverage).

4. `M4-WP4` Release artifact + promotion checklist packaging (`issue #25`)
- Target modules: release docs/checklists/evidence index artifacts.
- Deliverables: operator-facing promotion checklist and traceable release artifact packaging (`release_readiness/artifact_packaging.py`, `ops/scripts/run_release_artifact_packager.py`, `ops/scripts/check_release_artifact_package.py`, release artifact index + checklist docs).

5. `M4-WP5` M4 evidence pack and milestone closeout validation (`issue #26`)
- Target modules: `implementation/v1/planning/M4EvidencePack-v1.md` and milestone closeout docs.
- Deliverables: acceptance-criteria mapping with final validation evidence and closeout links, plus conformance coverage for evidence-pack integrity (`tests/conformance/test_m4_wp5_evidence_pack_conformance.py`).

### 7.3 M4 Exit Evidence Checklist
- Release-readiness dashboards/alerts are defined, linked to runbooks, and validated.
- Migration/rollback drills are repeatable with recorded evidence.
- `full` profile admin-bootstrap smoke + conformance gates are deterministic promotion blockers.
- Release artifact/promotion checklist package is complete and operator-usable.
- Full quality/release gates pass for merged M4 scope.
- Residual scope boundary is documented: `api_app`/worker placeholder containers are excluded from M4 promotion evidence and tracked as post-M4 hardening work.

## 8. Post-M4 MVP Completion Workplan
### 8.1 Objective and Boundary
- Convert post-M4 foundations into a governance-first MVP runtime aligned to the finalized operating model:
  - proposal/approval workflow owned by `owner` + `ceo` + `cwo`
  - CWO-initialized project charter/workforce setup
  - Project Manager-led execution with specialist touchability constraints
  - runnable Docker `full` profile runtime with non-placeholder app/worker services
  - governance/executive runtime validated through Gemini Flash free-tier provider path with quota accounting
  - Discord-originated owner command flows validated through the same governed ingress path
- Keep delivery incremental and evidence-driven across `M5`..`M9`.
- Preserve fail-closed behavior while adding persistent governance/project contracts.

### 8.2 Ordered Milestone Work Packages
1. `M5-WP1` Project lifecycle contract lock
- Target modules: `spec/state-machines/ProjectStateMachine.md`, governance transition validators, related API schemas.
- Deliverables: enforced lifecycle
  - `proposed -> approved -> active -> paused -> completed -> terminated -> archived`
  - no standalone `rejected` state
  - transition-guard enforcement in governed APIs.

2. `M5-WP2` Proposal discussion and approval API surfaces
- Target modules: `control_plane/routers/owner_discussions.py`, `control_plane/routers/governance.py`, handlers/schemas.
- Deliverables: proposal revision workflow in `proposed`, triad approval path (`owner`, `ceo`, `cwo`), immutable audit evidence.

3. `M5-WP3` CWO project initialization workflow
- Target modules: governance services + repositories, project artifact contracts.
- Deliverables: governed initialization for scope/objective/budget/metrics and workforce-plan records.

4. `M5-WP4` Workforce templating contract (`project_manager` + `domain_leader` declared-disabled)
- Target modules: agent registry contracts, template/prompt metadata, policy guard rules.
- Deliverables: CWO binds template + llm profile + system prompt package; `domain_leader` schema-declared but runtime-disabled.

5. `M6-WP1` Canonical project file root and pointer/hash model
- Target modules: `data_access/repositories/artifacts.py`, storage policy services, environment config.
- Deliverables: project docs stored under `${OPENQILIN_SYSTEM_ROOT}/projects/<project_id>/` with runtime `storage_uri` + `content_hash`.

6. `M6-WP2` Project document policy and volume cap enforcement
- Target modules: project artifact policy validators + governance middleware.
- Deliverables: strict approved doc-type enum, mixed per-type active-document caps plus project total active-document cap, and fail-closed over-cap handling.

7. `M6-WP3` Specialist touchability policy enforcement
- Target modules: owner command/policy integration + communication access checks.
- Deliverables: owner direct specialist command blocked; specialist path routed through `project_manager`.

8. `M6-WP4` Project Manager mandatory-operations template enforcement
- Target modules: Project Manager template registry + orchestrator planning contracts.
- Deliverables: mandatory Project Manager operations (milestones, decomposition, assignment, reporting) contract-tested, including active-state-only write behavior and controlled-doc update approval gates (`cwo+ceo`).

9. `M7-WP1` Persistent runtime-state adapters + recovery
- Target modules: runtime-state/communication repositories, service bootstrap dependencies, governance/agent registry repositories.
- Deliverables: restart/rehydration preserving idempotency and governance invariants, including institutional-agent bootstrap from persistent state.

10. `M7-WP2` Discord ingress context + identity/channel mapping
- Target modules: Discord adapter package, owner-command ingress schemas, connector identity repositories.
- Deliverables: canonical Discord communication context (`guild_id`, `channel_id`, `channel_type`) mapped into owner envelope contracts, connector verification, identity/channel mapping store with `pending|verified|revoked` states, and allowlist lookup primitives.

11. `M7-WP3` Discord chat-governance enforcement + policy/runtime integration
- Target modules: Discord adapter authorization path, policy input normalizer/rule evaluation, task/audit persistence contracts.
- Deliverables: fixed chat-class validator (`direct`, `leadership_council`, `governance`, `executive`, `project`), lifecycle-aware project membership resolver, specialist access constraints, pending-role activation flags (`secretary`, `cso`, `domain_leader`), and traceable context persistence for replay-safe decisions.

12. `M7-WP4` Docker `full` profile runtime cutover
- Target modules: `compose.yml`, runtime container entrypoints, healthchecks/startup sequencing, operator runbooks.
- Deliverables: `api_app`, `orchestrator_worker`, and `communication_worker` run real application entrypoints in Docker `full` profile (no placeholder commands).

13. `M7-WP5` Gemini Flash free-tier provider-path activation + quota telemetry validation
- Target modules: `llm_gateway/providers`, runtime settings/env wiring, budget/quota observability surfaces, acceptance tests.
- Deliverables: governed `llm_*` dispatch executes through configured Gemini Flash free-tier provider path with deterministic quota-usage evidence and fail-closed behavior on provider/runtime uncertainty.

14. `M7-WP6` MVP acceptance matrix and closeout evidence
- Target modules: `tests/contract`, `tests/conformance`, MVP evidence docs.
- Deliverables: end-to-end acceptance across proposal, activation, Project Manager-managed execution, completion approval, owner notification, full project lifecycle progression evidence, and Discord round-trip validation against governed chat classes.

15. `M8-WP1` Governance/discussion connector-auth parity hardening
- Target modules: `control_plane/routers/governance.py`, `control_plane/routers/owner_discussions.py`, connector-auth helpers/tests.
- Deliverables: governance mutation/discussion routes enforce connector signature + actor/idempotency parity with fail-closed denial evidence.

16. `M8-WP2` Governed lifecycle API surface completion
- Target modules: governance routers/handlers/schemas/repository + lifecycle tests.
- Deliverables: explicit `pause`, `resume`, `terminate`, and `archive` APIs with role/state transition guards and immutable audit events.

17. `M8-WP3` API-only lifecycle acceptance refactor + planning doc alignment
- Target modules: acceptance/integration tests and planning docs (`Milestones`, `ExecutionPlan`, `Roadmap`, `TODO`, `Progress`).
- Deliverables: remove direct repository lifecycle mutation from acceptance path and align planning wording with runtime-authoritative persistence model.

18. `M9-WP1` Real Discord bot worker runtime
- Target modules: new Discord worker app/service, connector adapter integration, response bridge handlers.
- Deliverables: real Discord gateway-connected bot that maps inbound events to `POST /v1/connectors/discord/messages` and posts governed responses back to Discord.

19. `M9-WP2` Docker full-profile Discord integration + secret hardening
- Target modules: `compose.yml`, runtime settings/startup validation, operator env docs.
- Deliverables: Discord worker is first-class in Docker `full` profile; non-local startup fails closed on unsafe/missing connector secret configuration.

20. `M9-WP3` Live Discord MVP acceptance validation
- Target modules: ops acceptance checklist, live-run evidence capture scripts/docs, conformance gates.
- Deliverables: live Discord E2E execution evidence for proposal/approval/activation/execution/completion/termination paths with governed chat constraints.

21. `M9-WP4` Live-instance evidence pack and closeout
- Target modules: MVP evidence-pack docs and progress closeout tracking.
- Deliverables: consolidated live-instance evidence pack mapped to MVP exit criteria and closeout linkage (issue/PR/merge evidence).

### 8.3 MVP Exit Evidence Checklist
- Proposal lifecycle and approval gates are enforced with canonical state transitions.
- CWO initialization produces governed project charter/workforce evidence.
- Project docs persist under canonical system root with type/cap/pointer-hash policy enforcement.
- Specialist touchability restrictions are enforced (`project_manager`-only in first MVP).
- Recovery path preserves governance/idempotency invariants and restores institutional agents.
- Governance/discussion mutation routes enforce connector-auth parity and deny spoofed requests fail-closed.
- Lifecycle pause/resume/terminate/archive transitions are executed through governed APIs (no repository-internal mutation in acceptance evidence).
- Docker `full` profile runtime is runnable with non-placeholder app/worker services.
- Real Discord bot runtime is connected and operational in Docker `full` profile.
- Non-local runtime enforces non-default connector secret configuration.
- Gemini Flash free-tier provider path is validated with quota accounting evidence.
- Discord round-trip owner command path is validated with governed access constraints.
- Full project lifecycle scenario is validated end-to-end with completion governance chain evidence.
- MVP evidence pack maps all exit criteria to deterministic test/ops evidence.

## 9. Tracking Interfaces
### 9.1 Issue Contract Fields
Each implementation issue must contain:
- `Milestone`: one of `M0`..`M9`
- `Goal`: outcome statement tied to milestone intent
- `Scope`: explicit in/out implementation boundaries
- `Acceptance Criteria`: testable completion conditions
- `Dependencies`: blocking issue IDs or external prerequisites
- `Evidence Links`: PRs, test runs, traces, audit logs, or screenshots
- `Definition of Done`: close condition beyond "code merged"

### 9.2 Label Taxonomy
Required label groups:
- `milestone:*` (example: `milestone:M1`)
- `type:*` (example: `type:feature`, `type:infra`, `type:test`)
- `area:*` (example: `area:control_plane`, `area:task_orchestrator`)
- `risk:*` (example: `risk:governance-core`)

## 10. Cadence and Update Rules
- PR-linked updates: every implementation PR references issue IDs and updates issue acceptance checklist status.
- Weekly summary: update `ImplementationProgress-v1.md` once per week with milestone percentages, active features, blockers, and evidence links.
- Milestone close rule: milestone can close only when exit evidence is attached and all required feature issues are closed.
- Governance check rule: run consistency/governance checks per `implementation/v1/workflow/RepositoryConsistencyAndGovernanceCheck-v1.md` (PR-level light checks; deep checks on milestone close and major structure/policy changes).

## 11. Related Documents
- `implementation/v1/workflow/AIAssistedDeliveryWorkflow-v1.md`
- `implementation/v1/planning/ImplementationBacklogSeed-v1.md`
- `implementation/v1/planning/ImplementationMilestones-v1.md`
- `implementation/v1/planning/ImplementationProgress-v1.md`
- `implementation/v1/mvp/MvpArchitectureRoadmap-v1.md`
- `implementation/v1/mvp/MvpCoreGovernance-v1.md`
- `implementation/v1/mvp/MvpRuntimeSpecification-v1.md`
- `implementation/v1/workflow/GitHubOperationsManagementGuide-v1.md`
- `implementation/v1/workflow/RepositoryConsistencyAndGovernanceCheck-v1.md`
