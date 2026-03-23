"""add summary_embedding to conversation_windows

Revision ID: 20260323_0017
Revises: 20260323_0016
Create Date: 2026-03-23 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "20260323_0017"
down_revision: Union[str, None] = "20260323_0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE conversation_windows ADD COLUMN IF NOT EXISTS summary_embedding vector(768)"
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_conversation_windows_embedding
        ON conversation_windows
        USING ivfflat (summary_embedding vector_cosine_ops)
        WITH (lists = 100)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_conversation_windows_embedding")
    op.execute("ALTER TABLE conversation_windows DROP COLUMN IF EXISTS summary_embedding")
