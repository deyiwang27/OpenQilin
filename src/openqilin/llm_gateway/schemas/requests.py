"""LLM gateway request schemas."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

LlmModelClass = Literal["interactive_fast", "reasoning_general", "embedding_text"]
AllocationMode = Literal["absolute", "ratio", "hybrid"]


@dataclass(frozen=True, slots=True)
class LlmBudgetContext:
    """Dual-dimension budget context passed to llm gateway."""

    currency_cap_usd: float | None = None
    quota_request_cap: int | None = None
    quota_token_cap: int | None = None
    allocation_mode: AllocationMode = "hybrid"
    project_share_ratio: float | None = None
    effective_budget_window: str | None = None


@dataclass(frozen=True, slots=True)
class LlmPolicyContext:
    """Policy context for governed llm request evaluation."""

    policy_version: str
    policy_hash: str
    rule_ids: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class LlmGatewayRequest:
    """Normalized llm gateway request payload."""

    request_id: str
    trace_id: str
    project_id: str
    agent_id: str
    task_id: str | None
    skill_id: str | None
    model_class: LlmModelClass
    routing_profile: str
    messages_or_prompt: str
    max_tokens: int
    temperature: float
    budget_context: LlmBudgetContext
    policy_context: LlmPolicyContext
