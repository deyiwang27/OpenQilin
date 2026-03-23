from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import cast
from unittest.mock import MagicMock

from openqilin.data_access.repositories.postgres.conversation_store import PostgresConversationStore
from openqilin.llm_gateway.providers.base import LiteLLMProviderRequest, LiteLLMProviderResult
from openqilin.llm_gateway.service import LlmGatewayService
from openqilin.shared_kernel.config import RuntimeSettings
from openqilin.task_orchestrator.dispatch.llm_dispatch import (
    ConversationTurn,
    LlmDispatchRequest,
    LlmGatewayDispatchAdapter,
    LocalConversationStore,
)


class _StaticProvider:
    def complete(self, request: LiteLLMProviderRequest) -> LiteLLMProviderResult:
        return LiteLLMProviderResult(
            model_identifier=f"gemini/{request.model_alias}",
            content="runtime summary",
            input_tokens=16,
            output_tokens=12,
            provider_cost_usd=None,
            quota_limit_source="policy_guardrail",
        )


class _RowsResult:
    def __init__(self, rows: Sequence[object]) -> None:
        self._rows = list(rows)

    def fetchall(self) -> list[object]:
        return list(self._rows)

    def fetchone(self) -> object | None:
        return self._rows[0] if self._rows else None


def _build_mock_session_factory(
    *,
    rows: list[tuple[str, str]] | None = None,
) -> tuple[MagicMock, MagicMock]:
    session = MagicMock()
    session.execute.return_value.fetchall.return_value = [] if rows is None else rows
    session.execute.return_value.fetchone.return_value = (0,)
    session_cm = MagicMock()
    session_cm.__enter__.return_value = session
    session_cm.__exit__.return_value = False
    session_factory = MagicMock(return_value=session_cm)
    return session_factory, session


def _build_dispatch_request() -> LlmDispatchRequest:
    return LlmDispatchRequest(
        task_id="task-conversation-store",
        request_id="request-conversation-store",
        trace_id="trace-conversation-store",
        principal_id="owner_001",
        principal_role="owner",
        project_id="project_1",
        command="llm_summarize",
        args=("Project status?",),
        recipient_role="ceo",
        recipient_id="ceo_core",
        policy_version="policy-v1",
        policy_hash="policy-hash-v1",
        rule_ids=("rule-1",),
        conversation_guild_id="guild_1",
        conversation_channel_id="channel_1",
        conversation_thread_id=None,
    )


def test_postgres_conversation_store_list_turns_empty() -> None:
    session_factory, _ = _build_mock_session_factory(rows=[])
    store = PostgresConversationStore(session_factory=session_factory, max_turns=6)

    turns = store.list_turns("scope-1")

    assert turns == ()


def test_postgres_conversation_store_list_turns_returns_oldest_first() -> None:
    session_factory, session = _build_mock_session_factory(
        rows=[
            ("user", "first question"),
            ("assistant", "first answer"),
            ("user", "second question"),
            ("assistant", "second answer"),
        ]
    )
    store = PostgresConversationStore(session_factory=session_factory, max_turns=6)

    turns = store.list_turns("scope-1")

    assert turns == (
        ConversationTurn(role="user", content="first question"),
        ConversationTurn(role="assistant", content="first answer"),
        ConversationTurn(role="user", content="second question"),
        ConversationTurn(role="assistant", content="second answer"),
    )
    statement = str(session.execute.call_args.args[0])
    assert "ORDER BY created_at DESC" in statement
    assert "ORDER BY created_at ASC" in statement


def test_postgres_conversation_store_list_turns_caps_at_max_turns() -> None:
    session_factory, session = _build_mock_session_factory(rows=[])
    store = PostgresConversationStore(session_factory=session_factory, max_turns=4)

    store.list_turns("scope-1")

    execute_params = session.execute.call_args.args[1]
    statement = str(session.execute.call_args.args[0])
    assert "LIMIT :limit" in statement
    assert execute_params["limit"] == 4


