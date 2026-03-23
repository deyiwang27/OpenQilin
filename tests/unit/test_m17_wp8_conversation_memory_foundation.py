from __future__ import annotations

from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock

from openqilin.agents.secretary.agent import SecretaryAgent
from openqilin.agents.secretary.models import SecretaryRequest
from openqilin.control_plane.grammar.models import ChatContext, IntentClass
from openqilin.data_access.repositories.postgres.conversation_store import PostgresConversationStore
from openqilin.llm_gateway.service import LlmGatewayService
from openqilin.task_orchestrator.dispatch.llm_dispatch import (
    ConversationTurn,
    ConversationWindowSummary,
    LlmDispatchRequest,
    LlmGatewayDispatchAdapter,
    LocalConversationStore,
    _compose_role_locked_prompt,
)


class _RowsResult:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def fetchall(self) -> list[object]:
        return list(self._rows)

    def fetchone(self) -> object | None:
        return self._rows[0] if self._rows else None


class _CountResult:
    def __init__(self, count: int) -> None:
        self._count = count

    def fetchone(self) -> tuple[int]:
        return (self._count,)


def _build_session_factory() -> tuple[MagicMock, MagicMock]:
    session = MagicMock()
    session_cm = MagicMock()
    session_cm.__enter__.return_value = session
    session_cm.__exit__.return_value = False
    session_factory = MagicMock(return_value=session_cm)
    return session_factory, session


def _build_dispatch_request(
    *,
    guild_id: str | None = "guild_1",
    channel_id: str | None = "channel_1",
    recipient_role: str = "ceo",
    recipient_id: str = "ceo_core",
) -> LlmDispatchRequest:
    return LlmDispatchRequest(
        task_id="task-memory-foundation",
        request_id="request-memory-foundation",
        trace_id="trace-memory-foundation",
        principal_id="owner_001",
        principal_role="owner",
        project_id="project_1",
        command="llm_summarize",
        args=("status?",),
        recipient_role=recipient_role,
        recipient_id=recipient_id,
        policy_version="policy-v1",
        policy_hash="policy-hash-v1",
        rule_ids=("rule-1",),
        conversation_guild_id=guild_id,
        conversation_channel_id=channel_id,
        conversation_thread_id=None,
    )


def test_unified_scope_drops_role_and_agent_id() -> None:
    payload = _build_dispatch_request(
        guild_id="guild_1",
        channel_id="channel_1",
        recipient_role="ceo",
        recipient_id="ceo_core",
    )

    scope = LlmGatewayDispatchAdapter._conversation_scope(payload)

    assert scope == "guild::guild_1::channel::channel_1"


def test_unified_scope_uses_fallback_when_guild_missing() -> None:
    payload = _build_dispatch_request(guild_id=None, channel_id="channel_1")

    scope = LlmGatewayDispatchAdapter._conversation_scope(payload)

    assert scope == "guild::guild-unspecified::channel::channel_1"


def test_secretary_scope_matches_async_scope_same_channel() -> None:
    payload = _build_dispatch_request(guild_id="g1", channel_id="c1")
    async_scope = LlmGatewayDispatchAdapter._conversation_scope(payload)

    llm = MagicMock()
    llm.complete.return_value = SimpleNamespace(decision="served", generated_text="advisory")
    conversation_store = MagicMock()
    conversation_store.list_turns.return_value = ()
    agent = SecretaryAgent(
        llm_gateway=cast(LlmGatewayService, llm),
        conversation_store=conversation_store,
    )
    req = SecretaryRequest(
        message="hello",
        intent=IntentClass.DISCUSSION,
        context=ChatContext(chat_class="governance", channel_id="c1", project_id=None),
        trace_id="trace-1",
        guild_id="g1",
        channel_id="c1",
    )

    agent.handle(req)

    conversation_store.list_turns.assert_called_once_with(async_scope)
    conversation_store.append_turns.assert_called_once_with(
        async_scope,
        user_prompt="hello",
        assistant_reply="advisory",
    )


def test_postgres_store_default_max_turns_is_40() -> None:
    session_factory, _ = _build_session_factory()

    store = PostgresConversationStore(session_factory=session_factory)

    assert store._max_turns == 40


def test_append_turns_writes_agent_id_column() -> None:
    session_factory, session = _build_session_factory()
    session.execute.side_effect = [MagicMock(), _CountResult(39)]
    store = PostgresConversationStore(session_factory=session_factory)

    store.append_turns(
        "scope-1",
        user_prompt="hello",
        assistant_reply="hi",
        agent_id="ceo_core",
    )

    statement = str(session.execute.call_args_list[0].args[0])
    params = session.execute.call_args_list[0].args[1]
    assert ":agent_id" in statement
    assert params["agent_id"] == "ceo_core"


def test_no_window_close_below_threshold() -> None:
    session_factory, session = _build_session_factory()
    session.execute.side_effect = [MagicMock(), _CountResult(39)]
    store = PostgresConversationStore(session_factory=session_factory, window_size=40)
    store._close_window = MagicMock()  # type: ignore[method-assign]

    store.append_turns("scope-1", user_prompt="hello", assistant_reply="hi")

    store._close_window.assert_not_called()


