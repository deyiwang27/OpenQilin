"""LiteLLM adapter shell used for governed llm boundary integration."""

from __future__ import annotations

from openqilin.llm_gateway.providers.base import (
    LiteLLMProvider,
    LiteLLMProviderError,
    LiteLLMProviderRequest,
    LiteLLMProviderResult,
)


class InMemoryLiteLLMAdapter(LiteLLMProvider):
    """Deterministic provider adapter used for local and test runtime."""

    def complete(self, request: LiteLLMProviderRequest) -> LiteLLMProviderResult:
        """Return deterministic completion or simulated provider failure."""

        if "llm_hard_fail" in request.prompt:
            raise LiteLLMProviderError(
                code="llm_provider_rejected",
                message="provider rejected llm request",
                retryable=False,
            )

        if "llm_runtime_error" in request.prompt:
            raise LiteLLMProviderError(
                code="llm_provider_unavailable",
                message="provider unavailable",
                retryable=True,
            )

        if "llm_fallback_once" in request.prompt and request.model_alias.endswith("_primary"):
            raise LiteLLMProviderError(
                code="llm_provider_primary_failed",
                message="primary route failed; fallback required",
                retryable=True,
            )

        input_tokens = max(1, len(request.prompt.split()) * 4)
        output_tokens = max(1, min(request.max_tokens, 48))
        return LiteLLMProviderResult(
            model_identifier=f"gemini/{request.model_alias}",
            content=f"simulated completion for {request.model_alias}",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            provider_cost_usd=None,
            quota_limit_source="policy_guardrail",
        )
