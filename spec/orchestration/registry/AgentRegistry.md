# OpenQilin - Agent Registry Specification

## 1. Scope
- Defines agent registration, identity metadata, capability binding, and lifecycle linkage.

## 2. Registry Fields
Minimum fields:
- `agent_id`
- `role`
- `status`
- `base_model_class`
- `tool_bindings`
- `skill_bindings`
- `memory_scope`
- `project_scope`
- `autonomy_level`
- `policy_version`
- `created_at`
- `updated_at`

## 3. Registry Semantics
- Every active agent must have explicit role and scope metadata.
- `tool_bindings` and `skill_bindings` must reference active registry/catalog entries.
- Agent status changes must be traceable and auditable.
- `secretary` role is advisory-only and must not be registered with command/execution/workforce capabilities.
- `secretary` may be bound to read-only dashboard/alert/chat data views for onboarding and status support.

## 4. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| REG-001 | Every active agent MUST have a unique immutable agent_id. | critical | Task Orchestrator |

## 5. Conformance Tests
- Duplicate registration fails deterministically.
- Agent activation fails when required skill/tool bindings are missing.
- `secretary` registration fails if non-advisory authority or mutating data capabilities are requested.
