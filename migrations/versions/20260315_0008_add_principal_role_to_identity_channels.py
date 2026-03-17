"""Add principal_role column to identity_channels for DB-backed role resolution.

Revision ID: 20260315_0008
Revises: 20260315_0007
Create Date: 2026-03-15

C-6 fix: role is now stored in the identity record at verification time rather
than trusted from an inbound HTTP header.  Existing rows default to 'owner'.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260315_0008"
down_revision: Union[str, None] = "20260315_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add principal_role column to identity_channels table."""

    op.execute(
        """
        ALTER TABLE identity_channels
        ADD COLUMN IF NOT EXISTS principal_role TEXT NOT NULL DEFAULT 'owner'
        """
    )


def downgrade() -> None:
    """Drop principal_role column from identity_channels table."""

    op.execute("ALTER TABLE identity_channels DROP COLUMN IF EXISTS principal_role")
