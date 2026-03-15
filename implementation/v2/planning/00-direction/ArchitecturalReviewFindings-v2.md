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
- Plan longer term for an OpenQilin-owned console as a first-class operator surface instead of assuming external chat apps remain the permanent product surface.

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

## 11. Operator Visibility and Dashboard Improvements

### 11.1 Add a lightweight owner-facing visibility surface
- Treat dashboarding as a core trust surface for MVP-v2.
- The owner should be able to see:
  - what is happening
  - what is blocked
  - what needs a decision
  - what is costing money
  - whether the system is healthy

### 11.2 Add project visibility
- Show project state, progress, blockers, risks, pending approvals, recent activity, and PM summary.
- Make project detail easy to inspect without reading long Discord histories.

### 11.3 Add portfolio visibility
- Show all active projects with priority, risk, owner-waiting state, progress, and budget health.
- Help the owner understand the whole workload at a glance.

### 11.4 Add system health visibility
- Show connector health, routing failures, tool success/failure, binding integrity, loop-stop events, and worker/runtime status.
- Make governance and runtime problems visible before they become trust failures.

### 11.5 Add budget and cost visibility
- Show budget spent vs allocated per project.
- Show token/model cost by project and by role.
- Make cost anomalies visible as part of normal operator workflow.

### 11.6 Keep dashboarding decision-oriented
- Avoid building a telemetry museum.
- Prioritize views that answer:
  - what matters now
  - what needs action
  - where cost or risk is rising
  - whether the system is healthy

### 11.7 Start with four MVP-v2 views
- `Owner Inbox`
- `Projects Overview`
- `Project Detail`
- `System Health`

### 11.8 Use Discord and dashboard together in MVP-v2
- Keep Discord as the primary conversational surface for MVP-v2.
- Use the dashboard as the secondary operator surface for:
  - summary
  - inspection
  - approvals
  - diagnostics
  - cost and health monitoring

### 11.9 Pin the dashboard link in `leadership_council`
- Use `leadership_council` as the shared leadership operations surface.
- Pin the dashboard link there.
- Optionally also reflect the link in the channel topic/description.

### 11.10 Route shared alerts by severity
- Post only severity-based shared alerts into `leadership_council`.
- Let `secretary` be the default explainer and summarizer in that channel.
- Let other institutional roles respond only on mention or policy-triggered follow-up.

### 11.11 Use Secretary DM as the default private alert inbox
- Lower-severity alerts should default to `owner <-> secretary` DM.
- Secretary should summarize, explain, and help the owner decide whether escalation is needed.

### 11.12 Support owner-controlled alert forwarding
- If a private alert needs broader discussion, the owner can manually forward the alert message into:
  - `leadership_council`
  - another institutional DM
  - a project channel
- Treat forwarding as a user-controlled escalation path rather than the default for all alerts.

### 11.13 Keep alert messages self-describing
- Include alert metadata such as:
  - severity
  - alert type
  - source surface
  - affected project or subsystem
- This matters because forwarded Discord messages are snapshots and should remain understandable out of context.

Reference:
- [OperatorVisibilityModel-v1.md](/Users/deyi/Documents/2.学习/VSCodeProject/OpenQilin/implementation/v2/planning/01-product/OperatorVisibilityModel-v1.md)

## 12. Architecture Improvements Inspired by OpenClaw

### 12.1 Introduce a cleaner adapter boundary
- Move toward a structure like:
  - connector adapters
  - normalized ingress envelope
  - conversation binding resolution
  - governance router
  - runtime recipient execution
  - presentation/output layer

### 12.2 Strengthen session/conversation state handling
- Make project-space context explicit and durable.
- Track channel/thread continuity without leaking context across roles.

### 12.3 Add more reusable channel semantics
- Build the Discord redesign in a way that could later support other channels without rewriting core governance logic.

### 12.4 Improve operator-focused product packaging
- Explain OpenQilin as a product more clearly.
- Make the user-facing system model easier to understand without reading internal planning artifacts.

## 13. LLM Configuration Improvements

### 13.1 Enable per-agent LLM profile configuration
- Add configurable LLM profiles for each agent rather than relying only on one shared runtime default.
- Support differentiated model posture by role and by project-scoped workforce binding.

