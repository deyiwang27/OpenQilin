"""Governed request guard checks for llm gateway."""

from __future__ import annotations

from openqilin.llm_gateway.schemas.requests import LlmGatewayRequest


class LlmGatewayGuardError(ValueError):
    """Raised when llm request violates governed contract."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def validate_llm_request(request: LlmGatewayRequest) -> None:
    """Validate governed llm request shape before routing/provider calls."""

    if not request.request_id.strip():
        raise LlmGatewayGuardError("llm_missing_request_id", "request_id is required")
    if not request.trace_id.strip():
        raise LlmGatewayGuardError("llm_missing_trace_id", "trace_id is required")
    if not request.project_id.strip():
        raise LlmGatewayGuardError("llm_missing_project_id", "project_id is required")
    if request.max_tokens <= 0:
        raise LlmGatewayGuardError("llm_invalid_max_tokens", "max_tokens must be positive")
    if not (0.0 <= request.temperature <= 2.0):
        raise LlmGatewayGuardError(
            "llm_invalid_temperature",
            "temperature must be within [0, 2]",
        )
    if not request.messages_or_prompt.strip():
        raise LlmGatewayGuardError("llm_missing_prompt", "messages_or_prompt is required")
    if not request.policy_context.policy_version.strip():
        raise LlmGatewayGuardError("llm_missing_policy_version", "policy version is required")
    if not request.policy_context.policy_hash.strip():
        raise LlmGatewayGuardError("llm_missing_policy_hash", "policy hash is required")
