# OpenQilin - Communication State Machine Specification

## 1. Scope
- Defines lifecycle states for A2A/ACP message delivery.
- Must align with `spec/orchestration/communication/AgentCommunicationA2A.md` and `spec/orchestration/communication/AgentCommunicationACP.md`.

## 2. States
- `created`
- `queued`
- `sent`
- `delivered`
- `acknowledged`
- `failed`
- `dead_lettered` (terminal)

## 3. Transitions
| From | Event | Guard | Action | To |
| --- | --- | --- | --- | --- |
| created | enqueue | envelope valid | persist queue entry | queued |
| queued | send | route resolved + policy check passed | dispatch frame | sent |
| sent | deliver | transport confirms receipt | emit delivery event | delivered |
| delivered | ack | receiver emits `ack` | persist ack record | acknowledged |
| sent/delivered | timeout_or_nack | attempts < max_attempts | increment attempt and retry | queued |
| sent/delivered | timeout_or_nack | attempts >= max_attempts | emit terminal delivery failure | dead_lettered |
| queued/sent/delivered | fail_hard | malformed frame or auth failure | emit failure event | failed |
| failed | dead_letter | non-recoverable | persist dead-letter payload | dead_lettered |

## 4. Illegal Transitions
- `acknowledged` -> any state.
- `dead_lettered` -> any state.
- `created` -> `sent` without queueing.

## 5. Conformance Tests
- Retry and dead-letter behavior follows configured limits.
- Duplicate frame delivery does not duplicate side effects with same idempotency key.
- Untrusted channel frames without valid auth context are rejected and dead-lettered.
