# OpenQilin - Communication Protocol (A2A) Specification

## 1. Scope
- Defines inter-agent messaging semantics and reliability guarantees.

## 2. Message Contract
```json
{
  "message_id": "uuid",
  "trace_id": "uuid",
  "from_agent": "string",
  "to_agent": "string",
  "type": "command|response|event|escalation",
  "payload": {},
  "deadline_ms": 30000,
  "idempotency_key": "string"
}
```

## 3. Reliability Rules
- A2A-001: Delivery guarantee MUST be at-least-once.
- A2A-002: Handlers MUST be idempotent by `idempotency_key`.
- A2A-003: Retries MUST use exponential backoff with max attempts.
- A2A-004: Timeout MUST emit failure event and escalate when required.

## 4. Ordering
- Per `(trace_id, target_agent)` ordering SHOULD be preserved.
- Cross-trace global ordering is not guaranteed.

## 5. Conformance Tests
- Duplicate delivery does not duplicate side effects.
- Timeout path emits escalation event.

