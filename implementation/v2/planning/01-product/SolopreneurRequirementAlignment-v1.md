# Solopreneur Requirement Alignment Analysis

Date: `2026-03-14`
Status: `discussion draft`
Stage: `pre-kickoff`

## 1. Purpose

- Identify the top user requirements for OpenQilin's target user: the solopreneur.
- Compare those requirements against the current MVP-v2 planning docs.
- Highlight what is already covered, what is only partially covered, and what is still missing.

## 2. Framing

Current OpenQilin product thesis:

- OpenQilin is built for the solopreneur: turning one capable person into a coordinated AI-augmented team.
- It does this through governed role delegation, project-centered execution, and explicit control over authority, budget, and evidence.

This analysis treats that thesis as the standard.

## 3. Market Signal

The strongest recent market signals are not "more autonomous agents." They are:
- productivity and time leverage
- lower operating cost
- trust and defined control boundaries
- adaptation to real business needs
- simplicity of setup and adoption

Supporting signals:
- QuickBooks reported in its June 25, 2025 survey of 2,200+ US small businesses that the top reported AI uses were marketing, customer service, administrative tasks, data processing, and bookkeeping, and that 74% of AI users said AI was boosting productivity. Source: https://quickbooks.intuit.com/r/small-business-data/april-2025-survey/
- Paychex reported on March 18, 2025 that 66% of AI-using respondents reported increased productivity, 44% cited cost savings, and 65% of businesses were already using AI. Source: https://www.paychex.com/newsroom/news-releases/survey-finds-ai-is-empowering-small-businesses
- The Federal Reserve's 2026 report on employer firms found that among AI users, top changes were in writing/marketing, productivity, planning/analysis, and administrative business functions. It also found top AI challenges included accuracy, adapting tools to business needs, data security/privacy concerns, time to implement/train, and cost. Source: https://www.fedsmallbusiness.org/-/media/project/clevelandfedtenant/fsbsite/reports/2026/2026-report-on-employer-firms/2026-report-on-employer-firms.pdf
- Deloitte reported on July 29, 2025 that trust was the main barrier to agentic AI adoption and that most respondents trusted AI agents only within a defined framework. Source: https://www.deloitte.com/us/en/about/press-room/trust-main-barrier-to-agentic-ai-adoption-in-finance-and-accounting.html

Inference:
- OpenQilin's target user does not just want an assistant.
- They want leverage, but only if it is understandable, trustworthy, affordable, and adaptable to their actual work.

## 4. Top Solopreneur Requirements

The following list is inferred from the market signal above and tailored to OpenQilin's intended product scope.

### 4.1 Real productivity leverage

The product must save time and reduce coordination burden in actual daily work:
- planning
- follow-up
- status tracking
- admin overhead
- decision support

This is the most basic requirement. If the user does not feel a shorter path from goal to progress, the product fails.

### 4.2 Fast time to first value

A solopreneur does not want a complex system setup project.

They need:
- simple onboarding
- fast first successful use
- clear guidance
- low configuration burden

### 4.3 Trustworthy control boundaries

The user needs AI to act within understandable limits.

That includes:
- explicit authority boundaries
- controlled mutation behavior
- visible denials and approvals
- evidence-backed outputs when decisions matter

### 4.4 Cost discipline

The user needs meaningful output per dollar, not expensive agent theater.

That includes:
- low-noise routing
- reduced redundant model calls
- visibility into token/model usage
- bounded escalation behavior

### 4.5 Human-friendly daily interaction

The product must feel usable in normal work.

That means:
- natural chat for common tasks
- concise commands for precise actions
- no raw JSON daily UX
- low cognitive overhead

### 4.6 Project and task visibility

A solopreneur needs to know:
- what is active
- what is blocked
- what changed
- what needs attention
- which agent is doing what

Without visibility, the system becomes another source of uncertainty.

### 4.7 Adaptation to the user's business and workflow

The product must fit real operating context.

That includes:
- role specialization
- project-specific context
- business-specific templates or playbooks
- the ability to adapt to different kinds of work over time

### 4.8 Integration with existing tools

The user will not live inside one AI surface forever.

They will eventually need:
- chat integration
- project/document/code system integration
- external action adapters

### 4.9 Continuity and memory

The product should remember enough to be useful over time:
- project continuity
- role continuity
- recurring preferences
- historical context

This should support work, not replace governed source-of-truth state.

### 4.10 Security, privacy, and reliability

Even for a solopreneur, this matters.

They need confidence that:
- data handling is sensible
- outputs are grounded
- the system fails safely
- runtime behavior is reliable enough for repeated use

## 5. Alignment to Current Docs