def test_postgres_conversation_store_append_turns_inserts_two_rows() -> None:
    session_factory, session = _build_mock_session_factory()
    store = PostgresConversationStore(session_factory=session_factory, max_turns=6)

    store.append_turns("scope-1", user_prompt="  hello  ", assistant_reply="  hi  ")

    statement = str(session.execute.call_args_list[0].args[0])
    params = session.execute.call_args_list[0].args[1]
    assert "INSERT INTO conversation_messages" in statement
    assert "(id, conversation_id, role, content, agent_id, metadata, created_at)" in statement
    assert "(:id1, :scope, 'user', :user_content, :agent_id, '{}', :created_at1)" in statement
    assert (
        "(:id2, :scope, 'assistant', :assistant_content, :agent_id, '{}', :created_at2)"
        in statement
    )
    assert params["scope"] == "scope-1"
    assert params["user_content"] == "hello"
    assert params["assistant_content"] == "hi"
    assert params["agent_id"] is None
    assert isinstance(params["created_at1"], datetime)
    assert params["created_at1"].tzinfo == UTC
    assert params["created_at2"] == params["created_at1"]
    session.commit.assert_called_once()


def test_postgres_conversation_store_clear_deletes_scope_rows() -> None:
    session_factory, session = _build_mock_session_factory()
    store = PostgresConversationStore(session_factory=session_factory, max_turns=6)

    store.clear(" scope-1 ")

    statement = str(session.execute.call_args.args[0])
    params = session.execute.call_args.args[1]
    assert "DELETE FROM conversation_messages WHERE conversation_id = :scope" in statement
    assert params == {"scope": "scope-1"}
    session.commit.assert_called_once()


def test_llm_dispatch_adapter_uses_injected_conversation_store() -> None:
    conversation_store = MagicMock()
    conversation_store.list_turns.return_value = (
        ConversationTurn(role="user", content="prior context"),
    )
    adapter = LlmGatewayDispatchAdapter(
        llm_gateway_service=LlmGatewayService(provider=_StaticProvider()),
        settings=RuntimeSettings(llm_default_routing_profile="dev_gemini_free"),
        conversation_store=conversation_store,
    )
    payload = _build_dispatch_request()

    receipt = adapter.dispatch(payload)

    assert receipt.accepted is True
    expected_scope = "guild::guild_1::channel::channel_1"
    conversation_store.list_turns.assert_called_once_with(expected_scope)
    conversation_store.append_turns.assert_called_once()
    assert adapter._conversation_store is conversation_store


def test_llm_dispatch_adapter_falls_back_to_local_store_when_none() -> None:
    adapter = LlmGatewayDispatchAdapter(
        llm_gateway_service=LlmGatewayService(provider=_StaticProvider()),
        settings=RuntimeSettings(llm_default_routing_profile="dev_gemini_free"),
        conversation_store=None,
    )

    assert isinstance(adapter._conversation_store, LocalConversationStore)


def test_conversation_persistence_survives_store_recreation() -> None:
    rows: list[tuple[str, str, str, datetime]] = []
    session = MagicMock()

    def execute_side_effect(statement: object, params: dict[str, object]) -> _RowsResult:
        query = str(statement)
        if "INSERT INTO conversation_messages" in query:
            created_at1 = cast(datetime, params["created_at1"])
            created_at2 = cast(datetime, params["created_at2"])
            rows.append(("scope-1", "user", str(params["user_content"]), created_at1))
            rows.append(("scope-1", "assistant", str(params["assistant_content"]), created_at2))
            return _RowsResult([])
        if "SELECT role, content" in query:
            scope = str(params["scope"])
            limit = cast(int, params["limit"])
            scoped = [row for row in rows if row[0] == scope]
            scoped.sort(key=lambda row: row[3])
            result_rows = [(row[1], row[2]) for row in scoped][-limit:]
            return _RowsResult(result_rows)
        if "SELECT COUNT(*) FROM conversation_messages" in query:
            scope = str(params["scope"])
            scoped = [row for row in rows if row[0] == scope]
            return _RowsResult([(len(scoped),)])
        if "DELETE FROM conversation_windows" in query:
            return _RowsResult([])
        if "DELETE FROM conversation_messages" in query:
            scope = str(params["scope"])
            rows[:] = [row for row in rows if row[0] != scope]
            return _RowsResult([])
        return _RowsResult([])

    session.execute.side_effect = execute_side_effect
    session_cm = MagicMock()
    session_cm.__enter__.return_value = session
    session_cm.__exit__.return_value = False
    session_factory = MagicMock(return_value=session_cm)

    first_store = PostgresConversationStore(session_factory=session_factory, max_turns=6)
    first_store.append_turns(
        "scope-1", user_prompt="first question", assistant_reply="first answer"
    )

    recreated_store = PostgresConversationStore(session_factory=session_factory, max_turns=6)
    turns = recreated_store.list_turns("scope-1")

    assert turns == (
        ConversationTurn(role="user", content="first question"),
        ConversationTurn(role="assistant", content="first answer"),
    )
