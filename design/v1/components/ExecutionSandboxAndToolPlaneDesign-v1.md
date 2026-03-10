# OpenQilin v1 - Execution Sandbox and Tool Plane Design

## 1. Scope
- Define the v1 execution boundary for sandboxed actions and governed tool invocation.
- Specify how sandbox profiles, tool bindings, and skill bindings combine at runtime.

## 2. Component Boundary
Components:
- `execution_sandbox`
- tool plane (`MCP/FastMCP` + internal tool registry/skill binding enforcement)

Responsibilities:
- enforce task-scoped isolation and quotas
- validate sandbox profile against policy obligations
- resolve tool requests through skill and tool registry bindings
- block direct privileged tool execution outside approved bindings

## 3. Runtime Binding Model
Execution requires all of:
- authorized task
- active skill binding
- active tool registry entry
- approved sandbox profile
- valid policy metadata and `trace_id`

Binding chain:
- `skill_id -> tool_ids`
- `skill_id -> model_classes`
- `skill_id -> sandbox_profiles`
- `tool_id -> sandbox_profile + network_policy + timeout`

## 4. Execution Flow
1. orchestrator selects execution target and passes obligations
2. sandbox validates profile and quotas
3. tool plane validates `skill_id` and `tool_id`
4. MCP/internal tool invocation executes within selected sandbox profile
5. sandbox returns status, usage, artifact refs, and trace metadata

## 5. Sandbox Profiles
- `read_only`
- `tool_exec_restricted`
- `code_exec_restricted`
- `external_bridge`

Enforcement:
- filesystem isolation
- deny-by-default network egress
- CPU/memory/time/output quotas
- secret redaction and reference-only injection

## 6. Failure Modes
| Failure | Handling |
| --- | --- |
| profile mismatch | deny before start |
| tool not bound to skill | deny before invocation |
| quota breach | terminate safely and emit containment event |
| denied network egress | block and audit |
| repeated sandbox failures | trigger pause/escalation workflow |

## 7. Observability
- required spans:
  - `execution_sandbox`
  - `tool_invocation`
- required fields:
  - `task_id`, `trace_id`, `skill_id`, `tool_id`, `sandbox_profile`, `resource_usage`, `artifact_refs`

## 8. Related `spec/` References
- `spec/infrastructure/security/ExecutionSandbox.md`
- `spec/orchestration/registry/SkillCatalogAndBindings.md`
- `spec/orchestration/registry/ToolRegistry.md`
- `spec/orchestration/registry/AgentRegistry.md`
- `spec/orchestration/control/TaskOrchestrator.md`
- `spec/observability/AuditEvents.md`
