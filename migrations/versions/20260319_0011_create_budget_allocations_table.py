"""Create budget_allocations table.

Revision ID: 20260319_0011
Revises: 20260318_0010
Create Date: 2026-03-19
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "20260319_0011"
down_revision: Union[str, None] = "20260318_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS budget_allocations (
            id                  TEXT PRIMARY KEY,
            project_id          TEXT NOT NULL,
            currency_limit_usd  NUMERIC(12, 6) NOT NULL DEFAULT 10.000000,
            quota_limit_tokens  BIGINT NOT NULL DEFAULT 500000,
            window_type         TEXT NOT NULL DEFAULT 'per_project',
            created_at          TIMESTAMPTZ NOT NULL,
            updated_at          TIMESTAMPTZ NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ix_budget_allocations_project_id
        ON budget_allocations (project_id)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS budget_allocations")
