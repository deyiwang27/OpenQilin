# OpenQilin - Decision Review Gates Specification

## 1. Scope

- Defines mandatory review gates for project and budget decisions.
- Source of truth alignment: `spec/governance/architecture/GovernanceArchitecture.md` section 4.2.

## 2. Gate Flow

MVP v1 (simplified, CSO deferred):

- owner/cwo proposal drafting → ceo+cwo review → owner+ceo approval → cwo project initialization
- cso strategic review path was deferred in v1.

MVP v2 (full gate, CSO active):

- owner/cwo proposal drafting → **cso strategic review** → ceo+cwo review → owner+ceo approval → **cwo initialization command**
- cso is activated in M13-WP7 and participates as a mandatory strategic review step before ceo+cwo review.
- proposal revisions remain in `proposed` project state until approval.

**Gate flow trigger:** Gate flow is triggered when CWO calls `submit_proposal(project_charter)`. Secretary registers the proposal in `governance_artifacts` with `status: gate_pending`. Secretary then initiates GATE-001 (CSO review) by routing to CSO. All subsequent gate transitions are driven by Secretary based on current gate state and recorded outcomes. (Note: CWO's GATE-005 action is a **workforce initialization command**, not a decision approval — `decision: deny` applies to CWO throughout the flow.)

## 3. Strategic Review Outcomes

- `Aligned`: proposal proceeds to ceo+cwo review.
- `Needs Revision`: proposal must be revised and resubmitted before advancing.
- `Strategic Conflict`: after three unresolved revision cycles, proposal is blocked. On block: emit `revision_cycle_exhausted` audit event with full revision history. Owner is notified directly by Secretary. Owner may either: (a) issue a `gate_override` command (with mandatory justification) to advance to the approval gate; or (b) issue a `proposal_terminate` command to close the gate flow. CEO and CWO both receive the block notification and cannot unilaterally restart the flow.

**Gate timeouts** (default values; configurable via `settings.py`):

| Gate | Stage | Timeout | On Expiry |
| --- | --- | --- | --- |
| GATE-001 | CSO strategic review | 24h | Emit `gate_timeout`; Secretary notifies CWO and CSO; CWO may resubmit |
| GATE-003 | CEO+CWO review | 48h | Emit `gate_timeout`; Secretary notifies CEO and CWO; proposal returns to `proposed` |
| GATE-004 | Owner+CEO approval | 48h | Emit `gate_timeout`; Secretary notifies owner; proposal returns to `proposed` |

## 4. Decision Ownership

- cwo prepares proposal/workforce initialization package.
- cso reviews proposal for strategic alignment, opportunity cost, and cross-project risk before ceo+cwo review.
- ceo co-owns proposal review and approval decision.
- owner co-approves project activation and major completion decisions.
- cwo executes project initialization after approval.

## 5. Rule Set

| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| GATE-001 | New projects MUST pass owner/ceo/cwo review gates before activation. | high | Task Orchestrator |
| GATE-002 | Proposals marked `Needs Revision` MUST NOT proceed without resubmission. | high | Task Orchestrator |
| GATE-003 | `Strategic Conflict` proposals with three unresolved revision cycles MUST require explicit ceo override to proceed. | high | Task Orchestrator |
| GATE-004 | ceo final decision outcomes MUST be audit logged with rationale. | medium | Observability |
| GATE-005 | Proposals MUST pass cso strategic review before entering ceo+cwo review (MVP v2). CWO project initialization (GATE-005 action) is a workforce command, not a decision approval. | high | Task Orchestrator |
| GATE-006 | cso strategic review outcomes MUST be recorded with traceable metadata before the proposal advances. | medium | Observability |

## 6. Gate Event Contract

Required fields:

- proposal_id
- project_scope
- cwo_submission_version
- cso_review_outcome (`Aligned` | `Needs Revision` | `Strategic Conflict`)
- cso_advisory_text
- review_outcome
- revision_cycle_count
- ceo_decision
- override_flag
- trace_id

## 7. Conformance Tests

- Proposal bypassing required gate is rejected.
- Proposal advancing past cso strategic review without a recorded cso outcome is rejected (MVP v2).
- `Needs Revision` proposals are blocked from approval path until resubmitted.
- Third unresolved `Strategic Conflict` cycle requires explicit ceo override flag.
- Approved proposals include auditable gate-decision event chain.
