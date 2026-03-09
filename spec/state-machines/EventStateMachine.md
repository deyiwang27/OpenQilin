# OpenQilin - Event State Machine Specification

## 1. Scope
- Defines lifecycle of runtime, observability, and audit events.

## 2. States
- `emitted`
- `validated`
- `persisted`
- `indexed`
- `archived`
- `rejected` (terminal)

## 3. Transitions
| From | Event | Guard | Action | To |
| --- | --- | --- | --- | --- |
| emitted | validate | schema and required fields valid | attach validation metadata | validated |
| emitted | validate | schema invalid | emit rejection reason | rejected |
| validated | persist | storage write success | store immutable event record | persisted |
| validated | persist | storage write failure retry exhausted | emit persistence failure | rejected |
| persisted | index | indexing backend available | update search/tracing index | indexed |
| indexed | archive | retention window reached | move to archival class | archived |

## 4. Illegal Transitions
- `rejected` -> any state.
- `archived` -> any state.
- `emitted` -> `persisted` without validation.

## 5. Conformance Tests
- Invalid events are rejected with deterministic error code.
- Persisted events include immutable references (`event_id`, `trace_id`, `policy_version`).
- Indexed state is eventually reached for valid persisted events.