Candidate role examples:
- `auditor`: conservative, highly grounded, low-creativity profile
- `ceo`: strategic synthesis and summary profile
- `project_manager`: planning/decomposition optimized profile
- `domain_leader::<domain>`: domain-specialized reasoning profile
- `secretary`: concise explanation and routing profile

### 13.2 Introduce named reusable LLM profiles
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

### 13.3 Support governed agent-to-profile bindings
- Bind institutional roles to default named profiles.
- Bind project-scoped workforce roles to inherited or overridden profiles.
- Keep bindings explicit and auditable.

Candidate binding layers:
- global default profile
- institutional role default profile
- project workforce role override

### 13.4 Support project-scoped overrides
- Allow project-specific workforce instances to override role defaults when needed.
- Example:
  - `project_manager::<project_id>` inherits from `project_manager_default`
  - `domain_leader::<project_id>::engineering` overrides to an engineering-tuned profile

### 13.5 Keep model configuration under governance
- Model profile changes and bindings should remain auditable, reviewable, and fail-closed.
- Only authorized roles should be able to change agent/profile bindings.
- Profile changes should be:
  - validated
  - auditable
  - fail-closed on invalid or missing references

### 13.6 Keep model profile separate from authority model
- Separate:
  - LLM profile configuration
  - role authority/policy
  - runtime identity
- Avoid conflating "which model a role uses" with "what the role is allowed to do."

Reference note:
- [LlmProfileBindingModel-v2.md](/Users/deyi/Documents/2.学习/VSCodeProject/OpenQilin/implementation/v2/planning/02-architecture/LlmProfileBindingModel-v2.md)

## 14. Tool and Skill Registry Improvements

### 14.1 Keep the internal registry authoritative
- External tool or skill ecosystems should be treated as discovery sources, not as authoritative runtime policy.
- OpenQilin should maintain its own governed:
  - tool registry
  - skill registry
  - role/skill/tool bindings

### 14.2 Use external registries for discovery only
- Candidate external discovery sources may include:
  - official MCP Registry
  - Smithery
  - ClawHub
  - GitHub repositories
- Discovery must not equal automatic activation.

### 14.3 Add trust tiers for imported capabilities
- Introduce internal trust tiers such as:
  - core trusted
  - reviewed community
  - experimental/quarantine
  - blocked/rejected

### 14.4 Add quality and safety gates
- Before activation, imported tools/skills should be reviewed for:
  - source and maintainer identity
  - license
  - required secrets
  - network and sandbox needs
  - dependency and execution risk
  - policy fit and least-privilege binding

### 14.5 Require quarantine and testing before activation
- External candidates should enter a quarantine path first.
- Run inspection, sandbox tests, and policy binding review before production activation.

### 14.6 Support governed capability-gap requests
- If a Specialist needs a missing capability, the system should support:
  - requesting the missing capability
  - researching external candidates through approved sources
  - reviewing them internally
  - registering them into OpenQilin's own registry
- Specialists should not directly auto-install arbitrary external capabilities into production.

Reference:
- [ToolAndSkillRegistryStrategy-v1.md](/Users/deyi/Documents/2.学习/VSCodeProject/OpenQilin/implementation/v2/planning/02-architecture/ToolAndSkillRegistryStrategy-v1.md)

## 15. Agent Naming and Persona Improvements

### 15.1 Add stable human-friendly names for institutional roles
- Support stable display names for:
  - `secretary`
  - `administrator`
  - `auditor`
  - `ceo`
  - `cwo`
  - `cso`
- Improve memorability, conversational UX, and demo quality.

### 15.2 Separate role identity from display identity
- Keep `role_id` as the authoritative governance identity.
- Use `display_name` as the user-facing presentation layer.
- Keep policy, routing, and audit attached to the canonical role identity.

### 15.3 Add lightweight persona profiles
- Allow optional persona metadata such as:
  - tone
  - explanation style
  - response signature
  - avatar/theme
- Use persona to support clarity and differentiation, not roleplay theater.

### 15.4 Preserve role clarity in presentation
- When needed, show both display name and role label, for example:
  - `Iris (Secretary)`
  - `Vale (Auditor)`
- Do not let names hide authority boundaries.

Reference:
- [AgentNamingAndPersonaStrategy-v1.md](/Users/deyi/Documents/2.学习/VSCodeProject/OpenQilin/implementation/v2/planning/01-product/AgentNamingAndPersonaStrategy-v1.md)

## 16. Runtime Integration and Wiring Improvements

