"""Usage normalization helpers for llm gateway responses."""

from __future__ import annotations

from openqilin.llm_gateway.providers.base import LiteLLMProviderResult
from openqilin.llm_gateway.schemas.responses import LlmBudgetUsage, LlmUsage


def normalize_usage(provider_result: LiteLLMProviderResult) -> LlmUsage:
    """Normalize provider usage into governed response schema."""

    input_tokens = max(0, provider_result.input_tokens)
    output_tokens = max(0, provider_result.output_tokens)
    return LlmUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        request_units=1,
    )


def derive_budget_usage(*, usage: LlmUsage, currency_delta_usd: float) -> LlmBudgetUsage:
    """Build budget deltas for response and downstream accounting."""

    return LlmBudgetUsage(
        currency_delta_usd=max(0.0, round(currency_delta_usd, 6)),
        request_units=usage.request_units,
        token_units=usage.total_tokens,
    )
