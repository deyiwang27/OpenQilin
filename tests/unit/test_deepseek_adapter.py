from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from openqilin.agents.auditor.agent import AuditorAgent
from openqilin.agents.shared.free_text_advisory import FreeTextAdvisoryRequest
from openqilin.llm_gateway.providers.base import (
    LiteLLMProviderError,
    LiteLLMProviderRequest,
)
from openqilin.llm_gateway.providers.deepseek_adapter import (
    DeepSeekAdapter,
    DeepSeekProviderConfig,
)
from openqilin.llm_gateway.routing.profile_resolver import resolve_routing_profile
from openqilin.llm_gateway.schemas.requests import LlmPolicyContext
from openqilin.llm_gateway.schemas.responses import (
    LlmBudgetContextEffective,
    LlmGatewayResponse,
)
from openqilin.shared_kernel.config import RuntimeSettings


def _request(prompt: str = "summarize the project update") -> LiteLLMProviderRequest:
    return LiteLLMProviderRequest(
        request_id="req-deepseek",
        trace_id="trace-deepseek",
        model_alias="deepseek_chat_primary",
        prompt=prompt,
        max_tokens=64,
        temperature=0.2,
    )


def _config(
    *,
    api_key: str | None = "test-key",
    max_retries: int = 0,
    retry_base_delay_seconds: float = 0.0,
    retry_max_delay_seconds: float = 0.0,
) -> DeepSeekProviderConfig:
    return DeepSeekProviderConfig(
        api_key=api_key,
        base_url="https://api.deepseek.com/v1",
        model="deepseek-chat",
        timeout_seconds=10.0,
        max_retries=max_retries,
        retry_base_delay_seconds=retry_base_delay_seconds,
        retry_max_delay_seconds=retry_max_delay_seconds,
    )


def _adapter(
    transport: httpx.BaseTransport,
    *,
    api_key: str | None = "test-key",
    max_retries: int = 0,
    retry_base_delay_seconds: float = 0.0,
    retry_max_delay_seconds: float = 0.0,
) -> DeepSeekAdapter:
    return DeepSeekAdapter(
        config=_config(
            api_key=api_key,
            max_retries=max_retries,
            retry_base_delay_seconds=retry_base_delay_seconds,
            retry_max_delay_seconds=retry_max_delay_seconds,
        ),
        http_client=httpx.Client(transport=transport, timeout=10.0),
    )


def test_deepseek_adapter_happy_path() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url == httpx.URL("https://api.deepseek.com/v1/chat/completions")
        assert request.headers["Authorization"] == "Bearer test-key"
        assert json.loads(request.read()) == {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": "summarize the project update"}],
            "max_tokens": 64,
            "temperature": 0.2,
        }
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "DeepSeek response"}}],
                "usage": {"prompt_tokens": 11, "completion_tokens": 17},
            },
        )

    result = _adapter(httpx.MockTransport(handler)).complete(_request())

    assert result.model_identifier == "deepseek/deepseek-chat"
    assert result.content == "DeepSeek response"
    assert result.input_tokens == 11
    assert result.output_tokens == 17
    assert result.quota_limit_source == "provider_config"


def test_deepseek_adapter_missing_api_key_raises() -> None:
    adapter = _adapter(httpx.MockTransport(lambda _: httpx.Response(200)), api_key="")

    with pytest.raises(LiteLLMProviderError) as exc_info:
        adapter.complete(_request())

    assert exc_info.value.code == "llm_provider_misconfigured"
    assert exc_info.value.retryable is False


def test_deepseek_adapter_429_retries_then_raises() -> None:
    call_count = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(429, json={"error": {"message": "rate limit"}})

    adapter = _adapter(
        httpx.MockTransport(handler),
        max_retries=2,
        retry_base_delay_seconds=0.0,
        retry_max_delay_seconds=0.0,
    )

    with pytest.raises(LiteLLMProviderError) as exc_info:
        adapter.complete(_request())

    assert exc_info.value.code == "llm_provider_unavailable"
    assert exc_info.value.retryable is True
    assert call_count == 3


def test_deepseek_adapter_4xx_raises_non_retryable() -> None:
    call_count = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(400, json={"error": {"message": "bad request"}})

    adapter = _adapter(httpx.MockTransport(handler), max_retries=2)

    with pytest.raises(LiteLLMProviderError) as exc_info:
        adapter.complete(_request())

    assert exc_info.value.code == "llm_provider_rejected"
    assert exc_info.value.retryable is False
    assert call_count == 1


