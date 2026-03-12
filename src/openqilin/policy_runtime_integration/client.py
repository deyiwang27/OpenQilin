"""Policy runtime client shell."""

from __future__ import annotations

from openqilin.policy_runtime_integration.models import (
    PolicyEvaluationInput,
    PolicyEvaluationResult,
)


class PolicyRuntimeClientError(RuntimeError):
    """Raised when policy runtime call cannot be completed."""


class InMemoryPolicyRuntimeClient:
    """Deterministic in-memory policy client for M1 integration."""

    def __init__(self, policy_version: str = "m1-policy-shell-v1") -> None:
        self._policy_version = policy_version
        self._policy_hash = "m1-policy-shell-hash-v1"

    def evaluate(self, payload: PolicyEvaluationInput) -> PolicyEvaluationResult:
        """Evaluate task against simulated policy rules."""

        if payload.action == "policy_error":
            raise PolicyRuntimeClientError("simulated policy runtime failure")

        if payload.principal_role not in {
            "owner",
            "secretary",
            "administrator",
            "auditor",
            "ceo",
            "cwo",
            "cso",
            "project_manager",
            "domain_leader",
            "specialist",
        }:
            return PolicyEvaluationResult(
                decision="deny",
                reason_code="unknown_role",
                reason_message="actor role not recognized by policy runtime",
                policy_version=self._policy_version,
                policy_hash=self._policy_hash,
                rule_ids=("POL-004",),
            )

        if payload.action == "policy_uncertain":
            return PolicyEvaluationResult(
                decision="uncertain",
                reason_code="policy_uncertain",
                reason_message="policy runtime returned uncertainty",
                policy_version=self._policy_version,
                policy_hash=self._policy_hash,
                rule_ids=("POL-003",),
            )

        if payload.principal_role == "owner" and (
            "specialist" in payload.recipient_types
            or payload.target.strip().lower() == "specialist"
            or payload.target.strip().lower().startswith("specialist_")
        ):
            return PolicyEvaluationResult(
                decision="deny",
                reason_code="governance_specialist_direct_command_denied",
                reason_message=(
                    "owner cannot directly command specialist; route through project_manager"
                ),
                policy_version=self._policy_version,
                policy_hash=self._policy_hash,
                rule_ids=("OIM-005",),
            )

        if payload.action.startswith("deny_"):
            return PolicyEvaluationResult(
                decision="deny",
                reason_code="policy_denied",
                reason_message="command denied by policy rule",
                policy_version=self._policy_version,
                policy_hash=self._policy_hash,
                rule_ids=("POL-001",),
            )

        return PolicyEvaluationResult(
            decision="allow",
            reason_code="policy_allowed",
            reason_message="command allowed by policy rule",
            policy_version=self._policy_version,
            policy_hash=self._policy_hash,
            rule_ids=("POL-001",),
        )
