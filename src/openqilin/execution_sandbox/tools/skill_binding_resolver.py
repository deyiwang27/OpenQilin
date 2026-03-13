"""Role-to-tool skill binding helpers for intent orchestration."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ToolSkillBinding:
    """Resolved role skill flags for tool orchestration."""

    tool_first_factual: bool
    citation_required: bool
    mutation_via_tools_only: bool


def resolve_tool_skill_binding(role: str) -> ToolSkillBinding:
    """Resolve MVP role binding for tool orchestration policy."""

    normalized = role.strip().lower()
    if normalized in {"ceo", "cwo", "project_manager", "auditor", "administrator", "owner"}:
        return ToolSkillBinding(
            tool_first_factual=True,
            citation_required=True,
            mutation_via_tools_only=True,
        )
    return ToolSkillBinding(
        tool_first_factual=False,
        citation_required=False,
        mutation_via_tools_only=True,
    )
