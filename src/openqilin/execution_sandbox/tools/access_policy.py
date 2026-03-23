"""Role-scoped tool access policy for MVP tool orchestration."""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

_READ_ALLOWLIST_BY_ROLE: Mapping[str, frozenset[str]] = MappingProxyType(
    {
        "owner": frozenset(
            {
                "get_project_lifecycle_state",
                "get_project_budget_snapshot",
                "get_project_milestone_status",
                "get_project_task_board",
                "search_project_docs",
                "get_project_doc_latest",
                "get_completion_gate_status",
                "get_project_workforce_snapshot",
                "get_audit_event_stream",
                "get_dispatch_denial_evidence",
                "get_conversation_window",
            }
        ),
        "ceo": frozenset(
            {
                "get_project_lifecycle_state",
                "get_project_budget_snapshot",
                "get_project_milestone_status",
                "get_project_task_board",
                "search_project_docs",
                "get_project_doc_latest",
                "get_completion_gate_status",
                "get_project_workforce_snapshot",
                "get_dispatch_denial_evidence",
                "get_conversation_window",
            }
        ),
        "cwo": frozenset(
            {
                "get_project_lifecycle_state",
                "get_project_budget_snapshot",
                "get_project_milestone_status",
                "get_project_task_board",
                "search_project_docs",
                "get_project_doc_latest",
                "get_completion_gate_status",
                "get_project_workforce_snapshot",
                "get_dispatch_denial_evidence",
                "get_conversation_window",
            }
        ),
        "auditor": frozenset(
            {
                "get_project_lifecycle_state",
                "get_project_budget_snapshot",
                "get_project_milestone_status",
                "get_project_task_board",
                "search_project_docs",
                "get_project_doc_latest",
                "get_completion_gate_status",
                "get_project_workforce_snapshot",
                "get_audit_event_stream",
                "get_dispatch_denial_evidence",
                "get_conversation_window",
            }
        ),
        "administrator": frozenset(
            {
                "get_project_lifecycle_state",
                "get_project_milestone_status",
                "get_project_task_board",
                "search_project_docs",
                "get_project_doc_latest",
                "get_audit_event_stream",
                "get_dispatch_denial_evidence",
                "get_conversation_window",
            }
        ),
        "project_manager": frozenset(
            {
                "get_project_lifecycle_state",
                "get_project_milestone_status",
                "get_project_task_board",
                "search_project_docs",
                "get_project_doc_latest",
                "get_completion_gate_status",
                "get_project_workforce_snapshot",
                "get_conversation_window",
            }
        ),
        "runtime_agent": frozenset(),
    }
)

_WRITE_ALLOWLIST_BY_ROLE: Mapping[str, frozenset[str]] = MappingProxyType(
    {
        "ceo": frozenset(
            {
                "transition_project_lifecycle",
                "append_decision_log",
                "append_progress_report",
                "upsert_project_artifact",
            }
        ),
        "cwo": frozenset(
            {
                "transition_project_lifecycle",
                "append_decision_log",
                "append_progress_report",
                "upsert_project_artifact",
            }
        ),
        "project_manager": frozenset(
            {
                "transition_project_lifecycle",
                "append_decision_log",
                "append_progress_report",
                "upsert_project_artifact",
            }
        ),
        "owner": frozenset(),
        "auditor": frozenset(),
        "administrator": frozenset(),
        "runtime_agent": frozenset(),
    }
)


def is_read_tool_allowed(*, role: str, tool_name: str) -> bool:
    """Return whether one role can invoke one read tool."""

    normalized_role = role.strip().lower()
    normalized_tool = tool_name.strip().lower()
    allowlist = _READ_ALLOWLIST_BY_ROLE.get(normalized_role, frozenset())
    return normalized_tool in allowlist


def is_write_tool_allowed(*, role: str, tool_name: str) -> bool:
    """Return whether one role can invoke one write tool."""

    normalized_role = role.strip().lower()
    normalized_tool = tool_name.strip().lower()
    allowlist = _WRITE_ALLOWLIST_BY_ROLE.get(normalized_role, frozenset())
    return normalized_tool in allowlist
