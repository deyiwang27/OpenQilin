# OpenQilin - Role Contract Template

## 1. Scope
- Defines the runtime contract for one role.

## 2. Role Identity
- `role_id`:
- `display_name`:
- `role_layer`: `support|governance|executive|operations|specialist`
- `reports_to`:
- `informs`:

## 3. Primary Duties
- Duty 1:
- Duty 2:
- Duty 3:

## 4. Authority Profile
- `decision`: `allow|deny`
- `command`: `allow|deny`
- `execution`: `allow|deny`
- `review`: `allow|deny`
- `advisory`: `allow|deny`
- `oversight`: `allow|deny`
- `workforce`: `allow|deny`

## 5. Data Access Boundaries
- Read scope:
- Write scope:
- Prohibited data classes:

## 6. Escalation and Routing
- Normal escalation targets:
- Escalation triggers:
- Out-of-scope routing behavior:

## 7. Runtime Interfaces
- Required query contracts:
- Allowed action categories:
- Required audit metadata:

## 8. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| REPLACE_WITH_RULE_ID | Replace with role-specific rule. | high | Policy Engine |

## 9. Conformance Tests
- Unauthorized actions are denied.
- Required metadata is present.
- Escalation behavior follows contract.
