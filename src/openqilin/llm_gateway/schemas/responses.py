"""LLM gateway response schemas."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from openqilin.llm_gateway.schemas.requests import AllocationMode, LlmPolicyContext

LlmGatewayDecision = Literal["served", "fallback_served", "denied"]
CostSource = Literal["provider_reported", "catalog_estimated", "none"]
QuotaLimitSource = Literal["policy_guardrail", "provider_config", "provider_signal"]


@dataclass(frozen=True, slots=True)
class LlmUsage:
    """Normalized token/request usage payload."""

    input_tokens: int
    output_tokens: int
    total_tokens: int
    request_units: int


@dataclass(frozen=True, slots=True)
class LlmCost:
    """Currency cost metadata for llm request."""

    estimated_cost_usd: float
    actual_cost_usd: float | None
    cost_source: CostSource


@dataclass(frozen=True, slots=True)
class LlmBudgetUsage:
    """Budget deltas for downstream accounting."""

    currency_delta_usd: float
    request_units: int
    token_units: int


@dataclass(frozen=True, slots=True)
class LlmBudgetContextEffective:
    """Effective allocation metadata after policy evaluation."""

    allocation_mode: AllocationMode
    project_share_ratio: float | None
    effective_budget: str


@dataclass(frozen=True, slots=True)
class LlmGatewayResponse:
    """Gateway completion response contract."""

    request_id: str
    trace_id: str
    decision: LlmGatewayDecision
    model_selected: str | None
    usage: LlmUsage | None
    cost: LlmCost | None
    budget_usage: LlmBudgetUsage | None
    budget_context_effective: LlmBudgetContextEffective | None
    quota_limit_source: QuotaLimitSource
    latency_ms: int
    policy_context: LlmPolicyContext
    route_metadata: dict[str, str] = field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None
    retryable: bool = False
