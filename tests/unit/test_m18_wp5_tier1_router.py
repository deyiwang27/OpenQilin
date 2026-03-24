"""M18-WP5 unit tests for Tier 1 deterministic advisory routing."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock, patch

from openqilin.control_plane.advisory.topic_router import RoutingDecision
from openqilin.control_plane.grammar.models import IntentClass
from openqilin.control_plane.routers.discord_ingress import submit_discord_message
from openqilin.control_plane.schemas.discord_ingress import DiscordIngressRequest
from openqilin.control_plane.schemas.owner_commands import OwnerCommandRecipient


def _payload() -> DiscordIngressRequest:
    return DiscordIngressRequest(
        trace_id="trace-1",
        external_message_id="discord-message-1",
        actor_external_id="owner-1",
        actor_role="owner",
        idempotency_key="idem-key-12345678",
        raw_payload_hash="a" * 64,
        timestamp=datetime(2026, 3, 23, 10, 0, 0, tzinfo=UTC),
        content="what is my budget status?",
        action="ask",
        target="sandbox",
        args=["what is my budget status?"],
        recipients=[OwnerCommandRecipient(recipient_type="runtime", recipient_id="runtime")],
        guild_id="guild-1",
        channel_id="channel-1",
        channel_type="text",
        chat_class="leadership_council",
        bot_role="secretary",
        bot_id="secretary_core",
        bot_user_id="secretary_user",
        is_everyone_mention=False,
    )


def _router_kwargs() -> dict[str, Any]:
    return {
        "request": MagicMock(),
        "admission_service": MagicMock(),
        "policy_runtime_client": MagicMock(),
        "budget_reservation_service": MagicMock(),
        "runtime_state_repo": MagicMock(),
        "task_dispatch_service": MagicMock(),
        "tracer": MagicMock(),
        "audit_writer": MagicMock(),
        "metric_recorder": MagicMock(),
        "governance_repository": MagicMock(),
        "identity_channel_repository": MagicMock(),
        "binding_service": MagicMock(),
        "grammar_classifier": MagicMock(classify=MagicMock(return_value=IntentClass.DISCUSSION)),
        "grammar_parser": MagicMock(),
        "grammar_router": MagicMock(
            resolve=MagicMock(return_value=SimpleNamespace(target_role="secretary"))
        ),
        "secretary_agent": MagicMock(
            handle=MagicMock(
                return_value=SimpleNamespace(
                    advisory_text="Secretary advisory",
                    routing_suggestion=None,
                )
            )
        ),
        "project_manager_agent": MagicMock(),
        "cso_agent": MagicMock(),
        "ceo_agent": MagicMock(),
        "cwo_agent": MagicMock(),
        "auditor_agent": MagicMock(),
        "administrator_agent": MagicMock(),
        "routing_resolver": MagicMock(resolve=MagicMock(return_value=None)),
        "advisory_topic_router": MagicMock(classify=MagicMock(return_value=None)),
        "bot_registry_reader": MagicMock(get_mention=MagicMock(return_value=None)),
        "x_openqilin_signature": "sha256=test",
    }


def test_tier1_routes_to_auditor_non_project() -> None:
    kwargs = _router_kwargs()
    kwargs["advisory_topic_router"] = MagicMock(
        classify=MagicMock(
            return_value=RoutingDecision("auditor", "high", matched_keywords=["budget"])
        )
    )
    auditor_agent = MagicMock(
        handle_free_text=MagicMock(return_value=SimpleNamespace(advisory_text="Auditor advisory"))
    )
    kwargs["auditor_agent"] = auditor_agent

    with patch(
        "openqilin.control_plane.routers.discord_ingress._validate_discord_connector_request",
        return_value=None,
    ):
        response = cast(Any, submit_discord_message)(payload=_payload(), **kwargs)

    assert response.data.command == "ask"
    assert response.data.llm_execution == {"advisory_response": "Auditor advisory"}
    advisory_request = auditor_agent.handle_free_text.call_args.args[0]
    assert advisory_request.text == "what is my budget status?"


def test_tier1_routes_to_cso_non_project() -> None:
    kwargs = _router_kwargs()
    kwargs["advisory_topic_router"] = MagicMock(
        classify=MagicMock(
            return_value=RoutingDecision("cso", "high", matched_keywords=["strategy"])
        )
    )
    kwargs["cso_agent"] = MagicMock(
        handle_free_text=MagicMock(return_value=SimpleNamespace(advisory_text="CSO advisory"))
    )
    payload = _payload()
    payload = payload.model_copy(update={"content": "portfolio alignment review"})

    with patch(
        "openqilin.control_plane.routers.discord_ingress._validate_discord_connector_request",
        return_value=None,
    ):
        response = cast(Any, submit_discord_message)(payload=payload, **kwargs)

    assert response.data.command == "ask"
    assert response.data.llm_execution == {"advisory_response": "CSO advisory"}
    cast(Any, kwargs["cso_agent"]).handle_free_text.assert_called_once()


def test_tier1_restricted_role_project_channel() -> None:
    kwargs = _router_kwargs()
    kwargs["advisory_topic_router"] = MagicMock(
        classify=MagicMock(
            return_value=RoutingDecision("auditor", "high", matched_keywords=["budget"])
        )
    )
    kwargs["routing_resolver"] = MagicMock(
        resolve=MagicMock(return_value=SimpleNamespace(project_id="proj-1"))
    )

    with patch(
        "openqilin.control_plane.routers.discord_ingress._validate_discord_connector_request",
        return_value=None,
    ):
        response = cast(Any, submit_discord_message)(payload=_payload(), **kwargs)

    assert "not available in project channels" in response.data.llm_execution["advisory_response"]
    assert "/oq ask auditor <your question>" in response.data.llm_execution["advisory_response"]
    cast(Any, kwargs["auditor_agent"]).handle_free_text.assert_not_called()


def test_tier1_referral_includes_mention() -> None:
    kwargs = _router_kwargs()
    kwargs["advisory_topic_router"] = MagicMock(
        classify=MagicMock(
            return_value=RoutingDecision("auditor", "high", matched_keywords=["budget"])
        )
    )
    kwargs["routing_resolver"] = MagicMock(
        resolve=MagicMock(return_value=SimpleNamespace(project_id="proj-1"))
    )
    kwargs["bot_registry_reader"] = MagicMock(get_mention=MagicMock(return_value="<@123>"))

    with patch(
        "openqilin.control_plane.routers.discord_ingress._validate_discord_connector_request",
        return_value=None,
    ):
        response = cast(Any, submit_discord_message)(payload=_payload(), **kwargs)

    assert "<@123>" in response.data.llm_execution["advisory_response"]


def test_tier1_no_match_falls_through() -> None:
    kwargs = _router_kwargs()

    with patch(
        "openqilin.control_plane.routers.discord_ingress._validate_discord_connector_request",
        return_value=None,
    ):
        response = cast(Any, submit_discord_message)(payload=_payload(), **kwargs)

    assert response.data.dispatch_target == "secretary"
    cast(Any, kwargs["secretary_agent"]).handle.assert_called_once()


def test_tier1_agent_exception_falls_through() -> None:
    kwargs = _router_kwargs()
    kwargs["advisory_topic_router"] = MagicMock(
        classify=MagicMock(
            return_value=RoutingDecision("auditor", "high", matched_keywords=["budget"])
        )
    )
    kwargs["auditor_agent"] = MagicMock(
        handle_free_text=MagicMock(side_effect=RuntimeError("boom"))
    )

    with patch(
        "openqilin.control_plane.routers.discord_ingress._validate_discord_connector_request",
        return_value=None,
    ):
        response = cast(Any, submit_discord_message)(payload=_payload(), **kwargs)

    assert response.data.dispatch_target == "secretary"
    cast(Any, kwargs["secretary_agent"]).handle.assert_called_once()


def test_tier1_router_none_falls_through() -> None:
    kwargs = _router_kwargs()
    kwargs["advisory_topic_router"] = None

    with patch(
        "openqilin.control_plane.routers.discord_ingress._validate_discord_connector_request",
        return_value=None,
    ):
        response = cast(Any, submit_discord_message)(payload=_payload(), **kwargs)

    assert response.data.dispatch_target == "secretary"
    cast(Any, kwargs["secretary_agent"]).handle.assert_called_once()
