# OpenQilin MVP v2 - Temporary Direction Plan

Date: `2026-03-13`
Status: `discussion draft`
Stage: `pre-kickoff`

## 1. Purpose

- Capture the current post-v1 direction discussion in one implementation-layer planning artifact.
- Define the provisional MVP-v2 Discord operating model before detailed milestone decomposition.
- Record locked decisions separately from open questions so later discussion can refine the plan without losing the current design baseline.

## 2. Product Thesis

OpenQilin is built for the solopreneur: turning one capable person into a coordinated AI-augmented team.
It does this through governed role delegation, project-centered execution, and explicit control over authority, budget, and evidence.

This product thesis should remain the governing frame for MVP-v2 decisions.

Implication:
- OpenQilin should optimize for high-leverage, founder-grade operational workflows
- OpenQilin should not drift into a generic assistant-everywhere product
- governance, project coordination, and controlled delegation must continue to serve the solopreneur use case directly

## 3. Design Goal

MVP-v2 should keep OpenQilin governance-first while simplifying the Discord operating model:
- preserve real institutional role presence for top-level governance and executive interaction
- remove heavy manual setup for project-scoped agent communication
- replace project-scoped Discord bot identities with backend-routed virtual agents
- let Discord channels/threads represent governed workspaces, while authority and routing remain runtime-owned

## 4. MVP-v2 Product Goals

Based on pain points seen in adjacent products such as OpenClaw, MVP-v2 should explicitly aim to solve:

### 4.1 Setup pain
- reduce operator setup burden materially
- make first successful use fast and observable
- replace fragile manual setup steps with guided validation where possible

### 4.2 OAuth / channel / config complexity
- keep the MVP operational surface simple
- minimize the number of required moving pieces for normal operation
- make Discord setup understandable for a non-specialist operator

### 4.3 Token burn and cost waste
- reduce unnecessary model calls
- avoid noisy multi-agent chatter
- keep routing intentional and scoped
- make model/profile selection and grounding discipline part of cost control

### 4.4 Solopreneur-centered workflow depth
- prioritize one serious use case over broad feature spread:
  - one operator
  - one governed institution layer
  - many projects over time
  - controlled execution through project spaces and governed roles

### 4.5 Discord-first simplicity for MVP, adapter-ready architecture for later
- MVP-v2 should focus on Discord as the only primary chat surface
- longer term, OpenQilin should be architected so broader chat adapter support is possible without rewriting governance logic

## 5. Core Direction Shift from v1

v1 proved:
- multi-bot institutional Discord role UX
- governed DM and mention routing
- project governance, lifecycle, and grounded tool flows

MVP-v2 provisional shift:
- keep real Discord bot identities only for stable institutional roles
- stop modeling `project_manager` and `domain_leader` as required Discord bot identities
- use project-scoped runtime agents behind routing for project workforce roles
- make project spaces the primary communication surface for project execution

## 6. Locked Provisional Decisions

### 6.1 Participation principles
- `owner` stays present in all institutional and project spaces.
- Channel membership, message routing, and execution authority are separate concerns and must not be conflated.
- Being present in a channel does not imply default response authority.

### 6.2 Institutional Discord identities
Real Discord bot identities are planned for:
- `administrator`
- `auditor`
- `ceo`
- `cwo`
- `cso`
- `secretary`

Notes:
- `cso` and `secretary` are treated as target active roles for v2 planning even though they remain pending/inactive in v1 runtime governance.
- Institutional roles retain DM surfaces.

### 6.3 Shared institutional spaces
Planned fixed shared spaces:

1. `leadership_council`
- participants: `owner`, `administrator`, `auditor`, `ceo`, `cwo`, `cso`, `secretary`

2. `executive`
- participants: `owner`, `ceo`, `cwo`, `cso`, `secretary`

3. `governance`
- participants: `owner`, `administrator`, `auditor`, `secretary`

Behavior:
- shared channels permit broad visibility and governed interaction
- default replies should remain narrow and intentional, not “everyone responds”
- institutional roles reply on direct prompt, explicit mention, or policy-governed escalation

### 6.4 Project spaces
Each active project gets one governed project space on Discord.

Planned default participants:
- `owner`
- `ceo`
- `cwo`
- `cso`
- `project_manager`

Project-space behavior:
- `project_manager` is the default responder
- `ceo`, `cwo`, and `cso` respond only when explicitly mentioned or when policy/escalation requires them
- project channels/threads are the only supported human-facing surface for project-scoped workforce communication
- project spaces are lifecycle-aware and should become read-only or locked in terminal states except for governed closeout/read flows

### 6.5 Project-scoped virtual roles
The following are planned as backend-routed virtual roles, not standalone Discord bot identities:
- `project_manager::<project_id>`
- `domain_leader::<project_id>::<domain_key>`
- specialist/runtime worker identities behind A2A

Implications:
- no direct-message surface for `project_manager`
- no direct-message surface for `domain_leader`
- routing to these roles requires project context
- project context is expected to come from the bound project channel/thread

### 6.6 Domain Leader posture
Current provisional design:
- `domain_leader` is not a default visible participant in project channels
- `project_manager` remains the primary project-facing representative
- `project_manager` communicates with `domain_leader` and specialists through internal A2A flows
- `domain_leader` may be surfaced exceptionally when `project_manager` escalates or when a future explicit review path is approved

