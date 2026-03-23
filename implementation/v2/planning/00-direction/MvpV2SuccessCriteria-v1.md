# OpenQilin MVP-v2 Success Criteria

Date: `2026-03-14`
Status: `active`
Stage: `M17-in-progress`

## 1. Purpose

- Define the bar for calling MVP-v2 successful.
- Convert the product thesis into measurable product, UX, governance, and runtime outcomes.
- Prevent MVP-v2 from expanding into an open-ended improvement stream without a finish line.

## 2. Success Standard

MVP-v2 succeeds if it gives one solopreneur a repeatable, trustworthy way to operate projects through Discord with lower setup friction, lower coordination burden, and better cost/control visibility than MVP-v1.

This means MVP-v2 must be judged by:
- real workflow usefulness
- lower operator friction
- clearer control boundaries
- visible cost discipline
- system trustworthiness
- public-readiness and contributor/sponsor readiness

## 3. Major Objectives

### 3.1 Make first use fast and understandable

Objective:
- reduce setup pain and time to first value

Success signals:
- one operator can complete setup without hand-holding
- Discord operating model is understandable after first use
- setup failures are diagnosable with clear feedback

### 3.2 Make daily interaction human-friendly

Objective:
- replace JSON-shaped daily use with normal chat plus compact commands

Success signals:
- common interactions are usable in free text
- governed mutations use concise command or confirmation flows
- Discord conversations feel like operating work, not API testing

### 3.3 Make project execution the center of the product

Objective:
- move from role-bot sprawl to project-space operation

Success signals:
- projects can be created and operated through governed project spaces
- PM is the default project-facing representative
- project lifecycle changes are reflected in communication behavior and visibility

### 3.4 Make governance and budget visibly useful

Objective:
- ensure control surfaces are operationally valuable, not just architecturally correct

Success signals:
- denials are understandable
- approvals and escalations are visible
- budget/cost issues can be detected and explained
- the owner can tell why the system allowed, denied, or escalated something

### 3.5 Make runtime behavior honest and integrated

Objective:
- reduce the gap between documented architecture and actual execution

Success signals:
- important services invoked in production are real, not placeholder shells where that matters
- topology claims match actual runtime behavior
- workers, callbacks, and state boundaries are either real or intentionally simplified

### 3.6 Make OpenQilin public-ready and sponsor-ready

Objective:
- ensure MVP-v2 leaves the project ready for public introduction, early contributors, and realistic sponsorship/startup-credit outreach

Success signals:
- the repo is understandable and contributor-ready
- MVP-v2 has a presentable demo and clear product story
- the project has the minimum assets needed for sponsorship and startup-credit applications

## 4. MVP-v2 Must-Have Criteria

These are the minimum criteria I would use to call MVP-v2 complete.

### 4.1 Product criteria

- The product thesis remains explicit and visible in the planning and user-facing framing.
- At least the top three core workflows are functional end to end.
- One solopreneur can use OpenQilin for real project work, not only demo prompts.

### 4.2 UX criteria

- Daily Discord interaction no longer requires raw JSON.
- The user can interact through free text and compact command syntax.
- Project spaces are materially simpler than the v1 multi-bot project setup model.

### 4.3 Routing and project-space criteria

- Project-space routing is implemented and stable.
- PM is the default responder in project spaces.
- Project-scoped workforce roles do not require standalone Discord bot identities.
- Ambiguous routing fails closed with understandable feedback.

### 4.4 Dashboard and visibility criteria

- Grafana is deployed as the single operator dashboard; no separate app or React console is required.
- The Grafana dashboard covers both business and ops visibility in one place:
  - owner inbox (pending decisions, escalations, proposals) from PostgreSQL
  - projects overview (status, blockers, lifecycle state) from PostgreSQL
  - project detail (per-project activity and cost) from PostgreSQL
  - budget and cost visibility (by project, by role) from PostgreSQL
  - system and runtime health (agent liveness, LLM latency, error rates) from OpenTelemetry
