from __future__ import annotations

from decimal import Decimal

from openqilin.budget_runtime.cost_evaluator import (
    DEFAULT_RATE_PER_1K_TOKENS,
    TokenCostEvaluator,
)


def test_estimate_interactive_fast_maps_to_gemini_flash() -> None:
    evaluator = TokenCostEvaluator()

    estimate = evaluator.estimate("interactive_fast", 1000)

    assert estimate.quota_tokens_estimate == 2000
    assert estimate.usd_estimate == Decimal("0.000035") * Decimal("2")


def test_estimate_reasoning_general_maps_to_gemini_pro() -> None:
    evaluator = TokenCostEvaluator()

    estimate = evaluator.estimate("reasoning_general", 500)

    assert estimate.quota_tokens_estimate == 1000
    assert estimate.usd_estimate == Decimal("0.00125")


def test_estimate_free_tier_zero_usd_nonzero_tokens() -> None:
    evaluator = TokenCostEvaluator()

    estimate = evaluator.estimate("gemini_flash_free", 500)

    assert estimate.usd_estimate == Decimal("0.0")
    assert estimate.quota_tokens_estimate == 1000


def test_estimate_unknown_model_uses_default_rate() -> None:
    evaluator = TokenCostEvaluator()

    estimate = evaluator.estimate("unknown_model_xyz", 100)

    assert estimate.quota_tokens_estimate == 200
    assert estimate.usd_estimate == DEFAULT_RATE_PER_1K_TOKENS * Decimal("0.2")
    assert estimate.usd_estimate > Decimal("0")


def test_estimate_direct_cost_tier_name_accepted() -> None:
    evaluator = TokenCostEvaluator()

    estimate = evaluator.estimate("gemini_pro", 100)

    assert estimate.usd_estimate == Decimal("0.00125") * Decimal("0.2")
    assert estimate.quota_tokens_estimate == 200


def test_settle_uses_total_tokens_not_character_count() -> None:
    evaluator = TokenCostEvaluator()

    actual = evaluator.settle(
        total_tokens=400,
        actual_cost_usd=0.005,
        model_class="interactive_fast",
    )

    assert actual.quota_tokens_actual == 400
    assert actual.usd_actual == Decimal("0.005")


def test_settle_free_tier_actual_cost_none_returns_zero_usd() -> None:
    evaluator = TokenCostEvaluator()

    actual = evaluator.settle(
        total_tokens=300,
        actual_cost_usd=None,
        model_class="gemini_flash_free",
    )

    assert actual.usd_actual == Decimal("0.0")
    assert actual.quota_tokens_actual == 300


def test_settle_fallback_computes_usd_from_rate_when_actual_none() -> None:
    evaluator = TokenCostEvaluator()

    actual = evaluator.settle(
        total_tokens=1000,
        actual_cost_usd=None,
        model_class="interactive_fast",
    )

    assert actual.usd_actual == Decimal("0.000035")
    assert actual.usd_actual > Decimal("0")
    assert actual.quota_tokens_actual == 1000
