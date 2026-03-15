# OpenQilin MVP v2 - LLM Profile Binding Model

Date: `2026-03-14`
Status: `discussion draft`
Stage: `pre-kickoff`

## 1. Purpose

- Make the per-agent LLM customization idea explicit.
- Define a concrete MVP-v2 model for LLM profiles, agent bindings, project overrides, and governance controls.
- Provide a design note that can later be converted into runtime contracts and milestones.

## 2. Problem Statement

OpenQilin currently has a strong role model but a comparatively weak model-configuration model.

That creates three problems:
- different roles may behave too similarly because they share the same effective LLM posture
- project-scoped workforce roles cannot be tuned cleanly for project/domain needs
- model configuration risks becoming ad hoc if overrides are introduced without a formal binding model

MVP-v2 should fix this by making model configuration:
- explicit
- reusable
- auditable
- governed
- fail-closed

## 3. Design Goal

Introduce a governed LLM profile system where:
- named profiles define model behavior
- institutional roles bind to profile defaults
- project-scoped workforce roles inherit and optionally override those defaults
- profile selection remains separate from role authority and policy

## 4. Core Principles

### 4.1 Separate model choice from role authority
- LLM profile determines how a role reasons and responds.
- Governance policy determines what a role is allowed to do.
- These must remain distinct runtime concerns.

### 4.2 Prefer named profiles over inline parameter blobs
- Profiles should be reusable and referenceable.
- Bindings should point to profile IDs rather than duplicating parameters everywhere.

### 4.3 Support inheritance
- Global defaults should exist.
- Role defaults should inherit from global defaults.
- Project-scoped bindings should inherit from role defaults unless explicitly overridden.

### 4.4 Fail closed on invalid configuration
- Missing profile
- invalid override
- disallowed provider/model
- invalid fallback chain

All should block activation or binding rather than silently degrading.

### 4.5 Keep profile changes auditable
- Changes to profile definitions and profile bindings should be recorded as governance-relevant configuration changes.

## 5. Runtime Objects

### 5.1 `llm_profile`

Reusable named profile definition.

Suggested fields:
- `profile_id`
- `display_name`
- `provider`
- `model`
- `temperature`
- `max_tokens`
- `reasoning_mode`
- `tool_use_mode`
- `grounding_mode`
- `fallback_profiles`
- `timeout_seconds`
- `retry_policy`
- `quota_policy_ref`
- `status`

Notes:
- `fallback_profiles` should reference other named profiles, not raw model strings.
- `status` can be used to disable a profile without deleting it.

### 5.2 `institutional_role_profile_binding`

Default profile binding for stable institutional roles.

Suggested fields:
- `role`
- `profile_id`
- `effective_from`
- `status`

Target roles:
- `administrator`
- `auditor`
- `ceo`
- `cwo`
- `cso`
- `secretary`

### 5.3 `project_workforce_profile_binding`

Project-scoped binding for virtual workforce roles.

Suggested fields:
- `project_id`
- `role`
- `agent_instance_id`
- `profile_id`
- `inherits_from_profile_id`
- `override_reason`
- `status`

Example `agent_instance_id` values:
- `project_manager::proj_alpha`
- `domain_leader::proj_alpha::engineering`
- `specialist::proj_alpha::research`

### 5.4 `llm_profile_override`

Optional structured override record for project-level specialization.

Suggested fields:
- `override_id`
- `binding_target`
- `base_profile_id`
- `override_fields`
- `approval_evidence`
- `status`

Use only if MVP-v2 wants fine-grained override patches instead of requiring every override to point at a separately named profile.

## 6. Resolution Order

Suggested effective-profile resolution order:

1. explicit project workforce binding
2. project workforce override on top of base role profile
3. institutional role default binding
4. global default profile
5. fail-closed error if unresolved

This must be deterministic and traceable in runtime metadata.

## 7. Suggested Behavioral Profiles by Role

### 7.1 `auditor`
- high grounding strictness
- low creativity
- conservative tool posture
- terse, evidence-heavy response style
- low tolerance for ambiguity

### 7.2 `administrator`
- operational clarity
- deterministic response style
- emphasis on runtime integrity and system state

### 7.3 `ceo`
- strategic synthesis
- prioritization and tradeoff explanation
- concise executive framing

### 7.4 `cwo`
- planning and workforce orchestration
- execution framing
- emphasis on plans, dependencies, and scope discipline

### 7.5 `cso`
- security/risk posture
- defensive reasoning
- threat and risk communication orientation

### 7.6 `secretary`
- concise explanatory style
- route-and-summarize posture
- minimal mutation/tool posture

### 7.7 `project_manager`
- planning/decomposition strength
- task and milestone orientation
- synthesis of downstream specialist/domain input

### 7.8 `domain_leader`
- domain-specialized reasoning
- stronger depth in one function
- usually not owner-facing by default

## 8. Example Config Shape

Illustrative only:

```json
{
  "llm_profiles": {
    "global_default": {
      "provider": "gemini",
      "model": "gemini-2.0-flash",
      "temperature": 0.3,
      "max_tokens": 2048,
      "reasoning_mode": "balanced",
      "tool_use_mode": "governed",
      "grounding_mode": "required",
      "fallback_profiles": ["global_safe_fallback"],
      "status": "active"
    },
    "auditor_strict": {
      "provider": "gemini",
      "model": "gemini-2.0-flash",
      "temperature": 0.1,
      "max_tokens": 1536,
      "reasoning_mode": "high",
      "tool_use_mode": "governed_read_heavy",
      "grounding_mode": "strict_required",
      "fallback_profiles": ["global_safe_fallback"],
      "status": "active"
    },
    "pm_planner": {
      "provider": "gemini",
      "model": "gemini-2.0-flash",
      "temperature": 0.4,
      "max_tokens": 3072,
      "reasoning_mode": "high",
      "tool_use_mode": "governed_project",
      "grounding_mode": "required",
      "fallback_profiles": ["global_default"],
      "status": "active"
    },
    "dl_engineering": {
      "provider": "gemini",
      "model": "gemini-2.0-flash",
      "temperature": 0.2,
      "max_tokens": 4096,
      "reasoning_mode": "high",
      "tool_use_mode": "governed_domain",
      "grounding_mode": "required",
      "fallback_profiles": ["pm_planner"],
      "status": "active"
    }
  },
  "institutional_role_profile_bindings": {
    "administrator": "global_default",
    "auditor": "auditor_strict",
    "ceo": "global_default",
    "cwo": "global_default",
    "cso": "global_default",
    "secretary": "global_default"
  }
}
```

Illustrative project binding:

```json
{
  "project_workforce_profile_bindings": [
    {
      "project_id": "proj_alpha",
      "agent_instance_id": "project_manager::proj_alpha",
      "role": "project_manager",
      "profile_id": "pm_planner",
      "status": "active"
    },
    {
      "project_id": "proj_alpha",
      "agent_instance_id": "domain_leader::proj_alpha::engineering",
      "role": "domain_leader",
      "profile_id": "dl_engineering",
      "status": "active"
    }
  ]
}
```

## 9. Governance Rules

Suggested governance posture:

### 9.1 Who may define or modify profiles
- restricted to governance/administrative configuration authorities
- not ordinary project-scoped runtime roles

### 9.2 Who may bind profiles
- institutional defaults: governance/administrative authority only
- project workforce bindings: likely `cwo` at workforce creation/bind time, subject to policy

### 9.3 Who may override project workforce profiles
- only authorized governance/executive roles
- should require explicit reason and audit evidence

### 9.4 What must be audited
- profile creation
- profile mutation
- role/profile binding creation
- project override creation
- activation failure caused by invalid profile reference

## 10. Runtime Validation Rules

Validation should fail closed when:
- referenced `profile_id` does not exist
- referenced profile is disabled
- fallback chain contains cycles
- provider/model is disallowed by runtime policy
- override references a missing base profile
- project role is activated without a resolvable effective profile

Startup or activation checks should surface:
- missing profile definitions
- invalid institutional role bindings
- invalid project workforce bindings

## 11. Runtime Metadata

Every relevant execution should be able to report:
- `effective_profile_id`
- `effective_provider`
- `effective_model`
- `binding_source`
  - `global_default`
  - `institutional_role_binding`
  - `project_workforce_binding`
  - `project_override`

This is useful for:
- audit
- debugging
- cost attribution
- behavior analysis

## 12. Operational Benefits

If implemented well, this model gives OpenQilin:
- stronger role differentiation
- cleaner project specialization
- better control of cost/quality tradeoffs
- safer and more auditable model evolution
- easier future expansion to multiple providers/models

## 13. Recommended MVP-v2 Scope

Suggested minimum useful scope:

1. named profile catalog
2. institutional role default bindings
3. project workforce explicit bindings
4. fail-closed validation
5. audit metadata on effective profile selection

Defer if needed:
- deep override patch system
- dynamic profile editing via chat UX
- complex fallback DAGs

## 14. Open Questions

- Should project-scoped overrides point only to named profiles, or also allow structured field overrides?
- Should `secretary` have a dedicated low-cost profile class for high-volume triage?
- Should profile changes be versioned separately from other governance/policy artifacts?
- How much of the profile should be operator-visible in response/audit surfaces?

## 15. Next Step

Use this note as input for:
- the MVP-v2 architecture delta document
- milestone planning for workforce/runtime refactor
- future config and schema design
