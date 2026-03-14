# OpenQilin MVP v2 - Temporary Improvement Points

Date: `2026-03-14`
Status: `discussion draft`
Stage: `pre-kickoff`

## 1. Purpose

- Capture potential improvement points raised during MVP-v2 direction discussion.
- Preserve candidate UX, architecture, governance, and operations improvements in one temporary planning artifact.
- Provide a reusable input list for later MVP-v2 design finalization and milestone decomposition.

## 2. Usage Note

- This document is intentionally temporary.
- Items here are not automatically approved for implementation.
- Use this document as a discussion backlog for MVP-v2 planning refinement.

## 3. Product Strategy Improvements

### 3.1 Keep the solopreneur thesis explicit
- OpenQilin is built for the solopreneur: turning one capable person into a coordinated AI-augmented team.
- It does this through governed role delegation, project-centered execution, and explicit control over authority, budget, and evidence.
- Product and architecture decisions should continue to serve that use case directly.
- Avoid drifting into a generic assistant-everywhere product thesis.

### 3.2 Make MVP-v2 explicitly solve the known pain points
- Treat the following as explicit MVP-v2 goals:
  - setup pain
  - OAuth / channel / config complexity
  - token burn and cost waste

### 3.3 Stay Discord-first for MVP, adapter-ready long term
- Keep MVP-v2 focused on Discord to minimize scope and complexity.
- Build the underlying abstractions so broader chat-app support is practical later without rewriting governance logic.

## 4. Product and UX Improvements

### 4.1 Replace JSON-based daily chat UX
- Remove raw JSON as the normal owner-to-agent interaction format on Discord.
- Keep JSON only for internal transport, debugging, tests, or advanced admin surfaces.
- Improve daily usability by making normal interactions look like normal chat rather than API payloads.

### 4.2 Introduce hybrid interaction mode
- Support free-text chat for normal discussion, status requests, summaries, planning, and reasoning.
- Support concise command-style syntax for explicit governed actions.
- Avoid requiring raw JSON for either mode.

Examples to explore:
- free text:
  - `Give me the latest status of Project Alpha`
  - `PM, break this goal into milestones`
  - `Auditor, explain the current budget risk`
- command style:
  - `/project create`
  - `/project approve alpha`
  - `/project pause alpha`
  - `/ask pm alpha draft milestone plan`
  - `/route auditor budget alpha`

### 4.3 Define a human-friendly command grammar
- Introduce a compact, readable syntax for explicit operations.
- Keep it portable across chat surfaces rather than binding the design only to native Discord slash commands.
- Separate:
  - conversational intent
  - read/query intent
  - governed mutation intent
  - admin/ops intent

### 4.4 Improve first-use experience
- Reduce setup burden for operators.
- Provide guided setup instead of relying on raw env/config editing.
- Make first successful Discord usage easy and observable.

### 4.5 Improve response clarity
- Make it obvious who is responding, why they are responding, and whether the response is:
  - conversational
  - evidence-backed
  - a recommendation
  - a governed action result
  - a denial

### 4.6 Reduce channel noise
- Default project response should come from `project_manager`.
- Other roles should respond only on mention, escalation, or governed workflow trigger.
- Prevent “everyone in the room replies” behavior.

## 5. Discord Surface Improvements

### 5.1 Replace role-bot sprawl with stable institutional surfaces
- Keep real Discord bot identities only for stable institutional roles:
  - `administrator`
  - `auditor`
  - `ceo`
  - `cwo`
  - `cso`
  - `secretary`
- Avoid requiring project-scoped Discord bot identities.

### 5.2 Use project spaces as the main execution surface
- Create one project-facing channel or thread per active project.
- Bind that Discord space to governed project context and runtime routing.
- Use project spaces as the only human-facing access path to project-scoped workforce roles.

### 5.3 Automate project channel/thread lifecycle
- After one-time app install and permission setup, automatically:
  - create project spaces
  - bind them to `project_id`
  - rename/move/archive/lock them based on lifecycle
  - maintain required routing metadata

### 5.4 Support virtual project-role presentation
- Present project-scoped roles through:
  - institution-owned reply labels, or
  - app-owned webhooks with overridden username/avatar
