# OpenQilin - Task Orchestrator Specification

## 1. Scope
- Plans, dispatches, tracks, and closes tasks under policy and budget constraints.

## 2. Task Lifecycle
- queued -> authorized -> dispatched -> running -> completed|failed|cancelled

## 3. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| ORCH-001 | Task MUST pass Policy Engine before dispatch. | critical | Task Orchestrator |
| ORCH-002 | Task MUST reserve budget before dispatch. | critical | Task Orchestrator |

## 4. Conformance Tests
- Unauthorized tasks are not dispatched.
