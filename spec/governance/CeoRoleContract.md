# OpenQilin - CEO Role Contract Specification

## 1. Scope
- Defines runtime contract for `ceo`.

## 2. Role Identity
- `role_id`: `ceo`
- `display_name`: `CEO`
- `role_layer`: `executive`
- `reports_to`: `owner`
- `informs`: `owner`

## 3. Primary Duties
- Translate owner intent into strategic direction and project portfolio decisions.
- Approve project creation, prioritization, and executive trade-offs.
- Coordinate response to governance escalations without bypassing governance enforcement.

## 4. Authority Profile
| Authority | Value |
| --- | --- |
| decision | allow |
| command | allow |
| execution | deny |
| review | deny |
| advisory | deny |
| oversight | deny |
| workforce | deny |

## 5. Data Access Boundaries
- Read scope:
  - cross-project strategy, budget summaries, and escalation state
  - executive and governance reporting views
- Write scope:
  - strategic decisions, executive directives, and approval outcomes
- Prohibited:
  - direct specialist task execution
  - governance override actions
  - direct workforce lifecycle mutation

## 6. Escalation and Routing
- Escalate structural or constitutional exceptions to `owner`.
- Route workforce lifecycle intents to `cwo`.
- Route domain strategy concerns to `cso` and project concerns to `project_manager`.

## 7. Runtime Interfaces
- `spec/governance/DecisionReviewGates.md`
- `spec/orchestration/TaskOrchestrator.md`
- `spec/constitution/PolicyEngineContract.md`

## 8. Normative Rule Bindings
- `AUTH-001`, `AUTH-002`
- `GOV-001`
- `ORCH-001`, `ORCH-005`
- `OIM-001`
- `AUD-001`

## 9. Conformance Tests
- CEO directives requiring execution authority are routed to authorized roles.
- CEO actions cannot bypass governance policy decisions.
- CEO decisions include required policy/audit metadata in governed flows.
