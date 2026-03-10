# OpenQilin - Failure and Recovery Model Specification

## 1. Scope
- Defines failure classes, deterministic recovery workflows, and zero-context restart protocol.

## 2. Failure Classes
- `transient`: recoverable with bounded retry.
- `persistent`: repeated failures requiring escalation/remediation.
- `safety_critical`: containment-first, no autonomous resume before approval.

## 3. Recovery Workflow (Deterministic)
1. Classify failure (`transient|persistent|safety_critical`).
2. Apply class policy:
   - transient: bounded retry with backoff.
   - persistent: pause + escalate + remediation plan.
   - safety_critical: immediate containment, block retries.
3. Emit immutable failure and escalation events.
4. Resume only after guard conditions are satisfied.

## 4. Zero-Context Restart Protocol
Mandatory restart artifact set:
- active policy metadata (`policy_version`, `policy_hash`)
- open task ledger (task ids + last known states)
- agent lifecycle snapshot
- budget reservation ledger
- communication dead-letter queue snapshot
- latest audit checkpoint

Restart sequence:
1. Load and validate restart artifacts.
2. Verify policy and budget snapshots are coherent.
3. Rebuild in-memory indexes from persisted source of record.
4. Reconcile in-flight tasks and communications.
5. Resume only tasks explicitly marked resumable.

## 5. Recovery Guards
- Resume is denied when artifact validation fails.
- Resume is denied when policy snapshot differs from active bundle without approved migration.
- Safety-critical incidents require explicit containment-clearance event.

## 6. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| FRM-001 | Safety-critical failures MUST trigger containment before retry. | critical | task_orchestrator |
| FRM-002 | Recovery behavior MUST be deterministic for same failure class + policy version. | high | runtime |
| FRM-003 | Zero-context restart MUST require validated restart artifact set. | critical | runtime |
| FRM-004 | Safety-critical recovery resume MUST require explicit clearance evidence. | critical | governance |
| FRM-005 | Recovery and restart actions MUST emit immutable audit events. | high | observability |

## 7. Conformance Tests
- Persistent failures escalate according to escalation policy.
- Safety-critical failure blocks autonomous retry.
- Restart fails when required artifact is missing or invalid.
- Restart reconciliation produces deterministic state restoration.
