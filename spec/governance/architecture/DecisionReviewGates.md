# OpenQilin - Decision Review Gates Specification

## 1. Scope
- Defines mandatory review gates for project and budget decisions.
- Source of truth alignment: `spec/governance/architecture/GovernanceArchitecture.md` section 4.2.

## 2. Gate Flow
- owner/cwo proposal drafting -> ceo+cwo review -> owner+ceo approval -> cwo project initialization

First MVP posture:
- cso strategic review path is deferred.
- proposal revisions remain in `proposed` project state until approval.

## 3. Strategic Review Outcomes
- `Aligned`: proposal proceeds to owner+ceo approval.
- `Needs Revision`: proposal must be revised and resubmitted.
- `Strategic Conflict`: after three unresolved revision cycles, proposal requires explicit ceo override to proceed.

## 4. Decision Ownership
- cwo prepares proposal/workforce initialization package.
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

## 6. Gate Event Contract
Required fields:
- proposal_id
- project_scope
- cwo_submission_version
- review_outcome
- revision_cycle_count
- ceo_decision
- override_flag
- trace_id

## 7. Conformance Tests
- Proposal bypassing required gate is rejected.
- `Needs Revision` proposals are blocked from approval path until resubmitted.
- Third unresolved `Strategic Conflict` cycle requires explicit ceo override flag.
- Approved proposals include auditable gate-decision event chain.
