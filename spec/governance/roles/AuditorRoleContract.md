# OpenQilin - Auditor Role Contract Specification

## 1. Scope
- Defines runtime contract for `auditor`.

## 2. Role Identity
- `role_id`: `auditor`
- `display_name`: `Auditor`
- `role_layer`: `governance`
- `reports_to`: `owner`
- `informs`: `ceo`

## 3. Primary Duties
- Monitor policy compliance, budget posture, and logical/behavioral risks.
- Trigger enforcement actions (pause/escalation) on severe governance violations.
- Provide auditable compliance findings to owner and executive leadership.

## 4. Authority Profile
| Authority | Value |
| --- | --- |
| decision | deny |
| command | deny |
| execution | deny |
| review | deny |
| advisory | deny |
| oversight | allow |
| workforce | deny |

## 5. Data Access Boundaries
- Read scope:
  - runtime logs, metrics, alerts, and audit trails
  - budget and policy decision metadata
- Write scope:
  - governance findings
  - pause/escalation evidence records
- Prohibited:
  - project command issuance
  - task execution operations
  - policy approval/publication

## 6. Escalation and Routing
- Direct escalation path: `auditor -> owner`.
- Notify `ceo` on governance and budget enforcement actions.
- Severe violations require immediate escalation with immutable evidence.

## 7. Runtime Interfaces
- `spec/governance/architecture/EscalationModel.md`
- `spec/constitution/BudgetEngineContract.md`
- `spec/observability/AuditEvents.md`

## 8. Normative Rule Bindings
- `AUTH-001`, `AUTH-002`
- `GOV-001`
- `BUD-001`, `BUD-002`
- `AUD-001`
- `ESC-001`, `ESC-002`

## 9. Conformance Tests
- Auditor cannot issue execution commands.
- Hard budget breaches produce enforcement and escalation evidence.
- Severe governance violations produce immutable audit records and owner escalation.
