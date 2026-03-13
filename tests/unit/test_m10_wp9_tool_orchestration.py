from __future__ import annotations

import re

from openqilin.execution_sandbox.tools.contracts import (
    ToolCallContext,
    ToolResult,
    ToolSourceDescriptor,
)
from openqilin.llm_gateway.providers.base import LiteLLMProviderRequest, LiteLLMProviderResult
from openqilin.llm_gateway.service import LlmGatewayService
from openqilin.shared_kernel.config import RuntimeSettings
from openqilin.task_orchestrator.dispatch.llm_dispatch import (
    LlmDispatchRequest,
    LlmGatewayDispatchAdapter,
)


class _CitationEchoProvider:
    def complete(self, request: LiteLLMProviderRequest) -> LiteLLMProviderResult:
        match = re.search(r"\[source:([A-Za-z0-9_.:-]+)\]", request.prompt)
        source_id = match.group(1) if match is not None else "unknown"
        return LiteLLMProviderResult(
            model_identifier=f"gemini/{request.model_alias}",
            content=f"tool-grounded answer [source:{source_id}]",
            input_tokens=10,
            output_tokens=8,
            provider_cost_usd=None,
            quota_limit_source="policy_guardrail",
        )


class _SpyReadToolService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object], ToolCallContext]] = []

    def call_tool(
        self,
        *,
        tool_name: str,
        arguments: dict[str, object],
        context: ToolCallContext,
    ) -> ToolResult:
        self.calls.append((tool_name, arguments, context))
        return ToolResult(
            decision="ok",
            tool_name=tool_name,
            tool_call_id="tool-call-001",
            trace_id=context.trace_id,
            request_id=context.request_id,
            data={"project_id": context.project_id, "status": "active"},
            sources=(
                ToolSourceDescriptor(
                    source_id=f"project:{context.project_id}",
                    source_kind="project_record",
                    version="status:active",
                    updated_at="2026-03-13T00:00:00+00:00",
                ),
            ),
            message="ok",
        )

    @staticmethod
    def summarize_for_grounding(result: ToolResult) -> str:
        return str(result.data)


def _build_request(prompt: str) -> LlmDispatchRequest:
    return LlmDispatchRequest(
        task_id="task-tool-policy-001",
        request_id="request-tool-policy-001",
        trace_id="trace-tool-policy-001",
        principal_id="owner_001",
        project_id="project_1",
        command="llm_reason",
        args=(prompt,),
        recipient_role="ceo",
        recipient_id="ceo_core",
        policy_version="policy-v1",
        policy_hash="policy-hash-v1",
        rule_ids=("rule_1",),
        conversation_guild_id="guild_1",
        conversation_channel_id="channel_1",
        conversation_thread_id=None,
    )


def test_llm_reason_uses_tool_first_grounding_when_configured() -> None:
    read_tools = _SpyReadToolService()
    adapter = LlmGatewayDispatchAdapter(
        llm_gateway_service=LlmGatewayService(provider=_CitationEchoProvider()),
        settings=RuntimeSettings(llm_default_routing_profile="dev_gemini_free"),
        read_tool_service=read_tools,  # type: ignore[arg-type]
    )

    receipt = adapter.dispatch(_build_request("Summarize project budget risk and lifecycle state."))

    assert receipt.accepted is True
    assert read_tools.calls
    assert receipt.gateway_response is not None
    assert receipt.gateway_response.generated_text is not None
    assert "[source:project:project_1]" in receipt.gateway_response.generated_text
    assert "project:project_1" in receipt.grounding_source_ids


def test_llm_reason_denies_mutation_intent_without_tool_write_command() -> None:
    read_tools = _SpyReadToolService()
    adapter = LlmGatewayDispatchAdapter(
        llm_gateway_service=LlmGatewayService(provider=_CitationEchoProvider()),
        settings=RuntimeSettings(llm_default_routing_profile="dev_gemini_free"),
        read_tool_service=read_tools,  # type: ignore[arg-type]
    )

    receipt = adapter.dispatch(_build_request("Update project status to archived now."))

    assert receipt.accepted is False
    assert receipt.error_code == "llm_mutation_requires_tool_write"
    assert read_tools.calls == []
