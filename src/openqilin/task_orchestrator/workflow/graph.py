"""LangGraph StateGraph construction for the OpenQilin task orchestration pipeline."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from openqilin.task_orchestrator.state.state_machine import (
    route_after_budget,
    route_after_obligation,
    route_after_policy,
)
from openqilin.task_orchestrator.workflow.nodes import (
    make_budget_reservation_node,
    make_dispatch_node,
    make_obligation_check_node,
    make_policy_evaluation_node,
)
from openqilin.task_orchestrator.workflow.state_models import TaskState, WorkflowServices


def build_task_graph(services: WorkflowServices) -> Any:
    """Build and compile the LangGraph StateGraph for task orchestration.

    The graph executes four sequential nodes with conditional early-exit edges:

        policy_evaluation_node
            → (blocked/failed) END
            → (authorized)    obligation_check_node
                → (not satisfied) END
                → (satisfied)     budget_reservation_node
                    → (blocked/failed) END
                    → (approved)       dispatch_node
                                           → END

    Each node is a closure over *services* so the graph is stateless across
    invocations and safe to reuse between worker cycles.
    """
    graph = StateGraph(TaskState)

    graph.add_node("policy_evaluation_node", make_policy_evaluation_node(services))
    graph.add_node("obligation_check_node", make_obligation_check_node(services))
    graph.add_node("budget_reservation_node", make_budget_reservation_node(services))
    graph.add_node("dispatch_node", make_dispatch_node(services))

    graph.set_entry_point("policy_evaluation_node")

    graph.add_conditional_edges(
        "policy_evaluation_node",
        route_after_policy,
        {
            "obligation_check_node": "obligation_check_node",
            "__end__": END,
        },
    )
    graph.add_conditional_edges(
        "obligation_check_node",
        route_after_obligation,
        {
            "budget_reservation_node": "budget_reservation_node",
            "__end__": END,
        },
    )
    graph.add_conditional_edges(
        "budget_reservation_node",
        route_after_budget,
        {
            "dispatch_node": "dispatch_node",
            "__end__": END,
        },
    )
    graph.add_edge("dispatch_node", END)

    return graph.compile()
