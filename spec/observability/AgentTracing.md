# OpenQilin - Agent Tracing Specification

## 1. Scope
- Defines distributed tracing across agent interactions and tool execution.

## 2. Trace Requirements
- End-to-end trace continuity across policy, orchestrator, sandbox, and events

## 3. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| TRC-001 | Every task execution path MUST preserve trace context. | critical | Runtime |

## 4. Conformance Tests
- Cross-component operations share same trace lineage.
