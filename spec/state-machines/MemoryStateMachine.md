# OpenQilin - Memory State Machine Specification

## 1. Scope
- Defines lifecycle states for memory artifacts and retention transitions.
- Must align with `spec/orchestration/memory/AgentMemoryModel.md` and `spec/infrastructure/data/StorageAndRetention.md`.

## 2. States
- `hot`
- `warm`
- `cold`
- `archived`
- `purged` (terminal)

## 3. Transitions
| From | Event | Guard | Action | To |
| --- | --- | --- | --- | --- |
| hot | compress | hot TTL elapsed and summary generated | persist summary + snapshot reference | warm |
| warm | archive | warm TTL elapsed and snapshot exists | move compressed payload to cold store | cold |
| cold | retain_archive | archive window reached | mark immutable archive record | archived |
| archived | purge | retention expiry and no legal hold | emit purge audit event | purged |
| hot/warm/cold/archived | purge_override | explicit `owner` approval present | emit override audit event | purged |

## 4. Illegal Transitions
- Any state -> `purged` without TTL expiry or approved override.
- `purged` -> any state.
- `hot` -> `cold` without compression/snapshot step.

## 5. Conformance Tests
- Retention transitions are deterministic under same timestamps and policy version.
- Purge override without `owner` approval is denied.
- Every lifecycle transition carries trace and policy metadata.
- Purged artifacts are non-recoverable from runtime retrieval interfaces.