def test_window_close_triggered_at_threshold() -> None:
    session_factory, session = _build_session_factory()
    session.execute.side_effect = [MagicMock(), _CountResult(40)]
    store = PostgresConversationStore(session_factory=session_factory, window_size=40)
    store._close_window = MagicMock()  # type: ignore[method-assign]

    store.append_turns("scope-1", user_prompt="hello", assistant_reply="hi")

    store._close_window.assert_called_once_with("scope-1", 0, 40)


def test_summarize_fn_called_on_window_close() -> None:
    session_factory, _ = _build_session_factory()
    summarize_fn = MagicMock(return_value="summary text")
    store = PostgresConversationStore(
        session_factory=session_factory,
        summarize_fn=summarize_fn,
    )
    turns = (
        ConversationTurn(role="user", content="u1"),
        ConversationTurn(role="assistant", content="a1"),
    )
    store.fetch_window = MagicMock(return_value=turns)  # type: ignore[method-assign]

    store._close_window("scope-1", 0, 40)

    summarize_fn.assert_called_once_with("scope-1", 0, turns)


def test_summarize_fn_failure_is_nonfatal() -> None:
    session_factory, session = _build_session_factory()
    session.execute.side_effect = [MagicMock(), _CountResult(40), MagicMock()]
    summarize_fn = MagicMock(side_effect=RuntimeError("summary-failed"))
    store = PostgresConversationStore(
        session_factory=session_factory,
        window_size=40,
        summarize_fn=summarize_fn,
    )
    store.fetch_window = MagicMock(  # type: ignore[method-assign]
        return_value=(ConversationTurn(role="user", content="u1"),)
    )

    store.append_turns("scope-1", user_prompt="hello", assistant_reply="hi")


def test_list_windows_returns_oldest_first() -> None:
    session_factory, session = _build_session_factory()
    session.execute.return_value = _RowsResult(
        [
            (0, "window zero summary"),
            (1, "window one summary"),
        ]
    )
    store = PostgresConversationStore(session_factory=session_factory)

    windows = store.list_windows("scope-1")

    assert windows == (
        ConversationWindowSummary(window_index=0, summary_text="window zero summary"),
        ConversationWindowSummary(window_index=1, summary_text="window one summary"),
    )


def test_list_windows_empty_when_no_summaries() -> None:
    session_factory, session = _build_session_factory()
    session.execute.return_value = _RowsResult([])
    store = PostgresConversationStore(session_factory=session_factory)

    windows = store.list_windows("scope-1")

    assert windows == ()


def test_fetch_window_returns_turns_for_window_index() -> None:
    session_factory, session = _build_session_factory()
    session.execute.return_value = _RowsResult(
        [
            ("user", "question"),
            ("assistant", "answer"),
        ]
    )
    store = PostgresConversationStore(session_factory=session_factory)

    turns = store.fetch_window("scope-1", 1)

    assert turns == (
        ConversationTurn(role="user", content="question"),
        ConversationTurn(role="assistant", content="answer"),
    )


def test_warm_summaries_appear_before_hot_history_in_prompt() -> None:
    prompt = _compose_role_locked_prompt(
        recipient_role="ceo",
        history=(
            ConversationTurn(role="user", content="latest user"),
            ConversationTurn(role="assistant", content="latest assistant"),
        ),
        warm_summaries=(
            ConversationWindowSummary(window_index=0, summary_text="earliest summary"),
            ConversationWindowSummary(window_index=1, summary_text="later summary"),
        ),
        user_prompt="what now?",
        grounding_evidence=(),
    )

    assert "Previous conversation context (summaries of earlier discussion):" in prompt
    assert "Recent conversation:" in prompt
    assert prompt.index("Previous conversation context") < prompt.index("Recent conversation:")


def test_warm_block_omitted_when_no_summaries() -> None:
    prompt = _compose_role_locked_prompt(
        recipient_role="ceo",
        history=(ConversationTurn(role="user", content="latest user"),),
        warm_summaries=(),
        user_prompt="what now?",
        grounding_evidence=(),
    )

    assert "Previous conversation context (summaries of earlier discussion):" not in prompt


def test_local_store_list_windows_returns_empty() -> None:
    store = LocalConversationStore(max_turns=40)

    assert store.list_windows("any") == ()


def test_local_store_append_turns_accepts_agent_id_kwarg() -> None:
    store = LocalConversationStore(max_turns=40)

    store.append_turns(
        "scope-1",
        user_prompt="hello",
        assistant_reply="hi",
        agent_id="x",
    )

    assert len(store.list_turns("scope-1")) == 2


def test_clear_also_deletes_windows() -> None:
    session_factory, session = _build_session_factory()
    store = PostgresConversationStore(session_factory=session_factory)

    store.clear("scope-1")

    first_statement = str(session.execute.call_args_list[0].args[0])
    second_statement = str(session.execute.call_args_list[1].args[0])
    assert "DELETE FROM conversation_windows" in first_statement
    assert "DELETE FROM conversation_messages" in second_statement
