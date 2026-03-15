# External Reference Landscape Spike

Date: `2026-03-14`
Status: `discussion draft`
Stage: `pre-kickoff`

## 1. Purpose

- Identify open-source repos beyond OpenClaw and Edict that are worth referencing for OpenQilin MVP-v2.
- Focus on repos that help with OpenQilin's actual problems:
  - better daily chat UX
  - channel/session abstraction
  - durable orchestration
  - operator visibility and intervention
  - setup simplification
  - integrations and automation
  - controlled memory/state
- Recommend where OpenQilin should study, borrow, adapt, or simply watch.

## 2. Framing

OpenQilin is not trying to be a generic AI playground.

The current product thesis is:

- OpenQilin is built for the solopreneur: turning one capable person into a coordinated AI-augmented team.
- It does this through governed role delegation, project-centered execution, and explicit control over authority, budget, and evidence.

That means the best references are not necessarily the biggest agent repos. The best references are the ones that help OpenQilin become:
- easier to use
- more durable in execution
- more observable
- more governed
- less expensive to operate badly

## 3. Selection Criteria

I used five filters:

- `product relevance`
  - does it help a serious operator, not just impress a demo viewer
- `architectural relevance`
  - does it solve routing, state, orchestration, or operator control cleanly
- `setup leverage`
  - does it reduce deployment/onboarding friction or show how to do so
- `governability`
  - can its ideas be adapted to OpenQilin's authority/budget/evidence model
- `portability`
  - are the ideas reusable without forcing OpenQilin into the wrong product identity

## 4. Highest-Value References

These are the repos I think are most worth studying next.

### 4.1 LangGraph

Repo:
- https://github.com/langchain-ai/langgraph

Why it matters:
- LangGraph explicitly positions itself as a framework to "build resilient language agents as graphs."
- It highlights durable execution and human-in-the-loop as first-class features.

What OpenQilin should learn:
- durable long-running workflow semantics
- resume-after-failure execution
- explicit interruption points
- human approval and state inspection patterns

Why it fits OpenQilin:
- OpenQilin needs project-centered execution that survives failures and can be resumed safely.
- This is much closer to OpenQilin's needs than generic free-chat multi-agent frameworks.

What not to copy blindly:
- LangGraph is still a framework, not a product.
- OpenQilin should borrow execution patterns, not turn itself into "LangGraph with Discord."

Recommendation:
- `high priority`
- especially relevant for project lifecycle orchestration, PM workflows, and approval gates

### 4.2 Letta

Repo:
- https://github.com/letta-ai/letta

Why it matters:
- Letta positions itself as a platform for building stateful agents with advanced memory.
- It also exposes both CLI and API surfaces and supports skills/subagents.

What OpenQilin should learn:
- memory layering for long-lived agent identity
- stateful agent runtime design
- separation between session context and persistent memory
- how to make agents feel continuous instead of stateless

Why it fits OpenQilin:
- OpenQilin's PM, Secretary, and institutional roles will eventually need durable memory and operating continuity.
- This is especially important for solopreneur support, where continuity is product value, not just a technical feature.

What not to copy blindly:
- OpenQilin should not become memory-first.
- Memory should support governed project execution, not replace project state and evidence systems.

Recommendation:
- `high priority`
- especially relevant for secretary continuity, PM memory, and future domain/workforce memory

### 4.3 LibreChat

Repo:
- https://github.com/danny-avila/LibreChat

Why it matters:
- LibreChat is one of the strongest self-hosted chat product references.
- It combines provider flexibility, agents, MCP support, conversation branching, secure multi-user auth, and token spend tooling in one operator-facing product.

What OpenQilin should learn:
- daily chat ergonomics
- multi-provider configuration UX
- secure self-hosted auth/admin patterns
- message branching and search
- token spend visibility
- how to expose tools and agents in a user-comprehensible way

Why it fits OpenQilin:
- OpenQilin's current JSON-shaped Discord interaction is too implementation-facing.
- LibreChat is a strong reference for what a practical human-facing AI surface should feel like.

What not to copy blindly:
- OpenQilin should not become a general-purpose chat hub.
- LibreChat is broad; OpenQilin still needs a narrower product identity.

Recommendation:
- `high priority`
- especially relevant for hybrid chat/command UX and model/provider management patterns

### 4.4 n8n

Repo:
- https://github.com/n8n-io/n8n

Why it matters:
- n8n offers 400+ integrations, AI-native workflows, and a flexible automation layer.
- It solves a real problem OpenQilin will hit after Discord: integrating external systems without custom one-off code everywhere.

What OpenQilin should learn:
- integration boundary design
- workflow/node abstraction for external actions
- when to externalize automation vs embed it in the agent runtime
- practical operator-friendly integration onboarding

Why it fits OpenQilin:
- OpenQilin is Discord-first now, but it will eventually need GitHub, Notion, Linear, email, calendar, and other business surfaces.
- n8n is a strong reference for adapter strategy and automation packaging.

What not to copy blindly:
- OpenQilin should not become a low-code automation builder.
- n8n is a good integration boundary reference, not a product model for OpenQilin.

Recommendation:
- `high priority`
- especially relevant for external action adapters and post-MVP integration strategy

## 5. Strong Secondary References

These repos are useful, but more selectively.

### 5.1 Agent Squad

Repo:
- https://github.com/awslabs/agent-squad

Why it matters:
- Agent Squad emphasizes intent classification, context management, team coordination, and dynamic delegation.

