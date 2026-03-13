"""Gemini Flash free-tier provider adapter for governed LLM gateway calls."""

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
class GeminiFlashProviderConfig:
    """Runtime configuration for Gemini Flash provider calls."""

    api_key: str | None
    base_url: str
    timeout_seconds: float
    model_alias_map: Mapping[str, str]
    max_retries: int = 2
    retry_base_delay_seconds: float = 1.0
    retry_max_delay_seconds: float = 8.0


class GeminiFlashFreeAdapter(LiteLLMProvider):
    """HTTP adapter targeting Gemini Flash generateContent API."""

    def __init__(
        self,
        *,
        config: GeminiFlashProviderConfig,
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
    ) -> GeminiFlashFreeAdapter:
        """Build adapter from runtime settings."""

        return cls(
            config=GeminiFlashProviderConfig(
                api_key=settings.gemini_api_key,
                base_url=settings.gemini_base_url.rstrip("/"),
                timeout_seconds=settings.gemini_request_timeout_seconds,
                model_alias_map={
                    "google_gemini_free_primary": settings.gemini_free_primary_model,
                    "google_gemini_free_fallback": settings.gemini_free_fallback_model,
                },
                max_retries=max(0, settings.gemini_max_retries),
                retry_base_delay_seconds=max(0.0, settings.gemini_retry_base_delay_seconds),
                retry_max_delay_seconds=max(0.0, settings.gemini_retry_max_delay_seconds),
            ),
            http_client=http_client,
        )

    def complete(self, request: LiteLLMProviderRequest) -> LiteLLMProviderResult:
        """Execute Gemini Flash completion and normalize provider output."""

        model_id = self._config.model_alias_map.get(request.model_alias)
        if model_id is None:
            raise LiteLLMProviderError(
                code="llm_model_alias_unmapped",
                message=f"unmapped gemini alias: {request.model_alias}",
                retryable=False,
            )

        api_key = (self._config.api_key or "").strip()
        if not api_key:
            raise LiteLLMProviderError(
                code="llm_provider_misconfigured",
                message="gemini api key is missing",
                retryable=False,
            )

        payload = {
            "contents": [{"parts": [{"text": request.prompt}]}],
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens,
            },
        }
        endpoint = f"{self._config.base_url}/models/{model_id}:generateContent"
        response: httpx.Response | None = None
        for attempt in range(self._config.max_retries + 1):
            try:
                response = self._client.post(
                    endpoint,
                    params={"key": api_key},
                    json=payload,
                )
            except httpx.RequestError as error:
                if attempt < self._config.max_retries:
                    sleep(
                        _compute_retry_delay_seconds(
                            config=self._config, response=None, attempt=attempt
                        )
                    )
                    continue
                raise LiteLLMProviderError(
                    code="llm_provider_unavailable",
                    message=f"gemini request failed: {error}",
                    retryable=True,
                ) from error

            if response.status_code == 429 or response.status_code >= 500:
                if attempt < self._config.max_retries:
                    sleep(
                        _compute_retry_delay_seconds(
                            config=self._config,
                            response=response,
                            attempt=attempt,
                        )
                    )
                    continue
                raise LiteLLMProviderError(
                    code="llm_provider_unavailable",
                    message=f"gemini transient failure: http {response.status_code}",
                    retryable=True,
                )
            if response.status_code >= 400:
                raise LiteLLMProviderError(
                    code="llm_provider_rejected",
                    message=f"gemini rejected request: http {response.status_code}",
                    retryable=False,
                )
            break
        if response is None:
            raise LiteLLMProviderError(
                code="llm_provider_unavailable",
                message="gemini request failed without response",
                retryable=True,
            )

        try:
            body = response.json()
        except ValueError as error:
            raise LiteLLMProviderError(
                code="llm_provider_invalid_response",
                message=f"gemini response is not valid json: {error}",
                retryable=False,
            ) from error

        content = _extract_text_content(body)
        usage = _extract_usage(body)
        model_identifier = f"gemini/{body.get('modelVersion') or model_id}"
        return LiteLLMProviderResult(
            model_identifier=model_identifier,
            content=content,
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
            provider_cost_usd=None,
            quota_limit_source="provider_config",
        )


def _extract_text_content(body: Mapping[str, Any]) -> str:
    candidates = body.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise LiteLLMProviderError(
            code="llm_provider_invalid_response",
            message="gemini response missing candidates",
            retryable=False,
        )
    first = candidates[0]
    if not isinstance(first, Mapping):
        raise LiteLLMProviderError(
            code="llm_provider_invalid_response",
            message="gemini candidate payload is invalid",
            retryable=False,
        )
    content_obj = first.get("content")
    if not isinstance(content_obj, Mapping):
        raise LiteLLMProviderError(
            code="llm_provider_invalid_response",
            message="gemini candidate content payload is invalid",
            retryable=False,
        )
    parts = content_obj.get("parts")
    if not isinstance(parts, list) or not parts:
        raise LiteLLMProviderError(
            code="llm_provider_invalid_response",
            message="gemini candidate parts are missing",
            retryable=False,
        )
    first_part = parts[0]
    if not isinstance(first_part, Mapping):
        raise LiteLLMProviderError(
            code="llm_provider_invalid_response",
            message="gemini first part payload is invalid",
            retryable=False,
        )
    text = first_part.get("text")
    if not isinstance(text, str) or not text.strip():
        raise LiteLLMProviderError(
            code="llm_provider_invalid_response",
            message="gemini response text is missing",
            retryable=False,
        )
    return text.strip()


def _extract_usage(body: Mapping[str, Any]) -> dict[str, int]:
    usage_metadata = body.get("usageMetadata")
    if not isinstance(usage_metadata, Mapping):
        raise LiteLLMProviderError(
            code="llm_provider_usage_unavailable",
            message="gemini usage metadata missing",
            retryable=False,
        )

    input_tokens = _as_nonnegative_int(usage_metadata.get("promptTokenCount"))
    output_tokens = _as_nonnegative_int(usage_metadata.get("candidatesTokenCount"))
    if input_tokens is None or output_tokens is None:
        raise LiteLLMProviderError(
            code="llm_provider_usage_unavailable",
            message="gemini usage metadata incomplete",
            retryable=False,
        )
    return {"input_tokens": input_tokens, "output_tokens": output_tokens}


def _as_nonnegative_int(value: Any) -> int | None:
    if not isinstance(value, int):
        return None
    if value < 0:
        return None
    return value


def _compute_retry_delay_seconds(
    *,
    config: GeminiFlashProviderConfig,
    response: httpx.Response | None,
    attempt: int,
) -> float:
    retry_after_delay = _parse_retry_after_seconds(response)
    if retry_after_delay is not None:
        return min(max(0.0, retry_after_delay), config.retry_max_delay_seconds)

    exponential_delay = config.retry_base_delay_seconds * (2**attempt)
    return min(max(0.0, exponential_delay), config.retry_max_delay_seconds)


def _parse_retry_after_seconds(response: httpx.Response | None) -> float | None:
    if response is None:
        return None
    value = response.headers.get("Retry-After")
    if value is None:
        return None
    try:
        seconds = float(value.strip())
    except ValueError:
        return None
    if seconds < 0:
        return None
    return seconds
