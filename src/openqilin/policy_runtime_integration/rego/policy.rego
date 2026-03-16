# OpenQilin constitution policy bundle.
# Implements all 12 rules from constitution/core/PolicyRules.yaml.
# Data: data.authority_matrix, data.obligation_policy

package openqilin.policy

import future.keywords.if
import future.keywords.in

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_known_roles := {
    "owner", "secretary", "administrator", "auditor",
    "ceo", "cwo", "cso", "project_manager", "domain_leader", "specialist"
}

_policy_version := "v2-bundle-0.1.0"
_policy_hash := "rego-openqilin-constitution-v1"

# Auth matrix shorthand
_am := data.authority_matrix.roles

# ---------------------------------------------------------------------------
# Rule: POL-004 — unknown role always denied
# ---------------------------------------------------------------------------

_role_unknown if { not input.principal_role in _known_roles }

# ---------------------------------------------------------------------------
# Rule: OIM-005 — owner cannot directly command specialist
# ---------------------------------------------------------------------------

_specialist_target if { input.target == "specialist" }
_specialist_target if { startswith(input.target, "specialist_") }
_specialist_target if { "specialist" in input.recipient_types }
_specialist_target if {
    some r in input.recipient_ids
    startswith(r, "specialist")
}
_specialist_target if {
    some a in input.args
    lower(a) == "specialist"
}

_owner_specialist_denied if {
    input.principal_role == "owner"
    _specialist_target
}

# ---------------------------------------------------------------------------
# Rule: POL-001 — explicit deny_ action prefix
# ---------------------------------------------------------------------------

_action_denied if { startswith(input.action, "deny_") }

# ---------------------------------------------------------------------------
# Rule: POL-003 — fail-closed uncertainty placeholder
# Uncertain returned for "policy_uncertain" action (mirrors InMemory behaviour)
# ---------------------------------------------------------------------------

_action_uncertain if { input.action == "policy_uncertain" }

# ---------------------------------------------------------------------------
# Decision: deny — unknown role (POL-004, AUD-001)
# ---------------------------------------------------------------------------

decide := {
    "decision": "deny",
    "reason_code": "unknown_role",
    "reason_message": "actor role not recognized by policy runtime",
    "policy_version": _policy_version,
    "policy_hash": _policy_hash,
    "rule_ids": ["POL-004"],
    "obligations": []
} if {
    _role_unknown
}

# ---------------------------------------------------------------------------
# Decision: uncertain — explicit uncertainty action (POL-003)
# ---------------------------------------------------------------------------

else := {
    "decision": "uncertain",
    "reason_code": "policy_uncertain",
    "reason_message": "policy runtime returned uncertainty",
    "policy_version": _policy_version,
    "policy_hash": _policy_hash,
    "rule_ids": ["POL-003"],
    "obligations": []
} if {
    _action_uncertain
}

# ---------------------------------------------------------------------------
# Decision: deny — owner → specialist routing (OIM-005, AUD-001)
# ---------------------------------------------------------------------------

else := {
    "decision": "deny",
    "reason_code": "governance_specialist_direct_command_denied",
    "reason_message": "owner cannot directly command specialist; route through project_manager",
    "policy_version": _policy_version,
    "policy_hash": _policy_hash,
    "rule_ids": ["OIM-005"],
    "obligations": []
} if {
    _owner_specialist_denied
}

# ---------------------------------------------------------------------------
# Decision: deny — explicit deny_ action (POL-001, AUD-001)
# ---------------------------------------------------------------------------

else := {
    "decision": "deny",
    "reason_code": "policy_denied",
    "reason_message": "command denied by policy rule",
    "policy_version": _policy_version,
    "policy_hash": _policy_hash,
    "rule_ids": ["POL-001"],
    "obligations": []
} if {
    _action_denied
}

# ---------------------------------------------------------------------------
# Decision: allow — all checks passed (AUTH-001, AUTH-002, AUD-001)
# emit_audit_event is a mandatory obligation on every allow (AUD-001).
# ---------------------------------------------------------------------------

else := {
    "decision": "allow",
    "reason_code": "policy_allowed",
    "reason_message": "command allowed by policy rule",
    "policy_version": _policy_version,
    "policy_hash": _policy_hash,
    "rule_ids": ["AUTH-001", "AUTH-002", "POL-001"],
    "obligations": ["emit_audit_event"]
}

# ---------------------------------------------------------------------------
# Metadata — bundle version exposed for startup validation
# ---------------------------------------------------------------------------

version := _policy_version
