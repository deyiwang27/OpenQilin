# OpenQilin - Tool Registry Specification

## 1. Scope
- Defines tool registration, permissions, sandbox profile, and policy constraints.

## 2. Tool Metadata
- tool_id, category, allowed_roles, sandbox_profile, network_policy, timeout_ms

## 3. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| TOOL-001 | Tool execution MUST be authorized by Policy Engine before invocation. | critical | Task Orchestrator |

## 4. Conformance Tests
- Unauthorized role-tool invocation is denied.
