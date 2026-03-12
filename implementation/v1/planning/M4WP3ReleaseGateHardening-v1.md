# OpenQilin v1 - M4-WP3 Full-Profile Smoke and Conformance Gate Hardening

Date: `2026-03-12`  
Milestone: `M4 Hardening and Release Readiness`  
Work package issue: `#24`

## 1. Scope
- Harden release-gate command determinism for CI and release-candidate promotion.
- Stabilize full-profile smoke gate contract and conformance gate mapping.
- Enforce gate/workflow alignment via static checks.

## 2. Implemented Artifacts
- `src/openqilin/release_readiness/gate_matrix.py`
  - deterministic release-gate command matrix contract
  - CI gate slice and release-candidate gate slice helpers
  - matrix invariant validation (includes required smoke + conformance promotion gates)
- `ops/scripts/run_release_gate_matrix.py`
  - deterministic matrix execution entrypoint for CI and release-candidate scopes
- `ops/scripts/check_release_gate_matrix.py`
  - static CI gate for matrix/workflow/compose/doc alignment
- `.github/workflows/ci.yml`
  - added `Release gate matrix checks` step
- `tests/unit/test_m4_wp3_release_gate_matrix.py`
  - matrix determinism and invariant coverage
- `tests/conformance/test_m4_wp3_release_gate_hardening_conformance.py`
  - workflow command alignment and full-profile smoke/conformance coverage checks
- `implementation/v1/quality/QualityAndDelivery-v1.md`
  - release-gate matrix commands and promotion-gate policy linkage

## 3. Release Gate Command Matrix (Contract Highlights)
- CI scope includes:
  - lint/format/type
  - spec integrity + migration rollback readiness + release-gate matrix checks
  - unit/component + contract/integration + conformance tests
- Release-candidate scope includes all promotion-required commands plus:
  - `docker compose --profile full run --rm admin bootstrap --smoke-in-process`

## 4. Validation Commands
- `uv run ruff check src/openqilin/release_readiness ops/scripts/check_release_gate_matrix.py ops/scripts/run_release_gate_matrix.py tests/unit/test_m4_wp3_release_gate_matrix.py tests/conformance/test_m4_wp3_release_gate_hardening_conformance.py`
- `uv run mypy .`
- `uv run pytest tests/unit/test_m4_wp3_release_gate_matrix.py tests/conformance/test_m4_wp3_release_gate_hardening_conformance.py`
- `uv run python ops/scripts/check_release_gate_matrix.py`
- `uv run pytest tests/unit tests/component tests/integration tests/contract tests/conformance`
