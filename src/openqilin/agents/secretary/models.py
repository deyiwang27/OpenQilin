"""Secretary agent request/response models."""

from __future__ import annotations

from dataclasses import dataclass

from openqilin.control_plane.grammar.models import ChatContext, IntentClass


@dataclass(frozen=True, slots=True)
class SecretaryRequest:
    """Advisory request routed to the Secretary agent."""

    message: str
    intent: IntentClass
    context: ChatContext
    trace_id: str
    channel_id: str = ""
    actor_id: str = ""
    addressed_agent: str = ""


@dataclass(frozen=True, slots=True)
class SecretaryResponse:
    """Advisory-only response from the Secretary agent. Contains no mutations."""

    advisory_text: str
    intent_confirmed: IntentClass
    routing_suggestion: str | None
    trace_id: str
    # Audit metadata (AUTH-004, AUTH-005): every interaction must include policy provenance.
    policy_version: str = "v2"
    policy_hash: str = "secretary-advisory-v1"
    rule_ids: tuple[str, ...] = ("AUTH-004", "AUTH-005")


class SecretaryPolicyError(Exception):
    """Raised when a request violates the Secretary advisory-only policy profile."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
