# OpenQilin - Skill Catalog and Bindings Specification

## 1. Scope
- Defines skill catalog structure and binding rules to tools/models.
- Defines governance controls for `skill -> policy -> tool/model` execution flow.

## 2. Skill Definition Contract
Minimum skill fields:
- `skill_id`
- `name`
- `description`
- `intent_category`
- `allowed_roles`
- `allowed_tools`
- `allowed_model_classes`
- `budget_class`
- `safety_tags`
- `version`
- `status` (`draft|active|deprecated|retired`)

## 3. Binding Model
Each active skill must have explicit bindings:
- `skill_id -> tool_ids` (MCP/tool registry references)
- `skill_id -> model_classes` (gateway-routable classes)
- `skill_id -> sandbox_profiles`
- `skill_id -> policy_constraints`

Binding constraints:
- no wildcard privileged tool access for non-governance roles
- model class must be approved for the skill's risk/safety profile
- deprecated/retired skills cannot be selected for new tasks

## 4. Execution Flow
1. Orchestrator resolves requested skill.
2. Policy engine validates role/scope/capability against skill metadata.
3. Tool/model invocation proceeds only within approved bindings.
4. Execution emits trace/audit metadata including `skill_id` and `version`.

## 5. Lifecycle and Change Control
- Skill updates require version bump.
- Active skill binding changes must be auditable and reversible.
- Breaking changes require compatibility note and migration path.

## 6. Interoperability
- Skills define governed capability contracts.
- MCP remains transport and tool-interoperability layer.
- Skill policy metadata is authoritative for runtime authorization scope.

## 7. Conformance Tests
- Skill resolution fails for inactive or unknown skill.
- Invocation outside allowed tool/model bindings is denied.
- Skill version and policy metadata are present in execution traces.
- Deprecated skills cannot be used for new task authorization.
