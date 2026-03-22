"""Create conversation_messages table.

Revision ID: 20260322_0014
Revises: 20260319_0013
Create Date: 2026-03-22
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "20260322_0014"
down_revision: Union[str, None] = "20260319_0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS conversation_messages (
            id              TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            role            TEXT NOT NULL,
            content         TEXT NOT NULL,
            metadata        JSONB NOT NULL DEFAULT '{}',
            created_at      TIMESTAMPTZ NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_conversation_messages_conversation_id_created_at
        ON conversation_messages (conversation_id, created_at)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_conversation_messages_conversation_id_created_at")
    op.execute("DROP TABLE IF EXISTS conversation_messages")
