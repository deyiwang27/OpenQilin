# OpenQilin v1 - M10 Evidence Pack

Date: `2026-03-13`  
Milestone: `M10 Multi-Bot Discord Role UI`  
Primary issue: `#61`  
WP closeout issue: `#67` (`M10-WP6`)

## 1. Scope

- Consolidate M10 evidence for multi-bot Discord runtime, DM/mention routing, role-lock memory isolation, and outbound delivery hardening.
- Map M10 exit criteria to deterministic tests and live evidence artifacts.
- Define closeout workflow and issue linkage.

## 2. Validation Commands

- `uv run pytest tests/unit/test_m9_wp1_discord_worker_entrypoint.py tests/unit/test_m9_wp2_startup_validation.py tests/unit/test_m10_wp1_role_bot_registry.py`
- `uv run pytest tests/component/test_m10_wp2_multi_bot_runtime.py tests/integration/test_m10_wp3_discord_recipient_routing.py`
- `uv run pytest tests/unit/test_m2_wp2_llm_dispatch_role_lock.py tests/unit/test_m1_wp5_dispatch_lifecycle.py`
- `uv run pytest tests/unit/test_m10_wp5_discord_delivery_hardening.py tests/conformance/test_m9_wp2_discord_runtime_conformance.py`
- `uv run ruff check .`
- `uv run mypy .`

## 3. Evidence Map by M10 Exit Checklist

### 3.1 Role-bot identity registry and startup hardening
- Runtime/services:
  - `src/openqilin/discord_runtime/role_bot_registry.py`
  - `src/openqilin/shared_kernel/startup_validation.py`
  - `src/openqilin/apps/discord_bot_worker.py`
- Tests:
  - `tests/unit/test_m10_wp1_role_bot_registry.py`
  - `tests/unit/test_m9_wp1_discord_worker_entrypoint.py`
  - `tests/unit/test_m9_wp2_startup_validation.py`

### 3.2 Multi-bot runtime fan-in and bot-identity ingress context
- Runtime/services:
  - `src/openqilin/apps/discord_bot_worker.py`
  - `src/openqilin/discord_runtime/bridge.py`
  - `src/openqilin/control_plane/schemas/discord_ingress.py`
  - `src/openqilin/control_plane/routers/discord_ingress.py`
- Tests:
  - `tests/component/test_m10_wp2_multi_bot_runtime.py`
  - `tests/unit/test_m9_wp1_discord_bridge.py`

### 3.3 DM + mention group recipient governance routing
- Runtime/services:
  - `src/openqilin/apps/discord_bot_worker.py`
- Tests:
  - `tests/integration/test_m10_wp3_discord_recipient_routing.py`

### 3.4 Role lock, injection denial, and memory isolation
- Runtime/services:
  - `src/openqilin/task_orchestrator/dispatch/llm_dispatch.py`
  - `src/openqilin/task_orchestrator/admission/envelope_validator.py`
  - `src/openqilin/task_orchestrator/services/task_service.py`
- Tests:
  - `tests/unit/test_m2_wp2_llm_dispatch_role_lock.py`
  - `tests/unit/test_m1_wp5_dispatch_lifecycle.py`

### 3.5 Outbound delivery hardening (chunking, retry, ordering)
- Runtime/services:
  - `src/openqilin/apps/discord_bot_worker.py`
  - `src/openqilin/discord_runtime/bridge.py`
  - `src/openqilin/shared_kernel/config.py`
- Tests:
  - `tests/unit/test_m10_wp5_discord_delivery_hardening.py`
  - `tests/conformance/test_m9_wp2_discord_runtime_conformance.py`

### 3.6 Live multi-bot acceptance + operator runbook
- Operator docs:
  - `implementation/v1/planning/M10LiveAcceptanceChecklist-v1.md`
  - `implementation/v1/planning/M10MultiBotOperatorRunbook-v1.md`
- Artifact targets:
  - `implementation/v1/planning/artifacts/m10_live_acceptance_notes.md`
  - `implementation/v1/planning/artifacts/m10_live_discord_worker_logs_latest.txt`
  - `implementation/v1/planning/artifacts/m10_live_api_app_logs_latest.txt`
  - `implementation/v1/planning/artifacts/m10_live_docker_compose_ps_latest.txt`
  - `implementation/v1/planning/artifacts/m10_live_scenarios_manifest_latest.json`
- Current status:
  - pending operator live execution and evidence attachment.

## 4. Acceptance Criteria Mapping (`#67`)

1. Live Discord evidence proves DM interaction for each role bot.  
- Covered by checklist Section 4.1 and artifact targets in Section 3.6.

2. Live evidence proves mention-group chat with multiple role bots in one channel.  
- Covered by checklist Section 4.2 and artifact targets in Section 3.6.

3. Planning/progress docs link all evidence and closeout references.  
- Covered by this evidence pack plus updates in `ImplementationProgress-v1.md` and `TODO.txt`.

4. Conformance checks pass for evidence-pack integrity.  
- Covered by `tests/conformance/test_m10_wp6_evidence_pack_conformance.py`.

## 5. Milestone Closeout Workflow

- Open milestone closeout PR from `feat/mvp-1-validation` to `main`.
- Link parent issue `#61` and child issues `#62`..`#67`, `#69`..`#71`.
- Re-run validation commands in Section 2.
- Execute live checklist and attach artifacts listed in Section 3.6.
- Merge PR and update `ImplementationProgress-v1.md` / `TODO.txt`.
- Close issue `#67` and parent issue `#61` with evidence links.

## 6. GitHub Issue Links

- Parent milestone issue: https://github.com/deyiwang27/OpenQilin/issues/61
- `M10-WP1`: https://github.com/deyiwang27/OpenQilin/issues/62
- `M10-WP2`: https://github.com/deyiwang27/OpenQilin/issues/63
- `M10-WP3`: https://github.com/deyiwang27/OpenQilin/issues/64
- `M10-WP4`: https://github.com/deyiwang27/OpenQilin/issues/65
- `M10-WP5`: https://github.com/deyiwang27/OpenQilin/issues/66
- `M10-WP6`: https://github.com/deyiwang27/OpenQilin/issues/67
- `M10-WP7`: https://github.com/deyiwang27/OpenQilin/issues/69
- `M10-WP8`: https://github.com/deyiwang27/OpenQilin/issues/70
- `M10-WP9`: https://github.com/deyiwang27/OpenQilin/issues/71
