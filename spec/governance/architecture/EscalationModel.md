# OpenQilin - Escalation Model Specification

## 1. Scope
- Defines escalation paths for operational, strategic, governance, and infrastructure incidents.
- Source of truth alignment: `spec/governance/architecture/GovernanceArchitecture.md` sections 4.5 and 8.6.

## 2. Canonical Paths
Escalation chains:
- Operational (general): specialist -> project_manager -> cwo -> ceo -> owner
- Operational coordination failures: specialist -> domain_leader -> project_manager -> cwo -> ceo
- Strategic: cso -> ceo -> owner
- Governance (authority escalation): auditor -> owner (direct)
- Budget violations:
  - risk monitoring chain: project_manager -> cwo
  - enforcement chain: auditor -> owner
- Behavioral violations:
  - escalation chain: specialist -> project_manager -> auditor -> owner
- Infrastructure: system_component -> administrator -> owner

Notification-only routes (not escalation chain ownership transfer):
- Budget violations: notify `ceo`.
- Behavioral violations: notify `ceo`.
- Agent pause reporting: any pause event -> notify `ceo`; critical impact -> immediate alert to `owner`.

## 3. Escalation Principles
- Operational agents cannot override governance enforcement.
- Independent oversight agents can intervene directly when required.
- Strategic decisions remain under executive or owner authority.
- Escalation events must be traceable and auditable.

## 4. Trigger Catalog (Deterministic)
Escalation trigger model:
- `Event -> Condition -> Target Authority -> Action`

Canonical triggers:
1. Budget hard breach -> threshold_state=`hard` -> auditor -> enforce stop, escalate owner, notify ceo
2. Domain disagreement -> unresolved after project_manager review -> ceo -> strategic arbitration
3. Governance violation -> constitutional rule breach -> owner -> direct governance escalation
4. Operational deadlock -> retries exhausted and progress blocked -> highest authority in scope -> forced resolution
5. Legal risk detected -> severity in `high|critical` -> owner -> immediate compliance escalation
6. Agent paused -> any pause event -> notify ceo
7. Agent paused (critical impact) -> critical impact true -> owner -> immediate alert

## 5. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| ESC-001 | Critical incidents MUST follow defined escalation path. | high | Task Orchestrator |
| ESC-002 | Governance and infrastructure escalations MUST permit direct owner escalation. | critical | Task Orchestrator |
| ESC-003 | Budget hard-threshold enforcement MUST be initiated by auditor independent of operational chain. | critical | Budget Engine |
| ESC-004 | Escalation records MUST include incident class, current stage, and next authority target. | high | Observability |
| ESC-005 | Any agent pause action MUST be reported to ceo. | high | Task Orchestrator |
| ESC-006 | Agent pause actions with critical impact MUST alert owner immediately. | critical | Task Orchestrator |

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
- Governance escalation can route auditor directly to owner.
- Budget hard-threshold breach includes auditor enforcement event before executive remediation.
- Behavioral incidents follow the defined governance-involved path.
- Agent pause events always notify ceo.
- Agent pause events marked critical impact alert owner.
