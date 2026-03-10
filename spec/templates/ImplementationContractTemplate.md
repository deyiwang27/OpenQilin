# OpenQilin - Implementation Contract Template Specification

## 1. Scope
- Document name:
- Layer:
- Out of scope:

## 2. Normative Language
- `MUST`: mandatory, test-enforced.
- `MUST NOT`: prohibited, test-enforced.
- `SHOULD`: recommended, deviation requires rationale.
- `MAY`: optional.

## 3. Precedence
- This document is subordinate to:
- This document overrides:
- Conflict resolution order:

## 4. Canonical Terms
- Define each term once.
- Avoid synonyms for enforceable concepts.

## 5. Rule Set (Normative)
| Rule ID | Statement | Severity | Enforced By | Verification |
| --- | --- | --- | --- | --- |
| DOC-001 | Example `MUST` rule. | critical | component | test/monitor |

## 6. Data Contracts
### 6.1 Inputs
```json
{
  "example_input": "define required schema"
}
```

### 6.2 Outputs
```json
{
  "example_output": "define required schema"
}
```

### 6.3 Errors
| Code | Condition | Required Action |
| --- | --- | --- |
| ERR_EXAMPLE | Trigger condition | Retry/escalate/fail |

## 7. State Machine
### 7.1 States
- `STATE_A`
- `STATE_B`

### 7.2 Events
- `EVENT_X`

### 7.3 Transitions
| From | Event | Guard | Action | To |
| --- | --- | --- | --- | --- |
| STATE_A | EVENT_X | condition | side effect | STATE_B |

## 8. Decision Logic
- Inputs evaluated:
- Deterministic order:
- Tie-breakers:
- Escalation trigger:

## 9. Observability
### 9.1 Required Events
| Event ID | When Emitted | Required Fields |
| --- | --- | --- |
| EVT_EXAMPLE | condition | trace_id, rule_id |

### 9.2 Metrics
- Counter:
- Gauge:
- Latency:

### 9.3 Logs
- Structured format:
- Redaction policy:

## 10. Security and Access
| Subject | Resource | Action | Allowed? | Condition |
| --- | --- | --- | --- | --- |
| role | object | op | yes/no | policy |

## 11. Failure and Recovery
- Retry policy:
- Idempotency key:
- Timeout budget:
- Compensating action:

## 12. Conformance Tests
| Test ID | Rule IDs | Scenario | Expected Result |
| --- | --- | --- | --- |
| T-001 | DOC-001 | case | pass/fail |

## 13. Open Questions
- Q1:

## 14. Change Log
- Date:
- Author:
- Summary:
