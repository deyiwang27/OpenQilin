# OpenQilin - System Logs Specification

## 1. Scope
- Defines required system log streams and structured fields.

## 2. Required Fields
- timestamp, level, component, trace_id, event_id, message, context

## 3. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| LOG-001 | Critical actions MUST emit structured logs with trace_id. | high | Observability |

## 4. Conformance Tests
- Logs missing trace_id fail validation where required.