### 16.1 Replace no-op worker placeholders with real processing loops
- The current `orchestrator_worker` and `communication_worker` entrypoints are effectively healthy no-op loops.
- MVP-v2 should either:
  - wire them into real orchestration and delivery processing, or
  - remove/re-scope them so the runtime topology matches reality.
- Avoid shipping multi-service compose topology that implies active workers when those workers only emit readiness markers.

### 16.2 Align deployed services with the actual runtime path
- The current API runtime still builds core services from `InMemory*` repositories and clients even when external infrastructure is started.
- MVP-v2 should explicitly choose and implement one of:
  - a true externalized runtime using DB/cache/policy services, or
  - a clearly documented single-process local architecture
- Avoid presenting Postgres/Redis/OPA/LiteLLM as active dependencies if the live path still bypasses them for core state and policy.

### 16.3 Make orchestration architecture real or reduce the claim
- The workflow/graph layer is still placeholder-level while the live path dispatches imperatively from ingress.
- MVP-v2 should either:
  - implement the intended orchestration layer on the real execution path, or
  - simplify the architecture/docs so they describe the actual runtime honestly.

### 16.4 Wire callback flows into production paths
- Communication and sandbox callback modules should not remain scaffold-only.
- If callback-driven lifecycle handling remains part of the architecture, MVP-v2 should:
  - connect delivery outcomes to callback processors
  - connect sandbox outcomes to task lifecycle updates
  - verify callback paths in integration tests

### 16.5 Replace hardcoded tool-skill policy with registry-driven policy
- The current tool/skill behavior in runtime is still partly hardcoded by role.
- MVP-v2 should make the internal skill/tool registry authoritative in practice, not just in spec:
  - role -> skill bindings
  - skill -> tool bindings
  - policy/risk/budget constraints
- Avoid capability governance that requires code edits for policy changes.

### 16.6 Strengthen system-level integration tests
- Current tests prove important slices, but some entrypoint tests only validate readiness markers.
- Add system-level tests that verify:
  - workers perform real work
  - callback paths are exercised
  - state survives process boundaries correctly
  - externalized infra is actually used when configured
  - compose/runtime topology matches execution reality

### 16.7 Make constitution binding and policy enforcement real runtime behavior
- MVP-v1 already has active enforcement on the ingress path:
  - Discord governance checks are invoked before dispatch.
  - policy evaluation is invoked with fail-closed handling for commands and queries.
- MVP-v2 should preserve those live checks while closing the gap between spec and implementation.

### 16.8 Close the gap between constitutional design and runtime authority
- The current policy path uses an in-memory policy shell with a narrow hardcoded rule set rather than a true constitution-bound runtime.
- MVP-v2 should load and activate constitutional policy from the actual bundle source of truth, including:
  - `constitution/core/PolicyManifest.yaml`
  - required YAML policy artifacts
  - versioned release snapshots under `constitution/versions/`
- Avoid treating synthetic shell values like `m1-policy-shell-v1` as if they were real constitution activation metadata.
- If external policy infrastructure remains part of the architecture, it should become the real evaluation source instead of a bypassed sidecar.

### 16.9 Expand policy coverage beyond the current shell rules
- The current active policy layer enforces only a narrow set of checks such as:
  - recognized roles
  - fail-closed uncertainty/error handling
  - owner direct-to-specialist denial
  - synthetic deny actions
- MVP-v2 should expand enforcement so constitutional and governance rules are covered in runtime, not only in specification text.
- Target areas include:
  - authority matrix alignment
  - role activation status
  - obligation handling
  - escalation policy
  - budget/safety/policy consistency across connectors and execution paths

### 16.10 Add explicit constitution-runtime verification
- Add tests and startup verification for:
  - constitution bundle presence and integrity
  - manifest-required file coverage
  - active policy version/hash provenance
  - fail-closed startup on invalid constitution bundle
  - audit records that reflect the actual active constitution version
- Make it easy to prove whether the runtime is enforcing a real constitution bundle or only fallback shell behavior.

### 16.11 Make budget control a real governed runtime subsystem
- MVP-v1 already has active budget enforcement on the main command path:
  - a budget reservation stage runs after policy authorization and before dispatch
  - budget denials block task execution fail-closed
  - write tools can also reserve budget before mutation
- MVP-v2 should preserve those live controls while replacing the shell implementation with a real governed budget subsystem.

