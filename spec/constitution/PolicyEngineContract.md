# OpenQilin - Policy Engine Contract Specification

## 1. Scope
- Defines the authorization and obligation interface for runtime actions.
- Defines deterministic policy evaluation behavior under global active policy version.

## 2. Request Schema
```json
{
  "request_id": "uuid",
  "trace_id": "uuid",
  "actor": {"id": "string", "role": "owner|secretary|administrator|auditor|ceo|cwo|cso|project_manager|domain_leader|specialist"},
  "action": "string",
  "target": "string",
  "context": {
    "project_id": "string",
    "budget_state": "ok|soft|hard",
    "incident_level": "none|warning|critical",
    "requested_capabilities": ["string"],
    "execution_target": {
      "target_type": "internal_sandbox|external_bridge|service_call",
      "sandbox_profile": "read_only|tool_exec_restricted|code_exec_restricted|external_bridge",
      "network_zone": "internal|restricted_egress|external"
    },
    "communication_context": {
      "protocol": "a2a|acp",
      "channel_id": "string",
      "channel_type": "direct|leadership_council|governance|executive|project",
      "project_lifecycle_stage": "proposed|approved|active|paused|completed|terminated|archived",
      "trust_level": "internal|external_verified|external_untrusted"
    }
  }
}
```

## 3. Response Schema
```json
{
  "decision": "allow|deny|allow_with_obligations",
  "rule_ids": ["string"],
  "obligations": [
    "emit_audit_event",
    "reserve_budget",
    "enforce_sandbox_profile",
    "require_owner_approval"
  ],
  "policy_version": "string",
  "policy_hash": "string",
  "reason": "string"
}
```

## 4. Evaluation Semantics
- Input policy source: YAML artifacts loaded via Constitution Binding Model.
- Active policy selection: single global active version.
- Decision mode: fail-closed (errors default to `deny`).
- Communication posture: runtime supports `a2a` payload with `acp` transport context.
- Communication policy posture: owner chat channel classes are fixed (`direct`, `leadership_council`, `governance`, `executive`, `project`).
- Secretary participation in owner chat classes is system-defined but may be marked pending/inactive by runtime profile (first MVP).
- When `channel_type=project`, policy evaluation must enforce lifecycle-stage membership constraints.
- Deterministic evaluation order:
  1. actor/role validation
  2. authority and governance constraints
  3. budget and safety constraints
  4. obligation assignment
  5. decision output

## 5. Error Contract
| Code | Condition | Engine Behavior |
| --- | --- | --- |
| `POLICY_LOAD_ERROR` | active policy unavailable | `deny` |
| `POLICY_VALIDATION_ERROR` | malformed policy data | `deny` |
| `UNKNOWN_ROLE` | actor role not in canonical enum | `deny` |
| `UNAUTHORIZED_ACTION` | authority mismatch | `deny` |
| `EVAL_INTERNAL_ERROR` | evaluation failure | `deny` |

## 6. Audit Profile
- Always emit immutable decision audit event.
- Detail level:
  - `allow`: compact envelope
  - `deny`: full context envelope
  - `allow_with_obligations`: full context envelope
- Emergency/governance-related decisions use full context envelope.

## 7. Rule Set
| Rule ID | Statement | Severity | Enforced By |
| --- | --- | --- | --- |
| POL-001 | Decisions MUST be deterministic for same normalized input and policy version. | critical | Policy Engine |
| POL-002 | Deny response MUST include at least one rule ID. | high | Policy Engine |
| POL-003 | Policy evaluation MUST fail-closed on load, validation, or runtime evaluation errors. | critical | Policy Engine |
| POL-004 | Unknown actor roles MUST be denied. | critical | Policy Engine |
| POL-005 | `allow_with_obligations` decisions MUST include explicit obligation values. | high | Policy Engine |
| POL-006 | Every decision MUST return policy version and hash metadata. | critical | Policy Engine |
| POL-007 | Policy evaluation MUST include execution-target and communication-context constraints when provided. | high | Policy Engine |

## 8. Conformance Tests
- Replay with same input and policy version returns same output.
- Unknown role returns `deny` with `UNKNOWN_ROLE`.
- Simulated policy load failure returns `deny` (fail-closed).
- `allow_with_obligations` responses include valid obligation set.
- Decision audit events include `policy_version`, `policy_hash`, and `rule_ids`.
- Untrusted communication context with privileged action is denied.
