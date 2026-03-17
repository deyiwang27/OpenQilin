# OpenQilin - Safety Doctrine Specification

## 1. Scope
- Defines safety principles, containment actions, and emergency controls.
- Source of truth alignment: `spec/governance/architecture/GovernanceArchitecture.md` sections 8.1-8.7.

## 2. Safety Principles
- Containment first
- Traceability required
- Human override available
- Separation of safety authority (governance enforces, operations execute)

## 3. Risk Categories
- Behavioral risks (auditor monitored)
- Execution risks (trace-analysis detected)
- Resource risks (budget governance monitored)
- Infrastructure risks (administrator monitored)

## 4. Monitoring Responsibilities
- auditor:
  - monitors behavioral and operational risks
  - enforces budget limits
  - may pause or restrict affected agents/projects
- administrator:
  - monitors infrastructure integrity and availability
  - may suspend components or isolate failures
- ceo:
  - evaluates major safety incidents (emergency_review carve-out; see `CeoRoleContract §4`)
  - may pause projects, adjust strategy, escalate to owner
  - emergency project shutdown authority (emergency action only; not routine project review)

## 5. Containment and Emergency Actions
- Containment:
  - agent suspension
  - project pause
  - resource lockdown
  - infrastructure isolation
- Emergency:
  - emergency project shutdown (ceo)
  - system safety mode (administrator)
  - owner override (ultimate authority)

Pause reporting requirements:
- Any agent pause action must notify ceo.
- If pause impact is critical to project continuity or governance integrity, owner must be alerted immediately.

**Project pause authority hierarchy:** `owner > auditor (safety) > ceo (emergency) > project_manager (budget/operational)`. Any agent may request a pause by issuing a `pause_request` event to the governance channel. Pause is applied immediately by Secretary (who tracks project state). Resume requires the pausing authority or owner to issue `resume_command`. Stacked pauses: a project remains paused until all active pause requests are cleared. Each pause request must reference the rule that triggered it.

## 6. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| SAF-001 | Safety containment MUST take priority over task completion. | critical | Task Orchestrator |
| SAF-002 | Safety enforcement MUST remain independent from operational execution. | critical | Policy Engine |
| SAF-003 | Safety incidents MUST be recorded in immutable execution logs. | critical | Observability |
| SAF-004 | owner override capability MUST remain available and auditable. | high | Runtime |
| SAF-005 | Agent pause events MUST notify ceo and escalate to owner when critical impact is detected. | high | Task Orchestrator |

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
- owner override action is accepted when authorized and fully audited.
- Agent pause actions always produce ceo notification records.
- Critical-impact pause actions produce owner alert records.