def test_deepseek_adapter_network_error_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("network down", request=request)

    adapter = _adapter(httpx.MockTransport(handler), max_retries=0)

    with pytest.raises(LiteLLMProviderError) as exc_info:
        adapter.complete(_request())

    assert exc_info.value.code == "llm_provider_unavailable"
    assert exc_info.value.retryable is True


def test_deepseek_adapter_invalid_json_raises() -> None:
    adapter = _adapter(
        httpx.MockTransport(lambda _: httpx.Response(200, content=b"not-json")),
    )

    with pytest.raises(LiteLLMProviderError) as exc_info:
        adapter.complete(_request())

    assert exc_info.value.code == "llm_provider_invalid_response"
    assert exc_info.value.retryable is False


def test_deepseek_adapter_missing_content_raises() -> None:
    adapter = _adapter(
        httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                json={
                    "choices": [{"message": {}}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 2},
                },
            )
        ),
    )

    with pytest.raises(LiteLLMProviderError) as exc_info:
        adapter.complete(_request())

    assert exc_info.value.code == "llm_provider_invalid_response"
    assert exc_info.value.retryable is False


def test_deepseek_from_settings_builds_correctly() -> None:
    settings = RuntimeSettings(
        deepseek_api_key="settings-key",
        deepseek_base_url="https://deepseek.example.com/",
        deepseek_model="deepseek-reasoner",
        deepseek_request_timeout_seconds=45.0,
        deepseek_max_retries=4,
        deepseek_retry_base_delay_seconds=1.5,
        deepseek_retry_max_delay_seconds=9.0,
    )

    adapter = DeepSeekAdapter.from_settings(settings)

    assert adapter._config == DeepSeekProviderConfig(
        api_key="settings-key",
        base_url="https://deepseek.example.com",
        model="deepseek-reasoner",
        timeout_seconds=45.0,
        max_retries=4,
        retry_base_delay_seconds=1.5,
        retry_max_delay_seconds=9.0,
    )


def test_dev_deepseek_profile_resolves() -> None:
    profile = resolve_routing_profile("dev_deepseek")

    assert profile.profile_id == "dev_deepseek"
    assert profile.status == "active"
    assert profile.model_class_map["interactive_fast"] == (
        "deepseek_chat_primary",
        "deepseek_chat_fallback",
    )
    assert profile.model_class_map["reasoning_general"] == (
        "deepseek_chat_primary",
        "deepseek_chat_fallback",
    )
    assert profile.model_class_map["embedding_text"] == ("deepseek_chat_primary",)
    assert profile.max_fallback_hops == 1


def test_agent_routing_profile_reads_from_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENQILIN_LLM_DEFAULT_ROUTING_PROFILE", "dev_deepseek")
    gateway = _RecordingGateway()
    agent = AuditorAgent(
        enforcement=object(),  # type: ignore[arg-type]
        governance_repo=object(),  # type: ignore[arg-type]
        audit_writer=object(),  # type: ignore[arg-type]
        trace_id_factory=lambda: "trace-fixed",
        llm_gateway=gateway,  # type: ignore[arg-type]
    )

    response = agent.handle_free_text(
        FreeTextAdvisoryRequest(
            text="What changed?",
            scope="guild-1:channel-1",
            guild_id="guild-1",
            channel_id="channel-1",
        )
    )

    assert gateway.last_request is not None
    assert gateway.last_request.routing_profile == "dev_deepseek"
    assert response.advisory_text == "configured profile response"


class _RecordingGateway:
    def __init__(self) -> None:
        self.last_request: Any | None = None

    def complete(self, request: Any) -> LlmGatewayResponse:
        self.last_request = request
        return LlmGatewayResponse(
            request_id=str(request.request_id),
            trace_id=str(request.trace_id),
            decision="served",
            model_selected="deepseek/deepseek-chat",
            usage=None,
            cost=None,
            budget_usage=None,
            budget_context_effective=LlmBudgetContextEffective(
                allocation_mode="absolute",
                project_share_ratio=None,
                effective_budget="daily",
            ),
            quota_limit_source="provider_config",
            latency_ms=1,
            policy_context=LlmPolicyContext(
                policy_version="policy-v1",
                policy_hash="hash-v1",
                rule_ids=("AUD-001",),
            ),
            route_metadata={},
            generated_text="configured profile response",
        )
