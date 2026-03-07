# Task Orchestrator Specification

## 1. Scope
- Plans, dispatches, tracks, and closes tasks under policy and budget constraints.
- This document is a component-spec under `spec/RuntimeInfrastructure.md`.
- It MUST inherit global runtime contracts `RT-001..RT-003`.

## 2. Task Lifecycle
- `queued -> authorized -> dispatched -> running -> completed|failed|cancelled`

## 3. Dispatch Contract
- ORCH-001: Task MUST pass Policy Engine before dispatch.
- ORCH-002: Task MUST reserve budget before dispatch.
- ORCH-003: Task cancellation MUST emit compensating actions when applicable.

## 4. Scheduling Rules
- Priority sources: governance > executive > operational.
- Starvation prevention: max wait window per priority class.

## 5. Conformance Tests
- Unauthorized task remains in `queued/denied`.
- Budget unavailable blocks dispatch.
- Every dispatched task carries a valid `trace_id`.