- Grafana alerting routes threshold notifications to Discord via webhook; the owner does not need to watch the dashboard to be alerted.
- The dashboard link is pinned in `leadership_council`.
- The owner can identify blocked projects, pending decisions, budget risk, and system health in under 2 minutes from the dashboard.

### 4.5 Governance criteria

- Active governance checks are actually invoked on the main execution path.
- Project lifecycle and role boundaries are enforced in runtime behavior.
- High-impact mutations require explicit command or confirmation.
- Denial and escalation behavior is visible and explainable.
- `secretary` is active as an advisory front-desk agent: handles intent disambiguation, summaries, and routing assistance without execution authority.
- `cso` is active as a real advisory governance gate, enforced by live OPA policy evaluation (not a placeholder).
- `domain_leader` is active as a backend-routed virtual agent scoped to project context; surfaced only through PM escalation or governed review paths, not as a default project-channel participant.

### 4.6 Budget and cost criteria

- Budget checks are actively enforced on the main write path.
- Cost and token usage are visible at least at the project and role-summary level.
- The system can identify and surface abnormal or wasteful spend patterns.

### 4.7 Runtime integrity criteria

- No important production service is advertised as active while remaining a no-op placeholder.
- Compose/runtime docs describe the actual execution model honestly.
- Integration tests cover the real critical path rather than only happy-path stubs.

### 4.8 Community-readiness criteria

- The repo is fit for early public introduction after MVP-v2.
- Minimum community-facing assets exist:
  - clear README
  - product thesis
  - roadmap
  - demo
  - contributor entry path
  - website/domain presence
  - sponsorship/funding-ready summary assets

## 5. Recommended Quantitative Targets

These are suggested targets, not yet final commitments.

### 5.1 Setup and first-value

- first guided setup completed in under `30 minutes`
- first successful project-space interaction in under `10 minutes` after setup completion
- zero manual creation of project-scoped Discord bot identities

### 5.2 Daily usability

- at least `80%` of normal owner interactions in dogfooding can happen without JSON
- at least `80%` of project-channel messages default cleanly to PM without manual rerouting

### 5.3 Visibility

- owner can identify:
  - projects waiting on them
  - blocked projects
  - budget risk
  - system health
  in under `2 minutes` from the dashboard

### 5.4 Cost discipline

- obvious multi-agent chatter loops are prevented by policy/runtime caps
- repeated avoidable model invocations are visibly reduced relative to v1 dogfooding
- cost visibility is available per project and at least one per-role roll-up

### 5.5 Reliability

- critical workflows pass end-to-end tests in the actual supported topology
- restart/recovery preserves critical runtime state where persistence is claimed

### 5.6 Public-readiness

- public landing page and matching contact email exist
- one-page deck exists
- MVP-v2 demo assets exist and are reusable for outreach
- contributor onboarding path is visible in under `10 minutes` of repo exploration

## 6. Non-Success Conditions

MVP-v2 should not be considered successful if any of these remain true:

- project operation still depends on heavy manual multi-bot setup
- normal daily chat still looks like structured JSON transport
- budget/cost control is mostly invisible to the owner
- governance exists mainly in spec/docs rather than runtime behavior
- runtime architecture claims remain materially ahead of what is actually wired
- the Grafana dashboard exists but does not help the owner decide what matters now
- the dashboard requires a separate app or React console that adds deployment complexity for the operator
- `secretary`, `cso`, or `domain_leader` remain inactive placeholders with no runtime behavior
- the repo is still too internally oriented to present publicly or invite early contributors

## 7. Recommended Review Method

MVP-v2 completion should be reviewed in five passes:

1. workflow pass
- run the core solopreneur workflows end to end

2. operator pass
- verify setup, daily use, alerts, and dashboard clarity

3. governance pass
- verify denials, approvals, lifecycle controls, and fail-closed behavior

4. runtime pass
- verify the actual topology, state boundaries, budget path, and callback/worker truthfulness

5. public-readiness pass
- verify README, demo, roadmap, website, contributor path, and sponsorship-readiness assets

## 8. Relationship to Major Objectives

These success criteria are meant to keep the major objectives concrete.

If the objectives are the direction, these criteria are the bar.
