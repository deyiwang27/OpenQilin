"""Create budget_reservations table.

Revision ID: 20260319_0012
Revises: 20260319_0011
Create Date: 2026-03-19
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "20260319_0012"
down_revision: Union[str, None] = "20260319_0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS budget_reservations (
            id              TEXT PRIMARY KEY,
            task_id         TEXT NOT NULL,
            project_id      TEXT NOT NULL,
            reserved_usd    NUMERIC(12, 6) NOT NULL DEFAULT 0,
            reserved_tokens BIGINT NOT NULL DEFAULT 0,
            status          TEXT NOT NULL DEFAULT 'reserved',
            created_at      TIMESTAMPTZ NOT NULL,
            settled_at      TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_budget_reservations_project_status
        ON budget_reservations (project_id, status)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_budget_reservations_task_id
        ON budget_reservations (task_id)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS budget_reservations")
