# OpenQilin - Budget Control System Specification

## 1. Scope
- Defines budget allocation, enforcement timing, thresholds, and escalation.

## 2. Budget Checkpoints
- Pre-dispatch authorization check
- In-flight metering check
- Post-commit reconciliation check

## 3. Threshold Defaults
- BUD-001: `soft_threshold_percent = 85`
- BUD-002: `hard_threshold_percent = 100`
- BUD-003: `daily_guardrail_percent = 15`

## 4. Enforcement Rules
- BUD-010: Requests breaching hard threshold MUST be denied/paused automatically.
- BUD-011: Soft threshold MUST trigger CEO+CWO notification.
- BUD-012: Parallel spend races MUST use atomic reservation before execution.

## 5. Escalation
- Risk path: `PM -> CWO -> CEO`
- Hard breach path: `Auditor -> Owner (direct)` and `CEO informed`

## 6. Conformance Tests
- Concurrent tasks cannot overspend reserved budget.
- Hard-threshold breach always produces pause event.

