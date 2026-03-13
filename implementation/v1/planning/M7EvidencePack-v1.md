# OpenQilin v1 - M7 Evidence Pack

Date: `2026-03-12`  
Milestone: `M7 MVP Persistence, Adapter, and Acceptance`  
Primary issue: `#41` (`M7: MVP Persistence, Adapter, and Acceptance Kickoff`)  
WP closeout issue: `#47` (`M7-WP6: MVP acceptance matrix and closeout evidence`)

## 1. Scope
- Consolidate M7 acceptance evidence for runtime persistence/recovery, Discord adapter governance, full-profile runtime cutover, Gemini provider-path activation, and MVP lifecycle acceptance closure.
- Map MVP exit criteria to deterministic tests, conformance checks, and operational artifacts.
- Document milestone closeout linkage workflow (parent issue, PR, merge, and close steps).

## 2. Validation Commands
- `uv run pytest -q tests/unit/test_m7_wp1_runtime_recovery.py tests/unit/test_m7_wp1_communication_repository_persistence.py tests/unit/test_m7_wp1_idempotency_cache_persistence.py`
- `uv run pytest -q tests/component/test_m7_wp2_wp3_discord_governance_router.py tests/unit/test_m7_wp2_identity_channel_repository.py`
- `uv run pytest -q tests/component/test_m7_discord_ingress_adapter_router.py`
- `uv run pytest -q tests/unit/test_m7_wp4_runtime_entrypoints.py tests/conformance/test_m7_wp4_runtime_cutover_conformance.py`
- `uv run pytest -q tests/unit/test_m7_wp5_gemini_provider_path.py tests/unit/test_m2_wp2_llm_gateway.py`
- `uv run pytest -q tests/integration/test_m7_wp6_mvp_acceptance_path.py`
- `uv run pytest -q tests/component/test_m7_completion_governance_router.py tests/unit/test_m7_completion_governance_repository.py`
- `uv run ruff check .`
- `uv run mypy .`
- Note: `docker compose config` validation is environment-dependent and was unavailable in this execution environment because `docker` CLI was not installed.

## 3. Acceptance Matrix by M7 Exit Checklist
### 3.1 Restart/recovery preserves governance and idempotency invariants and restores institutional agents
- Runtime/services:
  - `src/openqilin/data_access/repositories/runtime_state.py`
  - `src/openqilin/data_access/repositories/communication.py`
  - `src/openqilin/data_access/cache/idempotency_store.py`
  - `src/openqilin/control_plane/api/startup_recovery.py`
  - `src/openqilin/data_access/repositories/agent_registry.py`
- Tests:
  - `tests/unit/test_m7_wp1_runtime_recovery.py`
  - `tests/unit/test_m7_wp1_communication_repository_persistence.py`
  - `tests/unit/test_m7_wp1_idempotency_cache_persistence.py`

### 3.2 Discord-origin ingress is governed by fixed chat classes and identity/channel mapping policy
- Runtime/services:
  - `src/openqilin/control_plane/schemas/owner_commands.py`
  - `src/openqilin/control_plane/schemas/discord_ingress.py`
  - `src/openqilin/data_access/repositories/identity_channels.py`
  - `src/openqilin/control_plane/identity/discord_governance.py`
  - `src/openqilin/control_plane/routers/owner_commands.py`
  - `src/openqilin/control_plane/routers/discord_ingress.py`
- Tests:
  - `tests/component/test_m7_wp2_wp3_discord_governance_router.py`
  - `tests/component/test_m7_discord_ingress_adapter_router.py`
  - `tests/unit/test_m7_wp2_identity_channel_repository.py`
  - `tests/integration/test_m7_wp6_mvp_acceptance_path.py`

### 3.3 Docker `full` profile runs real runtime entrypoints with startup health dependencies
- Runtime/services:
  - `compose.yml`
  - `src/openqilin/control_plane/api/app.py`
  - `src/openqilin/apps/orchestrator_worker.py`
  - `src/openqilin/apps/communication_worker.py`
