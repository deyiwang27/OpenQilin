# OpenQilin - Constitution and Authority Rules Specification

## 1. Scope
- Defines constitutional constraints, authority boundaries, and conflict precedence for all agents.
- Primary consumers: Policy Engine, Task Orchestrator, Governance agents.

## 2. Precedence (Canonical)
1. Constitution rules
2. Governance enforcement actions
3. Executive decisions
4. Operational decisions
5. Specialist execution plans

## 3. Rule IDs
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| AUTH-001 | Every action request MUST include actor role and authority type. | critical | Policy Engine |
| AUTH-002 | Actions violating explicit authority matrix MUST be denied. | critical | Policy Engine |
| AUTH-003 | Emergency powers MUST generate immutable audit events. | high | Policy Engine |

## 4. Authorization Contract
### 4.1 Decision Input
```json
{
  "actor_id": "string",
  "actor_role": "CEO|CWO|CSO|PM|DL|Specialist|Auditor|Administrator|Owner",
  "action": "string",
  "target": "string",
  "context": {
    "project_id": "string",
    "budget_state": "ok|soft|hard",
    "incident_level": "none|warning|critical"
  }
}
```

### 4.2 Decision Output
```json
{
  "decision": "allow|deny|allow_with_obligations",
  "rule_ids": ["AUTH-001"],
  "obligations": ["emit_audit_event"],
  "reason": "string"
}
```

## 5. Conflict Resolution
- If two rules conflict, higher-precedence source wins.
- Ties at same precedence resolved by stricter rule (`deny` > `allow_with_obligations` > `allow`).

## 6. Conformance Tests
- Unauthorized workforce action is denied.
- Governance action cannot be overridden by executive action.
- All emergency actions include rule IDs and trace IDs.

