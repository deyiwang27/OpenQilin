"""Token-based cost estimation and settlement for budget accounting."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

# Cost per 1,000 tokens by model tier (USD).
# Free tier: currency cost is 0.0 but quota tokens are still tracked and enforced.
COST_PER_1K_TOKENS: dict[str, Decimal] = {
    "gemini_flash_free": Decimal("0.0"),
    "gemini_flash": Decimal("0.000035"),
    "gemini_pro": Decimal("0.00125"),
}

# Default rate for unknown model classes.
DEFAULT_RATE_PER_1K_TOKENS: Decimal = Decimal("0.001")

# Default token estimate used for pre-dispatch reservation when actual tokens are unknown.
DEFAULT_ESTIMATED_INPUT_TOKENS: int = 500

# Routing model class -> cost tier mapping.
_ROUTING_CLASS_TO_COST_TIER: dict[str, str] = {
    "interactive_fast": "gemini_flash",
    "reasoning_general": "gemini_pro",
    "embedding_text": "gemini_flash",
}


@dataclass(frozen=True, slots=True)
class CostEstimate:
    """Pre-dispatch cost estimate (both dimensions required)."""

    usd_estimate: Decimal
    quota_tokens_estimate: int


@dataclass(frozen=True, slots=True)
class ActualCost:
    """Post-completion actual cost settled from LLM response metadata."""

    usd_actual: Decimal
    quota_tokens_actual: int


class TokenCostEvaluator:
    """Converts LLM usage to budget dimensions using token-based accounting."""

    DEFAULT_ESTIMATED_INPUT_TOKENS: int = DEFAULT_ESTIMATED_INPUT_TOKENS

    def estimate(
        self,
        model_class: str,
        estimated_input_tokens: int = DEFAULT_ESTIMATED_INPUT_TOKENS,
    ) -> CostEstimate:
        """
        Estimate pre-dispatch cost for a model class and token count.

        Applies 2x output multiplier to produce total estimated tokens.
        Free-tier models return usd_estimate=Decimal("0.0") but quota_tokens_estimate > 0.
        Unknown model class uses DEFAULT_RATE_PER_1K_TOKENS.
        """
        normalized_model_class = _ROUTING_CLASS_TO_COST_TIER.get(model_class, model_class)
        rate = COST_PER_1K_TOKENS.get(normalized_model_class, DEFAULT_RATE_PER_1K_TOKENS)
        quota_tokens_estimate = max(estimated_input_tokens, 1) * 2
        if rate == Decimal("0.0"):
            usd_estimate = Decimal("0.0")
        else:
            usd_estimate = rate * Decimal(quota_tokens_estimate) / Decimal("1000")
        return CostEstimate(
            usd_estimate=usd_estimate,
            quota_tokens_estimate=quota_tokens_estimate,
        )

    def settle(
        self,
        *,
        total_tokens: int,
        actual_cost_usd: float | None,
        model_class: str,
    ) -> ActualCost:
        """
        Produce actual cost from LLM response metadata.

        Uses total_tokens directly — never character count.
        If actual_cost_usd is None, compute from token rate.
        """
        quota_tokens_actual = max(total_tokens, 0)
        if actual_cost_usd is not None:
            usd_actual = Decimal(str(actual_cost_usd))
        else:
            normalized_model_class = _ROUTING_CLASS_TO_COST_TIER.get(model_class, model_class)
            rate = COST_PER_1K_TOKENS.get(normalized_model_class, DEFAULT_RATE_PER_1K_TOKENS)
            usd_actual = rate * Decimal(quota_tokens_actual) / Decimal("1000")
        return ActualCost(
            usd_actual=usd_actual,
            quota_tokens_actual=quota_tokens_actual,
        )
