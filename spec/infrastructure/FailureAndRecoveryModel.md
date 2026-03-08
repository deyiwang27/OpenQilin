# OpenQilin - Failure and Recovery Model Specification

## 1. Scope
- Defines failure classes, recovery workflows, and compensating actions.

## 2. Failure Classes
- transient, persistent, safety-critical

## 3. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| FRM-001 | Safety-critical failures MUST trigger containment before retry. | critical | Task Orchestrator |

## 4. Conformance Tests
- Persistent failures escalate according to escalation policy.
