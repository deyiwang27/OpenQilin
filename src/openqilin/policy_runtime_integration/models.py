"""Policy runtime DTOs for governed decision integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PolicyDecision = Literal["allow", "deny", "uncertain"]


@dataclass(frozen=True, slots=True)
class PolicyEvaluationInput:
    """Normalized input sent to policy runtime."""

    task_id: str
    request_id: str
    trace_id: str
    principal_id: str
    connector: str
    command: str
    args: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PolicyEvaluationResult:
    """Policy runtime decision output."""

    decision: PolicyDecision
    reason_code: str
    reason_message: str
    policy_version: str
