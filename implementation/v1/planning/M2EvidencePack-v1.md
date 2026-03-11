# OpenQilin v1 - M2 Evidence Pack

Date: `2026-03-11`  
Milestone: `M2 Execution Targets`  
Primary issue: `#6` (`M2: Execution Targets Kickoff`)

## 1. Scope
- Consolidate M2 execution-target evidence for `M2-WP5`.
- Map milestone exit criteria to automated tests and validation commands.

## 2. Validation Commands
- `uv run pytest tests/unit tests/component tests/integration tests/contract tests/conformance`
- `uv run ruff check .`
- `uv run mypy .`

## 3. Test Evidence Map
### 3.1 Sandbox Adapter Boundary
- `tests/unit/test_m1_wp5_dispatch_lifecycle.py`
- `tests/component/test_m1_wp1_owner_command_router.py`
- `tests/integration/test_m1_wp1_governed_ingress_path.py`
- `tests/conformance/test_m2_wp5_execution_targets_conformance.py`

### 3.2 LiteLLM Gateway Path and Usage/Cost Metadata
- `tests/unit/test_m2_wp2_llm_gateway.py`
- `tests/component/test_m1_wp1_owner_command_router.py`
- `tests/integration/test_m1_wp1_governed_ingress_path.py`
- `tests/conformance/test_m2_wp5_execution_targets_conformance.py`

### 3.3 Retrieval-Backed Query Baseline
- `tests/unit/test_m2_wp3_retrieval_runtime.py`
- `tests/component/test_m2_wp3_retrieval_query_router.py`
- `tests/integration/test_m2_wp3_retrieval_query_path.py`
- `tests/contract/test_m2_wp5_query_contract.py`
- `tests/conformance/test_m2_wp5_execution_targets_conformance.py`

### 3.4 `pgvector` Bootstrap and Migration Contract
- `tests/unit/test_m2_wp4_pgvector_contract.py`
- `tests/unit/test_m1_wp7_admin_cli.py`
- `tests/conformance/test_m2_wp5_execution_targets_conformance.py`

## 4. Acceptance Criteria Mapping
1. Accepted governed path executes through sandbox adapter boundary: covered by dispatch lifecycle unit tests plus component/integration/conformance owner-command acceptance tests.
2. LiteLLM gateway path runs through integration boundary with usage/cost metadata captured: covered by LiteLLM unit tests plus owner-command component/integration/conformance assertions on `llm_execution` metadata.
3. Retrieval-backed baseline path is validated by deterministic integration tests: covered by retrieval runtime unit/component/integration tests and query contract/conformance tests.
4. `pgvector` bootstrap+migration contract is validated and documented: covered by migration/compose/admin bootstrap contract unit tests and conformance artifact checks; migration documentation captured in `migrations/README.md`.
5. Full quality gates pass for merged M2 scope (`ruff`, `mypy`, `pytest` suites): covered by validation command execution listed above.

## 5. GitHub Issue Evidence Links
- Parent milestone issue: https://github.com/deyiwang27/OpenQilin/issues/6
- `M2-WP1` issue + evidence: https://github.com/deyiwang27/OpenQilin/issues/7, https://github.com/deyiwang27/OpenQilin/issues/7#issuecomment-4041387963, https://github.com/deyiwang27/OpenQilin/issues/7#issuecomment-4041410417
- `M2-WP2` issue + evidence: https://github.com/deyiwang27/OpenQilin/issues/8, https://github.com/deyiwang27/OpenQilin/issues/8#issuecomment-4041918081
- `M2-WP3` issue + evidence: https://github.com/deyiwang27/OpenQilin/issues/9, https://github.com/deyiwang27/OpenQilin/issues/9#issuecomment-4042027286
- `M2-WP4` issue + evidence: https://github.com/deyiwang27/OpenQilin/issues/10, https://github.com/deyiwang27/OpenQilin/issues/10#issuecomment-4042180056
- `M2-WP5` issue + evidence: https://github.com/deyiwang27/OpenQilin/issues/11, https://github.com/deyiwang27/OpenQilin/issues/11#issuecomment-4042243972
- Parent issue update: https://github.com/deyiwang27/OpenQilin/issues/6#issuecomment-4042246242
