"""M18-WP1 unit tests for Project Manager conversational advisory."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from openqilin.agents.project_manager.agent import ProjectManagerAgent
from openqilin.agents.shared.free_text_advisory import FreeTextAdvisoryRequest
from openqilin.observability.testing.stubs import InMemoryMetricRecorder
from openqilin.task_orchestrator.dispatch.llm_dispatch import ConversationTurn


def _served_response(text: str) -> SimpleNamespace:
    return SimpleNamespace(decision="served", generated_text=text)


def _denied_response() -> SimpleNamespace:
    return SimpleNamespace(decision="denied", generated_text=None)


def _request() -> FreeTextAdvisoryRequest:
    return FreeTextAdvisoryRequest(
        text="What should happen on an active project?",
        scope="guild::guild-1::channel::channel-1",
        guild_id="guild-1",
        channel_id="channel-1",
        addressed_agent="project_manager",
    )


def _make_agent(
    *,
    llm: MagicMock | None = None,
    conversation_store: MagicMock | None = None,
    metric_recorder: InMemoryMetricRecorder | None = None,
) -> ProjectManagerAgent:
    return ProjectManagerAgent(
        llm_gateway=llm or MagicMock(),
        artifact_writer=MagicMock(),
        data_access=MagicMock(),  # type: ignore[arg-type]
        domain_leader_agent=MagicMock(),
        task_dispatch_service=MagicMock(),
        project_artifact_repo=MagicMock(),
        conversation_store=conversation_store,  # type: ignore[arg-type]
        metric_recorder=metric_recorder,
        trace_id_factory=lambda: "trace-free-text",
    )


def test_handle_free_text_uses_history_persists_turns_and_increments_metric() -> None:
    llm = MagicMock()
    llm.complete.return_value = _served_response("PM advisory")
    conversation_store = MagicMock()
    conversation_store.list_turns.return_value = (
        ConversationTurn(role="user", content="previous question"),
        ConversationTurn(role="assistant", content="previous answer"),
    )
    recorder = InMemoryMetricRecorder()
    agent = _make_agent(
        llm=llm,
        conversation_store=conversation_store,
        metric_recorder=recorder,
    )

    response = agent.handle_free_text(_request())

    assert response.advisory_text == "PM advisory"
    conversation_store.append_turns.assert_called_once_with(
        "guild::guild-1::channel::channel-1",
        user_prompt="What should happen on an active project?",
        assistant_reply="PM advisory",
        agent_id="project_manager",
    )
    prompt = llm.complete.call_args.args[0].messages_or_prompt
    assert "Conversation so far:" in prompt
    assert recorder.get_counter_value("llm_calls_total", labels={"purpose": "pm_response"}) == 1


def test_handle_free_text_returns_fallback_on_denied_llm_response() -> None:
    llm = MagicMock()
    llm.complete.return_value = _denied_response()
    agent = _make_agent(llm=llm)

    response = agent.handle_free_text(_request())

    assert response.advisory_text.startswith("I'm the Project Manager agent.")
    assert "/oq ask project_manager <project> <question>" in response.advisory_text


def test_handle_free_text_continues_when_store_read_fails() -> None:
    llm = MagicMock()
    llm.complete.return_value = _served_response("PM advisory after read failure")
    conversation_store = MagicMock()
    conversation_store.list_turns.side_effect = RuntimeError("boom")
    agent = _make_agent(llm=llm, conversation_store=conversation_store)

    response = agent.handle_free_text(_request())

    assert response.advisory_text == "PM advisory after read failure"
    conversation_store.append_turns.assert_called_once()


def test_handle_free_text_continues_when_store_write_fails() -> None:
    llm = MagicMock()
    llm.complete.return_value = _served_response("PM advisory after write failure")
    conversation_store = MagicMock()
    conversation_store.list_turns.return_value = ()
    conversation_store.append_turns.side_effect = RuntimeError("boom")
    agent = _make_agent(llm=llm, conversation_store=conversation_store)

    response = agent.handle_free_text(_request())

    assert response.advisory_text == "PM advisory after write failure"
