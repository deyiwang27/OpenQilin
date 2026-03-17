# Spec Design Review Findings — MVP v2

Status: `active`
Date: `2026-03-16`
Author: design review pass prior to M13 implementation start

---

## Purpose

Systematic review of all agent role specs, authority profiles, escalation models, gate flows, and cross-role interactions for design flaws, inconsistencies, ambiguities, and gaps. Findings are classified by severity and category. Each finding includes a proposed resolution and disposition status.

---

## Severity Key

| Severity | Meaning |
| --- | --- |
| **High** | Would cause runtime failure, security gap, or hard deadlock in production |
| **Medium** | Would produce incorrect or undefined behavior; requires a spec fix before implementation |
| **Low** | Ambiguity or cleanup; can be resolved with a clarification note |

---

## Summary

| # | Category | Finding | Severity | Status |
| --- | --- | --- | --- | --- |
| 1.1 | Authority Profile | CEO `review: deny` vs SafetyDoctrine "evaluates major safety incidents" | High | `resolved` |
| 1.2 | Authority Profile | PM workforce scope — creates Specialists only within project scope | Medium | `open` |
| 1.3 | Authority Profile | CWO co-approval — "command" or "approval role"? | Medium | `open` |
| 1.4 | Authority Profile | CSO `decision: allow` — outputs are recommendations, not decisions | Medium | `open` |
| 2.1 | Escalation Path | No timeout or non-response handling for owner approval requests | High | `resolved` |
| 2.2 | Escalation Path | Loop controls and escalation chains interact destructively | High | `resolved` |
| 2.3 | Escalation Path | No bypass path when PM is the behavioral violator | High | `resolved` |
| 2.4 | Escalation Path | No formal auditor accountability mechanism | Medium | `open` |
| 3.1 | Gate Flow | No proposal timeout — CWO proposal can block indefinitely | Medium | `open` |
| 3.2 | Gate Flow | GATE-003 three-cycle block — CEO still advances but accountability not logged | Medium | `open` |
| 3.3 | Gate Flow | `completion_report` immutability creates completion deadlock | High | `resolved` |
| 3.4 | Gate Flow | No trigger defined for DecisionReviewGate flow initiation | Medium | `open` |
| 4.1 | Cross-Role Boundary | Secretary can "request participation from Specialist" — conflicts with PM-dispatch-only | High | `resolved` |
| 4.2 | Cross-Role Boundary | Project pause authority gap — no single agent has clear pause authority | Medium | `open` |
| 4.3 | Cross-Role Boundary | Specialist→DL clarification path activation criteria undefined | Medium | `open` |
| 4.4 | Cross-Role Boundary | `project_charter` co-owner: CWO commands it, CEO approves it — write authority ambiguous | Medium | `open` |
| 5.1 | Stale Spec Text | OwnerInteractionModel describes CSO as OPA governance gate | High | `resolved` |
| 5.2 | Stale Spec Text | DL contract still says "disabled in current phase" | Low | `open` |
| 5.3 | Stale Spec Text | Specialist contract still says "disabled in current phase" | Low | `open` |
| 6.1 | Missing Spec | No Owner Role Contract | Medium | `open` |
| 6.2 | Missing Spec | No `task_execution_results` spec (referenced by M14-WP6/WP7) | Medium | `open` |
| 6.3 | Missing Spec | DL→CSO strategic insight request mechanism undefined | Low | `open` |

---

## Category 1 — Authority Profile Inconsistencies

### Finding 1.1 — CEO `review: deny` vs SafetyDoctrine (High)

**Location:** `spec/governance/architecture/SafetyDoctrine.md`, `spec/governance/contracts/CeoRoleContract.md`

**Description:** `AgentAuthorityGraph` sets CEO `review: deny`. `SafetyDoctrine` states "CEO evaluates major safety incidents" and "CEO can initiate emergency project shutdown." Evaluation implies review authority. This is a direct contradiction. If implemented as `review: deny`, the CEO cannot perform the safety evaluation described in the safety doctrine.

**Proposed resolution:** Narrow the CEO authority profile exception: `review: deny` applies to routine project review (artifact review, output review). Add an explicit carve-out: `emergency_review: allow` scoped to safety incidents and emergency shutdown initiation. Document this as a bounded exception in `CeoRoleContract §3`. The general `review: deny` stance is preserved — CEO does not review task outputs or project artifacts; CEO only acts on escalated safety escalations.

