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

## 7. Runtime Interfaces
- `spec/governance/DecisionReviewGates.md`
- `spec/orchestration/ProjectArtifactModel.md`
- `spec/cross-cutting/ProjectTaskQueryContracts.md`

## 8. Normative Rule Bindings
- `AUTH-001`, `AUTH-002`
- `GATE-001`, `GATE-002`
- `OIM-003`
- `AUD-001`

## 9. Conformance Tests
- CSO cannot issue command/workforce actions.
- Strategic conflict advisories are recorded with traceable metadata.
- Strategic review outcomes are visible to CEO decision flow.
