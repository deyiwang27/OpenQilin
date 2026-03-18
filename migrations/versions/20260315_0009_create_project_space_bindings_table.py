"""Create project_space_bindings table for Discord channel-to-project binding.

Revision ID: 20260315_0009
Revises: 20260315_0008
Create Date: 2026-03-17

M13-WP3: maps Discord (guild_id, channel_id) → project context and default
routing recipient.  binding_state lifecycle: proposed → pending_approval →
active → archived → locked.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260315_0009"
down_revision: Union[str, None] = "20260315_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create project_space_bindings table."""

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS project_space_bindings (
            id                  TEXT PRIMARY KEY,
            project_id          TEXT NOT NULL,
            guild_id            TEXT NOT NULL,
            channel_id          TEXT NOT NULL,
            binding_state       TEXT NOT NULL DEFAULT 'proposed',
            default_recipient   TEXT NOT NULL DEFAULT 'project_manager',
            created_at          TIMESTAMPTZ NOT NULL,
            updated_at          TIMESTAMPTZ NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ix_project_space_bindings_guild_channel
        ON project_space_bindings (guild_id, channel_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_project_space_bindings_project_id
        ON project_space_bindings (project_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_project_space_bindings_state
        ON project_space_bindings (binding_state)
        """
    )


def downgrade() -> None:
    """Drop project_space_bindings table."""

    op.execute("DROP TABLE IF EXISTS project_space_bindings")
