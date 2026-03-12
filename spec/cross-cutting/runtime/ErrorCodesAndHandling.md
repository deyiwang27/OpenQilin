# OpenQilin - Error Codes and Handling Specification

## 1. Scope
- Defines canonical error codes and handling behavior across components.
- Defines response envelope and protocol mappings for API, A2A, and ACP surfaces.

## 2. Error Classes
- `validation_error`: request shape/schema/required-field failures.
- `authorization_error`: policy deny, unknown role, authority mismatch, trust-level violation.
- `budget_error`: reservation failure, threshold breach, reconciliation failure.
- `runtime_error`: dependency timeout, execution failure, internal service faults.
- `safety_error`: containment trigger, unsafe operation, incident-mode restrictions.

## 3. Canonical Error Envelope
Required fields in every error response:
- `code`: stable machine-readable code in lower snake-case (for example `policy_validation_error`).
- `class`: one of Section 2 classes.
- `message`: operator-readable concise reason.
- `retryable`: boolean.
- `source_component`: emitting component (`policy_engine`, `task_orchestrator`, `budget_engine`, `sandbox`, `acp_runtime`, `api`).
- `trace_id`
- `policy_version` (when policy-protected path is involved)
- `policy_hash` (when policy-protected path is involved)
- `rule_ids` (when denial/obligation rule path applies)
- `details` (optional structured diagnostics with no secrets).

## 4. Canonical Code Families
- Policy and authority: `unknown_role`, `unauthorized_action`, `policy_load_error`, `policy_validation_error`, `eval_internal_error`.
- Budget: `budget_soft_threshold`, `budget_hard_threshold`, `budget_quota_soft_threshold`, `budget_quota_hard_threshold`, `budget_reservation_failed`, `budget_reconciliation_failed`.
- Runtime and execution: `execution_dispatch_failed`, `execution_timeout`, `dependency_unavailable`.
- Safety and governance: `safety_containment_active`, `project_paused_governance`.
- Protocol and transport: `a2a_schema_invalid`, `acp_ack_timeout`, `acp_retry_exhausted`, `acp_nack_non_retryable`.

## 5. Handling Model
- Fail-closed posture for policy, safety, and governance-related failures.
- Retryable runtime/transport errors use bounded retry and idempotency keys.
- Non-retryable denials fail fast and emit immutable audit events where required.
- Error details must be redacted for secrets, credentials, and raw prompt/tool payloads.

## 6. Protocol Mapping (A2A + ACP)
- A2A envelope failures map to `status=denied|error` with canonical `code` and `trace_id`.
- ACP transport failures map to ACK/NACK/DEAD-LETTER outcomes plus canonical `code`.
- Dead-letter events must include `trace_id`, retry counters, and last failure code.

## 7. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| ERR-001 | Error responses MUST include canonical code, actionable reason, and deterministic handling metadata. | high | Runtime |

## 8. Conformance Tests
- Unknown errors map to deterministic fallback code.
- Every error response includes required envelope fields.
- Retryable transport/runtime errors follow bounded retry policy and preserve idempotency.
- Policy/safety denials fail closed and include relevant rule IDs.
- ACP dead-letter records include canonical failure code and trace metadata.