**Disposition:** `open`

---

### Finding 1.2 — PM Workforce Scope (Medium)

**Location:** `spec/governance/contracts/ProjectManagerRoleContract.md`

**Description:** PM has `workforce: allow` but the scope boundary is "within project scope only." There is no formal constraint in the spec preventing a PM from requesting a Specialist dispatch outside its assigned project. The scope constraint is stated in prose but not enforced structurally.

**Proposed resolution:** Add `workforce_scope: project_bound` as a formal attribute in PM authority profile. In implementation (M14-WP1), the `dispatch_specialist()` method must validate `task.project_id == pm.assigned_project_id` before creating the Specialist. Add this as a done criterion to M14-WP1.

**Disposition:** `open`

---

### Finding 1.3 — CWO Co-Approval Classification (Medium)

**Location:** `spec/governance/contracts/CwoRoleContract.md`, `spec/governance/architecture/DecisionReviewGates.md`

**Description:** CWO has `decision: deny`, `command: allow`. GATE-005 requires "CWO initialization command." The gate description calls this a "co-approval" but the authority profile says decisions are denied. The word "co-approval" implies a decision act. This creates implementation ambiguity: is CWO's GATE-005 action a command (allowed) or a decision (denied)?

**Proposed resolution:** Clarify in `CwoRoleContract §4`: CWO GATE-005 action is a **command** (workforce readiness command to initialize project execution), not a decision approval. Rename "co-approval" to "initialization command" in DecisionReviewGates GATE-005. Decision authority belongs to CEO+owner; CWO's gate action is operational, not decisional.

**Disposition:** `open`

---

### Finding 1.4 — CSO `decision: allow` vs Advisory Outputs (Medium)

**Location:** `spec/governance/contracts/CsoRoleContract.md`, `spec/governance/architecture/AgentAuthorityGraph.md`

**Description:** CSO has `decision: allow` in the authority matrix. However, CSO outputs are recommendations, reviews, and strategic insight — not binding decisions. CSO cannot approve or block a project unilaterally. The `decision: allow` label is misleading and could be misread as CSO having approval authority.

**Proposed resolution:** Rename CSO authority label to `advisory_review: allow` in the authority matrix, or clarify in `CsoRoleContract §3`: "`decision: allow` means CSO may form and issue a strategic review opinion; it does not confer approval or veto authority. CSO recommendations are advisory and non-binding without CEO or owner endorsement." Add this distinction explicitly to `AgentAuthorityGraph §2`.

**Disposition:** `open`

---

## Category 2 — Escalation Path Design Gaps

### Finding 2.1 — No Escalation Timeout (High)

**Location:** `spec/orchestration/communication/EscalationModel.md`

**Description:** The escalation model has no timeout or non-response handling. If the owner does not respond to an approval request, the system has no defined behavior. The task blocks forever, consuming a reservation slot, holding a budget reservation open, and potentially stalling the entire project. This is a production reliability gap.

**Proposed resolution:** Add to `EscalationModel §3`: "Approval requests expire after `OWNER_APPROVAL_TIMEOUT_HOURS` (default: 48h, configurable via `settings.py`). On expiry: (1) emit audit event `approval_request_expired`; (2) task transitions to `blocked`; (3) budget reservation is released; (4) Secretary sends expiry notification to owner in `governance` channel; (5) PM receives `task_blocked` event and may resubmit." Add `ESC-007: approval_request_timeout` as a new escalation rule. Add to M14-WP7 or create a new WP in M16.

**Disposition:** `open`

---

### Finding 2.2 — Loop Controls vs Escalation Chain Interaction (High)

**Location:** `spec/orchestration/communication/AgentLoopControls.md`, `spec/orchestration/communication/EscalationModel.md`

**Description:** `AgentLoopControls` enforces a 5-hop max per trace. A full escalation chain (Specialist → DL → PM → CEO → owner) consumes all 5 hops. If a loop control breach fires mid-chain (e.g. at hop 4), the escalation stops without reaching its target. The current spec says "loop cap breach: stop dispatch → emit audit event → escalate to owner." But that escalation itself requires hops, which may be exhausted. This is a circular dependency that could silently swallow critical escalations.

