"""Create agents table for agent registry persistence.

Revision ID: 20260315_0003
Revises: 20260315_0002
Create Date: 2026-03-15
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260315_0003"
down_revision: Union[str, None] = "20260315_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create agents table for agent registry persistence."""

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS agents (
            agent_id    TEXT PRIMARY KEY,
            role        TEXT NOT NULL,
            agent_type  TEXT NOT NULL,
            status      TEXT NOT NULL,
            created_at  TIMESTAMPTZ NOT NULL,
            updated_at  TIMESTAMPTZ NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ix_agents_role
        ON agents (role)
        """
    )


def downgrade() -> None:
    """Drop agents table."""

    op.execute("DROP TABLE IF EXISTS agents")
