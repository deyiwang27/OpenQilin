# OpenQilin - Safety Doctrine Specification

## 1. Scope
- Defines safety principles, containment actions, and emergency controls.

## 2. Safety Principles
- Containment first
- Traceability required
- Human override available

## 3. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| SAF-001 | Safety containment MUST take priority over task completion. | critical | Task Orchestrator |

## 4. Conformance Tests
- Unsafe task path triggers containment action.
