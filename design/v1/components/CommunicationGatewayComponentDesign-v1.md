# OpenQilin v1 - Communication Gateway Component Design

## 1. Scope
- Define the v1 `communication_gateway` component for A2A + ACP handling.
- Specify producer/consumer boundaries, retries, dead-letter flow, and ordering enforcement.

## 2. Component Boundary
Component: `communication_gateway`

Responsibilities:
- validate A2A envelope completeness
- translate A2A envelopes into ACP frames
- manage ack/nack, retries, and dead-letter persistence
- enforce per-channel ordering key behavior
- expose delivery outcomes back to `task_orchestrator`

Non-responsibilities:
- does not authorize privileged actions independently
- does not own business task state

## 3. Message Flow
1. receive publish request from orchestrator
2. validate A2A envelope and mandatory `idempotency_key`
3. persist `created/queued`
4. send ACP frame using route and auth context
5. await ack/nack or timeout
6. retry or dead-letter according to reliability profile
7. publish terminal delivery outcome to orchestrator

## 4. Delivery Rules
- delivery guarantee: `at-least-once`
- `ack_deadline_ms`: `30000`
- `max_attempts`: `5`
- retry triggers:
  - ack timeout
  - retryable nack
- dead-letter triggers:
  - non-retryable nack
  - retry exhaustion

## 5. Ordering Enforcement
- direct/group: monotonic by `conversation_id`
- project: monotonic by `project_id:task_id`
- executive: monotonic by `channel_id`
- governance: monotonic by incident stream id

## 6. Storage and Coordination
- PostgreSQL:
  - `messages`
  - attempt ledger
  - dead-letter ledger
- Redis:
  - idempotency key dedupe
  - transient coordination markers only

## 7. Failure Modes
| Failure | Handling |
| --- | --- |
| schema invalid | fail fast, dead-letter if non-recoverable |
| auth/route failure | nack-based retry or dead-letter by retryability |
| ack timeout | bounded retry |
| duplicate delivery | no duplicate side effects, safe ack |

## 8. Observability
- required spans:
  - `a2a_emit`
  - `acp_send`
  - `acp_ack_or_nack`
- required fields:
  - `message_id`, `trace_id`, `channel_id`, `attempt`, `delivery_status`, `terminal_code`

## 9. Related `spec/` References
- `spec/orchestration/communication/AgentCommunicationA2A.md`
- `spec/orchestration/communication/AgentCommunicationACP.md`
- `spec/state-machines/CommunicationStateMachine.md`
- `spec/cross-cutting/runtime/ErrorCodesAndHandling.md`
- `spec/observability/AuditEvents.md`