**Proposed resolution:** Add to `AgentLoopControls §3`: "Escalation messages are exempt from per-trace hop counting. An escalation message (identified by `message.type == 'escalation'`) always opens a fresh trace with a new `trace_id`. Normal task messages remain subject to hop limits." Add `LOOP-006: escalation_trace_reset` as a new rule. This is consistent with the spirit of hop limits (prevent runaway agent loops, not prevent critical safety signals from reaching the owner).

**Disposition:** `open`

---

### Finding 2.3 — PM Behavioral Violation Bypass Gap (High)

**Location:** `spec/governance/contracts/AuditorRoleContract.md`, `spec/orchestration/communication/EscalationModel.md`

**Description:** The escalation model routes behavioral violations from Specialist → PM → ... But if PM is the source of the behavioral violation (PM overriding task scope, PM fabricating status reports, PM bypassing budget limits), there is no defined bypass path. Escalating to PM when PM is the violator is not a safe design.

**Proposed resolution:** Add to `AuditorRoleContract §4` and `EscalationModel §4`: "Behavioral violations involving the PM escalate directly: PM violation → Auditor → owner (bypassing PM and CEO). Auditor has authority to escalate any agent violation directly to owner without passing through the violating agent's chain. Add `ESC-008: pm_violation_direct_to_auditor` as a new escalation rule. This is consistent with Auditor's `oversight: allow` authority and the separation-of-safety-authority principle in SafetyDoctrine.

**Disposition:** `open`

---

### Finding 2.4 — No Formal Auditor Accountability (Medium)

**Location:** `spec/governance/contracts/AuditorRoleContract.md`

**Description:** The Auditor can issue pause notifications, behavioral violation flags, and escalations to the owner. There is no mechanism for the owner to dispute or override an Auditor finding, and no path for the Auditor itself to be held accountable if it issues a false positive. The Auditor is a single point of authority with no checks.

**Proposed resolution:** Add to `AuditorRoleContract §5`: "Owner may issue an `auditor_override` command to clear a behavioral flag. Auditor must record the override in `audit_events` with `overridden_by: owner`. Auditor cannot reissue the same finding for the same task/agent without new evidence." This limits Auditor false-positive loops while preserving independence.

**Disposition:** `open`

---

## Category 3 — Gate Flow Weaknesses

### Finding 3.1 — No CWO Proposal Timeout (Medium)

**Location:** `spec/governance/architecture/DecisionReviewGates.md`

**Description:** The DecisionReviewGate flow starts with a CWO proposal (GATE-001). There is no defined timeout for the CSO review (GATE-002), the CEO+CWO review (GATE-003), or the final owner+CEO approval (GATE-004). Any gate can stall indefinitely with no defined recovery path.

**Proposed resolution:** Add gate timeout rules to `DecisionReviewGates §4`: each gate has a default timeout (CSO review: 24h; CEO review: 48h; owner approval: 48h). On timeout: gate emits `gate_timeout` event; Secretary notifies relevant principals; CWO may resubmit or escalate. Add to M13-WP7 or M14-WP2 implementation scope.

**Disposition:** `open`

---

### Finding 3.2 — GATE-003 Three-Cycle Block Accountability (Medium)

**Location:** `spec/governance/architecture/DecisionReviewGates.md`

**Description:** GATE-003 allows a maximum of 3 revision cycles between CEO and CWO. After 3 cycles, the proposal is blocked. The spec does not define who is accountable for the block (CEO who kept rejecting, or CWO who kept re-proposing), and does not define whether the block can be overridden and by whom.

**Proposed resolution:** Add to `DecisionReviewGates §3`: "On GATE-003 block: emit `revision_cycle_exhausted` audit event with full revision history. Owner is notified directly. Owner may either: (a) issue a `gate_override` command to advance the proposal to GATE-004 with mandatory justification; or (b) issue a `proposal_terminate` command to close the gate flow. CEO and CWO both receive the block notification and cannot unilaterally restart the flow."

**Disposition:** `open`

---

### Finding 3.3 — `completion_report` Immutability Deadlock (High)

**Location:** `spec/state-machines/ProjectArtifactModel.md`, `spec/governance/contracts/ProjectManagerRoleContract.md`

**Description:** `completion_report` is immutable after publish. PM writes the completion report to signal project completion. If the completion report contains an error (wrong final status, missing budget summary), there is no correction path. The owner cannot approve a flawed completion report but also cannot request a corrected one through any defined mechanism. This creates a completion deadlock.

