# OpenQilin - Runtime Architecture Specification

## 1. Scope
- Defines runtime components, contracts, and canonical governance-core execution boundary.

## 2. Runtime Components
- `policy_engine`: authorization and obligation assignment
- `task_orchestrator`: task lifecycle + dispatch pipeline
- `budget_engine`: budget reservation and threshold enforcement
- `llm_gateway`: model routing/fallback/budget attribution boundary
- `execution_sandbox`: isolated tool/code execution runtime
- `observability`: logs, traces, metrics, and immutable audit events

## 3. Canonical v1 Governance-Core Gate Order
1. Validate request envelope and actor identity.
2. Evaluate policy decision (`allow|deny|allow_with_obligations`).
3. Execute mandatory obligations in deterministic order.
4. Reserve budget (for costed actions).
5. Dispatch via sandbox/runtime target.
6. Emit observability and audit events for every critical transition.
7. Route escalation events when containment/enforcement triggers fire.

## 4. Component Boundaries
- `policy_engine` returns decisions only; does not execute tasks.
- `task_orchestrator` cannot override governance enforcement.
- `budget_engine` is authoritative for threshold-state transitions.
- `execution_sandbox` enforces isolation and cannot bypass policy context.
- `observability` receives append-only events from all runtime components.

## 5. Runtime Contract Interfaces
- Policy API: input/output per `spec/constitution/PolicyEngineContract.md`.
- Task API: lifecycle and envelope per `spec/orchestration/control/TaskOrchestrator.md`.
- Communication API: A2A payload + ACP transport contracts.
- LLM Gateway API: request/response and routing constraints per `spec/infrastructure/architecture/LlmGatewayContract.md`.
- Audit Event API: event schema per `spec/observability/AuditEvents.md`.

## 6. Deployment and Operations Alignment
- Deployment topology and promotion gates are defined in `spec/infrastructure/operations/DeploymentTopologyAndOps.md`.
- Runtime implementation order follows local-first then cloud promotion policy.

## 7. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| RT-001 | No action executes without `policy_engine` decision. | critical | task_orchestrator |
| RT-002 | Every execution unit MUST carry `trace_id` and policy metadata. | high | runtime |
| RT-003 | Budget reservation MUST complete before dispatch for costed actions. | critical | task_orchestrator |
| RT-004 | Governance enforcement actions MUST NOT be bypassed by runtime components. | critical | runtime |
| RT-005 | Obligations from `allow_with_obligations` decisions MUST be executed before dispatch. | high | task_orchestrator |
| RT-006 | Runtime event emission MUST be append-only and immutable for governance-critical actions. | critical | observability |

## 8. Conformance Tests
- Policy denial prevents execution and emits immutable deny audit event.
- Missing `trace_id` or policy metadata fails runtime validation.
- Costed task dispatch without reservation is blocked.
- Governance enforcement blocks cannot be overridden by orchestrator retry logic.
