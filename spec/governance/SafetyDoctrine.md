# OpenQilin - Safety Doctrine Specification

## 1. Scope
- Defines safety principles, containment actions, and emergency controls.
- Source of truth alignment: `spec/governance/GovernanceArchitecture.md` sections 8.1-8.7.

## 2. Safety Principles
- Containment first
- Traceability required
- Human override available
- Separation of safety authority (governance enforces, operations execute)

## 3. Risk Categories
- Behavioral risks (Auditor monitored)
- Execution risks (trace-analysis detected)
- Resource risks (budget governance monitored)
- Infrastructure risks (Administrator monitored)

## 4. Monitoring Responsibilities
- Auditor:
  - monitors behavioral and operational risks
  - enforces budget limits
  - may pause or restrict affected agents/projects
- Administrator:
  - monitors infrastructure integrity and availability
  - may suspend components or isolate failures
- CEO:
  - evaluates major safety incidents
  - may pause projects, adjust strategy, escalate to Owner

## 5. Containment and Emergency Actions
- Containment:
  - agent suspension
  - project pause
  - resource lockdown
  - infrastructure isolation
- Emergency:
  - emergency project shutdown (CEO)
  - system safety mode (Administrator)
  - Owner override (ultimate authority)

## 6. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| SAF-001 | Safety containment MUST take priority over task completion. | critical | Task Orchestrator |
| SAF-002 | Safety enforcement MUST remain independent from operational execution. | critical | Policy Engine |
| SAF-003 | Safety incidents MUST be recorded in immutable execution logs. | critical | Observability |
| SAF-004 | Owner override capability MUST remain available and auditable. | high | Runtime |

## 7. Incident Record Contract
Required fields:
- timestamp
- affected agents/components
- triggering condition
- containment actions
- final resolution

## 8. Conformance Tests
- Unsafe task path triggers containment action.
- Safety incidents produce complete immutable incident records.
- Owner override action is accepted when authorized and fully audited.
