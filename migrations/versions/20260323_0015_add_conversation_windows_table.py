"""Add conversation_windows table for warm-tier summaries.

Revision ID: 20260323_0015
Revises: 20260322_0014
Create Date: 2026-03-23
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "20260323_0015"
down_revision: Union[str, None] = "20260322_0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS conversation_windows (
            id              SERIAL PRIMARY KEY,
            scope           TEXT NOT NULL,
            window_index    INTEGER NOT NULL,
            summary_text    TEXT NOT NULL,
            turn_start      INTEGER NOT NULL,
            turn_end        INTEGER NOT NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (scope, window_index)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_conversation_windows_scope
        ON conversation_windows (scope)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_conversation_windows_scope")
    op.execute("DROP TABLE IF EXISTS conversation_windows")
