"""Cost estimation helpers for llm gateway."""

from __future__ import annotations

from openqilin.llm_gateway.schemas.responses import LlmCost


def estimate_cost(
    *,
    model_alias: str,
    usage_total_tokens: int,
    provider_cost_usd: float | None,
) -> LlmCost:
    """Compute normalized cost fields with explicit cost source."""

    if provider_cost_usd is not None:
        rounded_cost = round(max(0.0, provider_cost_usd), 6)
        return LlmCost(
            estimated_cost_usd=rounded_cost,
            actual_cost_usd=rounded_cost,
            cost_source="provider_reported",
        )

    if model_alias.startswith("google_gemini_free_"):
        return LlmCost(
            estimated_cost_usd=0.0,
            actual_cost_usd=0.0,
            cost_source="none",
        )

    estimated_cost = round(max(0, usage_total_tokens) * 0.000002, 6)
    return LlmCost(
        estimated_cost_usd=estimated_cost,
        actual_cost_usd=None,
        cost_source="catalog_estimated",
    )