- Tests:
  - `tests/conformance/test_m7_wp4_runtime_cutover_conformance.py`
  - `tests/unit/test_m7_wp4_runtime_entrypoints.py`

### 3.4 Gemini Flash free-tier provider path executes with quota telemetry and fail-closed behavior
- Runtime/services:
  - `src/openqilin/llm_gateway/providers/gemini_flash_adapter.py`
  - `src/openqilin/llm_gateway/service.py`
  - `src/openqilin/shared_kernel/config.py`
  - `.env.example`
- Tests:
  - `tests/unit/test_m7_wp5_gemini_provider_path.py`
  - `tests/unit/test_m2_wp2_llm_gateway.py`
  - `tests/integration/test_m1_wp1_governed_ingress_path.py` (LLM path slice)

### 3.5 Full project lifecycle acceptance is validated, including completion and termination branches
- Runtime/services:
  - `src/openqilin/control_plane/routers/governance.py`
  - `src/openqilin/control_plane/routers/owner_discussions.py`
  - `src/openqilin/data_access/repositories/governance.py`
- Tests:
  - `tests/component/test_m7_completion_governance_router.py`
  - `tests/unit/test_m7_completion_governance_repository.py`
  - `tests/integration/test_m7_wp6_mvp_acceptance_path.py`
    - proposal discussion and triad approvals
    - initialization and Project Manager workforce binding
    - completion governance chain (`completion/report`, `completion/approve`, `completion/finalize`) before completed
    - active -> paused -> active -> completed -> archived path
    - active -> terminated -> archived path
    - completed read-only channel policy and archived channel lock
    - invalid transition guard (`completed -> terminated`) fail-closed

### 3.6 Quality and evidence-pack conformance contracts are wired for milestone closeout
- Tests/checks:
  - `tests/conformance/test_m7_wp6_evidence_pack_conformance.py`
  - `uv run ruff check .`
  - `uv run mypy .`

## 4. Acceptance Criteria Mapping (`#47`)
1. MVP acceptance matrix maps each M7 exit criterion to concrete tests/checks.
- Covered by Section 3 with explicit runtime module and test mapping.

2. Final validation summary is posted to parent issue `#41`.
- Covered by WP evidence comments and parent progress updates for `#42`..`#47`.

3. Milestone closeout PR references and closure steps are documented.
- Closeout sequence for M7:
  - Open milestone closeout PR from `feat/41-m7-persistence-adapter-acceptance-kickoff` to `main`.
  - In PR description, link parent issue `#41` and child issues `#42`..`#47`.
  - Re-run required gates (`ruff`, `mypy`, targeted M7 acceptance suites, and full `pytest` where required by release policy).
  - Merge PR and update `ImplementationProgress-v1.md` M7 row to `completed` and `100%`.
  - Close parent issue `#41` with merge commit and evidence links.

## 5. GitHub Issue Evidence Links
- Parent milestone issue: https://github.com/deyiwang27/OpenQilin/issues/41
- `M7-WP1` issue + evidence: https://github.com/deyiwang27/OpenQilin/issues/42
- `M7-WP2` issue + evidence: https://github.com/deyiwang27/OpenQilin/issues/43
- `M7-WP3` issue + evidence: https://github.com/deyiwang27/OpenQilin/issues/44
- `M7-WP4` issue + evidence: https://github.com/deyiwang27/OpenQilin/issues/45, https://github.com/deyiwang27/OpenQilin/issues/45#issuecomment-4051270581
- `M7-WP5` issue + evidence: https://github.com/deyiwang27/OpenQilin/issues/46, https://github.com/deyiwang27/OpenQilin/issues/46#issuecomment-4051296962
- `M7-WP6` issue + evidence: https://github.com/deyiwang27/OpenQilin/issues/47
- Parent progress updates: https://github.com/deyiwang27/OpenQilin/issues/41#issuecomment-4051270580, https://github.com/deyiwang27/OpenQilin/issues/41#issuecomment-4051296967
