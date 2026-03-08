# OpenQilin - Budget Engine Contract Specification

## 1. Scope
- Defines budget thresholds, reservations, and enforcement outcomes.

## 2. Core Parameters
- soft_threshold_percent
- hard_threshold_percent
- daily_guardrail_percent

## 3. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| BUD-001 | Hard-threshold breaches MUST block or pause execution. | critical | Budget Engine |
| BUD-002 | Concurrent spend MUST use atomic reservation. | high | Budget Engine |

## 4. Conformance Tests
- Parallel requests cannot exceed reserved budget.
