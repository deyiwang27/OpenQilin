# Policy Engine Specification

## 1. Scope
- Central authorization and obligation engine for all system actions.
- This document is a component-spec under `spec/RuntimeInfrastructure.md`.
- It MUST inherit global runtime contracts `RT-001..RT-003`.

## 2. API Contract
### Request
```json
{
  "request_id": "uuid",
  "trace_id": "uuid",
  "actor": {"id": "string", "role": "string"},
  "action": "string",
  "target": "string",
  "context": {}
}
```

### Response
```json
{
  "decision": "allow|deny|allow_with_obligations",
  "rule_ids": ["string"],
  "obligations": ["string"],
  "reason": "string"
}
```

## 3. Rules
- POL-001: Engine decisions MUST be deterministic for same normalized input and policy version.
- POL-002: Deny decision MUST include at least one rule ID.
- POL-003: Versioned policy bundle hash MUST be logged with every decision.
- POL-004: Policy Engine MUST expose decisions in a format consumable by Task Orchestrator and Execution Sandbox.

## 4. Conformance Tests
- Replay returns same decision for same input+policy version.
- Missing actor role yields deny.
- Denied decision blocks downstream execution in orchestrator/sandbox path.
