"""Create identity_channels table for connector actor/channel mapping persistence.

Revision ID: 20260315_0005
Revises: 20260315_0004
Create Date: 2026-03-15
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260315_0005"
down_revision: Union[str, None] = "20260315_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create identity_channels table for connector identity/channel mapping persistence."""

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS identity_channels (
            mapping_id          TEXT PRIMARY KEY,
            connector           TEXT NOT NULL,
            actor_external_id   TEXT NOT NULL,
            guild_id            TEXT NOT NULL,
            channel_id          TEXT NOT NULL,
            channel_type        TEXT NOT NULL,
            status              TEXT NOT NULL DEFAULT 'pending',
            created_at          TIMESTAMPTZ NOT NULL,
            updated_at          TIMESTAMPTZ NOT NULL,
            UNIQUE (connector, actor_external_id, guild_id, channel_id, channel_type)
        )
        """
    )


def downgrade() -> None:
    """Drop identity_channels table."""

    op.execute("DROP TABLE IF EXISTS identity_channels")
