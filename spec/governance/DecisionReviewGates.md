# OpenQilin - Decision Review Gates Specification

## 1. Scope
- Defines mandatory review gates for project and budget decisions.
- Source of truth alignment: `spec/governance/GovernanceArchitecture.md` section 4.2.

## 2. Gate Flow
- CWO proposal -> CSO strategic review -> CEO decision -> project initialization

## 3. Strategic Review Outcomes
- `Aligned`: proposal proceeds to CEO approval.
- `Needs Revision`: proposal must be revised and resubmitted.
- `Strategic Conflict`: after three rejections, proposal cannot proceed unless CEO explicitly overrides.

## 4. Decision Ownership
- CSO provides strategic review and advisory outcomes.
- CEO retains final decision authority for project approval/rejection.
- CWO executes project initialization after approval.

## 5. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| GATE-001 | New projects MUST pass CSO strategic review before CEO approval. | high | Task Orchestrator |
| GATE-002 | Proposals marked `Needs Revision` MUST NOT proceed without resubmission. | high | Task Orchestrator |
| GATE-003 | `Strategic Conflict` proposals rejected three times MUST require explicit CEO override to proceed. | high | Task Orchestrator |
| GATE-004 | CEO final decision outcomes MUST be audit logged with rationale. | medium | Observability |

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
- Third `Strategic Conflict` rejection requires explicit CEO override flag.
- Approved proposals include auditable gate-decision event chain.
