# OpenQilin - Runtime Architecture Specification

## 1. Scope
- Defines runtime components and integration contracts.

## 2. Components
- Policy Engine
- Task Orchestrator
- Execution Sandbox
- Observability

## 3. Global Runtime Rules
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| RT-001 | No action executes without Policy Engine decision. | critical | Task Orchestrator |
| RT-002 | Every execution unit MUST carry trace_id. | high | Runtime |

## 4. Conformance Tests
- Policy denial prevents execution.