### 16.12 Close the gap between budget tracing and budget management
- The current active budget path is still an in-memory shell with a synthetic version and a single remaining-units counter.
- MVP-v2 should introduce real budget management concepts such as:
  - project-level budget allocation
  - role or capability-specific spending controls
  - policy-bound budget thresholds
  - durable reservation and spend records
  - budget state recovery across process restarts
- Avoid treating shell-level cost-unit deduction as if it were complete budget governance.

### 16.13 Improve cost accounting fidelity and operator visibility
- The runtime already exposes useful LLM cost and usage metadata such as:
  - estimated cost
  - actual cost
  - currency delta
  - token units
- MVP-v2 should connect this metadata to:
  - per-project budget views
  - per-role cost analysis
  - alerting on abnormal spend
  - dashboard-level budget status and trends
- Budget tracing should become visible and actionable for the operator, not only embedded in response payloads and audit events.

### 16.14 Add explicit budget-runtime verification
- Add tests and startup/runtime checks that prove:
  - configured budget policies are actually active
  - reservations are persistent and replay-safe
  - project budget exhaustion produces the expected deny behavior
  - tool-level write reservations and LLM-level cost accounting stay consistent
  - restart/recovery preserves budget state correctly when persistence is enabled
- Make it easy to distinguish between shell accounting behavior and real budget management behavior.

## 17. Architectural Review Findings (2026-03-15)

The following specific bugs, security issues, and coupling problems were identified in a full code review of the v1 runtime. Items are tagged with severity (`[Critical]`, `[High]`, `[Medium]`) and mapped to milestones for remediation.

### 17.1 Security Findings

**[Critical] Role self-assertion via HTTP header — `principal_resolver.py:83`**
Actor role is taken directly from `x-openqilin-actor-role` without cryptographic binding. Any caller with a valid connector secret can claim any role including `owner`. Must be fixed before Secretary and CSO activation. → M12

**[Critical] Write tool access checked against recipient, not principal — `write_tools.py:91`**
`is_write_tool_allowed` checks `context.recipient_role` (the agent being addressed) instead of `context.principal_role` (the authenticated requester). Authority boundaries for write operations are inverted. → M12

**[Critical] Unknown `chat_class` raises unhandled `KeyError` → 500 — `discord_governance.py:95`**
`_MEMBERSHIP_BY_CHAT_CLASS[chat_class]` raises `KeyError` for any unexpected value. Should fail-closed with a 403. Trivial fix, do in M11. → M11

**[Medium] `connector_verifier.py` is an empty placeholder**
Intended for additional connector verification logic. Currently a one-line docstring. → M12

### 17.2 Missing Enforcement Points

**[Critical] OPA is never called — policy enforcement is trigger-string matching — `policy_runtime_integration/client.py`**
`InMemoryPolicyRuntimeClient` checks if an action string starts with `"deny_"`. It does not contact OPA. The OPA container exists in `compose.yml` but receives no requests. Every rule in `constitution/core/PolicyRules.yaml` is declared `enforced_by: policy_engine` but never evaluated. → M12

**[Critical] Obligation application is an empty placeholder — `obligations.py`**
`allow_with_obligations` decisions pass through as unconditional allows. `reserve_budget`, `enforce_sandbox_profile`, and `require_owner_approval` obligations are never applied. → M12

**[Critical] Sandbox enforcement is an empty placeholder — `execution_sandbox/profiles/enforcement.py`**
No process isolation, seccomp, or namespace containment is applied. `SAF-001` has no implementation. → M13

**[High] Unknown dispatch targets silently succeed — `task_service.py:394-415`**
The fallback dispatch arm marks any unrecognized target as `dispatched` with a fake dispatch ID. Should fail-closed. → M12

**[Medium] Budget check silently skipped when client is `None` — `write_tools.py:404`**
`if self._budget_runtime_client is None: return None` — skips budget enforcement with no log, error, or governance record. Must fail-closed or raise. → M14

### 17.3 Data Model and State Bugs

**[Critical] LangGraph declared but not present — `task_orchestrator/state/state_machine.py`, `workflow/graph.py`**
Both files are one-line placeholders. LangGraph is not in `pyproject.toml`. All orchestration is a linear synchronous call chain inside the HTTP request handler. Adding new multi-step role workflows (CSO gates, DL escalations) to this model is unsustainable. → M13

