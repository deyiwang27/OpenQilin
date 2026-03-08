# OpenQilin - Conformance Test Plan Specification

## 1. Scope
- Defines cross-spec conformance strategy and release gates.

## 2. Test Categories
- policy enforcement
- orchestration behavior
- safety containment
- budget enforcement
- observability completeness

## 3. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| TEST-001 | Critical rules MUST have at least one automated conformance test. | critical | CI Pipeline |

## 4. Release Gate
- No release if critical conformance tests fail.
