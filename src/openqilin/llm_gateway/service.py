"""LLM gateway service for routing, provider calls, and normalized accounting."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import cast

from openqilin.llm_gateway.accounting.cost_estimator import estimate_cost
from openqilin.llm_gateway.accounting.usage_recorder import derive_budget_usage, normalize_usage
from openqilin.llm_gateway.policy.request_guard import LlmGatewayGuardError, validate_llm_request
from openqilin.llm_gateway.providers.base import (
    LiteLLMProvider,
    LiteLLMProviderError,
    LiteLLMProviderRequest,
)
from openqilin.llm_gateway.providers.gemini_flash_adapter import GeminiFlashFreeAdapter
from openqilin.llm_gateway.providers.litellm_adapter import InMemoryLiteLLMAdapter
from openqilin.llm_gateway.routing.model_selector import select_model_aliases
from openqilin.llm_gateway.routing.profile_resolver import (
    RoutingProfileError,
    resolve_routing_profile,
)
from openqilin.llm_gateway.schemas.requests import LlmGatewayRequest
from openqilin.llm_gateway.schemas.responses import (
    LlmBudgetContextEffective,
    LlmGatewayResponse,
    QuotaLimitSource,
)
from openqilin.shared_kernel.settings import get_settings


@dataclass(frozen=True, slots=True)
class LlmGatewayService:
    """Governed llm gateway service for deterministic routing and response shaping."""

    provider: LiteLLMProvider

    def complete(self, request: LlmGatewayRequest) -> LlmGatewayResponse:
        """Execute governed request through routed provider path."""

        started_at = perf_counter()
        try:
            validate_llm_request(request)
            profile = resolve_routing_profile(request.routing_profile)
            aliases = select_model_aliases(profile, request.model_class)
        except (LlmGatewayGuardError, RoutingProfileError) as error:
            return LlmGatewayResponse(
                request_id=request.request_id,
                trace_id=request.trace_id,
                decision="denied",
                model_selected=None,
                usage=None,
                cost=None,
                budget_usage=None,
                budget_context_effective=LlmBudgetContextEffective(
                    allocation_mode=request.budget_context.allocation_mode,
                    project_share_ratio=request.budget_context.project_share_ratio,
                    effective_budget=request.budget_context.effective_budget_window
                    or "window-unspecified",
                ),
                quota_limit_source="policy_guardrail",
                latency_ms=self._elapsed_ms(started_at),
                policy_context=request.policy_context,
                route_metadata={"routing_profile": request.routing_profile},
                error_code=error.code,
                error_message=error.message,
                retryable=False,
                generated_text=None,
            )

        fallback_limit = min(len(aliases) - 1, profile.max_fallback_hops)
        for index, alias in enumerate(aliases):
            if index > fallback_limit:
                break
            provider_request = LiteLLMProviderRequest(
                request_id=request.request_id,
                trace_id=request.trace_id,
                model_alias=alias,
                prompt=request.messages_or_prompt,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
            )
            try:
                provider_result = self.provider.complete(provider_request)
            except LiteLLMProviderError as error:
                has_more = index < fallback_limit
                if has_more and error.retryable:
                    continue
                return LlmGatewayResponse(
                    request_id=request.request_id,
                    trace_id=request.trace_id,
                    decision="denied",
                    model_selected=alias,
                    usage=None,
                    cost=None,
                    budget_usage=None,
                    budget_context_effective=LlmBudgetContextEffective(
                        allocation_mode=request.budget_context.allocation_mode,
                        project_share_ratio=request.budget_context.project_share_ratio,
                        effective_budget=request.budget_context.effective_budget_window
                        or "window-unspecified",
                    ),
                    quota_limit_source="provider_signal",
                    latency_ms=self._elapsed_ms(started_at),
                    policy_context=request.policy_context,
                    route_metadata={
                        "routing_profile": request.routing_profile,
                        "fallback_hops": str(index),
                        "route_reason": "provider_failure_terminal",
                    },
                    error_code=error.code,
                    error_message=error.message,
                    retryable=error.retryable,
                    generated_text=None,
                )

            usage = normalize_usage(provider_result)
            cost = estimate_cost(
                model_alias=alias,
                usage_total_tokens=usage.total_tokens,
                provider_cost_usd=provider_result.provider_cost_usd,
            )
            budget_usage = derive_budget_usage(
                usage=usage,
                currency_delta_usd=cost.actual_cost_usd
                if cost.actual_cost_usd is not None
                else cost.estimated_cost_usd,
            )
            return LlmGatewayResponse(
                request_id=request.request_id,
                trace_id=request.trace_id,
                decision="served" if index == 0 else "fallback_served",
                model_selected=provider_result.model_identifier,
                usage=usage,
                cost=cost,
                budget_usage=budget_usage,
                budget_context_effective=LlmBudgetContextEffective(
                    allocation_mode=request.budget_context.allocation_mode,
                    project_share_ratio=request.budget_context.project_share_ratio,
                    effective_budget=request.budget_context.effective_budget_window
                    or "window-unspecified",
                ),
                quota_limit_source=_normalize_quota_limit_source(
                    provider_result.quota_limit_source
                ),
                latency_ms=self._elapsed_ms(started_at),
                policy_context=request.policy_context,
                route_metadata={
                    "routing_profile": request.routing_profile,
                    "fallback_hops": str(index),
                    "route_reason": "primary" if index == 0 else "fallback",
                },
                error_code=None,
                error_message=None,
                retryable=False,
                generated_text=provider_result.content,
            )

        return LlmGatewayResponse(
            request_id=request.request_id,
            trace_id=request.trace_id,
            decision="denied",
            model_selected=None,
            usage=None,
            cost=None,
            budget_usage=None,
            budget_context_effective=LlmBudgetContextEffective(
                allocation_mode=request.budget_context.allocation_mode,
                project_share_ratio=request.budget_context.project_share_ratio,
                effective_budget=request.budget_context.effective_budget_window
                or "window-unspecified",
            ),
            quota_limit_source="provider_signal",
            latency_ms=self._elapsed_ms(started_at),
            policy_context=request.policy_context,
            route_metadata={"routing_profile": request.routing_profile},
            error_code="llm_route_exhausted",
            error_message="all configured llm routes exhausted",
            retryable=False,
            generated_text=None,
        )

    @staticmethod
    def _elapsed_ms(started_at: float) -> int:
        return max(0, int((perf_counter() - started_at) * 1000))


def build_llm_gateway_service() -> LlmGatewayService:
    """Build gateway service with configured provider backend."""

    settings = get_settings()
    backend = settings.llm_provider_backend.strip().lower()
    if backend == "gemini_flash_free":
        provider: LiteLLMProvider = GeminiFlashFreeAdapter.from_settings(settings)
    else:
        provider = InMemoryLiteLLMAdapter()
    return LlmGatewayService(provider=provider)


def _normalize_quota_limit_source(value: str) -> QuotaLimitSource:
    if value in {"policy_guardrail", "provider_config", "provider_signal"}:
        return cast(QuotaLimitSource, value)
    return "policy_guardrail"
