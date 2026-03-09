# OpenQilin - Agent Communication A2A Specification

## 1. Scope
- Defines inter-agent message contract, authority metadata, and delivery semantics.
- Defines governance constraints for read/write/observe communication behavior.
- Transport-agnostic envelope; ACP defines wire-level transport behavior.

## 2. Canonical Message Envelope
```json
{
  "message_id": "uuid",
  "trace_id": "uuid",
  "conversation_id": "uuid",
  "idempotency_key": "string",
  "timestamp": "RFC3339",
  "from_agent": {"agent_id": "string", "role": "string"},
  "to_agent": {"agent_id": "string", "role": "string"},
  "type": "command|response|event|escalation",
  "payload": {},
  "authority_context": {
    "required_authority": "decision|command|execution|review|advisory|oversight|workforce",
    "project_scope": "string"
  },
  "policy_context": {
    "policy_version": "string",
    "policy_hash": "string",
    "decision": "allow|deny|allow_with_obligations",
    "rule_ids": ["string"]
  },
  "channel_context": {
    "channel_id": "string",
    "channel_type": "direct|group|project|executive|governance",
    "trust_level": "internal|external_verified|external_untrusted",
    "ordering_key": "string"
  },
  "delivery_context": {
    "attempt": 1,
    "max_attempts": 5,
    "sequence": 10,
    "ack_deadline_ms": 30000
  },
  "observer_context": {
    "observer_roles": ["auditor"],
    "observer_mode": "read_only"
  }
}
```

## 3. Delivery and Ordering Semantics
- Delivery guarantee: at-least-once.
- Idempotency guarantee: side effects MUST be idempotent by `idempotency_key`.
- Ordering guarantee: monotonic `sequence` per `ordering_key`.
- Dead-letter requirement: messages exceeding retry limit MUST be dead-lettered with failure reason.

## 4. Access and Trust Constraints
- `auditor` may observe all channels in `read_only` mode.
- Observer roles MUST NOT emit command/event payloads into observed channels.
- `external_untrusted` channels cannot carry privileged command payloads.
- `secretary` role may process onboarding/status/triage queries only and cannot dispatch command or execution payloads.

## 5. ACP Interoperability
- A2A envelope is payload contract.
- ACP is required wire protocol for runtime transport semantics:
  - frame structure
  - route resolution
  - ack/nack handling
  - retry/dead-letter behavior

## 6. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| A2A-001 | Delivery MUST be at-least-once with idempotent handling. | high | Task Orchestrator |
| A2A-002 | Every command/event message MUST include authority and policy context metadata. | critical | Task Orchestrator |
| A2A-003 | `auditor` observer mode MUST be read-only across all channels. | critical | Policy Engine |
| A2A-004 | Messages in untrusted channels MUST fail closed for privileged actions. | critical | Policy Engine |
| A2A-005 | Messages exceeding retry limits MUST be dead-lettered with immutable audit metadata. | high | Observability |

## 7. Conformance Tests
- Duplicate messages do not duplicate side effects.
- `auditor` channel participation attempts are denied for write actions.
- Missing authority/policy context fails validation.
- Untrusted-channel privileged command is denied and audited.
- Retry exhaustion produces dead-letter records with trace + rule IDs.
