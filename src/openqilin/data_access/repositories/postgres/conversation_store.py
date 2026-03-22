"""PostgreSQL-backed conversation turn store."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from openqilin.task_orchestrator.dispatch.llm_dispatch import ConversationTurn


class PostgresConversationStore:
    """Persistent conversation turn storage backed by PostgreSQL.

    Implements the same interface as ``LocalConversationStore`` so it is a
    drop-in replacement inside ``LlmGatewayDispatchAdapter``.

    Rows are stored one per message (two rows per exchange: user + assistant).
    ``list_turns`` returns at most ``max_turns`` rows, ordered oldest-first,
    so the prompt builder receives chronological history.
    """

    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        max_turns: int = 6,
    ) -> None:
        self._session_factory = session_factory
        self._max_turns = max(2, max_turns)

    def list_turns(self, scope: str) -> tuple[ConversationTurn, ...]:
        """Return the most recent ``max_turns`` turns for ``scope``, oldest first.

        Returns an empty tuple when no history exists.
        """
        normalized = scope.strip() or "default-scope"
        with self._session_factory() as session:
            rows = session.execute(
                text(
                    """
                    SELECT role, content
                    FROM (
                        SELECT role, content, created_at
                        FROM conversation_messages
                        WHERE conversation_id = :scope
                        ORDER BY created_at DESC
                        LIMIT :limit
                    ) sub
                    ORDER BY created_at ASC
                    """
                ),
                {"scope": normalized, "limit": self._max_turns},
            ).fetchall()
        return tuple(ConversationTurn(role=row[0], content=row[1]) for row in rows)

    def append_turns(self, scope: str, *, user_prompt: str, assistant_reply: str) -> None:
        """Insert a user + assistant turn pair for ``scope``.

        Inserts two rows atomically. If the DB write fails, the error propagates
        to the caller — do not swallow exceptions.
        """
        normalized = scope.strip() or "default-scope"
        now = datetime.now(tz=UTC)
        with self._session_factory() as session:
            session.execute(
                text(
                    """
                    INSERT INTO conversation_messages (id, conversation_id, role, content, metadata, created_at)
                    VALUES (:id1, :scope, 'user', :user_content, '{}', :created_at1),
                           (:id2, :scope, 'assistant', :assistant_content, '{}', :created_at2)
                    """
                ),
                {
                    "id1": str(uuid4()),
                    "id2": str(uuid4()),
                    "scope": normalized,
                    "user_content": user_prompt.strip(),
                    "assistant_content": assistant_reply.strip(),
                    "created_at1": now,
                    "created_at2": now,
                },
            )
            session.commit()

    def clear(self, scope: str) -> None:
        """Delete all stored turns for ``scope``."""
        normalized = scope.strip() or "default-scope"
        with self._session_factory() as session:
            session.execute(
                text("DELETE FROM conversation_messages WHERE conversation_id = :scope"),
                {"scope": normalized},
            )
            session.commit()
