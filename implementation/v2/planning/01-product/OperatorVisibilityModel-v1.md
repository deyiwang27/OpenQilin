# Operator Visibility Model

Date: `2026-03-14`
Status: `discussion draft`
Stage: `pre-kickoff`

## 1. Purpose

- Define the owner-facing visibility surface needed for OpenQilin MVP-v2.
- Make dashboarding and visibility a first-class product topic rather than a background implementation detail.
- Specify the minimum practical views needed for a solopreneur to trust and operate OpenQilin.

## 2. Why This Matters

OpenQilin is built for the solopreneur: turning one capable person into a coordinated AI-augmented team.

For that user, governance without visibility feels like bureaucracy, and automation without visibility feels risky.

The owner needs fast answers to:
- what is happening
- what is blocked
- what needs my decision
- what is costing money
- whether the system is healthy

Dashboarding is therefore not a nice-to-have. It is part of the trust and leverage model.

## 3. Design Goal

MVP-v2 should provide a visibility surface that is:
- decision-oriented
- lightweight
- operationally useful
- consistent with governed execution
- understandable by one busy operator

The dashboard should not be a telemetry museum. It should help the owner decide what matters now.

## 4. Core Visibility Layers

### 4.1 Project layer

The owner must be able to inspect one project clearly.

Required visibility:
- current project state
- milestone or phase progress
- recent important activity
- blockers and risks
- pending approvals or decisions
- budget allocation and consumption
- PM summary
- evidence and outcome links

### 4.2 Portfolio layer

The owner must be able to understand the whole active workload.

Required visibility:
- all active projects
- priority and risk ordering
- stalled or overdue projects
- projects waiting on owner action
- budget roll-up across projects
- daily or weekly executive summary

### 4.3 System layer

The owner must know whether OpenQilin itself is functioning safely.

Required visibility:
- connector health
- routing failures or denials
- model usage and token cost
- tool invocation success/failure
- project-space binding health
- loop-stop or escalation events
- worker/runtime health

## 5. MVP-v2 Recommended Views

MVP-v2 should keep the surface narrow. A good first version is four views.

### 5.1 Owner Inbox

Purpose:
- show what needs the owner's attention now

Core widgets:
- pending approvals
- pending decisions
- blocked projects
- budget alerts
- governance/routing warnings
- recent escalations

Key question answered:
- `What do I need to act on right now?`

### 5.2 Projects Overview

Purpose:
- show the active project portfolio at a glance

Core widgets:
- project list with status
- progress indicator
- risk level
- next milestone
- owner-waiting flag
- budget health
- last meaningful update

Key question answered:
- `How are all my current projects doing?`

### 5.3 Project Detail

Purpose:
- show one project's execution picture in enough detail to trust it

Core widgets:
- project summary from PM
- lifecycle state
- milestone/task progress
- recent timeline/activity feed
- blockers and risks
- pending approvals
- budget burn and allocation
- evidence or output links
- participating roles and recent actions

Key question answered:
- `What is happening in this project and why?`

### 5.4 System Health

Purpose:
- show whether the OpenQilin runtime and connectors are healthy

Core widgets:
- Discord connector health
- channel/project binding integrity
- routing-denial count
- tool success/failure rate
- loop-prevention events
- model usage and token/cost trends
- worker/process health

Key question answered:
- `Is the system healthy and are we wasting money or breaking governance?`

## 6. Metrics That Matter

Metrics should be selected for operator usefulness, not completeness.

### 6.1 Project metrics

- project state
- milestone completion percentage
- time since last meaningful update
- blocker count
- open risk count
- pending approval count
- budget spent vs allocated
- forecast overrun risk

### 6.2 Portfolio metrics

- active project count
- projects blocked
- projects waiting on owner
- projects over budget
- projects overdue
- total budget committed vs spent

### 6.3 System metrics

- total model calls by role
- token usage by project and role
- estimated cost by period
- tool call success rate
- routing ambiguity count
- denied mutation count
- loop-stop trigger count
- connector error count

