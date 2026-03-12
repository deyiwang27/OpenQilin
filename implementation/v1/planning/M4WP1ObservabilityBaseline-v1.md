# OpenQilin v1 - M4-WP1 Observability Baseline

Date: `2026-03-12`  
Milestone: `M4 Hardening and Release Readiness`  
Work package issue: `#22`

## 1. Scope
- Define a release-readiness dashboard and alert-threshold contract for M4-WP1.
- Provide deterministic routing and fallback semantics for alert ownership.

## 2. Implemented Artifacts
- `src/openqilin/observability/alerts/release_readiness.py`
  - release dashboard catalog (`5` dashboards, panel contracts)
  - release alert catalog (`6` alert types with threshold definitions)
  - routing ownership and runbook references
- `src/openqilin/observability/alerts/alert_emitter.py`
  - in-memory alert emitter with:
    - required alert event fields
    - `ceo` fallback routing for ambiguous owners
    - audit emission + labeled alert counters
- `tests/unit/test_m4_wp1_observability_release_readiness.py`
  - dashboard/alert catalog contract checks
  - alert emitter route/fallback/audit/metric checks

## 3. Release Alert Runbook Mapping
- `policy_eval_error_spike` -> `spec/infrastructure/operations/FailureAndRecoveryModel.md#2-recovery-posture-by-class`
- `budget_hard_breach_detected` -> `spec/governance/architecture/EscalationModel.md#5-v1-operational-escalation-paths`
- `safety_critical_incident` -> `spec/infrastructure/operations/FailureAndRecoveryModel.md#2-recovery-posture-by-class`
- `orchestration_deadlock` -> `spec/infrastructure/operations/FailureAndRecoveryModel.md#3-restart-policy-boundaries`
- `acp_dead_letter_spike` -> `spec/infrastructure/operations/FailureAndRecoveryModel.md#2-recovery-posture-by-class`
- `collector_ingest_failure` -> `spec/infrastructure/operations/DeploymentTopologyAndOps.md#5-deployment-pattern-phasing`

## 4. Validation Commands
- `uv run ruff check src/openqilin/observability/alerts tests/unit/test_m4_wp1_observability_release_readiness.py`
- `uv run mypy src/openqilin/observability/alerts`
- `uv run pytest tests/unit/test_m4_wp1_observability_release_readiness.py`
