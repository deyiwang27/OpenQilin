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

## 5. Tracking Interfaces
### 5.1 Issue Contract Fields
Each implementation issue must contain:
- `Milestone`: one of `M0`..`M4`
- `Goal`: outcome statement tied to milestone intent
- `Scope`: explicit in/out implementation boundaries
- `Acceptance Criteria`: testable completion conditions
- `Dependencies`: blocking issue IDs or external prerequisites
- `Evidence Links`: PRs, test runs, traces, audit logs, or screenshots
- `Definition of Done`: close condition beyond "code merged"

### 5.2 Label Taxonomy
Required label groups:
- `milestone:*` (example: `milestone:M1`)
- `type:*` (example: `type:feature`, `type:infra`, `type:test`)
- `area:*` (example: `area:control_plane`, `area:task_orchestrator`)
- `risk:*` (example: `risk:governance-core`)

## 6. Cadence and Update Rules
- PR-linked updates: every implementation PR references issue IDs and updates issue acceptance checklist status.
- Weekly summary: update `ImplementationProgress-v1.md` once per week with milestone percentages, active features, blockers, and evidence links.
- Milestone close rule: milestone can close only when exit evidence is attached and all required feature issues are closed.
- Governance check rule: run consistency/governance checks per `implementation/v1/workflow/RepositoryConsistencyAndGovernanceCheck-v1.md` (PR-level light checks; deep checks on milestone close and major structure/policy changes).

## 7. Related Documents
- `implementation/v1/workflow/AIAssistedDeliveryWorkflow-v1.md`
- `implementation/v1/planning/ImplementationBacklogSeed-v1.md`
- `implementation/v1/planning/ImplementationMilestones-v1.md`
- `implementation/v1/planning/ImplementationProgress-v1.md`
- `implementation/v1/workflow/GitHubOperationsManagementGuide-v1.md`
- `implementation/v1/workflow/RepositoryConsistencyAndGovernanceCheck-v1.md`