## 7. Design Principles

### 7.1 Make views action-oriented

Every metric or panel should help answer:
- what changed
- what matters
- what action is needed

### 7.2 Prefer summaries over raw logs

Raw events are useful, but the default should be synthesized:
- PM summary
- risk summary
- budget summary
- system alert summary

### 7.3 Keep governance visible

When the system denies or escalates something, the dashboard should explain:
- what happened
- why it happened
- what the operator can do next

### 7.4 Keep costs visible

Cost should not be buried in debug pages.

The owner should be able to see:
- which projects consume the most
- which roles consume the most
- whether wasteful routing behavior is occurring

### 7.5 Keep it small for MVP-v2

The goal is not to build a giant admin console.

The goal is to provide just enough visibility for:
- trust
- intervention
- cost discipline
- decision support

## 8. Relationship to Discord

Discord remains the primary interaction surface in MVP-v2.

The dashboard is not a replacement for Discord. It is a secondary operator surface for:
- summary
- inspection
- approvals
- diagnostics
- cost and health monitoring

This split is healthy:
- Discord for conversation and project interaction
- dashboard for portfolio/system visibility and intervention

### 8.1 Dashboard link placement in Discord

For MVP-v2:
- pin the dashboard link in `leadership_council`
- allow the same link to appear in channel topic/description when useful
- treat the dashboard link as shared infrastructure for the leadership surface, not as a separate alert channel requirement

### 8.2 Shared versus private alert routing

Recommended alert routing:
- `critical` or clearly leadership-relevant alerts:
  - post into `leadership_council`
- lower-severity or owner-specific alerts:
  - send to `owner <-> secretary` DM

This keeps shared channels useful while preserving a private default alert path.

### 8.3 Secretary as the dashboard narrator

`secretary` should be the default explainer/summarizer for dashboard and alert-derived information.

Expected behavior:
- reads dashboard state
- summarizes what changed
- explains alerts in human terms
- helps the owner decide whether escalation is necessary

Other institutional roles should usually respond only:
- on explicit mention
- on role-relevant policy-triggered follow-up

### 8.4 Forwarding as owner-controlled escalation

Discord message forwarding can be used as a practical escalation bridge.

Recommended use:
- Secretary DM receives lower-severity alerts
- owner forwards selected messages into:
  - `leadership_council`
  - another institutional DM
  - a project channel

This keeps escalation under human control and avoids turning all alerts into channel noise.

### 8.5 Longer-term console direction

MVP-v2 still treats the dashboard as a secondary operator surface.

Longer term, OpenQilin should plan for an OpenQilin-owned console that can expand beyond dashboarding into:
- chat
- approvals
- project management
- budget/cost control
- system health and diagnostics

In that longer-term model, external chat platforms like Discord should become optional adapters rather than the permanent primary product surface.

## 9. What This Adds to the Current Plan

This model makes several previously implicit needs explicit:
- project visibility is a product requirement
- budget visibility is a product requirement
- system health visibility is a product requirement
- dashboarding should be scoped as a trust surface, not as a vanity console

## 10. Suggested MVP-v2 Scope

For MVP-v2, I would define dashboard scope as:

Must have:
- Owner Inbox
- Projects Overview
- Project Detail
- System Health

Should have:
- daily summary view
- cost trend summary
- explicit approval queue

Not required yet:
- advanced analytics
- custom report builder
- broad role-specific admin pages
- multi-user enterprise dashboards

## 11. Open Questions

- Should the dashboard be read-mostly in MVP-v2, or also allow some approvals/interventions directly?
- Should project approvals happen only in Discord, only in dashboard, or in both?
- What is the minimum useful budget model for display in MVP-v2?
- Should the dashboard show raw agent activity, or mostly synthesized summaries plus expandable detail?
- Which alert severities should be shared automatically in `leadership_council` versus kept private in Secretary DM?