- Keep runtime identity authoritative in backend metadata rather than Discord bot accounts.

### 5.5 Clarify project channel vs thread strategy
- Decide whether project workspaces should be:
  - one top-level channel per project
  - one thread per project under shared parent channel
  - mixed strategy based on lifecycle or scale

## 6. Routing and Runtime Improvements

### 6.1 Add a conversation-binding abstraction
- Introduce a runtime-owned conversation or project-space binding layer.
- Candidate binding fields:
  - `connector`
  - `guild_id`
  - `channel_id`
  - `thread_id`
  - `chat_class`
  - `project_id`
  - `default_recipient`
  - `allowed_mentions`
  - lifecycle metadata

### 6.2 Separate channel membership from routing from authority
- Membership:
  - who can be present in the surface
- Routing:
  - who receives the message
- Authority:
  - who may actually act

This separation should become an explicit runtime rule.

### 6.3 Resolve recipient in deterministic layers
- Candidate resolution order:
  1. connector + conversation binding
  2. chat class
  3. project binding
  4. default recipient
  5. mention or alias target
  6. governance/policy-triggered escalation
  7. fail-closed deny if ambiguous

### 6.4 Separate transport identity from runtime role identity
- Discord identity should be transport-facing.
- Institutional role identity should be runtime-facing.
- Project workforce identity should be project-facing and virtual when appropriate.

### 6.5 Add explicit intent classification
- Introduce a first-class distinction between:
  - discussion
  - query/read
  - governed write
  - admin/ops
  - escalation
- Use intent classification to choose free-text response, tool-read, tool-write, approval path, or denial.

## 7. Project Workforce Role Improvements

### 7.1 Keep `project_manager` as the primary project representative
- `project_manager` should remain the default responder in project spaces.
- PM should synthesize and coordinate rather than force the owner to manage multiple downstream roles directly.

### 7.2 Keep `domain_leader` behind PM by default
- Treat `domain_leader` as a project-scoped virtual role.
- Let PM communicate with DL through governed A2A by default.
- Surface DL externally only when there is a good reason such as review or escalation.

### 7.3 Keep specialists behind PM/DL
- Avoid direct specialist attendance in normal owner-facing channels.
- Preserve role hierarchy and reduce chatter.

### 7.4 Prevent direct DM access to project-scoped workforce roles
- `project_manager` and `domain_leader` should not require DM surfaces.
- Their invocation should be bound to project channels/threads where routing context exists.

## 8. Secretary Improvements

### 8.1 Activate Secretary as a real institutional front desk
- Make `secretary` a real institutional Discord surface.
- Use it for onboarding, explanation, routing help, and summarization.

### 8.2 Keep Secretary advisory-only
- Secretary should not:
  - execute commands
  - mutate runtime/project state
  - silently delegate with command authority

### 8.3 Use Secretary to reduce cognitive load
- Let owner ask Secretary:
  - who should handle something
  - what changed
  - what is blocked
  - what happened in a project
- Use Secretary as a human-friendly front door into the system.

## 9. Governance and Safety Improvements

### 9.1 Keep fail-closed behavior visible and consistent
- Missing context, ambiguous routing, or insufficient authority should fail closed.
- Denials should be human-readable and actionable.

### 9.2 Add explicit anti-loop controls
- Prevent endless role-to-role chatter in shared channels.
- Candidate controls:
  - max inter-agent hop count
  - max repeated pair rounds
  - cooldown on repeated churn
  - hard stop or escalation on cap hit

### 9.3 Keep high-impact mutations explicit
- Even with free-text UX, dangerous or important changes should require:
  - explicit command syntax, or
  - explicit confirmation

### 9.4 Add governance-aware diagnostics
- Create tooling to detect:
  - invalid bot registry
  - unsafe connector config
  - invalid project-space bindings
  - routing ambiguity
  - channel/governance mismatch

## 10. Onboarding and Operations Improvements

### 10.1 Add guided setup
- Introduce a setup flow for:
  - institutional bot tokens
  - guild selection
  - permission verification
  - project-space automation capability
  - connector secret validation

