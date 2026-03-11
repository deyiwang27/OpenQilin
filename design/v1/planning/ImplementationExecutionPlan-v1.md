# OpenQilin v1 - Implementation Execution Plan

## 1. Scope
- Define the execution model for v1 implementation after design closeout.
- Lock milestone structure, feature grouping, tracking interfaces, and progress cadence.

## 2. Authority and Tracking Boundary
- `design/TODO.txt` remains the historical and design-stage tracker. It is not reused as the live implementation backlog.
- GitHub Issues/Project is the primary execution system for implementation tracking and day-to-day status.
- `design/v1/planning/ImplementationProgress-v1.md` is the in-repo mirror for milestone-level progress snapshots.

## 3. Milestone Model
Milestone names and ordering match `design/v1/planning/ImplementationMilestones-v1.md`.

| Milestone | Goal | Feature Set | Exit Evidence |
| --- | --- | --- | --- |
| `M0 Foundation Scaffold` | establish runnable implementation baseline | `uv` project initialization, base package tree, Docker Compose baseline, CI skeleton (lint/type/unit) | baseline commands execute, scaffold and checks are wired, CI baseline is running |
| `M1 First Executable Slice` | deliver first governed end-to-end path | API ingress, task admission, policy check, budget reserve, sandbox/LLM dispatch stub, audit+trace emission | owner command accept/block path works and fail-closed behavior for policy/budget uncertainty is verified |
| `M2 Execution Targets` | replace stubs with real execution adapters | real sandbox dispatch, LiteLLM-backed `llm_gateway`, basic retrieval-backed query path | governed dispatch reaches sandbox or Gemini-backed path; usage/cost metadata and retrieval path are validated |
| `M3 Communication Reliability` | harden delivery lifecycle | A2A validation, ACP send/ack/nack, retries, dead-letter flow, orchestrator callback integration | deterministic at-least-once behavior, duplicate safety, and dead-letter alert/audit evidence |
| `M4 Hardening and Release Readiness` | complete release hardening gates | dashboards/alerts, migration and rollback validation, conformance+smoke suites, release artifact prep | `full` profile passes smoke and conformance gates and release candidate is promotable |

## 4. Tracking Interfaces
### 4.1 Issue Contract Fields
Each implementation issue must contain:
- `Milestone`: one of `M0`..`M4`
- `Goal`: outcome statement tied to milestone intent
- `Scope`: explicit in/out implementation boundaries
- `Acceptance Criteria`: testable completion conditions
- `Dependencies`: blocking issue IDs or external prerequisites
- `Evidence Links`: PRs, test runs, traces, audit logs, or screenshots
- `Definition of Done`: close condition beyond "code merged"

### 4.2 Label Taxonomy
Required label groups:
- `milestone:*` (example: `milestone:M1`)
- `type:*` (example: `type:feature`, `type:infra`, `type:test`)
- `area:*` (example: `area:control_plane`, `area:task_orchestrator`)
- `risk:*` (example: `risk:governance-core`)

## 5. Cadence and Update Rules
- PR-linked updates: every implementation PR references issue IDs and updates issue acceptance checklist status.
- Weekly summary: update `ImplementationProgress-v1.md` once per week with milestone percentages, active features, blockers, and evidence links.
- Milestone close rule: milestone can close only when exit evidence is attached and all required feature issues are closed.

## 6. Related Documents
- `design/v1/foundation/AIAssistedDeliveryWorkflow-v1.md`
- `design/v1/planning/ImplementationBacklogSeed-v1.md`
- `design/v1/planning/ImplementationMilestones-v1.md`
- `design/v1/planning/ImplementationProgress-v1.md`
- `design/v1/foundation/GitHubOperationsManagementGuide-v1.md`
