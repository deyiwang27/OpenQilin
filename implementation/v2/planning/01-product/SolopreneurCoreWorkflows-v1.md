# Solopreneur Core Workflows

Date: `2026-03-14`
Status: `discussion draft`
Stage: `pre-kickoff`

## 1. Purpose

- Define the first core workflows OpenQilin MVP-v2 must do well for the solopreneur user.
- Turn the product thesis into concrete operator outcomes.
- Give MVP-v2 implementation and evaluation a workflow-centered anchor instead of a feature-centered one.

## 2. Product Thesis Reminder

OpenQilin is built for the solopreneur: turning one capable person into a coordinated AI-augmented team.
It does this through governed role delegation, project-centered execution, and explicit control over authority, budget, and evidence.

These workflows are the first practical expression of that thesis.

## 3. Selection Rules

The first MVP-v2 workflows should:
- save real time for one operator
- benefit from governed delegation rather than one-shot prompting
- fit the Discord-first plus dashboard-assisted operating model
- make cost, visibility, and authority boundaries matter
- be demonstrable end to end

## 4. Proposed Core MVP-v2 Workflows

### 4.1 Start a new project from a goal

Owner intent:
- `I want to launch X`
- `Turn this goal into a governed project`

Expected system behavior:
- Secretary or PM helps clarify scope if needed
- project proposal is created
- proposal discussion and approval happen through the institutional layer
- a project space is created automatically
- PM becomes the default project representative
- the project appears in the dashboard with initial status, budget, and next actions

Why this matters:
- this is the front door into the product
- it proves project-centered execution instead of generic chat

### 4.2 Drive one active project through planning and execution

Owner intent:
- `PM, break this into milestones`
- `What is blocked this week?`
- `What should happen next?`

Expected system behavior:
- PM decomposes work into milestones and tasks
- PM coordinates with downstream DL/specialist roles through A2A
- PM returns integrated status, risks, and next-step recommendations
- the project timeline, blockers, and recent activity remain visible in dashboard

Why this matters:
- this is the daily operating loop
- if this is weak, OpenQilin becomes a planning toy rather than a useful operating system

### 4.3 Escalate and resolve a decision or blocker

Owner intent:
- `Why is this blocked?`
- `Escalate this to leadership`
- `Auditor, explain the budget issue`

Expected system behavior:
- system identifies blocker, risk, or budget/governance issue
- Secretary summarizes the issue when appropriate
- severity-based alerts surface in the right place
- the right institutional role joins by mention or policy-triggered escalation
- a visible decision or denial is recorded with evidence

Why this matters:
- solopreneurs need help with decision pressure, not just task generation
- this proves the governance layer is useful rather than decorative

### 4.4 Review budget, cost, and operating health

Owner intent:
- `What is costing me the most?`
- `Which projects are over budget risk?`
- `Is the system healthy?`

Expected system behavior:
- dashboard shows project budget status, cost usage, and system health
- Secretary can explain alerts and summarize trends
- budget denials and abnormal cost patterns are visible and understandable
- the owner can decide whether to pause, reduce scope, or continue

Why this matters:
- cost discipline is a core product promise for this ICP
- this is where OpenQilin must beat agent theater

### 4.5 Close, pause, resume, or archive a project cleanly

Owner intent:
- `Pause this project`
- `Resume it next week`
- `Archive completed work`

Expected system behavior:
- governed lifecycle transitions remain explicit
- project space behavior changes with lifecycle state
- dashboard state updates immediately
- project context and evidence remain inspectable after closure

Why this matters:
- solopreneurs need continuity across many projects over time
- lifecycle discipline is part of what makes the product feel operationally trustworthy

## 5. What Is Explicitly Not Core for MVP-v2

The following may exist later, but should not define MVP-v2 success:
- multi-channel parity beyond Discord
- open-ended autonomous agent society behavior
- broad public marketplace/tooling ecosystem
- many concurrent exposed workforce personas in owner-facing channels
- deep console-first replacement of Discord

## 6. Workflow-to-Surface Mapping

### 6.1 Discord

Primary use:
- ask
- direct
- escalate
- confirm
- discuss

Best suited for:
- project conversation
- Secretary guidance
- leadership escalation
- fast operational interaction

### 6.2 Dashboard

Primary use:
- inspect
- compare
- monitor
- review

Best suited for:
- portfolio overview
- project detail
- budget and cost status
- health and alert visibility

## 7. Workflow-to-Role Mapping

### 7.1 Secretary
- front door
- explainer
- summarizer
- router

### 7.2 Project Manager
- default project representative
- planner
- coordinator
- synthesizer of downstream work

### 7.3 Administrator
- system/runtime escalation
- operational integrity explanation

### 7.4 Auditor
- budget, compliance, and evidence explanation

### 7.5 CEO / CWO / CSO
- leadership decision and escalation layer

## 8. MVP-v2 Priority Order

Recommended order:

1. Start a new project from a goal
2. Drive one active project through planning and execution
3. Escalate and resolve a decision or blocker
4. Review budget, cost, and operating health
5. Close, pause, resume, or archive a project cleanly

## 9. Design Implications

If a feature does not make one of these workflows better, it should be treated as secondary for MVP-v2.

The most important question for MVP-v2 planning should be:
- does this reduce coordination burden for the solopreneur in one of the core workflows above?