### 10.2 Add doctor / audit / probe commands
- Candidate commands:
  - `openqilin doctor`
  - `openqilin discord probe`
  - `openqilin project-space check`
  - `openqilin governance-audit`

### 10.3 Add operator-friendly troubleshooting docs
- Document:
  - setup
  - role surfaces
  - project space lifecycle
  - routing model
  - denials and recovery
  - common Discord failure cases

### 10.4 Treat cost discipline as an MVP-v2 operational goal
- Add visibility and controls for:
  - unnecessary model invocations
  - noisy multi-agent escalation chatter
  - overly expensive role/profile defaults
  - avoidable grounded-query repetition
- Make token/cost discipline part of operator UX rather than an afterthought.

## 11. Architecture Improvements Inspired by OpenClaw

### 11.1 Introduce a cleaner adapter boundary
- Move toward a structure like:
  - connector adapters
  - normalized ingress envelope
  - conversation binding resolution
  - governance router
  - runtime recipient execution
  - presentation/output layer

### 11.2 Strengthen session/conversation state handling
- Make project-space context explicit and durable.
- Track channel/thread continuity without leaking context across roles.

### 11.3 Add more reusable channel semantics
- Build the Discord redesign in a way that could later support other channels without rewriting core governance logic.

### 11.4 Improve operator-focused product packaging
- Explain OpenQilin as a product more clearly.
- Make the user-facing system model easier to understand without reading internal planning artifacts.

## 12. LLM Configuration Improvements

### 12.1 Enable per-agent LLM profile configuration
- Add configurable LLM profiles for each agent rather than relying only on one shared runtime default.
- Support differentiated model posture by role and by project-scoped workforce binding.

Candidate role examples:
- `auditor`: conservative, highly grounded, low-creativity profile
- `ceo`: strategic synthesis and summary profile
- `project_manager`: planning/decomposition optimized profile
- `domain_leader::<domain>`: domain-specialized reasoning profile
- `secretary`: concise explanation and routing profile

### 12.2 Introduce named reusable LLM profiles
- Use named profile objects rather than ad hoc per-agent parameter blobs.
- Candidate profile fields:
  - provider
  - model identifier
  - temperature
  - max tokens
  - reasoning / effort mode
  - tool-use posture
  - grounding strictness
  - fallback chain

### 12.3 Support governed agent-to-profile bindings
- Bind institutional roles to default named profiles.
- Bind project-scoped workforce roles to inherited or overridden profiles.
- Keep bindings explicit and auditable.

Candidate binding layers:
- global default profile
- institutional role default profile
- project workforce role override

### 12.4 Support project-scoped overrides
- Allow project-specific workforce instances to override role defaults when needed.
- Example:
  - `project_manager::<project_id>` inherits from `project_manager_default`
  - `domain_leader::<project_id>::engineering` overrides to an engineering-tuned profile

### 12.5 Keep model configuration under governance
- Only authorized roles should be able to change agent/profile bindings.
- Profile changes should be:
  - validated
  - auditable
  - fail-closed on invalid or missing references

### 12.6 Keep model profile separate from authority model
- Separate:
  - LLM profile configuration
  - role authority/policy
  - runtime identity
- Avoid conflating “which model a role uses” with “what the role is allowed to do.”

Reference note:
- `implementation/v2/planning/LlmProfileBindingModel-v2.md`

## 13. Potential Discussion Buckets for Later MVP-v2 Design

Suggested buckets for refinement:

1. Chat UX
- free-text vs command design
- command grammar
- alias syntax

2. Discord topology
- institutional surfaces
- project channels/threads
- webhook presentation model

3. Runtime abstractions
- conversation binding
- routing resolution
- virtual workforce identity

4. Governance semantics
- explicit confirmations
- anti-loop rules
- role attendance and authority boundaries

5. Operator experience
- onboarding
- diagnostics
- docs and troubleshooting

6. LLM configuration
- profile catalog
- role/profile bindings
- project-scoped overrides
- governance for profile changes

## 14. Immediate Next Step

Use this document as a temporary improvement backlog while finalizing:
- MVP-v2 direction
- architecture delta from v1
- milestone decomposition for the first post-v1 implementation slices
