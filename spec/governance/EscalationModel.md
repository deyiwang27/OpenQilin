# OpenQilin - Escalation Model Specification

## 1. Scope
- Defines escalation paths for operational, strategic, governance, and infrastructure incidents.
- Source of truth alignment: `spec/governance/GovernanceArchitecture.md` sections 4.5 and 8.6.

## 2. Canonical Paths
- Operational (general): Specialist -> PM -> CWO -> CEO -> Owner
- Operational coordination failures: Specialist -> Domain Lead -> PM -> CWO -> CEO
- Strategic: CSO -> CEO -> Owner
- Governance (authority escalation): Auditor -> Owner (direct)
- Budget violations (risk + enforcement): PM -> CWO (risk monitoring), Auditor -> Owner -> CEO (informed by Auditor)
- Behavioral violations: Specialist -> PM -> Auditor -> Owner -> CEO (informed by Auditor)
- Infrastructure: System Component -> Administrator -> Owner
- Agent pause reporting: any pause event -> CEO notification; critical impact -> Owner immediate alert

## 3. Escalation Principles
- Operational agents cannot override governance enforcement.
- Independent oversight agents can intervene directly when required.
- Strategic decisions remain under executive or Owner authority.
- Escalation events must be traceable and auditable.

## 4. Trigger Catalog (Deterministic)
Escalation trigger model:
- `Event -> Condition -> Target Authority -> Action`

Canonical triggers:
1. Budget hard breach -> threshold_state=`hard` -> Auditor -> enforce stop, escalate Owner, notify CEO
2. Domain disagreement -> unresolved after PM review -> CEO -> strategic arbitration
3. Governance violation -> constitutional rule breach -> Owner -> direct governance escalation
4. Operational deadlock -> retries exhausted and progress blocked -> highest authority in scope -> forced resolution
5. Legal risk detected -> severity in `high|critical` -> Owner -> immediate compliance escalation
6. Agent paused -> any pause event -> CEO -> notification
7. Agent paused (critical impact) -> critical impact true -> Owner -> immediate alert

## 5. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| ESC-001 | Critical incidents MUST follow defined escalation path. | high | Task Orchestrator |
| ESC-002 | Governance and infrastructure escalations MUST permit direct Owner escalation. | critical | Task Orchestrator |
| ESC-003 | Budget hard-threshold enforcement MUST be initiated by Auditor independent of operational chain. | critical | Budget Engine |
| ESC-004 | Escalation records MUST include incident class, current stage, and next authority target. | high | Observability |
| ESC-005 | Any agent pause action MUST be reported to CEO. | high | Task Orchestrator |
| ESC-006 | Agent pause actions with critical impact MUST alert Owner immediately. | critical | Task Orchestrator |

## 6. Event Contract
Minimum escalation event fields:
- `event_id`
- `trace_id`
- `incident_type`
- `severity`
- `current_owner_role`
- `next_owner_role`
- `path_reference`
- `rule_ids`

## 7. Conformance Tests
- Critical incident emits escalation event with trace and path metadata.
- Governance escalation can route Auditor directly to Owner.
- Budget hard-threshold breach includes Auditor enforcement event before executive remediation.
- Behavioral incidents follow the defined governance-involved path.
- Agent pause events always notify CEO.
- Agent pause events marked critical impact alert Owner.
