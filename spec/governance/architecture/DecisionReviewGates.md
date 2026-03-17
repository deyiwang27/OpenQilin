# OpenQilin - Decision Review Gates Specification

## 1. Scope

- Defines mandatory review gates for project and budget decisions.
- Source of truth alignment: `spec/governance/architecture/GovernanceArchitecture.md` section 4.2.

## 2. Gate Flow

MVP v1 (simplified, CSO deferred):

- owner/cwo proposal drafting → ceo+cwo review → owner+ceo approval → cwo project initialization
- cso strategic review path was deferred in v1.

MVP v2 (full gate, CSO active):

- owner/cwo proposal drafting → **cso strategic review** → ceo+cwo review → owner+ceo approval → cwo project initialization
- cso is activated in M12 and participates as a mandatory strategic review step before ceo+cwo review.
- proposal revisions remain in `proposed` project state until approval.

## 3. Strategic Review Outcomes

- `Aligned`: proposal proceeds to ceo+cwo review.
- `Needs Revision`: proposal must be revised and resubmitted before advancing.
- `Strategic Conflict`: after three unresolved revision cycles, proposal requires explicit ceo override to proceed.

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
| GATE-005 | Proposals MUST pass cso strategic review before entering ceo+cwo review (MVP v2). | high | Task Orchestrator |
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