**Proposed resolution:** Add to `ProjectArtifactModel §6`: "`completion_report` immutability applies to content once approved by owner. Before owner approval, PM may issue a `completion_report_revision` (new version, prior version archived). After owner approval, the report is sealed. Owner approval of `completion_report` is the sealing event — not publication." This gives PM a correction window while preserving immutability as a post-approval guarantee.

**Disposition:** `open`

---

### Finding 3.4 — No DecisionReviewGate Flow Trigger (Medium)

**Location:** `spec/governance/architecture/DecisionReviewGates.md`

**Description:** The spec describes the gate flow in full detail but does not specify what triggers the flow. It is implied that a CWO proposal triggers GATE-001, but "proposal" is not formally defined as a trigger event type. There is no spec for what message type, channel, or system event initiates the gate flow.

**Proposed resolution:** Add to `DecisionReviewGates §1`: "Gate flow is triggered when CWO calls `submit_proposal(project_charter)`. The Secretary registers the proposal in `governance_artifacts` with `status: gate_pending`. Secretary then initiates the GATE-001 CSO review by routing to CSO. All subsequent gate transitions are driven by Secretary based on the current gate state." This closes the trigger gap and clarifies Secretary's role as the gate flow coordinator.

**Disposition:** `open`

---

## Category 4 — Cross-Role Boundary Ambiguities

### Finding 4.1 — Secretary→Specialist Routing Conflict (High)

**Location:** `spec/governance/contracts/SecretaryRoleContract.md §6`

**Description:** `SecretaryRoleContract §6` allows Secretary to "request participation from Specialist" in certain contexts. This directly conflicts with the PM-dispatch-only constraint: Specialists may only be created and dispatched by PM (M14-WP6). If Secretary can directly route to Specialist, it bypasses PM oversight, task tracking, and budget reservation.

**Proposed resolution:** Remove `specialist` from Secretary's routing list in `SecretaryRoleContract §6`. Secretary may route to: owner, CEO, CWO, CSO, PM, Auditor, Administrator only. To involve a Specialist, Secretary routes through PM. Add note: "Secretary does not directly address Specialist agents. If a task requires specialist execution, Secretary routes the request to PM for Specialist dispatch."

**Disposition:** `open`

---

### Finding 4.2 — Project Pause Authority Gap (Medium)

**Location:** `spec/governance/architecture/SafetyDoctrine.md`, multiple role contracts

**Description:** Multiple agents can request a project pause (Auditor via safety violation, CEO via emergency shutdown, PM via budget breach). But no spec defines: (1) who has final pause authority, (2) whether pauses can stack (two agents both pause the same project), and (3) what resumes a pause.

**Proposed resolution:** Add to `SafetyDoctrine §4`: "Project pause authority hierarchy: owner > Auditor (safety) > CEO (emergency) > PM (budget/operational). Any agent may request a pause by issuing a `pause_request` event to the governance channel. Pause is applied immediately by the Secretary (who tracks project state). Resume requires the pausing authority or owner to issue `resume_command`. Stacked pauses: project remains paused until all active pause requests are cleared."

**Disposition:** `open`

---

### Finding 4.3 — Specialist→DL Clarification Activation Criteria (Medium)

**Location:** `spec/governance/contracts/SpecialistRoleContract.md`, `spec/governance/contracts/DomainLeaderRoleContract.md`

**Description:** The M14-WP6 plan includes a Specialist→DL clarification path for ambiguous task requirements. But neither spec formally defines the activation criteria: under what conditions may Specialist route to DL vs. marking the task as blocked? Without this, each Specialist implementation may use different criteria, creating inconsistent behavior.

**Proposed resolution:** Add to `SpecialistRoleContract §5`: "Specialist may request DL clarification when: (1) task requirements are contradictory; (2) required resource is outside task scope as defined by PM; (3) tool access is ambiguous. Specialist must first mark task as `clarification_needed` before routing. DL responds within the same trace. If DL cannot resolve, DL escalates to PM. Specialist does not block task without first requesting clarification."

**Disposition:** `open`

---

### Finding 4.4 — `project_charter` Co-Owner Write Conflict (Medium)

**Location:** `spec/state-machines/ProjectArtifactModel.md`, `spec/governance/contracts/CwoRoleContract.md`, `spec/governance/contracts/CeoRoleContract.md`

**Description:** CWO has write authority for `project_charter` (initialization command). CEO approves the `project_charter` as part of GATE-004. But `ProjectArtifactModel` does not explicitly specify whether CEO's approval is a write action (update of artifact state) or a side-channel event. If it's a write, CEO has an implicit write path for `project_charter` despite not being listed as a writer.

