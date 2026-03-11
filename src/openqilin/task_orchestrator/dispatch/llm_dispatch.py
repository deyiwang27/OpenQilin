"""LLM dispatch adapter for governed llm_gateway execution path."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4

from openqilin.llm_gateway.schemas.requests import (
    LlmBudgetContext,
    LlmGatewayRequest,
    LlmModelClass,
    LlmPolicyContext,
)
from openqilin.llm_gateway.schemas.responses import LlmGatewayResponse
from openqilin.llm_gateway.service import LlmGatewayService


@dataclass(frozen=True, slots=True)
class LlmDispatchRequest:
    """Dispatch payload for llm_gateway boundary."""

    task_id: str
    request_id: str
    trace_id: str
    principal_id: str
    project_id: str | None
    command: str
    args: tuple[str, ...]
    policy_version: str
    policy_hash: str
    rule_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LlmDispatchReceipt:
    """LLM dispatch receipt for orchestrator lifecycle handling."""

    accepted: bool
    dispatch_id: str | None
    error_code: str | None
    message: str
    gateway_response: LlmGatewayResponse | None


class LlmDispatchAdapter(Protocol):
    """LLM dispatch adapter protocol."""

    def dispatch(self, payload: LlmDispatchRequest) -> LlmDispatchReceipt:
        """Dispatch admitted llm task through gateway boundary."""


class LlmGatewayDispatchAdapter:
    """Adapter that forwards dispatch payloads into llm_gateway service."""

    def __init__(self, llm_gateway_service: LlmGatewayService) -> None:
        self._llm_gateway_service = llm_gateway_service

    def dispatch(self, payload: LlmDispatchRequest) -> LlmDispatchReceipt:
        """Dispatch llm task and map gateway decision to dispatch receipt."""

        model_class: LlmModelClass = (
            "reasoning_general" if payload.command.startswith("llm_reason") else "interactive_fast"
        )
        request = LlmGatewayRequest(
            request_id=payload.request_id,
            trace_id=payload.trace_id,
            project_id=payload.project_id or "project-default",
            agent_id=payload.principal_id,
            task_id=payload.task_id,
            skill_id=None,
            model_class=model_class,
            routing_profile="dev_gemini_free",
            messages_or_prompt=self._build_prompt(payload),
            max_tokens=128,
            temperature=0.2,
            budget_context=LlmBudgetContext(
                currency_cap_usd=None,
                quota_request_cap=1_000,
                quota_token_cap=100_000,
                allocation_mode="hybrid",
                project_share_ratio=0.1,
                effective_budget_window="daily",
            ),
            policy_context=LlmPolicyContext(
                policy_version=payload.policy_version,
                policy_hash=payload.policy_hash,
                rule_ids=payload.rule_ids,
            ),
        )
        response = self._llm_gateway_service.complete(request)
        if response.decision in {"served", "fallback_served"}:
            return LlmDispatchReceipt(
                accepted=True,
                dispatch_id=f"llm-{uuid4()}",
                error_code=None,
                message="llm gateway dispatch accepted",
                gateway_response=response,
            )
        return LlmDispatchReceipt(
            accepted=False,
            dispatch_id=None,
            error_code=response.error_code or "llm_gateway_dispatch_failed",
            message=response.error_message or "llm gateway denied request",
            gateway_response=response,
        )

    @staticmethod
    def _build_prompt(payload: LlmDispatchRequest) -> str:
        args = " ".join(payload.args).strip()
        if args:
            return f"{payload.command}: {args}"
        return payload.command
