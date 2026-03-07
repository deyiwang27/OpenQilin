# OpenQilin -  Memory Architecture Specification

## 1. Scope
- Defines memory tiers, access control, retention, and audit constraints.

## 2. Memory Tiers
- Hot: active task context
- Warm: project historical context
- Cold: archived records and institutional memory

## 3. Access Policy
| Role | Hot | Warm | Cold | Write |
| --- | --- | --- | --- | --- |
| PM | scoped | scoped | summary-only | scoped |
| CWO | limited | cross-project summary | summary-only | limited |
| Auditor | read | read | read | none |
| Administrator | infra-level | infra-level | infra-level | maintenance only |

## 4. Data Rules
- MEM-001: Immutable logs MUST be append-only.
- MEM-002: Sensitive data MUST be redacted in non-authorized views.
- MEM-003: Retention TTL MUST be explicitly defined per tier.

## 5. Conformance Tests
- Unauthorized read is denied with auditable reason.
- Redaction policy applied in role-scoped query.

