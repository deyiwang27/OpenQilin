"""Per-task loop cap enforcement for the OpenQilin task orchestration pipeline.

Enforces two caps per task trace:
- hop_count: total node/agent invocations in a trace (default limit=5).
- pair_rounds: consecutive rounds between the same (sender, recipient) agent pair (default limit=2).

Both caps raise LoopCapBreachError on breach. The orchestrator exception path catches this,
marks the task blocked, emits a loop_cap.breach audit event, and notifies the owner.

Usage in LangGraph nodes::

    from openqilin.task_orchestrator.loop_control import check_and_increment_hop, LoopCapBreachError

    def my_node(state: TaskState) -> dict[str, Any]:
        check_and_increment_hop(state["loop_state"])
        # ... node logic

For A2A delegation hops (PM → DL, DL → Specialist), call check_and_increment_pair()
from the dispatch adapter at each agent-to-agent boundary. These call sites are activated
in M14 when PM, DL, and Specialist agents are wired.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LoopState:
    """Mutable per-task loop tracking state.

    Created fresh for each task invocation in the orchestrator worker.
    Never shared across tasks.
    """

    hop_count: int = 0
    pair_rounds: dict[tuple[str, str], int] = field(default_factory=dict)


class LoopCapBreachError(Exception):
    """Raised when a per-task hop or pair-round cap is exceeded."""

    def __init__(
        self,
        cap_type: str,
        count: int,
        limit: int,
        *,
        pair: tuple[str, str] | None = None,
    ) -> None:
        self.cap_type = cap_type
        self.count = count
        self.limit = limit
        self.pair = pair
        pair_info = f" pair={pair!r}" if pair else ""
        super().__init__(f"Loop cap breached: {cap_type}={count} exceeded limit={limit}{pair_info}")


def check_and_increment_hop(loop_state: LoopState, limit: int = 5) -> None:
    """Increment hop count and raise LoopCapBreachError if the limit is exceeded.

    Mutates loop_state.hop_count in place. The limit is inclusive: hop_count is allowed
    to reach *limit* but raises on the (limit+1)th call.

    Args:
        loop_state: Per-task mutable loop state. Must not be shared across tasks.
        limit: Maximum allowed hop count. Default 5.

    Raises:
        LoopCapBreachError: When hop_count exceeds limit after increment.

    M14 entry criteria — deferred spec rules:

    LOOP-005 (AgentLoopControls §4): cap limits MUST be configurable via governed policy
    without requiring code changes. Currently limits are Python default arguments with no
    policy binding or env-var override. Wire via RuntimeSettings or a policy-read path in M14.

    LOOP-006 (AgentLoopControls §4): escalation messages (message.type == 'escalation')
    MUST be exempt from per-trace hop counting and MUST open a fresh trace with a new
    trace_id. No exemption exists yet. This applies across all A2A communication paths.
    Implement in M14 when PM→DL→Specialist escalation paths are wired.
    """
    loop_state.hop_count += 1
    if loop_state.hop_count > limit:
        raise LoopCapBreachError("hop_count", loop_state.hop_count, limit)


def check_and_increment_pair(
    loop_state: LoopState,
    sender: str,
    recipient: str,
    limit: int = 2,
) -> None:
    """Increment the pair-round counter and raise LoopCapBreachError if the limit is exceeded.

    Call this at every A2A delegation boundary (e.g. PM→DL, DL→Specialist).
    Tracks each (sender, recipient) pair independently.

    Args:
        loop_state: Per-task mutable loop state.
        sender: Sending agent role identifier.
        recipient: Receiving agent role identifier.
        limit: Maximum allowed rounds for this pair. Default 2.

    Raises:
        LoopCapBreachError: When pair_rounds[pair] exceeds limit after increment.
    """
    pair = (sender, recipient)
    current = loop_state.pair_rounds.get(pair, 0) + 1
    loop_state.pair_rounds[pair] = current
    if current > limit:
        raise LoopCapBreachError("pair_rounds", current, limit, pair=pair)
