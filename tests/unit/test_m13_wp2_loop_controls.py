"""Unit tests for M13-WP2 loop controls enforcement.

Verifies:
- LoopState is per-task (not shared)
- check_and_increment_hop raises LoopCapBreachError on the (limit+1)th call
- check_and_increment_pair raises LoopCapBreachError on the (limit+1)th call for same pair
- Different pairs are tracked independently
- LoopCapBreachError carries correct attributes
"""

from __future__ import annotations

import pytest

from openqilin.task_orchestrator.loop_control import (
    LoopCapBreachError,
    LoopState,
    check_and_increment_hop,
    check_and_increment_pair,
)


class TestLoopState:
    def test_loop_state_default_values(self) -> None:
        state = LoopState()
        assert state.hop_count == 0
        assert state.pair_rounds == {}

    def test_loop_states_are_independent(self) -> None:
        s1 = LoopState()
        s2 = LoopState()
        check_and_increment_hop(s1)
        assert s1.hop_count == 1
        assert s2.hop_count == 0

    def test_pair_rounds_dict_not_shared_between_instances(self) -> None:
        s1 = LoopState()
        s2 = LoopState()
        check_and_increment_pair(s1, "pm", "dl")
        assert ("pm", "dl") in s1.pair_rounds
        assert ("pm", "dl") not in s2.pair_rounds


class TestCheckAndIncrementHop:
    def test_first_hop_does_not_raise(self) -> None:
        state = LoopState()
        check_and_increment_hop(state)
        assert state.hop_count == 1

    def test_hops_up_to_limit_do_not_raise(self) -> None:
        state = LoopState()
        for _ in range(5):
            check_and_increment_hop(state)
        assert state.hop_count == 5

    def test_sixth_hop_raises_loop_cap_breach_error(self) -> None:
        state = LoopState()
        for _ in range(5):
            check_and_increment_hop(state)
        with pytest.raises(LoopCapBreachError) as exc_info:
            check_and_increment_hop(state)
        err = exc_info.value
        assert err.cap_type == "hop_count"
        assert err.count == 6
        assert err.limit == 5
        assert err.pair is None

    def test_custom_limit_respected(self) -> None:
        state = LoopState()
        check_and_increment_hop(state, limit=2)
        check_and_increment_hop(state, limit=2)
        with pytest.raises(LoopCapBreachError) as exc_info:
            check_and_increment_hop(state, limit=2)
        assert exc_info.value.count == 3
        assert exc_info.value.limit == 2

    def test_hop_count_incremented_before_raise(self) -> None:
        state = LoopState(hop_count=5)
        with pytest.raises(LoopCapBreachError):
            check_and_increment_hop(state)
        assert state.hop_count == 6


class TestCheckAndIncrementPair:
    def test_first_pair_round_does_not_raise(self) -> None:
        state = LoopState()
        check_and_increment_pair(state, "pm", "dl")
        assert state.pair_rounds[("pm", "dl")] == 1

    def test_pair_rounds_up_to_limit_do_not_raise(self) -> None:
        state = LoopState()
        check_and_increment_pair(state, "pm", "dl")
        check_and_increment_pair(state, "pm", "dl")
        assert state.pair_rounds[("pm", "dl")] == 2

    def test_third_pair_round_raises_loop_cap_breach_error(self) -> None:
        state = LoopState()
        check_and_increment_pair(state, "pm", "dl")
        check_and_increment_pair(state, "pm", "dl")
        with pytest.raises(LoopCapBreachError) as exc_info:
            check_and_increment_pair(state, "pm", "dl")
        err = exc_info.value
        assert err.cap_type == "pair_rounds"
        assert err.count == 3
        assert err.limit == 2
        assert err.pair == ("pm", "dl")

    def test_different_pairs_tracked_independently(self) -> None:
        state = LoopState()
        # pm→dl and dl→specialist are separate pairs
        check_and_increment_pair(state, "pm", "dl")
        check_and_increment_pair(state, "pm", "dl")
        check_and_increment_pair(state, "dl", "specialist")
        check_and_increment_pair(state, "dl", "specialist")
        # Both at limit=2, no breach yet
        assert state.pair_rounds[("pm", "dl")] == 2
        assert state.pair_rounds[("dl", "specialist")] == 2

    def test_pair_round_breach_only_for_same_pair(self) -> None:
        state = LoopState()
        check_and_increment_pair(state, "pm", "dl")
        check_and_increment_pair(state, "pm", "dl")
        # Third round for pm→dl breaches
        with pytest.raises(LoopCapBreachError) as exc_info:
            check_and_increment_pair(state, "pm", "dl")
        assert exc_info.value.pair == ("pm", "dl")
        # dl→specialist is unaffected
        check_and_increment_pair(state, "dl", "specialist")

    def test_custom_pair_limit_respected(self) -> None:
        state = LoopState()
        check_and_increment_pair(state, "pm", "dl", limit=1)
        with pytest.raises(LoopCapBreachError) as exc_info:
            check_and_increment_pair(state, "pm", "dl", limit=1)
        assert exc_info.value.limit == 1

    def test_reverse_pair_is_separate_from_forward_pair(self) -> None:
        state = LoopState()
        check_and_increment_pair(state, "pm", "dl")
        check_and_increment_pair(state, "pm", "dl")
        # pm→dl at limit; dl→pm is a different pair, not yet at limit
        check_and_increment_pair(state, "dl", "pm")


class TestLoopCapBreachError:
    def test_error_message_includes_cap_type_and_counts(self) -> None:
        err = LoopCapBreachError("hop_count", 6, 5)
        assert "hop_count" in str(err)
        assert "6" in str(err)
        assert "5" in str(err)

    def test_error_message_includes_pair_when_provided(self) -> None:
        err = LoopCapBreachError("pair_rounds", 3, 2, pair=("pm", "dl"))
        assert "pair_rounds" in str(err)
        assert "pm" in str(err)
        assert "dl" in str(err)

    def test_error_is_exception_subclass(self) -> None:
        assert issubclass(LoopCapBreachError, Exception)
