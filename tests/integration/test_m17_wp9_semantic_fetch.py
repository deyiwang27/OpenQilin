"""M17-WP9 integration tests — semantic fetch and agent tool."""

from __future__ import annotations

from collections.abc import Generator
import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from openqilin.data_access.repositories.postgres.conversation_store import PostgresConversationStore
from openqilin.execution_sandbox.tools.contracts import ToolCallContext
from openqilin.execution_sandbox.tools.read_tools import GovernedReadToolService

pytestmark = pytest.mark.integration

_VECTOR_A = (1.0,) + (0.0,) * 767
_VECTOR_B = (0.0, 1.0) + (0.0,) * 766


class _StubEmbeddingService:
    def __init__(self, values_by_text: dict[str, tuple[float, ...]]) -> None:
        self._values_by_text = values_by_text

    def embed(self, text_value: str) -> tuple[float, ...] | None:
        return self._values_by_text.get(text_value)


@pytest.fixture
def session_factory() -> Generator[sessionmaker[Session], None, None]:
    db_url = os.getenv("OPENQILIN_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not db_url:
        pytest.skip("database url not configured")
    engine = create_engine(db_url, future=True)
    factory = sessionmaker(bind=engine, class_=Session, future=True)
    try:
        yield factory
    finally:
        engine.dispose()


@pytest.fixture
def read_tool_service(session_factory: sessionmaker[Session]) -> GovernedReadToolService:
    from openqilin.apps.api_app import app

    services = app.state.runtime_services
    return GovernedReadToolService(
        governance_repository=services.governance_repo,
        project_artifact_repository=services.project_artifact_repo,
        runtime_state_repository=services.runtime_state_repo,
        retrieval_query_service=services.retrieval_query_service,
        audit_writer=services.audit_writer,
        communication_repository=services.communication_repo,
        conversation_store=PostgresConversationStore(session_factory=session_factory),
    )


def _scope(prefix: str) -> str:
    return f"{prefix}-{uuid4()}"


def _insert_window(
    session_factory: sessionmaker[Session],
    *,
    scope: str,
    window_index: int,
    summary_text: str,
) -> None:
    with session_factory() as session:
        session.execute(
            text(
                """
                INSERT INTO conversation_windows
                    (scope, window_index, summary_text, turn_start, turn_end, created_at)
                VALUES
                    (:scope, :window_index, :summary_text, :turn_start, :turn_end, :created_at)
                """
            ),
            {
                "scope": scope,
                "window_index": window_index,
                "summary_text": summary_text,
                "turn_start": window_index * 40,
                "turn_end": (window_index * 40) + 39,
                "created_at": datetime.now(tz=UTC),
            },
        )
        session.commit()


def _insert_window_turns(
    session_factory: sessionmaker[Session],
    *,
    scope: str,
    window_index: int,
) -> None:
    now = datetime.now(tz=UTC)
    with session_factory() as session:
        session.execute(
            text(
                """
                INSERT INTO conversation_messages
                    (id, conversation_id, role, content, agent_id, metadata, created_at, window_index)
                VALUES
                    (:user_id, :scope, 'user', 'question', NULL, '{}'::jsonb, :created_at, :window_index),
                    (:assistant_id, :scope, 'assistant', 'answer', NULL, '{}'::jsonb, :created_at, :window_index)
                """
            ),
            {
                "user_id": str(uuid4()),
                "assistant_id": str(uuid4()),
                "scope": scope,
                "created_at": now,
                "window_index": window_index,
            },
        )
        session.commit()


def _tool_context() -> ToolCallContext:
    return ToolCallContext(
        task_id="task-conversation-window-001",
        request_id="request-conversation-window-001",
        trace_id="trace-conversation-window-001",
        principal_id="owner_001",
        principal_role="owner",
        recipient_role="ceo",
        recipient_id="ceo_core",
        project_id=None,
    )


def test_embed_and_store_window_populates_embedding(session_factory: sessionmaker[Session]) -> None:
    scope = _scope("semantic-embed")
    _insert_window(session_factory, scope=scope, window_index=0, summary_text="alpha")
    store = PostgresConversationStore(
        session_factory=session_factory,
        embedding_service=_StubEmbeddingService({"alpha": _VECTOR_A}),
    )

    store._embed_and_store_window(scope, 0, "alpha")

    with session_factory() as session:
        row = session.execute(
            text(
                """
                SELECT summary_embedding IS NOT NULL
                FROM conversation_windows
                WHERE scope = :scope AND window_index = 0
                """
            ),
            {"scope": scope},
        ).fetchone()
    assert row is not None
    assert row[0] is True


def test_find_relevant_windows_returns_above_threshold(
    session_factory: sessionmaker[Session],
) -> None:
    scope = _scope("semantic-match")
    _insert_window(session_factory, scope=scope, window_index=0, summary_text="alpha")
    _insert_window(session_factory, scope=scope, window_index=1, summary_text="beta")
    store = PostgresConversationStore(
        session_factory=session_factory,
        embedding_service=_StubEmbeddingService({"alpha": _VECTOR_A, "beta": _VECTOR_B}),
    )
    store._embed_and_store_window(scope, 0, "alpha")
    store._embed_and_store_window(scope, 1, "beta")

    windows = store.find_relevant_windows(scope, _VECTOR_A, threshold=0.75, limit=3)

    assert windows
    assert windows[0].window_index == 0
    assert windows[0].summary_text == "alpha"


def test_find_relevant_windows_excludes_below_threshold(
    session_factory: sessionmaker[Session],
) -> None:
    scope = _scope("semantic-threshold")
    _insert_window(session_factory, scope=scope, window_index=0, summary_text="beta")
    store = PostgresConversationStore(
        session_factory=session_factory,
        embedding_service=_StubEmbeddingService({"beta": _VECTOR_B}),
    )
    store._embed_and_store_window(scope, 0, "beta")

    windows = store.find_relevant_windows(scope, _VECTOR_A, threshold=0.75, limit=3)

    assert windows == ()


def test_find_relevant_windows_returns_empty_when_no_embeddings(
    session_factory: sessionmaker[Session],
) -> None:
    scope = _scope("semantic-none")
    _insert_window(session_factory, scope=scope, window_index=0, summary_text="alpha")
    store = PostgresConversationStore(session_factory=session_factory)

    assert store.find_relevant_windows(scope, _VECTOR_A) == ()


def test_fetch_channel_summary_returns_latest(session_factory: sessionmaker[Session]) -> None:
    scope = _scope("channel-latest")
    _insert_window(session_factory, scope=scope, window_index=0, summary_text="old summary")
    _insert_window(session_factory, scope=scope, window_index=2, summary_text="new summary")
    store = PostgresConversationStore(session_factory=session_factory)

    summary = store.fetch_channel_summary(scope)

    assert summary is not None
    assert summary.window_index == 2
    assert summary.summary_text == "new summary"
    assert summary.scope == scope


def test_fetch_channel_summary_returns_none_for_missing_scope(
    session_factory: sessionmaker[Session],
) -> None:
    store = PostgresConversationStore(session_factory=session_factory)

    assert store.fetch_channel_summary(_scope("missing")) is None


def test_get_conversation_window_tool_returns_turns(
    session_factory: sessionmaker[Session],
    read_tool_service: GovernedReadToolService,
) -> None:
    scope = _scope("tool-window")
    _insert_window_turns(session_factory, scope=scope, window_index=2)

    result = read_tool_service.call_tool(
        tool_name="get_conversation_window",
        arguments={"scope": scope, "window_index": 2},
        context=_tool_context(),
    )

    assert result.decision == "ok"
    assert result.data is not None
    assert result.data["scope"] == scope
    assert result.data["turn_count"] == 2


def test_get_conversation_window_tool_denies_missing_scope(
    read_tool_service: GovernedReadToolService,
) -> None:
    result = read_tool_service.call_tool(
        tool_name="get_conversation_window",
        arguments={"window_index": 2},
        context=_tool_context(),
    )

    assert result.decision == "denied"
    assert result.error_code == "tool_scope_missing"
