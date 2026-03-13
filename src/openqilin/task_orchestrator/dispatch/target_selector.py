"""Dispatch target selection for orchestrator handoff."""

from __future__ import annotations

from typing import Literal

from openqilin.data_access.repositories.runtime_state import TaskRecord

DispatchTarget = Literal["sandbox", "llm", "communication"]


def select_dispatch_target(task: TaskRecord) -> DispatchTarget:
    """Select dispatch target based on admitted task command."""

    if task.command.startswith("llm_"):
        return "llm"
    if task.command.startswith("tool_"):
        return "llm"
    if task.command.startswith("msg_"):
        return "communication"
    return "sandbox"
