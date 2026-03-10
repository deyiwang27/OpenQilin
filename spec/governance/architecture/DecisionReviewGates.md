# OpenQilin - Decision Review Gates Specification

## 1. Scope
- Defines mandatory review gates for project and budget decisions.
- Source of truth alignment: `spec/governance/architecture/GovernanceArchitecture.md` section 4.2.

## 2. Gate Flow
- cwo proposal -> cso strategic review -> ceo decision -> project initialization

## 3. Strategic Review Outcomes
- `Aligned`: proposal proceeds to ceo approval.
- `Needs Revision`: proposal must be revised and resubmitted.
- `Strategic Conflict`: after three rejections, proposal cannot proceed unless ceo explicitly overrides.

## 4. Decision Ownership
- cso provides strategic review and advisory outcomes.
- ceo retains final decision authority for project approval/rejection.
- cwo executes project initialization after approval.

## 5. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| GATE-001 | New projects MUST pass cso strategic review before ceo approval. | high | Task Orchestrator |
| GATE-002 | Proposals marked `Needs Revision` MUST NOT proceed without resubmission. | high | Task Orchestrator |
| GATE-003 | `Strategic Conflict` proposals rejected three times MUST require explicit ceo override to proceed. | high | Task Orchestrator |
| GATE-004 | ceo final decision outcomes MUST be audit logged with rationale. | medium | Observability |

## 6. Gate Event Contract
Required fields:
- proposal_id
- project_scope
- cwo_submission_version
- cso_outcome
- rejection_count
- ceo_decision
- override_flag
- trace_id

## 7. Conformance Tests
- Proposal bypassing required gate is rejected.
- `Needs Revision` proposals are blocked from approval path until resubmitted.
- Third `Strategic Conflict` rejection requires explicit ceo override flag.
- Approved proposals include auditable gate-decision event chain.
