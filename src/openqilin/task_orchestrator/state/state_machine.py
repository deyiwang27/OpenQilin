"""Routing functions for LangGraph conditional edges in the task orchestration graph.

Each function inspects the current TaskState and returns the name of the next
node to execute (or END) as a string understood by LangGraph's add_conditional_edges.
"""

from __future__ import annotations

from typing import Literal

from openqilin.task_orchestrator.workflow.state_models import TaskState

_TERMINAL: frozenset[str] = frozenset({"blocked", "failed"})


def route_after_policy(
    state: TaskState,
) -> Literal["obligation_check_node", "__end__"]:
    """Route to obligation check on 'authorized'; terminate otherwise."""
    final = state.get("final_state", "")
    if final in _TERMINAL:
        return "__end__"
    return "obligation_check_node"


def route_after_obligation(
    state: TaskState,
) -> Literal["dispatch_node", "__end__"]:
    """Route to dispatch when obligations are satisfied; terminate otherwise."""
    if not state.get("obligation_satisfied", False):
        return "__end__"
    final = state.get("final_state", "")
    if final in _TERMINAL:
        return "__end__"
    return "dispatch_node"
