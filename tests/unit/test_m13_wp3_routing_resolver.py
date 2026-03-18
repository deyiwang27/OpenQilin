"""Unit tests for M13-WP3: ProjectSpaceRoutingResolver.

Verifies:
- Known active channel resolves to correct RoutingContext (project_id, default_recipient)
- Unknown channel returns None (fail-closed)
- Inactive binding (archived, locked) returns None (fail-closed)
- BindingState lifecycle constants are correct
- LifecycleEvent carries event_type
"""

from __future__ import annotations

import pytest

from openqilin.project_spaces.binding_repository import build_project_space_binding
from openqilin.project_spaces.models import BindingState, LifecycleEvent, RoutingContext
from openqilin.project_spaces.routing_resolver import ProjectSpaceRoutingResolver
from tests.testing.infra_stubs import InMemoryProjectSpaceBindingRepository


def _make_resolver() -> tuple[InMemoryProjectSpaceBindingRepository, ProjectSpaceRoutingResolver]:
    repo = InMemoryProjectSpaceBindingRepository()
    resolver = ProjectSpaceRoutingResolver(binding_repo=repo)  # type: ignore[arg-type]
    return repo, resolver


class TestRoutingResolverUnknownChannel:
    def test_unknown_channel_returns_none(self) -> None:
        _, resolver = _make_resolver()
        result = resolver.resolve("guild-unknown", "channel-unknown")
        assert result is None

    def test_unknown_guild_with_known_channel_returns_none(self) -> None:
        repo, resolver = _make_resolver()
        binding = build_project_space_binding(
            "proj-001", "guild-A", "ch-001", state=BindingState.ACTIVE
        )
        repo.insert(binding)
        # Same channel_id but different guild_id → no match
        result = resolver.resolve("guild-B", "ch-001")
        assert result is None


class TestRoutingResolverActiveChannel:
    def test_active_binding_resolves_to_routing_context(self) -> None:
        repo, resolver = _make_resolver()
        binding = build_project_space_binding(
            "proj-active-001",
            "guild-001",
            "ch-proj-001",
            default_recipient="project_manager",
            state=BindingState.ACTIVE,
        )
        repo.insert(binding)

        result = resolver.resolve("guild-001", "ch-proj-001")

        assert result is not None
        assert isinstance(result, RoutingContext)
        assert result.project_id == "proj-active-001"
        assert result.default_recipient == "project_manager"
        assert result.binding_state == BindingState.ACTIVE

    def test_active_binding_uses_custom_default_recipient(self) -> None:
        repo, resolver = _make_resolver()
        binding = build_project_space_binding(
            "proj-002",
            "guild-002",
            "ch-proj-002",
            default_recipient="domain_leader",
            state=BindingState.ACTIVE,
        )
        repo.insert(binding)

        result = resolver.resolve("guild-002", "ch-proj-002")

        assert result is not None
        assert result.default_recipient == "domain_leader"


class TestRoutingResolverInactiveStates:
    @pytest.mark.parametrize(
        "state",
        [
            BindingState.PROPOSED,
            BindingState.PENDING_APPROVAL,
            BindingState.ARCHIVED,
            BindingState.LOCKED,
        ],
    )
    def test_non_active_binding_returns_none(self, state: BindingState) -> None:
        repo, resolver = _make_resolver()
        binding = build_project_space_binding(
            f"proj-{state.value}", "guild-x", f"ch-{state.value}", state=state
        )
        repo.insert(binding)

        result = resolver.resolve("guild-x", f"ch-{state.value}")

        assert result is None, f"Expected None for state={state.value}, got {result}"


class TestBindingStateEnum:
    def test_all_states_present(self) -> None:
        states = {s.value for s in BindingState}
        assert states == {"proposed", "pending_approval", "active", "archived", "locked"}

    def test_active_is_the_only_routable_state(self) -> None:
        routable = [s for s in BindingState if s == BindingState.ACTIVE]
        assert len(routable) == 1


class TestLifecycleEvent:
    def test_lifecycle_event_carries_event_type(self) -> None:
        event = LifecycleEvent(event_type="activate")
        assert event.event_type == "activate"

    def test_lifecycle_event_is_frozen(self) -> None:
        event = LifecycleEvent(event_type="archive")
        with pytest.raises((AttributeError, TypeError)):
            event.event_type = "lock"  # type: ignore[misc]


class TestRoutingContextImmutability:
    def test_routing_context_is_frozen(self) -> None:
        ctx = RoutingContext(
            project_id="p1",
            default_recipient="project_manager",
            binding_state=BindingState.ACTIVE,
        )
        with pytest.raises((AttributeError, TypeError)):
            ctx.project_id = "p2"  # type: ignore[misc]
