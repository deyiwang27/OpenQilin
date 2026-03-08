# OpenQilin - Audit Events Specification

## 1. Scope
- Defines immutable governance/audit event taxonomy.

## 2. Event Categories
- policy_decision
- escalation
- enforcement
- lifecycle_transition
- budget_violation

## 3. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| AUD-001 | Governance-critical actions MUST emit immutable audit events. | critical | Observability |

## 4. Conformance Tests
- Audit events include policy_version, policy_hash, and rule_ids.
