"""PostgreSQL-backed conversation turn store."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Callable
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from openqilin.task_orchestrator.dispatch.llm_dispatch import (
    ConversationTurn,
    ConversationWindowSummary,
)


class PostgresConversationStore:
    """Persistent conversation turn storage backed by PostgreSQL.

    Implements ConversationStoreProtocol for use inside LlmGatewayDispatchAdapter.

    Rows are stored one per message (two rows per exchange: user + assistant).
    ``list_turns`` returns at most ``max_turns`` rows, ordered oldest-first.

    When total turns for a scope reach a multiple of ``window_size``, the
    completed window is tagged with a ``window_index`` and summarized via the
    optional ``summarize_fn``. Summary failures are non-fatal.
    """

    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        max_turns: int = 40,
        window_size: int = 40,
        summarize_fn: Callable[[str, int, tuple[ConversationTurn, ...]], str] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._max_turns = max(2, max_turns)
        self._window_size = max(4, window_size)
        self._summarize_fn = summarize_fn

    def list_turns(self, scope: str) -> tuple[ConversationTurn, ...]:
        """Return the most recent ``max_turns`` turns for ``scope``, oldest first."""
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

    def append_turns(
        self,
        scope: str,
        *,
        user_prompt: str,
        assistant_reply: str,
        agent_id: str | None = None,
    ) -> None:
        """Insert a user + assistant turn pair for ``scope``.

        After inserting, checks if a window has completed and triggers
        summarization via ``summarize_fn`` if provided. Summary failure is
        non-fatal — the turn write is not rolled back.
        """
        normalized = scope.strip() or "default-scope"
        now = datetime.now(tz=UTC)
        with self._session_factory() as session:
            session.execute(
                text(
                    """
                    INSERT INTO conversation_messages
                        (id, conversation_id, role, content, agent_id, metadata, created_at)
                    VALUES
                        (:id1, :scope, 'user', :user_content, :agent_id, '{}', :created_at1),
                        (:id2, :scope, 'assistant', :assistant_content, :agent_id, '{}', :created_at2)
                    """
                ),
                {
                    "id1": str(uuid4()),
                    "id2": str(uuid4()),
                    "scope": normalized,
                    "user_content": user_prompt.strip(),
                    "assistant_content": assistant_reply.strip(),
                    "agent_id": agent_id,
                    "created_at1": now,
                    "created_at2": now,
                },
            )
            session.commit()
            # Check total row count; trigger window summarization if window fills.
            count_row = session.execute(
                text("SELECT COUNT(*) FROM conversation_messages WHERE conversation_id = :scope"),
                {"scope": normalized},
            ).fetchone()
        total = int(count_row[0]) if count_row else 0
        if total > 0 and total % self._window_size == 0:
            completed_window_index = (total // self._window_size) - 1
            self._close_window(normalized, completed_window_index, total)

    def list_windows(self, scope: str) -> tuple[ConversationWindowSummary, ...]:
        """Return all closed window summaries for ``scope``, oldest first."""
        normalized = scope.strip() or "default-scope"
        with self._session_factory() as session:
            rows = session.execute(
                text(
                    """
                    SELECT window_index, summary_text
                    FROM conversation_windows
                    WHERE scope = :scope
                    ORDER BY window_index ASC
                    LIMIT :limit
                    """
                ),
                {"scope": normalized, "limit": 10},
            ).fetchall()
        return tuple(
            ConversationWindowSummary(window_index=row[0], summary_text=row[1]) for row in rows
        )

    def fetch_window(self, scope: str, window_index: int) -> tuple[ConversationTurn, ...]:
        """Return raw turns for a specific closed window, oldest first."""
        normalized = scope.strip() or "default-scope"
        with self._session_factory() as session:
            rows = session.execute(
                text(
                    """
                    SELECT role, content
                    FROM conversation_messages
                    WHERE conversation_id = :scope
                      AND window_index = :window_index
                    ORDER BY created_at ASC
                    """
                ),
                {"scope": normalized, "window_index": window_index},
            ).fetchall()
        return tuple(ConversationTurn(role=row[0], content=row[1]) for row in rows)

    def clear(self, scope: str) -> None:
        """Delete all stored turns and window summaries for ``scope``."""
        normalized = scope.strip() or "default-scope"
        with self._session_factory() as session:
            session.execute(
                text("DELETE FROM conversation_windows WHERE scope = :scope"),
                {"scope": normalized},
            )
            session.execute(
                text("DELETE FROM conversation_messages WHERE conversation_id = :scope"),
                {"scope": normalized},
            )
            session.commit()

    def _close_window(self, scope: str, window_index: int, total_rows: int) -> None:
        """Tag completed window rows and generate summary. Non-fatal on failure."""
        turn_start = window_index * self._window_size
        turn_end = turn_start + self._window_size - 1
        try:
            with self._session_factory() as session:
                # Tag rows in this window with window_index using row ordering.
                session.execute(
                    text(
                        """
                        UPDATE conversation_messages
                        SET window_index = :window_index
                        WHERE conversation_id = :scope
                          AND window_index IS NULL
                          AND ctid IN (
                              SELECT ctid FROM conversation_messages
                              WHERE conversation_id = :scope
                                AND window_index IS NULL
                              ORDER BY created_at ASC
                              LIMIT :window_size
                          )
                        """
                    ),
                    {
                        "scope": scope,
                        "window_index": window_index,
                        "window_size": self._window_size,
                    },
                )
                session.commit()
        except Exception:
            return  # Non-fatal: window tagging failure does not block responses.

        if self._summarize_fn is None:
            return

        try:
            window_turns = self.fetch_window(scope, window_index)
            if not window_turns:
                return
            summary_text = self._summarize_fn(scope, window_index, window_turns)
            if not summary_text.strip():
                return
            with self._session_factory() as session:
                session.execute(
                    text(
                        """
                        INSERT INTO conversation_windows
                            (scope, window_index, summary_text, turn_start, turn_end, created_at)
                        VALUES
                            (:scope, :window_index, :summary_text, :turn_start, :turn_end, :now)
                        ON CONFLICT (scope, window_index) DO NOTHING
                        """
                    ),
                    {
                        "scope": scope,
                        "window_index": window_index,
                        "summary_text": summary_text.strip(),
                        "turn_start": turn_start,
                        "turn_end": turn_end,
                        "now": datetime.now(tz=UTC),
                    },
                )
                session.commit()
        except Exception:
            pass  # Non-fatal: summary failure does not block responses.
