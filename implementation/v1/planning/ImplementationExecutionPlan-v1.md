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
- Deliverables: operator-facing promotion checklist and traceable release artifact packaging.

5. `M4-WP5` M4 evidence pack and milestone closeout validation (`issue #26`)
- Target modules: `implementation/v1/planning/M4EvidencePack-v1.md` and milestone closeout docs.
- Deliverables: acceptance-criteria mapping with final validation evidence and closeout links.

### 7.3 M4 Exit Evidence Checklist
- Release-readiness dashboards/alerts are defined, linked to runbooks, and validated.
- Migration/rollback drills are repeatable with recorded evidence.
- `full` profile smoke + conformance gates are deterministic promotion blockers.
- Release artifact/promotion checklist package is complete and operator-usable.
- Full quality/release gates pass for merged M4 scope.

## 8. Tracking Interfaces
### 8.1 Issue Contract Fields
Each implementation issue must contain:
- `Milestone`: one of `M0`..`M4`
- `Goal`: outcome statement tied to milestone intent
- `Scope`: explicit in/out implementation boundaries
- `Acceptance Criteria`: testable completion conditions
- `Dependencies`: blocking issue IDs or external prerequisites
- `Evidence Links`: PRs, test runs, traces, audit logs, or screenshots
- `Definition of Done`: close condition beyond "code merged"

### 8.2 Label Taxonomy
Required label groups:
- `milestone:*` (example: `milestone:M1`)
- `type:*` (example: `type:feature`, `type:infra`, `type:test`)
- `area:*` (example: `area:control_plane`, `area:task_orchestrator`)
- `risk:*` (example: `risk:governance-core`)

## 9. Cadence and Update Rules
- PR-linked updates: every implementation PR references issue IDs and updates issue acceptance checklist status.
- Weekly summary: update `ImplementationProgress-v1.md` once per week with milestone percentages, active features, blockers, and evidence links.
- Milestone close rule: milestone can close only when exit evidence is attached and all required feature issues are closed.
- Governance check rule: run consistency/governance checks per `implementation/v1/workflow/RepositoryConsistencyAndGovernanceCheck-v1.md` (PR-level light checks; deep checks on milestone close and major structure/policy changes).

## 10. Related Documents
- `implementation/v1/workflow/AIAssistedDeliveryWorkflow-v1.md`
- `implementation/v1/planning/ImplementationBacklogSeed-v1.md`
- `implementation/v1/planning/ImplementationMilestones-v1.md`
- `implementation/v1/planning/ImplementationProgress-v1.md`
- `implementation/v1/workflow/GitHubOperationsManagementGuide-v1.md`
- `implementation/v1/workflow/RepositoryConsistencyAndGovernanceCheck-v1.md`
