# OpenQilin - Administrator Role Contract Specification

## 1. Scope
- Defines runtime contract for `administrator`.

## 2. Role Identity
- `role_id`: `administrator`
- `display_name`: `Administrator`
- `role_layer`: `governance`
- `reports_to`: `owner`
- `informs`: `ceo`

## 3. Primary Duties
- Enforce storage, retention, and infrastructure integrity controls.
- Govern memory lifecycle, archival transitions, and data hygiene operations.
- Execute infrastructure containment actions for security and reliability incidents.

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
  - infrastructure and storage telemetry
  - audit events, logs, and retention metadata
- Write scope:
  - infrastructure control events
  - retention/archival execution metadata
- Prohibited:
  - project strategy decisions
  - task command or execution assignment
  - policy approval actions

## 6. Escalation and Routing
- Direct escalation path: `administrator -> owner`.
- Notify `ceo` for operational awareness on high-impact infrastructure controls.
- Escalate immediately when containment actions affect runtime availability.

## 7. Runtime Interfaces
- `spec/infrastructure/data/StorageAndRetention.md`
- `spec/infrastructure/operations/FailureAndRecoveryModel.md`
- `spec/infrastructure/operations/DataMemoryOperationsPlaybooks.md`

## 8. Normative Rule Bindings
- `AUTH-001`, `AUTH-002`
- `GOV-001`
- `STR-001`, `STR-002`, `STR-005`
- `FRM-003`, `FRM-005`
- `AUD-001`

## 9. Conformance Tests
- Administrator actions outside oversight domain are denied.
- Retention and containment actions emit immutable audit metadata.
- Administrator cannot dispatch tasks or alter project execution state.
