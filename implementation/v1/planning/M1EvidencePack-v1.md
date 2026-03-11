# OpenQilin v1 - M1 Evidence Pack

Date: `2026-03-11`  
Milestone: `M1 First Executable Slice`  
Primary issue: `#4` (`M1: Governed Path Kickoff`)

## 1. Scope
- Consolidate final M1 test and evidence artifacts for `M1-WP8`.
- Confirm acceptance criteria from `ImplementationExecutionPlan-v1.md` are backed by automated evidence.

## 2. Validation Commands
- `uv run pytest tests/unit tests/component tests/integration tests/contract tests/conformance`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run mypy .`

## 3. Test Evidence Map
### 3.1 Fail-Closed Policy/Budget
- `tests/unit/test_m1_wp3_policy_runtime.py`
- `tests/unit/test_m1_wp4_budget_runtime.py`
- `tests/component/test_m1_wp1_owner_command_router.py`
- `tests/integration/test_m1_wp1_governed_ingress_path.py`

### 3.2 Owner Command Accept/Deny
- `tests/component/test_m1_wp1_owner_command_router.py`
- `tests/integration/test_m1_wp1_governed_ingress_path.py`
- `tests/contract/test_m1_wp8_owner_command_contract.py`

### 3.3 CLI Command Behavior
- `tests/unit/test_m1_wp7_admin_cli.py`

### 3.4 Observability Accept/Block Emission
- `tests/unit/test_m1_wp6_observability.py`
- `tests/component/test_m1_wp1_owner_command_router.py`
- `tests/integration/test_m1_wp1_governed_ingress_path.py`

## 4. Acceptance Criteria Mapping
1. Owner command deterministic `accepted`/`denied` outcomes: covered by component/integration/contract tests above.
2. Policy uncertainty fail-closed block: covered by policy runtime + router + integration tests.
3. Budget uncertainty/runtime-failure fail-closed block: covered by budget runtime + router + integration tests.
4. Admission idempotency replay safety: covered by `tests/unit/test_m1_wp2_admission_idempotency.py` and router/integration replay tests.
5. Trace metadata on governed path: covered by integration trace-id tests and observability tests.
6. Audit evidence emitted on decision/outcome points: covered by WP6 observability tests.
7. Required test slices pass: unit/component/integration/contract/conformance command suite passes.
8. Canonical owner command envelope + connector signature/external-identity checks: covered by updated component/integration/contract owner-command tests and `tests/unit/test_m1_wp1_ingress_primitives.py`.
9. Canonical orchestrator state progression + required audit fields + required trace span boundaries: covered by updated owner-command component/integration observability assertions and `tests/unit/test_m1_wp5_dispatch_lifecycle.py` + `tests/unit/test_m1_wp6_observability.py`.

## 5. GitHub Issue Evidence Links
- https://github.com/deyiwang27/OpenQilin/issues/4#issuecomment-4036337089
- https://github.com/deyiwang27/OpenQilin/issues/4#issuecomment-4036383512
- https://github.com/deyiwang27/OpenQilin/issues/4#issuecomment-4036480967
- https://github.com/deyiwang27/OpenQilin/issues/4#issuecomment-4036512133
- https://github.com/deyiwang27/OpenQilin/issues/4#issuecomment-4036603835
- https://github.com/deyiwang27/OpenQilin/issues/4#issuecomment-4036667402
- https://github.com/deyiwang27/OpenQilin/issues/4#issuecomment-4036709005
- https://github.com/deyiwang27/OpenQilin/issues/4#issuecomment-4036736848
- https://github.com/deyiwang27/OpenQilin/issues/4#issuecomment-4036790944
- https://github.com/deyiwang27/OpenQilin/issues/4#issuecomment-4036825182
- https://github.com/deyiwang27/OpenQilin/issues/4#issuecomment-4036865485
- https://github.com/deyiwang27/OpenQilin/issues/4#issuecomment-4036991382