**Proposed resolution:** Add to `ProjectArtifactModel §3`: "`project_charter` write authority: CWO creates and revises; CEO issues an approval record in `governance_artifacts` (not a write to the charter itself); owner countersigns via approval record. The charter artifact itself is written only by CWO. Approval is recorded as a separate `gate_approval` record linked to the charter version."

**Disposition:** `open`

---

## Category 5 — Stale Spec Text

### Finding 5.1 — OwnerInteractionModel CSO Description (High)

**Location:** `spec/orchestration/communication/OwnerInteractionModel.md` and `spec/governance/architecture/OwnerInteractionModel.md`

**Description:** The MVP v2 profile still describes CSO as "active as a real advisory governance gate enforced by live OPA." CSO does not use OPA. CSO is the Chief Strategy Officer, a portfolio strategy advisor. This framing was correct for an earlier design iteration that has since been replaced.

**Proposed resolution:** Update the CSO row in OwnerInteractionModel MVP v2 profile: "CSO (Chief Strategy Officer) — activated in M13-WP7. Provides portfolio strategy review for CWO proposals and cross-project strategic insight. No OPA dependency. Routes through governance channel."

**Disposition:** `open`

---

### Finding 5.2 — DL Contract "Disabled" Text (Low)

**Location:** `spec/governance/contracts/DomainLeaderRoleContract.md`

**Description:** DL role contract still contains "disabled in current phase" language. DL is being activated in M13-WP5. The stale text creates confusion about the agent's status.

**Proposed resolution:** Remove "disabled" language from `DomainLeaderRoleContract`. Update status to "activated in M13-WP5."

**Disposition:** `open`

---

### Finding 5.3 — Specialist Contract "Disabled" Text (Low)

**Location:** `spec/governance/contracts/SpecialistRoleContract.md`

**Description:** Same issue as 5.2 — Specialist contract still contains "disabled in current phase." Specialist activates in M14-WP6.

**Proposed resolution:** Remove "disabled" language. Update status to "activated in M14-WP6."

**Disposition:** `open`

---

## Category 6 — Missing Formal Specs

### Finding 6.1 — No Owner Role Contract (Medium)

**Location:** `spec/governance/contracts/`

**Description:** All 9 agent roles have role contracts. The owner has authority over all agents, can override Auditor findings, can approve/reject gate proposals, can issue emergency commands — but there is no Owner Role Contract defining owner authority profile, what the owner can and cannot do, and what channels the owner uses. This creates an implicit "owner can do anything" assumption that is not formally bounded.

**Proposed resolution:** Create `spec/governance/contracts/OwnerRoleContract.md` with: authority profile (`all: allow`), interaction channels (all channels allowed), formal constraints (owner cannot impersonate an agent role; owner cannot retroactively alter `audit_events`; owner cannot bypass `completion_report` immutability once sealed). This is primarily a documentation task but establishes the principle that even the owner operates within formal constraints.

**Disposition:** `open`

---

### Finding 6.2 — No `task_execution_results` Spec (Medium)

**Location:** `spec/state-machines/`, `implementation/v2/planning/05-milestones/M14-WorkPackages-v1.md`

**Description:** M14-WP6 resolves the Specialist artifact write conflict by introducing `task_execution_results` as a task-scoped output table distinct from project artifacts. But there is no formal spec for `task_execution_results`: what fields it contains, who can read it, whether it is immutable, retention policy, and how PM synthesizes it into project artifacts.

**Proposed resolution:** Create `spec/state-machines/TaskExecutionResultsModel.md` defining: schema (`task_id`, `project_id`, `specialist_id`, `output_type`, `content`, `content_hash`, `created_at`); immutability rule (immutable after task completion); read authority (PM, DL, Auditor, owner); write authority (Specialist only, once); PM synthesis path (PM reads and cites `task_execution_results` in project artifacts). Add to M14-WP6 as an output artifact.

**Disposition:** `open`

---

### Finding 6.3 — DL→CSO Strategic Insight Mechanism (Low)

**Location:** `spec/governance/contracts/DomainLeaderRoleContract.md`, `spec/governance/contracts/CsoRoleContract.md`

**Description:** CSO provides cross-project strategic insight. The spec implies DL may surface domain-specific signals to CSO. But there is no defined mechanism: how does DL request CSO insight, what channel is used, what does CSO return, and what does DL do with the response?

