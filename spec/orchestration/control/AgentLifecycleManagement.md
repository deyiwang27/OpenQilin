# OpenQilin - Agent Lifecycle Management Specification

## 1. Scope
- Defines lifecycle enforcement responsibilities in the orchestration layer.
- Transition definitions are normative in `spec/state-machines/AgentStateMachine.md`.

## 2. Source of Truth Boundary
- State names, transition guards, and illegal transitions: `spec/state-machines/AgentStateMachine.md`.
- This file defines how orchestrator services apply those transitions at runtime.

## 3. Orchestrator Enforcement Responsibilities
- Validate requested lifecycle event against canonical state machine before mutation.
- Call policy evaluation before any transition that changes authority or execution posture.
- Emit immutable lifecycle events with `trace_id`, `policy_version`, `policy_hash`, and `rule_ids`.
- Trigger escalation routing for pause/retire events when governance or critical impact flags are present.
- Reject illegal transitions without partial state mutation.

## 4. Required Integration Sequence
1. Load current agent state.
2. Validate requested transition against `AgentStateMachine`.
3. Evaluate policy and obligations.
4. Apply transition atomically.
5. Emit lifecycle + audit events.
6. Execute required escalation notifications.

## 5. Conformance Tests
- Runtime transition checks use `AgentStateMachine` as the only transition authority.
- Illegal transitions are rejected before write.
- Approved transitions produce lifecycle and audit events with required metadata.
- Pause events with critical impact trigger escalation notifications.
