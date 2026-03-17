"""Create artifacts, messages, and dead_letters tables for governance artifact persistence.

Revision ID: 20260315_0007
Revises: 20260315_0006
Create Date: 2026-03-15
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260315_0007"
down_revision: Union[str, None] = "20260315_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create artifacts, messages, and dead_letters tables."""

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS artifacts (
            artifact_id     TEXT PRIMARY KEY,
            project_id      TEXT NOT NULL,
            artifact_type   TEXT NOT NULL,
            revision_no     INTEGER NOT NULL,
            storage_uri     TEXT NOT NULL,
            content_hash    TEXT NOT NULL,
            content         TEXT NOT NULL DEFAULT '',
            byte_size       INTEGER NOT NULL,
            created_at      TIMESTAMPTZ NOT NULL,
            UNIQUE (project_id, artifact_type, revision_no)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_artifacts_project_type
        ON artifacts (project_id, artifact_type)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            ledger_id           TEXT PRIMARY KEY,
            task_id             TEXT NOT NULL,
            trace_id            TEXT NOT NULL,
            message_id          TEXT NOT NULL,
            external_message_id TEXT NOT NULL,
            connector           TEXT NOT NULL,
            command             TEXT NOT NULL,
            target              TEXT NOT NULL,
            route_key           TEXT NOT NULL,
            endpoint            TEXT NOT NULL,
            attempt             INTEGER NOT NULL DEFAULT 0,
            state               TEXT NOT NULL,
            dispatch_id         TEXT,
            delivery_id         TEXT,
            retryable           BOOLEAN,
            error_code          TEXT,
            error_message       TEXT,
            transitions         JSONB NOT NULL DEFAULT '[]',
            created_at          TIMESTAMPTZ NOT NULL,
            updated_at          TIMESTAMPTZ NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_messages_task_id
        ON messages (task_id)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS dead_letters (
            dead_letter_id      TEXT PRIMARY KEY,
            task_id             TEXT NOT NULL,
            trace_id            TEXT NOT NULL,
            principal_id        TEXT NOT NULL,
            idempotency_key     TEXT NOT NULL,
            message_id          TEXT NOT NULL,
            external_message_id TEXT NOT NULL,
            connector           TEXT NOT NULL,
            command             TEXT NOT NULL,
            target              TEXT NOT NULL,
            route_key           TEXT NOT NULL,
            endpoint            TEXT NOT NULL,
            error_code          TEXT NOT NULL,
            error_message       TEXT NOT NULL,
            attempts            INTEGER NOT NULL,
            ledger_id           TEXT,
            created_at          TIMESTAMPTZ NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_dead_letters_task_id
        ON dead_letters (task_id)
        """
    )


def downgrade() -> None:
    """Drop artifacts, messages, and dead_letters tables."""

    op.execute("DROP TABLE IF EXISTS dead_letters")
    op.execute("DROP TABLE IF EXISTS messages")
    op.execute("DROP TABLE IF EXISTS artifacts")
