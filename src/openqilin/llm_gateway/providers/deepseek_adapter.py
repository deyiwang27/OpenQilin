"""DeepSeek provider adapter for governed LLM gateway calls."""

from __future__ import annotations

from dataclasses import dataclass
from time import sleep
from typing import Any, Mapping

import httpx

from openqilin.llm_gateway.providers.base import (
    LiteLLMProvider,
    LiteLLMProviderError,
    LiteLLMProviderRequest,
    LiteLLMProviderResult,
)
from openqilin.shared_kernel.config import RuntimeSettings


@dataclass(frozen=True, slots=True)
class DeepSeekProviderConfig:
    """Runtime configuration for DeepSeek provider calls."""

    api_key: str | None
    base_url: str
    model: str
    timeout_seconds: float
    max_retries: int = 2
    retry_base_delay_seconds: float = 1.0
    retry_max_delay_seconds: float = 8.0


class DeepSeekAdapter(LiteLLMProvider):
    """HTTP adapter targeting DeepSeek's OpenAI-compatible chat completions API."""

    def __init__(
        self,
        *,
        config: DeepSeekProviderConfig,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._config = config
        self._client = http_client or httpx.Client(timeout=config.timeout_seconds)

    @classmethod
    def from_settings(
        cls,
        settings: RuntimeSettings,
        *,
        http_client: httpx.Client | None = None,
    ) -> DeepSeekAdapter:
        """Build adapter from runtime settings."""

        return cls(
            config=DeepSeekProviderConfig(
                api_key=settings.deepseek_api_key,
                base_url=settings.deepseek_base_url.rstrip("/"),
                model=settings.deepseek_model,
                timeout_seconds=settings.deepseek_request_timeout_seconds,
                max_retries=max(0, settings.deepseek_max_retries),
                retry_base_delay_seconds=max(0.0, settings.deepseek_retry_base_delay_seconds),
                retry_max_delay_seconds=max(0.0, settings.deepseek_retry_max_delay_seconds),
            ),
            http_client=http_client,
        )

    def complete(self, request: LiteLLMProviderRequest) -> LiteLLMProviderResult:
        """Execute DeepSeek completion and normalize provider output."""

        api_key = (self._config.api_key or "").strip()
        if not api_key:
            raise LiteLLMProviderError(
                code="llm_provider_misconfigured",
                message="deepseek api key is missing",
                retryable=False,
            )

        payload = {
            "model": self._config.model,
            "messages": [{"role": "user", "content": request.prompt}],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        endpoint = f"{self._config.base_url}/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}"}
        response: httpx.Response | None = None
        for attempt in range(self._config.max_retries + 1):
            try:
                response = self._client.post(endpoint, json=payload, headers=headers)
            except httpx.RequestError as error:
                if attempt < self._config.max_retries:
                    sleep(_compute_retry_delay_seconds(config=self._config, attempt=attempt))
                    continue
                raise LiteLLMProviderError(
                    code="llm_provider_unavailable",
                    message=f"deepseek request failed: {error}",
                    retryable=True,
                ) from error

            if response.status_code == 429 or response.status_code >= 500:
                if attempt < self._config.max_retries:
                    sleep(_compute_retry_delay_seconds(config=self._config, attempt=attempt))
                    continue
                raise LiteLLMProviderError(
                    code="llm_provider_unavailable",
                    message=f"deepseek transient failure: http {response.status_code}",
                    retryable=True,
                )
            if response.status_code >= 400:
                raise LiteLLMProviderError(
                    code="llm_provider_rejected",
                    message=f"deepseek rejected request: http {response.status_code}",
                    retryable=False,
                )
            break

        if response is None:
            raise LiteLLMProviderError(
                code="llm_provider_unavailable",
                message="deepseek request failed without response",
                retryable=True,
            )

        try:
            body = response.json()
        except ValueError as error:
            raise LiteLLMProviderError(
                code="llm_provider_invalid_response",
                message=f"deepseek response is not valid json: {error}",
                retryable=False,
            ) from error

        content = _extract_text_content(body)
        usage = _extract_usage(body)
        return LiteLLMProviderResult(
            model_identifier=f"deepseek/{self._config.model}",
            content=content,
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
            provider_cost_usd=None,
            quota_limit_source="provider_config",
        )


def _extract_text_content(body: Mapping[str, Any]) -> str:
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        raise LiteLLMProviderError(
            code="llm_provider_invalid_response",
            message="deepseek response missing choices",
            retryable=False,
        )
    first_choice = choices[0]
    if not isinstance(first_choice, Mapping):
        raise LiteLLMProviderError(
            code="llm_provider_invalid_response",
            message="deepseek choice payload is invalid",
            retryable=False,
        )
    message = first_choice.get("message")
    if not isinstance(message, Mapping):
        raise LiteLLMProviderError(
            code="llm_provider_invalid_response",
            message="deepseek message payload is invalid",
            retryable=False,
        )
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise LiteLLMProviderError(
            code="llm_provider_invalid_response",
            message="deepseek response text is missing",
            retryable=False,
        )
    return content.strip()


def _extract_usage(body: Mapping[str, Any]) -> dict[str, int]:
    usage = body.get("usage")
    if not isinstance(usage, Mapping):
        raise LiteLLMProviderError(
            code="llm_provider_invalid_response",
            message="deepseek usage payload is missing",
            retryable=False,
        )

    input_tokens = _as_nonnegative_int(usage.get("prompt_tokens"))
    output_tokens = _as_nonnegative_int(usage.get("completion_tokens"))
    if input_tokens is None or output_tokens is None:
        raise LiteLLMProviderError(
            code="llm_provider_invalid_response",
            message="deepseek usage payload is incomplete",
            retryable=False,
        )
    return {"input_tokens": input_tokens, "output_tokens": output_tokens}


def _as_nonnegative_int(value: Any) -> int | None:
    if not isinstance(value, int):
        return None
    if value < 0:
        return None
    return value


def _compute_retry_delay_seconds(*, config: DeepSeekProviderConfig, attempt: int) -> float:
    exponential_delay = config.retry_base_delay_seconds * (2**attempt)
    return min(max(0.0, exponential_delay), config.retry_max_delay_seconds)
