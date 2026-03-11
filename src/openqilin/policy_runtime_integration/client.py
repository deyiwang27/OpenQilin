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

    def evaluate(self, payload: PolicyEvaluationInput) -> PolicyEvaluationResult:
        """Evaluate task against simulated policy rules."""

        if payload.command == "policy_error":
            raise PolicyRuntimeClientError("simulated policy runtime failure")

        if payload.command == "policy_uncertain":
            return PolicyEvaluationResult(
                decision="uncertain",
                reason_code="policy_uncertain",
                reason_message="policy runtime returned uncertainty",
                policy_version=self._policy_version,
            )

        if payload.command.startswith("deny_"):
            return PolicyEvaluationResult(
                decision="deny",
                reason_code="policy_denied",
                reason_message="command denied by policy rule",
                policy_version=self._policy_version,
            )

        return PolicyEvaluationResult(
            decision="allow",
            reason_code="policy_allowed",
            reason_message="command allowed by policy rule",
            policy_version=self._policy_version,
        )
