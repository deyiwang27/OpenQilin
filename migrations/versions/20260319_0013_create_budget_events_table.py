"""Create budget_events table.

Revision ID: 20260319_0013
Revises: 20260319_0012
Create Date: 2026-03-19
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "20260319_0013"
down_revision: Union[str, None] = "20260319_0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS budget_events (
            id              TEXT PRIMARY KEY,
            task_id         TEXT NOT NULL,
            project_id      TEXT NOT NULL,
            role            TEXT NOT NULL DEFAULT '',
            model_class     TEXT NOT NULL DEFAULT '',
            actual_tokens   BIGINT NOT NULL DEFAULT 0,
            actual_cost_usd NUMERIC(12, 6) NOT NULL DEFAULT 0,
            created_at      TIMESTAMPTZ NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_budget_events_project_id
        ON budget_events (project_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_budget_events_task_id
        ON budget_events (task_id)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS budget_events")
