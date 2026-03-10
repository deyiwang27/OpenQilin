# OpenQilin - Agent Tracing Specification

## 1. Scope
- Defines distributed tracing across agent interactions and tool execution.
- Defines required trace context propagation across policy, orchestration, sandbox, A2A, and ACP.

## 2. Trace Model
- `trace_id`: stable identifier across end-to-end workflow.
- `span_id`: identifier for current component operation.
- `parent_span_id`: upstream caller span identifier.
- `trace_flags`: sampling and diagnostic flags.

## 3. Required Span Boundaries
- `owner_ingress` (owner/API/channel entrypoint)
- `policy_evaluation`
- `task_orchestration`
- `budget_reservation`
- `execution_sandbox`
- `a2a_emit` and `a2a_consume`
- `acp_send` and `acp_ack_or_nack`
- `audit_emit`

## 4. Propagation Requirements
- A2A envelopes must carry `trace_id` and caller span metadata.
- ACP frames must preserve A2A trace context and append transport span metadata.
- Cross-component calls must create child spans, not new root traces.
- Retries keep same `trace_id` and create new retry spans linked to original parent.

## 5. Sampling and Retention
- Governance/safety/budget incidents: force sampled.
- Denied policy decisions: force sampled.
- Normal successful flows: configurable sampling rate by environment.
- Trace retention follows observability retention policy and must support audit correlation windows.

## 6. Correlation and Redaction
- Trace events must include correlation keys to `event_id`, `task_id`, `project_id`, and `agent_id` when available.
- Sensitive fields (tokens, credentials, raw secret values) must be redacted before export/storage.

## 7. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| TRC-001 | Every task execution path MUST preserve trace context. | critical | Runtime |

## 8. Conformance Tests
- Cross-component operations share same trace lineage.
- A2A->ACP hops preserve `trace_id` and parent-child span relationships.
- Retry attempts do not create new root traces.
- Denied policy decisions and safety incidents are always trace-sampled.
- Exported traces do not contain unredacted secrets.
