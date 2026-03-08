# OpenQilin - Escalation Model Specification

## 1. Scope
- Defines escalation paths for operational, strategic, governance, and infrastructure incidents.

## 2. Canonical Paths
- Operational: Specialist -> Domain Lead -> PM -> CWO -> CEO
- Strategic: CSO -> CEO -> Owner
- Governance: Auditor -> Owner (CEO informed)
- Infrastructure: Component -> Administrator -> Owner

## 3. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| ESC-001 | Critical incidents MUST follow defined escalation path. | high | Task Orchestrator |

## 4. Conformance Tests
- Critical incident emits escalation event with trace and path metadata.
