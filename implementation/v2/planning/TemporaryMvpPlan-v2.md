# OpenQilin MVP v2 - Temporary Direction Plan

Date: `2026-03-13`
Status: `discussion draft`
Stage: `pre-kickoff`

## 1. Purpose

- Capture the current post-v1 direction discussion in one implementation-layer planning artifact.
- Define the provisional MVP-v2 Discord operating model before detailed milestone decomposition.
- Record locked decisions separately from open questions so later discussion can refine the plan without losing the current design baseline.

## 2. Design Goal

MVP-v2 should keep OpenQilin governance-first while simplifying the Discord operating model:
- preserve real institutional role presence for top-level governance and executive interaction
- remove heavy manual setup for project-scoped agent communication
- replace project-scoped Discord bot identities with backend-routed virtual agents
- let Discord channels/threads represent governed workspaces, while authority and routing remain runtime-owned

## 3. Core Direction Shift from v1

v1 proved:
- multi-bot institutional Discord role UX
- governed DM and mention routing
- project governance, lifecycle, and grounded tool flows

MVP-v2 provisional shift:
- keep real Discord bot identities only for stable institutional roles
- stop modeling `project_manager` and `domain_leader` as required Discord bot identities
- use project-scoped runtime agents behind routing for project workforce roles
- make project spaces the primary communication surface for project execution

## 4. Locked Provisional Decisions

### 4.1 Participation principles
- `owner` stays present in all institutional and project spaces.
- Channel membership, message routing, and execution authority are separate concerns and must not be conflated.
- Being present in a channel does not imply default response authority.

### 4.2 Institutional Discord identities
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

### 4.3 Shared institutional spaces
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

### 4.4 Project spaces
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

### 4.5 Project-scoped virtual roles
The following are planned as backend-routed virtual roles, not standalone Discord bot identities:
- `project_manager::<project_id>`
- `domain_leader::<project_id>::<domain_key>`
- specialist/runtime worker identities behind A2A

Implications:
- no direct-message surface for `project_manager`
- no direct-message surface for `domain_leader`
- routing to these roles requires project context
- project context is expected to come from the bound project channel/thread

### 4.6 Domain Leader posture
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

### 4.7 Secretary posture
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

## 5. Discord Surface and Routing Model

### 5.1 Routing rules
- Institutional DM messages route by real bot identity.
- Shared-channel messages route by explicit mention, direct prompt, or governance/policy escalation.
- Project-channel messages default to `project_manager`.
- Unresolved or ambiguous routing fails closed.

### 5.2 Virtual workforce invocation
For project-scoped roles:
- do not rely on native Discord user mentions
- use runtime-owned routing tied to project channel/thread context
- permit alias-style invocation if needed for future UX (`@pm`, `@dl-engineering`, etc.), but treat these as application-level commands rather than Discord-native user identities

### 5.3 Presentation model
Project-scoped virtual roles may be presented through:
- institution-owned bot reply labels, or
- app-owned webhooks with overridden username/avatar for project-scoped presentation

This is presentation only; runtime identity remains governed metadata, not Discord user identity.

## 6. Discord Automation Posture

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

## 7. Safety and Loop Controls

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

## 8. Governance Implications

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

## 9. Open Questions for Further Discussion

The following remain intentionally open for follow-up discussion:
- Should each project use a top-level channel, a thread under a common parent, or a mixed model?
- Should `domain_leader` ever be directly invokable by the `owner`, or only through `project_manager`?
- Should `secretary` be allowed to trigger non-authoritative escalation requests automatically, or require owner confirmation every time?
- Should project channels expose optional “review mode” personas for `domain_leader`, or keep all domain feedback synthesized by `project_manager`?
- What exact routing syntax should be used for virtual project roles (`@pm`, `/oq ask pm`, structured buttons, etc.)?
- What lifecycle states should create, unlock, archive, or lock project Discord spaces?

## 10. Suggested First v2 Planning Milestones

Provisional milestone themes for later decomposition:

1. `M11 Discord Surface Refactor`
- replace project-scoped multi-bot assumptions with fixed institutional bots plus virtual project-role routing

2. `M12 Project Space Automation`
- implement automatic Discord project channel/thread provisioning and lifecycle management

3. `M13 Project Workforce Routing`
- add project-scoped routing registry for `project_manager`, `domain_leader`, and specialist A2A coordination

4. `M14 Secretary + CSO Activation`
- activate `secretary` and `cso` as fully governed institutional Discord surfaces

## 11. Next Step

This document is intentionally temporary.

Immediate next step:
- continue discussion and refine this draft into a finalized MVP-v2 direction doc and milestone plan before execution kickoff.
