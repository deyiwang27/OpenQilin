"""Add agent_id and window_index to conversation_messages.

Revision ID: 20260323_0016
Revises: 20260323_0015
Create Date: 2026-03-23
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "20260323_0016"
down_revision: Union[str, None] = "20260323_0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE conversation_messages ADD COLUMN IF NOT EXISTS agent_id TEXT")
    op.execute("ALTER TABLE conversation_messages ADD COLUMN IF NOT EXISTS window_index INTEGER")


def downgrade() -> None:
    op.execute("ALTER TABLE conversation_messages DROP COLUMN IF EXISTS agent_id")
    op.execute("ALTER TABLE conversation_messages DROP COLUMN IF EXISTS window_index")
