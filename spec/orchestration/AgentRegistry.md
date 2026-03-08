# OpenQilin - Agent Registry Specification

## 1. Scope
- Defines agent registration, identity metadata, capability binding, and lifecycle linkage.

## 2. Registry Fields
- agent_id, role, model, tools, memory_scope, status, created_at, policy_version

## 3. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| REG-001 | Every active agent MUST have a unique immutable agent_id. | critical | Task Orchestrator |

## 4. Conformance Tests
- Duplicate registration fails deterministically.
