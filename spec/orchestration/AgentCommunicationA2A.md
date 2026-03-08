# OpenQilin - Agent Communication A2A Specification

## 1. Scope
- Defines inter-agent message schema and delivery guarantees.

## 2. Message Envelope
```json
{
  "message_id": "uuid",
  "trace_id": "uuid",
  "from_agent": "string",
  "to_agent": "string",
  "type": "command|response|event|escalation",
  "payload": {},
  "idempotency_key": "string"
}
```

## 3. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| A2A-001 | Delivery MUST be at-least-once with idempotent handling. | high | Task Orchestrator |

## 4. Conformance Tests
- Duplicate messages do not duplicate side effects.
