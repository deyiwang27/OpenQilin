# Agent Naming and Persona Strategy

Date: `2026-03-14`
Status: `discussion draft`
Stage: `pre-kickoff`

## 1. Purpose

- Define how OpenQilin should support human-friendly names and personas for agents.
- Keep agent naming aligned with governance clarity rather than turning into identity confusion.
- Make the role/name/persona split explicit for MVP-v2 planning.

## 2. Why This Matters

Using only raw role labels such as:
- `secretary`
- `administrator`
- `auditor`
- `ceo`
- `cwo`
- `cso`

is functionally clear, but not very human.

Stable names improve:
- memorability
- conversational comfort
- personality differentiation
- demo quality
- public product presentation

This is especially useful for a solopreneur product, where the user is meant to feel they are working with a coordinated AI-augmented team rather than a list of abstract system roles.

## 3. Core Principle

OpenQilin should separate:
- `role_id`
- `display_name`
- `persona_profile`

These are different concerns and should not be merged.

## 4. Identity Layers

### 4.1 `role_id`

Canonical governance identity.

Examples:
- `secretary`
- `administrator`
- `auditor`
- `ceo`
- `cwo`
- `cso`

This is what should be used for:
- policy
- routing
- authority
- bindings
- audit trails

### 4.2 `display_name`

Human-facing stable agent name.

Examples:
- `Iris`
- `Vale`
- `Orion`

This is what should be used for:
- chat presentation
- dashboard display
- screenshots and demos

### 4.3 `persona_profile`

Presentation and behavior metadata.

Examples:
- tone
- explanation style
- verbosity preference
- avatar
- response signature

This should influence presentation, not authority.

## 5. Recommended Rule

OpenQilin should use:
- `role_id` as the system-of-record identity
- `display_name` as the normal user-facing identity
- `persona_profile` as optional presentation enrichment

When clarity matters, show both:
- `Iris (Secretary)`
- `Vale (Auditor)`

This preserves friendliness without losing governance clarity.

## 6. MVP-v2 Scope Recommendation

For MVP-v2:
- support stable names for institutional roles first
- do not over-expand naming to every dynamic project-scoped role yet

Target MVP-v2 named roles:
- `secretary`
- `administrator`
- `auditor`
- `ceo`
- `cwo`
- `cso`

This is enough to materially improve user experience without creating identity sprawl.

## 7. Guardrails

### 7.1 Do not hide role authority

The user must still be able to tell what role an agent actually holds.

Bad:
- only showing a poetic or character-like name with no role context

Better:
- `Iris (Secretary)`

### 7.2 Keep names stable

Names should not drift frequently.

The user should build familiarity with:
- who each named agent is
- what kind of responsibility it holds

### 7.3 Keep policy attached to `role_id`

Changing a display name must not affect:
- permissions
- model bindings
- routing
- audit traces

### 7.4 Keep personas lightweight

Personas should support clarity and differentiation, not theatrical roleplay.

OpenQilin is a serious operator product, not a character simulator.

## 8. Suggested Runtime Model

Potential fields for institutional agents:
- `role_id`
- `display_name`
- `persona_profile_id`
- `avatar_ref`
- `status`

Potential `persona_profile` fields:
- `tone`
- `summary_style`
- `response_length`
- `signature_style`
- `default_avatar_theme`

## 9. Relationship to Other v2 Work

This strategy connects directly to:
- Discord presentation
- dashboard display
- Secretary/operator UX
- per-agent LLM profile differentiation
- public demo polish

It should stay coordinated with:
- [LlmProfileBindingModel-v2.md](/Users/deyi/Documents/2.学习/VSCodeProject/OpenQilin/implementation/v2/planning/02-architecture/LlmProfileBindingModel-v2.md)
- [TemporaryMvpPlan-v2.md](/Users/deyi/Documents/2.学习/VSCodeProject/OpenQilin/implementation/v2/planning/00-direction/TemporaryMvpPlan-v2.md)
- [TemporaryImprovementPoints-v2.md](/Users/deyi/Documents/2.学习/VSCodeProject/OpenQilin/implementation/v2/planning/00-direction/TemporaryImprovementPoints-v2.md)

## 10. Bottom Line

Yes, OpenQilin should support names for institutional agents.

The right strategy is:
- stable human-friendly names
- stable governance role IDs underneath
- lightweight persona metadata
- clear role visibility when needed

That improves usability and product quality without weakening governance.