**Proposed resolution:** Add to `CsoRoleContract §5`: "DL may submit a `strategic_insight_request` to CSO through the governance channel (routed by Secretary). CSO responds with an advisory record in `governance_artifacts`. DL treats the response as non-binding advisory input. DL does not wait on CSO response before proceeding — it is an async advisory pattern."

**Disposition:** `open`

---

## Resolution Tracker

| Finding | Resolution | Spec File Changed | Milestone Impact | Done |
| --- | --- | --- | --- | --- |
| 1.1 | CEO emergency_review carve-out in CeoRoleContract §3 | `CeoRoleContract.md`, `AgentAuthorityGraph.md` | M14-WP2 done criteria | ☐ |
| 1.2 | `workforce_scope: project_bound` in PM profile + M14-WP1 done criterion | `ProjectManagerRoleContract.md` | M14-WP1 | ☐ |
| 1.3 | CWO GATE-005 is command not approval; rename in DecisionReviewGates | `CwoRoleContract.md`, `DecisionReviewGates.md` | M14-WP3 | ☐ |
| 1.4 | Clarify CSO `decision: allow` as advisory opinion, not binding | `CsoRoleContract.md`, `AgentAuthorityGraph.md` | M13-WP7 | ☐ |
| 2.1 | ESC-007 approval timeout; Secretary expiry notification | `EscalationModel.md` | M16 or new WP | ☐ |
| 2.2 | LOOP-006 escalation trace reset — escalation messages exempt from hop count | `AgentLoopControls.md` | M13-WP1 | ☐ |
| 2.3 | ESC-008 PM violation → Auditor → owner direct path | `EscalationModel.md`, `AuditorRoleContract.md` | M14-WP4 | ☐ |
| 2.4 | Owner `auditor_override` command; Auditor records override | `AuditorRoleContract.md` | M14-WP4 | ☐ |
| 3.1 | Gate timeouts in DecisionReviewGates §4 | `DecisionReviewGates.md` | M13-WP7 / M14-WP2 | ☐ |
| 3.2 | GATE-003 block → owner notification + override/terminate options | `DecisionReviewGates.md` | M14-WP2 | ☐ |
| 3.3 | `completion_report` sealing on owner approval, not publication | `ProjectArtifactModel.md` | M14-WP7 | ☐ |
| 3.4 | Gate flow trigger: CWO `submit_proposal()` → Secretary initiates GATE-001 | `DecisionReviewGates.md` | M13-WP7 | ☐ |
| 4.1 | Remove `specialist` from Secretary routing list | `SecretaryRoleContract.md` | M13-WP8 | ☐ |
| 4.2 | Pause authority hierarchy + stacked pause handling | `SafetyDoctrine.md` | M14-WP4 or M16 | ☐ |
| 4.3 | Specialist clarification criteria in SpecialistRoleContract §5 | `SpecialistRoleContract.md` | M14-WP6 | ☐ |
| 4.4 | `project_charter` write = CWO only; CEO approval = separate record | `ProjectArtifactModel.md` | M14-WP3 | ☐ |
| 5.1 | Fix OwnerInteractionModel CSO description | `OwnerInteractionModel.md` (both copies) | M13-WP7 | ☐ |
| 5.2 | Remove DL "disabled" text | `DomainLeaderRoleContract.md` | M13-WP5 | ☐ |
| 5.3 | Remove Specialist "disabled" text | `SpecialistRoleContract.md` | M14-WP6 | ☐ |
| 6.1 | Create OwnerRoleContract.md | new file | M16 or M17 | ☐ |
| 6.2 | Create TaskExecutionResultsModel.md | new file | M14-WP6 | ☐ |
| 6.3 | CSO async advisory pattern in CsoRoleContract §5 | `CsoRoleContract.md` | M13-WP7 | ☐ |

---

## References

- `spec/governance/architecture/AgentAuthorityGraph.md`
- `spec/governance/architecture/DecisionReviewGates.md`
- `spec/governance/architecture/SafetyDoctrine.md`
- `spec/orchestration/communication/EscalationModel.md`
- `spec/orchestration/communication/AgentLoopControls.md`
- `spec/orchestration/communication/OwnerInteractionModel.md`
- `spec/state-machines/ProjectArtifactModel.md`
- All role contracts in `spec/governance/contracts/`
