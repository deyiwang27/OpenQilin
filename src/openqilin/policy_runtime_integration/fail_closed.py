"""Fail-closed policy guard for governed path."""

from __future__ import annotations

from dataclasses import dataclass

from openqilin.policy_runtime_integration.client import InMemoryPolicyRuntimeClient
from openqilin.policy_runtime_integration.models import (
    PolicyEvaluationInput,
    PolicyEvaluationResult,
)


@dataclass(frozen=True, slots=True)
class PolicyFailClosedOutcome:
    """Fail-closed decision result used by ingress router."""

    allowed: bool
    error_code: str | None
    message: str
    policy_result: PolicyEvaluationResult | None


def evaluate_with_fail_closed(
    payload: PolicyEvaluationInput,
    client: InMemoryPolicyRuntimeClient,
) -> PolicyFailClosedOutcome:
    """Apply fail-closed semantics to policy runtime evaluation."""

    try:
        result = client.evaluate(payload)
    except Exception as error:
        return PolicyFailClosedOutcome(
            allowed=False,
            error_code="policy_runtime_error_fail_closed",
            message=f"policy evaluation failed: {error}",
            policy_result=None,
        )

    if result.decision in {"allow", "allow_with_obligations"}:
        return PolicyFailClosedOutcome(
            allowed=True,
            error_code=None,
            message="policy allowed command",
            policy_result=result,
        )

    if result.decision == "deny":
        return PolicyFailClosedOutcome(
            allowed=False,
            error_code=result.reason_code,
            message=result.reason_message,
            policy_result=result,
        )

    return PolicyFailClosedOutcome(
        allowed=False,
        error_code="policy_uncertain_fail_closed",
        message="policy decision uncertain; fail-closed block applied",
        policy_result=result,
    )
