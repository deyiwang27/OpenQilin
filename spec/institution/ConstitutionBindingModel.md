# OpenQilin - Constitution Binding Model Specification

## 1. Scope
- Defines how runtime components bind and enforce constitutional artifacts.

## 2. Binding Model
- Static load at startup
- Hot reload on approved version changes
- Version pinning per execution context

## 3. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| CBM-001 | Policy evaluation MUST use an explicit constitution version. | critical | Policy Engine |

## 4. Conformance Tests
- Action decision records include constitution version and rule IDs.
