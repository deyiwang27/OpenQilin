"""Provider interfaces for llm gateway runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class LiteLLMProviderRequest:
    """Normalized request payload sent to provider adapter."""

    request_id: str
    trace_id: str
    model_alias: str
    prompt: str
    max_tokens: int
    temperature: float


@dataclass(frozen=True, slots=True)
class LiteLLMProviderResult:
    """Provider completion payload."""

    model_identifier: str
    content: str
    input_tokens: int
    output_tokens: int
    provider_cost_usd: float | None


class LiteLLMProviderError(RuntimeError):
    """Raised when provider call cannot serve request deterministically."""

    def __init__(self, code: str, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


class LiteLLMProvider(Protocol):
    """Provider adapter contract for llm gateway."""

    def complete(self, request: LiteLLMProviderRequest) -> LiteLLMProviderResult:
        """Execute completion against configured provider boundary."""
