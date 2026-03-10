# OpenQilin - Execution Sandbox Specification

## 1. Scope
- Defines isolation controls, sandbox profiles, and fail-closed execution behavior.

## 2. Sandbox Profiles
- `read_only`: no filesystem writes, no network egress.
- `tool_exec_restricted`: allowlisted tool calls, bounded network egress.
- `code_exec_restricted`: ephemeral workspace, strict CPU/memory/time quotas.
- `external_bridge`: brokered external calls with signed request envelope.

## 3. Isolation Controls
- Filesystem: ephemeral task-scoped root; deny host path escape.
- Network: deny-by-default egress with explicit allowlists.
- Process: PID namespace isolation; orphan/child cleanup required.
- Resources: CPU, memory, wall-clock timeout, output size quotas.
- Secrets: runtime secret injection via references only, never raw secret logs.

## 4. Failure Modes and Containment
- Quota breach -> terminate task, emit containment event.
- Policy/sandbox profile mismatch -> deny before start.
- External bridge contract failure -> fail-closed and escalate by severity.
- Repeated sandbox failures -> trigger project/agent pause workflow.

## 5. Runtime Integration Contract
- Input: task envelope + policy obligations + sandbox profile.
- Output: execution status + resource usage + artifact refs + trace metadata.
- Every sandbox action must emit start/end/failure events.

## 6. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| SAN-001 | Sandbox MUST enforce per-task resource quotas. | critical | execution_sandbox |
| SAN-002 | Forbidden capabilities MUST fail closed. | critical | execution_sandbox |
| SAN-003 | Profile selection MUST be authorized by policy obligations before execution. | critical | task_orchestrator |
| SAN-004 | Sandbox failures MUST produce immutable containment telemetry. | high | observability |
| SAN-005 | Secrets MUST NOT be persisted in logs or task outputs by default. | critical | execution_sandbox |

## 7. Conformance Tests
- Quota breach terminates execution safely and emits containment event.
- Unauthorized sandbox profile use is denied pre-dispatch.
- Denied network egress attempts are blocked and audited.
- Secret redaction policy is enforced in logs and artifacts.