**[High] Task status accepts arbitrary strings with no transition guard — `runtime_state.py:104-143`**
`update_task_status` accepts any string. Invalid transitions (e.g. `queued → completed`) are not rejected. Intermediate states defined in the spec (`policy_evaluation`, `budget_reservation`) are never written by the current code. → M12

**[High] Snapshot write failure causes in-memory/disk split-brain — `runtime_state.py:172-186`**
`_flush_snapshot()` raises `RuntimeStateRepositoryError` on `OSError`, which is uncaught by callers. In-memory state is mutated before the flush; a failure leaves disk and memory diverged with no recovery protocol. → M13

**[High] `dispatched` miscounted as terminal during startup recovery — `dependencies.py:156-161`**
`dispatched` (in-flight) is grouped with terminal states (`completed`, `failed`, `cancelled`) in the recovery counter, inflating the terminal count and causing incorrect recovery decisions. → M12

**[High] Failed/cancelled tasks permanently block their idempotency key — `dependencies.py:139-152`**
During startup recovery, all tasks are re-claimed in `ingress_dedupe` regardless of status. Failed or cancelled tasks prevent any future request with the same idempotency key from being admitted; legitimate retries are rejected as replays. → M12

**[Medium] Conversation history not persisted — `llm_dispatch.py:147`**
`InMemoryConversationStore` is created fresh at startup. All conversation context is lost on restart even when `runtime_persistence_enabled=True`. → M15

**[Medium] Agent registry bootstrap overwrites persisted data — `agent_registry.py`**
`bootstrap_institutional_agents()` runs on every startup with no idempotency check, overwriting persisted agent records. → M14

**[Medium] Idempotency namespaces not separated**
Ingress-level (`InMemoryIngressDedupe`) and communication-level (`InMemoryCommunicationIdempotencyStore`) stores share the same key space with no namespace prefix; task and delivery keys can silently collide. → M15

### 17.4 Architectural Coupling Problems

**[High] Dual `RuntimeServices` initialization paths — `app.py:35`, `dependencies.py:197-202`**
`build_runtime_services()` is called eagerly at module load and also has a lazy init path in `get_runtime_services()`. Two separate `RuntimeServices` instances with separate in-memory repositories can exist simultaneously, silently breaking idempotency. → M12

**[Medium] Multiple independent `RuntimeSettings()` instantiations per request**
At least four separate `RuntimeSettings()` instances can exist within a single request lifecycle (`llm_gateway/service.py`, `task_service.py`, `LlmGatewayDispatchAdapter.__init__`). Settings mutations between instantiations (common in tests) cause inconsistency. → M15

**[Medium] `orchestrator_worker` is a sleep loop with no orchestration**
The worker process emits a readiness marker and sleeps forever. All orchestration runs inline in the HTTP request handler. Decoupling orchestration from the request path requires LangGraph adoption. → M13

### 17.5 Spec vs. Implementation Gaps (Beyond Runtime Wiring)

**MCP/FastMCP declared, not implemented**
`ArchitectureBaseline-v1.md` §3.2 specifies MCP/FastMCP as tool connectivity. The execution sandbox uses direct Python function calls. No MCP server or client exists in the codebase. Defer to post-v2 but do not add new spec claims about MCP until implementation is real.

**A2A + ACP transport is in-memory only**
`a2a_validator.py` and `acp_client.py` exist, but `InMemoryAcpClient` is the only transport. No real ACP wire protocol. A2A envelopes are validated but transported in-memory.

**pgvector declared, not implemented**
`ArchitectureBaseline-v1.md` §3.3 specifies pgvector for embedding search. `InMemoryArtifactSearchReadModel` contains three hard-coded fixture records; search is substring matching on static content.

### 17.6 Test Coverage Gaps

- No tests for OPA policy evaluation or constitution YAML rule correctness
- No concurrency tests for budget reservation (`BUD-002` atomicity requirement)
- No snapshot persistence tests (write → restart → verify state recovery)
- No database integration tests against PostgreSQL or Redis
- No test for `chat_class` `KeyError` (security gap, trivial to add)
- `tests/conformance/` files are scaffolds; actual OPA conformance is entirely absent

## 18. Potential Discussion Buckets for Later MVP-v2 Design

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

## 18. Immediate Next Step

Use this document as a temporary improvement backlog while finalizing:
- MVP-v2 direction
- architecture delta from v1
- milestone decomposition for the first post-v1 implementation slices
