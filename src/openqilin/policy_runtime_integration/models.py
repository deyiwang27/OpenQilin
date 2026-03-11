"""Policy runtime DTOs for governed decision integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PolicyDecision = Literal["allow", "deny", "allow_with_obligations", "uncertain"]


@dataclass(frozen=True, slots=True)
class PolicyEvaluationInput:
    """Normalized input sent to policy runtime."""

    task_id: str
    request_id: str
    trace_id: str
    principal_id: str
    principal_role: str
    trust_domain: str
    connector: str
    action: str
    target: str
    args: tuple[str, ...]
    project_id: str | None


@dataclass(frozen=True, slots=True)
class PolicyEvaluationResult:
    """Policy runtime decision output."""

    decision: PolicyDecision
    reason_code: str
    reason_message: str
    policy_version: str
    policy_hash: str
    rule_ids: tuple[str, ...]
    obligations: tuple[str, ...] = ()
