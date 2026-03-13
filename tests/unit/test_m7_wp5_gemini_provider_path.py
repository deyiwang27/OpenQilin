import httpx

from openqilin.llm_gateway.providers.gemini_flash_adapter import (
    GeminiFlashFreeAdapter,
    GeminiFlashProviderConfig,
)
from openqilin.llm_gateway.schemas.requests import (
    LlmBudgetContext,
    LlmGatewayRequest,
    LlmPolicyContext,
)
from openqilin.llm_gateway.service import LlmGatewayService, build_llm_gateway_service


def _build_request(*, prompt: str) -> LlmGatewayRequest:
    return LlmGatewayRequest(
        request_id="req-m7-wp5",
        trace_id="trace-m7-wp5",
        project_id="project-m7-wp5",
        agent_id="owner-m7-wp5",
        task_id="task-m7-wp5",
        skill_id=None,
        model_class="interactive_fast",
        routing_profile="dev_gemini_free",
        messages_or_prompt=prompt,
        max_tokens=64,
        temperature=0.1,
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


def _build_service(
    transport: httpx.BaseTransport, *, api_key: str | None = "test-key"
) -> LlmGatewayService:
    provider = GeminiFlashFreeAdapter(
        config=GeminiFlashProviderConfig(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta",
            timeout_seconds=10.0,
            model_alias_map={
                "google_gemini_free_primary": "gemini-2.0-flash",
                "google_gemini_free_fallback": "gemini-2.0-flash-lite",
            },
            max_retries=0,
            retry_base_delay_seconds=0.0,
            retry_max_delay_seconds=0.0,
        ),
        http_client=httpx.Client(transport=transport, timeout=10.0),
    )
    return LlmGatewayService(provider=provider)


def test_m7_wp5_gemini_provider_path_serves_with_quota_telemetry() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/models/gemini-2.0-flash:generateContent")
        return httpx.Response(
            200,
            json={
                "modelVersion": "gemini-2.0-flash",
                "candidates": [{"content": {"parts": [{"text": "ok"}]}}],
                "usageMetadata": {
                    "promptTokenCount": 12,
                    "candidatesTokenCount": 20,
                    "totalTokenCount": 32,
                },
            },
        )

    service = _build_service(httpx.MockTransport(handler))
    response = service.complete(_build_request(prompt="summarize project updates"))

    assert response.decision == "served"
    assert response.model_selected == "gemini/gemini-2.0-flash"
    assert response.usage is not None
    assert response.usage.input_tokens == 12
    assert response.usage.output_tokens == 20
    assert response.usage.total_tokens == 32
    assert response.budget_usage is not None
    assert response.budget_usage.token_units == 32
    assert response.budget_usage.request_units == 1
    assert response.cost is not None
    assert response.cost.cost_source == "none"
    assert response.quota_limit_source == "provider_config"


def test_m7_wp5_gemini_provider_path_uses_fallback_on_retryable_primary_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/models/gemini-2.0-flash:generateContent"):
            return httpx.Response(503, json={"error": {"message": "transient"}})
        return httpx.Response(
            200,
            json={
                "modelVersion": "gemini-2.0-flash-lite",
                "candidates": [{"content": {"parts": [{"text": "fallback-ok"}]}}],
                "usageMetadata": {
                    "promptTokenCount": 8,
                    "candidatesTokenCount": 16,
                    "totalTokenCount": 24,
                },
            },
        )

    service = _build_service(httpx.MockTransport(handler))
    response = service.complete(_build_request(prompt="fallback path test"))

    assert response.decision == "fallback_served"
    assert response.model_selected == "gemini/gemini-2.0-flash-lite"
    assert response.route_metadata["fallback_hops"] == "1"
    assert response.quota_limit_source == "provider_config"


def test_m7_wp5_gemini_provider_path_fails_closed_on_missing_usage_metadata() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": "no-usage"}]}}]},
        )

    service = _build_service(httpx.MockTransport(handler))
    response = service.complete(_build_request(prompt="missing usage metadata"))

    assert response.decision == "denied"
    assert response.error_code == "llm_provider_usage_unavailable"
    assert response.retryable is False
    assert response.quota_limit_source == "provider_signal"


def test_m7_wp5_gemini_provider_path_fails_closed_on_missing_api_key() -> None:
    service = _build_service(httpx.MockTransport(lambda _: httpx.Response(200)), api_key=None)
    response = service.complete(_build_request(prompt="any request"))

    assert response.decision == "denied"
    assert response.error_code == "llm_provider_misconfigured"
    assert response.retryable is False


def test_m7_wp5_build_gateway_service_uses_configured_gemini_backend(monkeypatch) -> None:
    monkeypatch.setenv("OPENQILIN_LLM_PROVIDER_BACKEND", "gemini_flash_free")
    monkeypatch.delenv("OPENQILIN_GEMINI_API_KEY", raising=False)

    service = build_llm_gateway_service()
    response = service.complete(_build_request(prompt="backend wiring check"))

    assert response.decision == "denied"
    assert response.error_code == "llm_provider_misconfigured"


def test_m7_wp5_gemini_provider_retries_transient_429_then_serves() -> None:
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        assert request.url.path.endswith("/models/gemini-2.0-flash:generateContent")
        if call_count == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(
            200,
            json={
                "modelVersion": "gemini-2.0-flash",
                "candidates": [{"content": {"parts": [{"text": "retry-ok"}]}}],
                "usageMetadata": {
                    "promptTokenCount": 10,
                    "candidatesTokenCount": 14,
                    "totalTokenCount": 24,
                },
            },
        )

    provider = GeminiFlashFreeAdapter(
        config=GeminiFlashProviderConfig(
            api_key="test-key",
            base_url="https://generativelanguage.googleapis.com/v1beta",
            timeout_seconds=10.0,
            model_alias_map={
                "google_gemini_free_primary": "gemini-2.0-flash",
                "google_gemini_free_fallback": "gemini-2.0-flash-lite",
            },
            max_retries=1,
            retry_base_delay_seconds=0.0,
            retry_max_delay_seconds=0.0,
        ),
        http_client=httpx.Client(transport=httpx.MockTransport(handler), timeout=10.0),
    )
    service = LlmGatewayService(provider=provider)

    response = service.complete(_build_request(prompt="retry transient 429"))

    assert response.decision == "served"
    assert response.model_selected == "gemini/gemini-2.0-flash"
    assert call_count == 2
