# OpenQilin - CSO Role Contract Specification

## 1. Scope
- Defines runtime contract for `cso`.

## 2. Role Identity
- `role_id`: `cso`
- `display_name`: `CSO`
- `role_layer`: `executive`
- `reports_to`: `ceo`
- `informs`: `ceo`

## 3. Primary Duties
- Provide portfolio strategy and long-horizon risk analysis.
- Review project proposals for strategic alignment and opportunity cost.
- Issue strategic advisories and conflict flags for executive decisions.

## 4. Authority Profile
| Authority | Value |
| --- | --- |
| decision | allow |
| command | deny |
| execution | deny |
| review | deny |
| advisory | allow |
| oversight | deny |
| workforce | deny |

**Note on `decision: allow`:** CSO `decision: allow` means CSO may form and issue a strategic review opinion (e.g. `Aligned`, `Needs Revision`, `Strategic Conflict`). It does **not** confer approval or veto authority over projects. CSO recommendations are advisory and non-binding without CEO or owner endorsement. CSO cannot approve, block, or terminate a project unilaterally.

## 5. Data Access Boundaries
- Read scope:
  - cross-project metrics, strategic trend signals, risk summaries
  - proposal and portfolio planning artifacts
- Write scope:
  - strategic advisories, risk forecasts, and recommendation records
- Prohibited:
  - direct task execution control
  - workforce lifecycle actions
  - governance override actions

## 6. Escalation and Routing
- Strategic conflicts escalate to `ceo`.
- Material strategic risk may be routed to `owner` per governance policy.
- Execution-level remediation requests are routed to `cwo` or `project_manager`.
- Domain leader advisory path: `domain_leader` may submit a `strategic_insight_request` to CSO through the governance channel (routed by Secretary). CSO responds with an advisory record in `governance_artifacts`. The response is non-binding; DL does not wait on CSO before proceeding (async advisory pattern).

## 7. Runtime Interfaces
- `spec/governance/architecture/DecisionReviewGates.md`
- `spec/orchestration/memory/ProjectArtifactModel.md`
- `spec/cross-cutting/contracts/ProjectTaskQueryContracts.md`

## 8. Normative Rule Bindings
- `AUTH-001`, `AUTH-002`
- `GATE-001`, `GATE-002`
- `OIM-003`
- `AUD-001`

## 9. Conformance Tests
- CSO cannot issue command/workforce actions.
- Strategic conflict advisories are recorded with traceable metadata.
- Strategic review outcomes are visible to CEO decision flow.
