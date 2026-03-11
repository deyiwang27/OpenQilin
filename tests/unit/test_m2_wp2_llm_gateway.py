from openqilin.llm_gateway.schemas.requests import (
    LlmBudgetContext,
    LlmGatewayRequest,
    LlmPolicyContext,
)
from openqilin.llm_gateway.service import build_llm_gateway_service


def _build_request(
    *,
    prompt: str,
    routing_profile: str = "dev_gemini_free",
) -> LlmGatewayRequest:
    return LlmGatewayRequest(
        request_id="req-llm-1",
        trace_id="trace-llm-1",
        project_id="project_1",
        agent_id="owner_1",
        task_id="task_1",
        skill_id=None,
        model_class="interactive_fast",
        routing_profile=routing_profile,
        messages_or_prompt=prompt,
        max_tokens=64,
        temperature=0.2,
        budget_context=LlmBudgetContext(
            currency_cap_usd=None,
            quota_request_cap=1000,
            quota_token_cap=50000,
            allocation_mode="hybrid",
            project_share_ratio=0.1,
            effective_budget_window="daily",
        ),
        policy_context=LlmPolicyContext(
            policy_version="policy-v1",
            policy_hash="policy-hash-v1",
            rule_ids=("rule_1",),
        ),
    )


def test_llm_gateway_serves_dev_gemini_free_path() -> None:
    service = build_llm_gateway_service()

    response = service.complete(_build_request(prompt="llm_summarize project status"))

    assert response.decision == "served"
    assert response.model_selected is not None
    assert response.usage is not None
    assert response.usage.total_tokens > 0
    assert response.cost is not None
    assert response.cost.cost_source == "none"
    assert response.budget_usage is not None
    assert response.budget_usage.token_units == response.usage.total_tokens
    assert response.quota_limit_source == "policy_guardrail"


def test_llm_gateway_uses_fallback_when_primary_fails_retryable() -> None:
    service = build_llm_gateway_service()

    response = service.complete(_build_request(prompt="llm_fallback_once summarize"))

    assert response.decision == "fallback_served"
    assert response.model_selected is not None
    assert "fallback" in response.model_selected
    assert response.route_metadata["fallback_hops"] == "1"


def test_llm_gateway_denies_on_provider_terminal_failure() -> None:
    service = build_llm_gateway_service()

    response = service.complete(_build_request(prompt="llm_runtime_error"))

    assert response.decision == "denied"
    assert response.error_code == "llm_provider_unavailable"
    assert response.retryable is True
    assert response.quota_limit_source == "provider_signal"


def test_llm_gateway_denies_on_unknown_routing_profile() -> None:
    service = build_llm_gateway_service()

    response = service.complete(
        _build_request(prompt="llm_summarize", routing_profile="unknown_profile")
    )

    assert response.decision == "denied"
    assert response.error_code == "llm_unknown_routing_profile"
