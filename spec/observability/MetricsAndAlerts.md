# OpenQilin - Metrics and Alerts Specification

## 1. Scope
- Defines operational/governance metrics and alert routing.

## 2. Core Metrics
- authorization deny rate
- budget breach count
- task failure rate
- mean time to containment

## 3. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| MET-001 | Critical incidents MUST trigger alerts to governance channels. | critical | Observability |

## 4. Conformance Tests
- Alert is emitted for critical incident class events.