What OpenQilin should learn:
- routing and handoff heuristics
- supervisor patterns
- multi-agent context-sharing boundaries

Why it fits:
- OpenQilin will need clearer message classification and routing between institutional roles, PM, and project scopes.

Limit:
- it is still more orchestration-framework oriented than governance-product oriented

Recommendation:
- `medium priority`
- especially relevant for routing policy design

### 5.2 OpenHands

Repo:
- https://github.com/OpenHands/OpenHands

Why it matters:
- OpenHands is one of the strongest open examples of an agent product with SDK, CLI, and GUI surfaces.
- It also demonstrates a real execution runtime with cloud/local packaging and scale-up posture.

What OpenQilin should learn:
- bounded execution loop design
- agent runtime packaging
- local GUI and operator entrypoint patterns
- how to package serious agent capability without raw prompt tooling leaking everywhere

Why it fits:
- OpenQilin will likely need stronger execution surfaces for coding, research, and specialist work.

Limit:
- OpenHands is code-task centered, not solopreneur org centered.
- It is more useful as a runtime/product packaging reference than as a product thesis reference.

Recommendation:
- `medium priority`
- especially relevant for specialist execution runtimes and future GitHub-linked workflows

### 5.3 CopilotKit

Repo:
- https://github.com/CopilotKit/CopilotKit

Why it matters:
- CopilotKit focuses on generative UI, shared state, and human-in-the-loop workflows.
- It offers a clean conceptual bridge between agents, UI, and human approvals.

What OpenQilin should learn:
- human approval UX
- UI-mediated tool and workflow interactions
- how agents and UI can share state without muddying responsibilities

Why it fits:
- OpenQilin will likely need a stronger operator console later.
- CopilotKit is a good reference for building interactive approval and intervention surfaces.

Limit:
- this is more relevant if OpenQilin builds a serious web operator UI, not for Discord-first MVP-v2 alone

Recommendation:
- `medium priority`
- especially relevant for future dashboard/operator UI work

### 5.4 Open WebUI

Repo:
- https://github.com/open-webui/open-webui

Why it matters:
- Open WebUI is one of the strongest references for setup simplicity, permissions, observability, and production-facing self-hosted AI UX.

What OpenQilin should learn:
- fast self-hosted onboarding
- admin and permissions surfaces
- observability exposure
- scalable self-hosted deployment posture

Why it fits:
- OpenQilin wants to reduce setup pain and improve operator clarity.

Limit:
- it is still a broad AI UI platform, not a governed execution product

Recommendation:
- `medium priority`
- especially relevant for setup, admin UX, and self-hosted operator surfaces

## 6. Lower-Priority or Contextual References

These are useful to know, but not where I would spend time first.

### 6.1 assistant-ui

Repo:
- https://github.com/assistant-ui/assistant-ui

Value:
- production-grade chat UI primitives
- tool rendering
- inline human approvals

Use case:
- useful if OpenQilin later builds a custom React operator UI from scratch

Why lower priority:
- OpenQilin is still Discord-first in MVP-v2
- this is a component library, not a product or orchestration reference

### 6.2 Mastra

Repo:
- https://github.com/mastra-ai/mastra

Value:
- workflows
- human-in-the-loop
- context management
- observability

Why lower priority:
- overlaps with LangGraph, CopilotKit, and Agent Squad
- less immediately specific to OpenQilin's current problems than those references

## 7. Suggested Reference Strategy

I would not try to study everything equally.

The best next-pass study order is:

1. `LangGraph`
   - for durable execution and approval/resume semantics
2. `LibreChat`
   - for daily user experience, model/provider management, and token/admin controls
3. `Letta`
   - for memory/state design
4. `n8n`
   - for future integration boundary design
5. `Agent Squad`
   - for routing and context delegation
6. `OpenHands`
   - for bounded execution product/runtime patterns
7. `CopilotKit` and `Open WebUI`
   - for later operator console and self-hosted UX polish

## 8. Direct Implications for OpenQilin MVP-v2

This landscape reinforces several MVP-v2 directions already under discussion:

- stay Discord-first for now
- replace JSON daily UX with hybrid free-text plus compact commands
- build project-space routing instead of multi-bot sprawl
- add stronger observability and intervention surfaces
- make setup much easier
- expose token spend and model/profile discipline
- support durable, resumable, governed execution

It also suggests a more explicit architectural split:

- `conversation/product surface`
  - Discord now, more channels later
- `governed control plane`
  - authority, budget, evidence, lifecycle
- `orchestration runtime`
  - durable execution, task flow, recovery, routing
- `integration boundary`
  - GitHub, Notion, Linear, email, calendar, external systems
- `memory layer`
  - role continuity without replacing project truth

## 9. Bottom Line

The best external references for OpenQilin are not the loudest multi-agent demos.

The most useful repo set is:
- `LangGraph` for durable orchestration
- `Letta` for stateful memory
- `LibreChat` for operator-facing chat UX
- `n8n` for integrations
- `Agent Squad` for routing
- `OpenHands` for execution runtime packaging
- `CopilotKit` and `Open WebUI` for future operator UI and self-hosted product polish

If OpenClaw showed a broad assistant platform and Edict showed an orchestration layer over that platform, these repos help define the remaining missing pieces around:
- durability
- memory
- chat ergonomics
- integrations
- operator console design

That is the part of the landscape most likely to benefit OpenQilin.
