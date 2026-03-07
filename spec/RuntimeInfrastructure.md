# OpenQilin - Agent Runtime and Infrastructure Architecture

## 1. Scope
- Defines runtime components and their integration contracts.
- This is the parent specification for:
  - `spec/PolicyEngine.md`
  - `spec/TaskOrchestrator.md`
  - `spec/ExecutionSandbox.md`
  - `spec/Observability.md`
- If component specs conflict with this file, this file takes precedence.

## 2. Components
- Policy Engine
- Task Orchestrator
- Execution Sandbox
- Observability

## 3. Component Integration Boundaries
- Policy Engine: authorization decision point for every action.
- Task Orchestrator: task lifecycle and dispatch coordinator.
- Execution Sandbox: isolated execution environment for tools/code.
- Observability: mandatory telemetry and audit trace layer.

All four components are architectural sub-components of this runtime layer, not independent top-level architectures.

## 4. Global Runtime Contracts
- RT-001: No action executes without Policy Engine decision.
- RT-002: Every execution unit MUST carry `trace_id`.
- RT-003: Side effects MUST be emitted as structured events.

## 5. Failure Model
- Component failure classes: transient, persistent, safety-critical.
- Recovery strategy per class MUST be documented and tested.

## 6. Conformance Tests
- Policy denial prevents execution.
- Trace continuity preserved across all components.
