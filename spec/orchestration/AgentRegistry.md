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
- Role-phase agents (`concierge_bootstrap`, `concierge_passive`) must honor phase constraints.

## 4. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| REG-001 | Every active agent MUST have a unique immutable agent_id. | critical | Task Orchestrator |

## 5. Conformance Tests
- Duplicate registration fails deterministically.
- Agent activation fails when required skill/tool bindings are missing.
- Phase-constrained concierge registration transitions follow authority policy.