Rationale:
- reduce channel noise
- preserve hierarchy
- lower loop risk
- keep the project surface simple for the owner

### 6.7 Secretary posture
`secretary` is planned as a real institutional role with advisory-only authority.

Planned role shape:
- DM-capable institutional front-desk agent
- onboarding guide, explainer, summarizer, and routing assistant
- read-only access posture for relevant dashboard/alert/chat-derived views
- may recommend escalation or draft requests
- must not execute commands, mutate project/runtime state, or act as hidden delegation authority

Planned channel posture:
- present in `leadership_council`, `executive`, and `governance`
- not a default participant in project channels

## 7. Discord Surface and Routing Model

### 7.1 Routing rules
- Institutional DM messages route by real bot identity.
- Shared-channel messages route by explicit mention, direct prompt, or governance/policy escalation.
- Project-channel messages default to `project_manager`.
- Unresolved or ambiguous routing fails closed.

### 7.2 Virtual workforce invocation
For project-scoped roles:
- do not rely on native Discord user mentions
- use runtime-owned routing tied to project channel/thread context
- permit alias-style invocation if needed for future UX (`@pm`, `@dl-engineering`, etc.), but treat these as application-level commands rather than Discord-native user identities

### 7.3 Presentation model
Project-scoped virtual roles may be presented through:
- institution-owned bot reply labels, or
- app-owned webhooks with overridden username/avatar for project-scoped presentation

This is presentation only; runtime identity remains governed metadata, not Discord user identity.

## 8. Channel Strategy

### 8.1 MVP-v2 channel strategy
- Discord is the only primary chat surface for MVP-v2.
- MVP-v2 should optimize for one excellent Discord operating model rather than shallow multi-channel breadth.

### 8.2 Longer-term adapter posture
- OpenQilin should remain architecturally open to broader chat adapters after MVP-v2.
- Future channel expansion should reuse the same governance, routing, and project-space abstractions rather than create per-channel governance forks.

## 9. Discord Automation Posture

Target operating assumption:
- one-time app creation/install and permission grant remain manual/operator setup
- after install, Discord channels and threads for governed workspaces should be created and managed automatically by the system

Planned automation scope:
- create project channels/threads
- bind project Discord spaces to `project_id`
- rename/move/archive/lock project spaces as lifecycle changes
- manage thread/channel metadata needed for routing and governance

Not planned as runtime automation:
- dynamic creation of new Discord applications/bot identities per project

## 10. Safety and Loop Controls

If agents can mention or escalate to each other, MVP-v2 should enforce explicit anti-loop controls:
- bots do not autonomously continue bot-to-bot conversation without governed orchestration context
- no open-ended self-sustaining reply chains in shared channels
- maximum inter-agent hop count per trace
- maximum repeated rounds per same sender/recipient pair per trace
- cooldown or hard-stop on repeated pair churn in one channel/thread
- terminal deny/escalation behavior when loop caps are hit

Provisional baseline:
- human prompt starts the turn
- `project_manager` may escalate downstream through governed orchestration
- downstream agents answer once unless a new governed continuation is explicitly authorized

## 11. Governance Implications

MVP-v2 planning assumes:
- `owner` remains the top-level human principal
- `project_manager` is the project-facing coordinator
- `domain_leader` remains subordinate to project coordination rather than becoming a parallel owner-facing channel surface
- `secretary` remains advisory-only
- institutional executive/governance roles should not be flattened into an always-chatting panel

The design should continue to preserve:
- fail-closed routing
- explicit authority boundaries
- auditable escalation paths
- project-context-bound communication for dynamic workforce roles

## 12. Open Questions for Further Discussion

The following remain intentionally open for follow-up discussion:
- Should each project use a top-level channel, a thread under a common parent, or a mixed model?
- Should `domain_leader` ever be directly invokable by the `owner`, or only through `project_manager`?
- Should `secretary` be allowed to trigger non-authoritative escalation requests automatically, or require owner confirmation every time?
- Should project channels expose optional “review mode” personas for `domain_leader`, or keep all domain feedback synthesized by `project_manager`?
- What exact routing syntax should be used for virtual project roles (`@pm`, `/oq ask pm`, structured buttons, etc.)?
- What lifecycle states should create, unlock, archive, or lock project Discord spaces?

## 13. Suggested First v2 Planning Milestones

Provisional milestone themes for later decomposition:

1. `M11 Discord Surface Refactor`
- replace project-scoped multi-bot assumptions with fixed institutional bots plus virtual project-role routing

2. `M12 Project Space Automation`
- implement automatic Discord project channel/thread provisioning and lifecycle management

3. `M13 Project Workforce Routing`
- add project-scoped routing registry for `project_manager`, `domain_leader`, and specialist A2A coordination

4. `M14 Secretary + CSO Activation`
- activate `secretary` and `cso` as fully governed institutional Discord surfaces

5. `M15 Onboarding, Diagnostics, and Cost Discipline`
- reduce setup pain, reduce configuration friction, add guided validation/doctor flows, and tighten token/cost discipline as explicit product goals

## 14. Next Step

This document is intentionally temporary.

Immediate next step:
- continue discussion and refine this draft into a finalized MVP-v2 direction doc and milestone plan before execution kickoff.
