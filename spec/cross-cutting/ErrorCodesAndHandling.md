# OpenQilin - Error Codes and Handling Specification

## 1. Scope
- Defines canonical error codes and handling behavior across components.

## 2. Error Classes
- validation_error, authorization_error, budget_error, runtime_error, safety_error

## 3. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| ERR-001 | Error responses MUST include canonical code and actionable reason. | high | Runtime |

## 4. Conformance Tests
- Unknown errors map to deterministic fallback code.
