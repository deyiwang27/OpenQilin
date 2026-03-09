# OpenQilin - Tool Registry Specification

## 1. Scope
- Defines tool registration, permissions, sandbox profile, and policy constraints.
- Defines tool interoperability boundary for MCP and skill-based governance bindings.

## 2. Tool Metadata
Minimum metadata:
- `tool_id`
- `name`
- `category`
- `provider_type` (`internal|external|mcp`)
- `allowed_roles`
- `allowed_skills`
- `sandbox_profile`
- `network_policy`
- `timeout_ms`
- `version`
- `status` (`active|deprecated|disabled`)

## 3. Binding Model
- Tools are invoked via approved skill bindings and policy checks.
- MCP tools must be mapped to internal `tool_id` entries before use.
- Tools without explicit skill binding are not invokable in governed execution paths.

## 4. Execution Constraints
- Tool invocation must include `trace_id` and policy metadata.
- External/untrusted channel requests cannot directly trigger privileged tool classes.
- Disabled/deprecated tool versions are denied for new task dispatch.

## 5. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| TOOL-001 | Tool execution MUST be authorized by Policy Engine before invocation. | critical | Task Orchestrator |

## 6. Conformance Tests
- Unauthorized role-tool invocation is denied.
- Invocation without approved skill binding is denied.
- MCP-mapped tool invocations preserve `tool_id` + `trace_id` correlation metadata.
