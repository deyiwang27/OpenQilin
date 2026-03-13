# OpenQilin v1 - M9 Evidence Pack

Date: `2026-03-13`  
Milestone: `M9 MVP Real Discord Runtime and Live Validation`  
Primary issue: `#49` (`M9 kickoff: real Discord runtime integration and live MVP instance validation`)  
WP closeout issue: `#56` (`M9-WP4: MVP live-instance evidence pack and closeout`)

## 1. Scope
- Consolidate M9 acceptance evidence for the real Discord bot runtime, Docker full-profile integration, and live end-to-end MVP lifecycle validation.
- Map M9 exit criteria to deterministic tests, scripts, and operator-captured artifacts.
- Define milestone closeout linkage workflow (parent issue, PR, merge, and close steps).

## 2. Validation Commands
- `uv run pytest -q tests/unit/test_m9_wp1_discord_bridge.py tests/unit/test_m9_wp1_discord_worker_entrypoint.py`
- `uv run pytest -q tests/unit/test_m9_wp2_startup_validation.py tests/conformance/test_m9_wp2_discord_runtime_conformance.py tests/conformance/test_m7_wp4_runtime_cutover_conformance.py`
- `uv run pytest -q tests/unit/test_m9_wp3_live_acceptance_script.py`
- `uv run pytest -q tests/unit/test_m9_wp4_live_acceptance_artifact_checks.py tests/conformance/test_m9_wp4_evidence_pack_conformance.py`
- `uv run python ops/scripts/run_m9_live_discord_acceptance.py --mode preflight`
- `uv run python ops/scripts/run_m9_live_discord_acceptance.py --mode init-manifest --project-id <project_id>`
- `uv run python ops/scripts/run_m9_live_discord_acceptance.py --mode init-notes --project-id <project_id>`
- `uv run python ops/scripts/check_m9_live_acceptance_artifacts.py`
- `uv run ruff check .`
- `uv run mypy .`

## 3. Evidence Map by M9 Exit Checklist
### 3.1 Real Discord bot runtime is active and governed
- Runtime/services:
  - `src/openqilin/apps/discord_bot_worker.py`
  - `src/openqilin/discord_runtime/bridge.py`
  - `src/openqilin/control_plane/routers/discord_ingress.py`
- Tests:
  - `tests/unit/test_m9_wp1_discord_bridge.py`
  - `tests/unit/test_m9_wp1_discord_worker_entrypoint.py`

### 3.2 Docker `full` profile includes Discord worker and startup secret hardening
- Runtime/services:
  - `compose.yml`
  - `src/openqilin/shared_kernel/startup_validation.py`
  - `src/openqilin/control_plane/api/app.py`
  - `src/openqilin/apps/orchestrator_worker.py`
  - `src/openqilin/apps/communication_worker.py`
- Tests:
  - `tests/conformance/test_m9_wp2_discord_runtime_conformance.py`
  - `tests/conformance/test_m7_wp4_runtime_cutover_conformance.py`
  - `tests/unit/test_m9_wp2_startup_validation.py`

### 3.3 Live Discord acceptance scenarios are executable with deterministic artifact outputs
- Runtime/scripts:
  - `implementation/v1/planning/M9LiveAcceptanceChecklist-v1.md`
  - `ops/scripts/run_m9_live_discord_acceptance.py`
  - `ops/scripts/check_m9_live_acceptance_artifacts.py`
- Tests:
  - `tests/unit/test_m9_wp3_live_acceptance_script.py`
  - `tests/unit/test_m9_wp4_live_acceptance_artifact_checks.py`
- Artifact targets:
  - `implementation/v1/planning/artifacts/m9_live_preflight_latest.json`
  - `implementation/v1/planning/artifacts/m9_live_acceptance_manifest_latest.json`
  - `implementation/v1/planning/artifacts/m9_live_acceptance_notes.md`
  - `implementation/v1/planning/artifacts/m9_live_governance_execution_latest.json`
  - `implementation/v1/planning/artifacts/m9_live_docker_compose_ps_latest.txt`
  - `implementation/v1/planning/artifacts/m9_live_api_app_logs_latest.txt`
  - `implementation/v1/planning/artifacts/m9_live_discord_bot_worker_logs_latest.txt`

### 3.4 Live-run execution status and current execution evidence
- Current status: `completed`.
- Environment prerequisites pass (`docker` + required env keys set) and `docker compose --profile full up -d --build` boots the full stack.
- Discord runtime unblock verified:
  - `discord_bot_worker` now stays healthy and logs `discord.worker.ready` after privileged-intents configuration.
- Live execution artifacts captured:
  - `implementation/v1/planning/artifacts/m9_live_governance_execution_latest.json`
  - `implementation/v1/planning/artifacts/m9_live_docker_compose_ps_latest.txt`
  - `implementation/v1/planning/artifacts/m9_live_api_app_logs_latest.txt`
  - `implementation/v1/planning/artifacts/m9_live_discord_bot_worker_logs_latest.txt`
  - `implementation/v1/planning/artifacts/m9_live_acceptance_notes.md`
- Most recent local preflight output:
  - `[OK] command_docker: /opt/homebrew/bin/docker`
  - `[OK] env_OPENQILIN_DISCORD_BOT_TOKEN: set`
  - `[OK] env_OPENQILIN_GEMINI_API_KEY: set`
  - `[OK] env_OPENQILIN_CONNECTOR_SHARED_SECRET: set`
  - `[INFO] M9 live acceptance preflight passed.`
- Completion notes:
  - live governance lifecycle branches succeeded (`completed -> archived` and `terminated -> archived`) and guard check `completed -> terminated` was denied with expected `409`.
  - artifact-integrity check passed (`uv run python ops/scripts/check_m9_live_acceptance_artifacts.py`).

## 4. Acceptance Criteria Mapping (`#56`)
1. Publish live-instance MVP evidence pack with command matrix and runtime mapping.
- Covered by Sections 2 and 3.

2. Capture deterministic artifact locations and blocker visibility for repeatable operator execution.
- Covered by Sections 3.3 and 3.4.

3. Document milestone closeout workflow and required issue/PR linkage.
- Covered by Section 5.

## 5. Milestone Closeout Workflow
- Open milestone closeout PR from `feat/49-m9-real-discord-runtime-kickoff` to `main`.
- In PR description, link parent issue `#49` and child issues `#53`..`#56`.
- Re-run required gates (`ruff`, `mypy`, and M9-targeted/unit/conformance suites).
- Execute live checklist once operator prerequisites are available and attach artifacts/screenshots/log excerpts.
- Merge PR and update `ImplementationProgress-v1.md` and `TODO.txt` to `M9 completed`.
- Close parent issue `#49` with merge commit and evidence links.

## 6. GitHub Issue Links
- Parent milestone issue: https://github.com/deyiwang27/OpenQilin/issues/49
- `M9-WP1` issue: https://github.com/deyiwang27/OpenQilin/issues/53
- `M9-WP2` issue: https://github.com/deyiwang27/OpenQilin/issues/54
- `M9-WP3` issue: https://github.com/deyiwang27/OpenQilin/issues/55
- `M9-WP4` issue: https://github.com/deyiwang27/OpenQilin/issues/56
