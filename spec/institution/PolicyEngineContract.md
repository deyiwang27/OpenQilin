# OpenQilin - Policy Engine Contract Specification

## 1. Scope
- Defines the authorization and obligation interface for runtime actions.

## 2. Request Schema
```json
{
  "request_id": "uuid",
  "trace_id": "uuid",
  "actor": {"id": "string", "role": "string"},
  "action": "string",
  "target": "string",
  "context": {}
}
```

## 3. Response Schema
```json
{
  "decision": "allow|deny|allow_with_obligations",
  "rule_ids": ["string"],
  "obligations": ["string"],
  "reason": "string"
}
```

## 4. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| POL-001 | Decisions MUST be deterministic for same normalized input and policy version. | critical | Policy Engine |
| POL-002 | Deny response MUST include at least one rule ID. | high | Policy Engine |

## 5. Conformance Tests
- Replay with same input and policy version returns same output.