Current planning docs reviewed:
- [TemporaryMvpPlan-v2.md](/Users/deyi/Documents/2.学习/VSCodeProject/OpenQilin/implementation/v2/planning/00-direction/TemporaryMvpPlan-v2.md)
- [TemporaryImprovementPoints-v2.md](/Users/deyi/Documents/2.学习/VSCodeProject/OpenQilin/implementation/v2/planning/00-direction/TemporaryImprovementPoints-v2.md)
- [LlmProfileBindingModel-v2.md](/Users/deyi/Documents/2.学习/VSCodeProject/OpenQilin/implementation/v2/planning/02-architecture/LlmProfileBindingModel-v2.md)
- [OpenClawReferenceLearningReport-v1.md](/Users/deyi/Documents/2.学习/VSCodeProject/OpenQilin/implementation/v2/planning/04-research/OpenClawReferenceLearningReport-v1.md)
- [ExternalReferenceLandscapeSpike-v1.md](/Users/deyi/Documents/2.学习/VSCodeProject/OpenQilin/implementation/v2/planning/04-research/ExternalReferenceLandscapeSpike-v1.md)

### 5.1 Covered well

#### A. Trustworthy control boundaries

Coverage status:
- `well covered`

Why:
- the product thesis explicitly centers authority, budget, and evidence
- the docs consistently preserve fail-closed routing, governed role delegation, explicit authority boundaries, and project-context-bound communication

Evidence in current docs:
- [TemporaryMvpPlan-v2.md](/Users/deyi/Documents/2.学习/VSCodeProject/OpenQilin/implementation/v2/planning/00-direction/TemporaryMvpPlan-v2.md)
- [TemporaryImprovementPoints-v2.md](/Users/deyi/Documents/2.学习/VSCodeProject/OpenQilin/implementation/v2/planning/00-direction/TemporaryImprovementPoints-v2.md)

#### B. Fast time to first value / setup reduction

Coverage status:
- `well covered`

Why:
- setup pain, OAuth/channel/config complexity, and guided setup are already explicit MVP-v2 goals

Evidence:
- [TemporaryMvpPlan-v2.md](/Users/deyi/Documents/2.学习/VSCodeProject/OpenQilin/implementation/v2/planning/00-direction/TemporaryMvpPlan-v2.md)
- [TemporaryImprovementPoints-v2.md](/Users/deyi/Documents/2.学习/VSCodeProject/OpenQilin/implementation/v2/planning/00-direction/TemporaryImprovementPoints-v2.md)

#### C. Cost discipline

Coverage status:
- `well covered`

Why:
- token burn and cost waste are explicitly called out
- anti-loop controls, per-agent LLM profiles, routing discipline, and reduced chatter are already part of the planning set

Evidence:
- [TemporaryMvpPlan-v2.md](/Users/deyi/Documents/2.学习/VSCodeProject/OpenQilin/implementation/v2/planning/00-direction/TemporaryMvpPlan-v2.md)
- [TemporaryImprovementPoints-v2.md](/Users/deyi/Documents/2.学习/VSCodeProject/OpenQilin/implementation/v2/planning/00-direction/TemporaryImprovementPoints-v2.md)
- [LlmProfileBindingModel-v2.md](/Users/deyi/Documents/2.学习/VSCodeProject/OpenQilin/implementation/v2/planning/02-architecture/LlmProfileBindingModel-v2.md)

#### D. Human-friendly daily interaction

Coverage status:
- `well covered`

Why:
- replacing JSON daily UX with hybrid free-text plus concise command syntax is already explicit

Evidence:
- [TemporaryImprovementPoints-v2.md](/Users/deyi/Documents/2.学习/VSCodeProject/OpenQilin/implementation/v2/planning/00-direction/TemporaryImprovementPoints-v2.md)

#### E. Project-centered execution

Coverage status:
- `well covered`

Why:
- project spaces, PM-default routing, virtual workforce roles, and lifecycle-aware project communication are central to the current design

Evidence:
- [TemporaryMvpPlan-v2.md](/Users/deyi/Documents/2.学习/VSCodeProject/OpenQilin/implementation/v2/planning/00-direction/TemporaryMvpPlan-v2.md)
- [TemporaryImprovementPoints-v2.md](/Users/deyi/Documents/2.学习/VSCodeProject/OpenQilin/implementation/v2/planning/00-direction/TemporaryImprovementPoints-v2.md)

### 5.2 Covered partially

#### A. Real productivity leverage

Coverage status:
- `partial`

What is covered:
- the thesis says the product is for solopreneur leverage
- project execution, PM coordination, and Secretary support are aligned with that

What is missing:
- explicit definition of the first 3 to 5 core workflows that must save time
- explicit success criteria for productivity gain
- explicit "time saved / coordination load reduced" product metrics

Assessment:
- the intent is clear
- the operating outcomes are not yet explicit enough

#### B. Project and task visibility

Coverage status:
- `partial`

What is covered:
- better observability and intervention are mentioned
- reference studies on OpenClaw and Edict already identify dashboard/visibility gaps

What is missing:
- a concrete MVP-v2 visibility surface
- defined operator dashboard, inbox, alerts, or status model
- an explicit answer to "how does the owner know what matters right now?"

Assessment:
- recognized gap
- not yet planned concretely enough

#### C. Adaptation to the user's business and workflow

Coverage status:
- `partial`

What is covered:
- project-scoped PM/DL roles
- per-agent LLM profiles
- eventual adapter-ready architecture

What is missing:
- explicit business templates or operating playbooks
- explicit customization layer for different solopreneur work modes
- clearer guidance on how OpenQilin adapts to different project types

Assessment:
- the technical hooks exist
- the product-level adaptation story is still underdeveloped

#### D. Integration with existing tools

Coverage status:
- `partial`

What is covered:
- the docs explicitly keep the architecture adapter-ready
- external references note the future need for GitHub, Notion, Linear, email, calendar, and other systems

What is missing:
- a concrete MVP-v2 integration boundary
- a prioritized integration roadmap
- explicit definition of which external systems matter first for the solopreneur ICP

Assessment:
- direction exists
- near-term product decision is still open

#### E. Continuity and memory

Coverage status:
- `partial`

What is covered:
- LLM profile binding is explicit
- external reference work identifies memory/state as an important future layer

What is missing:
- a concrete memory model for Secretary, PM, and institutional roles
- a distinction between conversational memory, project memory, and governed evidence state

Assessment:
- clearly relevant
- not yet represented in a dedicated OpenQilin design note

#### F. Security, privacy, and reliability

Coverage status:
- `partial`

What is covered:
- fail-closed behavior
- governance-aware diagnostics
- evidence orientation
- anti-loop controls

What is missing:
- explicit privacy posture
- explicit secret/data handling model for Discord and future adapters
- explicit reliability/error-budget or recovery expectations at the product level

Assessment:
- the safety instinct is present
- the user-facing trust posture is still incomplete

### 5.3 Missing or under-specified

#### A. Explicit time-to-value and ROI success metrics

Coverage status:
- `missing`

Gap:
- current docs do not define how OpenQilin will prove it helps a solopreneur enough to keep using it

Examples of missing criteria:
- time to first successful project-space workflow
- time from request to actionable plan
- reduction in manual coordination effort
- cost per completed governed workflow

#### B. Explicit first-use-case set for the solopreneur ICP

Coverage status:
- `missing`

Gap:
- the docs say "one serious use case," but do not yet define the specific top workflows in concrete user terms

Examples that should likely be spelled out:
- turn a goal into a governed project
- track status/risk/blockers across active projects
- request a plan, approve it, and get controlled execution updates
- ask for evidence-backed budget/risk summary

#### C. Explicit business adaptation layer

Coverage status:
- `missing`

Gap:
- there is not yet a formal concept for templates, playbooks, or presets by work type

This matters because the Fed survey indicates that finding or adapting tools to business needs is a major barrier.

#### D. Explicit operator visibility surface definition

Coverage status:
- `missing`

Gap:
- while observability is repeatedly identified as important, there is no defined MVP-v2 artifact yet for:
  - owner dashboard
  - priority inbox
  - daily summary
  - risk/blocked view
  - cost view

## 6. Summary Judgment

The current docs are directionally strong for the solopreneur thesis.

They already cover the core governance-aligned requirements well:
- trustworthy control boundaries
- setup reduction
- cost discipline
- human-friendly interaction direction
- project-centered execution

The biggest weakness is not philosophical drift. It is missing product concretization around:
- measurable productivity outcomes
- first-use-case definition
- operator visibility
- workflow adaptation
- memory and continuity
- integration priorities

In other words:
- the current docs describe a good control model
- they do not yet fully describe the solopreneur operating experience

## 7. Recommended Next Additions

I would add the following planning artifacts next:

1. `SolopreneurCoreWorkflows-v1.md`
- define the top 3 to 5 workflows OpenQilin must make excellent

2. `MvpV2SuccessCriteria-v1.md`
- define measurable success bars for setup, productivity, trust, and cost

3. `OperatorVisibilityModel-v1.md`
- define the owner-facing dashboard/inbox/summary/risk surfaces

4. `BusinessPlaybookTemplateModel-v1.md`
- define how OpenQilin adapts to different project/work types without becoming a generic platform

5. `MemoryAndContinuityModel-v1.md`
- define what roles remember, what projects remember, and what counts as governed source of truth
