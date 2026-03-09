# OpenQilin - Agent Communication Protocol (ACP) Specification

## 1. Scope
- Defines wire-level protocol for transporting A2A envelopes.
- Defines framing, routing, auth-context propagation, and acknowledgement semantics.

## 2. ACP Frame Contract
```json
{
  "protocol": "acp/1.0",
  "frame_id": "uuid",
  "message_id": "uuid",
  "trace_id": "uuid",
  "conversation_id": "uuid",
  "route": {
    "source": "agent://<agent_id>",
    "destination": "agent://<agent_id>",
    "channel_id": "string",
    "partition_key": "string"
  },
  "auth": {
    "actor_id": "string",
    "actor_role": "string",
    "token_ref": "string",
    "policy_version": "string",
    "policy_hash": "string"
  },
  "reliability": {
    "attempt": 1,
    "max_attempts": 5,
    "ack_deadline_ms": 30000,
    "ttl_ms": 600000
  },
  "payload": {
    "content_type": "application/json",
    "a2a_envelope": {}
  }
}
```

## 3. Ack/Nack Semantics
Ack frame:
```json
{
  "protocol": "acp/1.0",
  "type": "ack",
  "frame_id": "uuid",
  "message_id": "uuid",
  "status": "accepted|processed",
  "timestamp": "RFC3339"
}
```

Nack frame:
```json
{
  "protocol": "acp/1.0",
  "type": "nack",
  "frame_id": "uuid",
  "message_id": "uuid",
  "error_code": "AUTH_FAILED|VALIDATION_FAILED|ROUTE_FAILED|TIMEOUT",
  "retryable": true,
  "timestamp": "RFC3339"
}
```

## 4. Retry and Dead-Letter Behavior
- Retry on `nack.retryable=true` or ack timeout.
- Backoff strategy: bounded exponential with jitter.
- Dead-letter when retries exhausted or non-retryable `nack` received.
- Dead-letter payload must include original frame + terminal error metadata.

## 5. Security and Validation
- Frames without valid `auth` context are rejected before route execution.
- `policy_version` and `policy_hash` must be carried end-to-end.
- ACP implementations must validate frame schema before queueing.

## 6. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| ACP-001 | Every ACP frame MUST include route and auth context before dispatch. | critical | ACP Runtime |
| ACP-002 | Ack timeout or retryable nack MUST trigger bounded retry policy. | high | ACP Runtime |
| ACP-003 | Retry exhaustion MUST transition frame to dead-letter state with immutable diagnostics. | high | ACP Runtime |
| ACP-004 | Non-retryable nack MUST fail fast and produce audit event. | high | ACP Runtime |
| ACP-005 | ACP payload MUST encapsulate valid A2A envelope schema. | critical | ACP Runtime |

## 7. Conformance Tests
- Frames missing auth context are rejected deterministically.
- Ack timeout produces retry attempts with backoff metadata.
- Non-retryable nack transitions directly to dead-letter path.
- Dead-letter records preserve original message and final error details.
