"""Create task_execution_results table.

Revision ID: 20260318_0010
Revises: 20260315_0009
Create Date: 2026-03-18
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "20260318_0010"
down_revision: Union[str, None] = "20260315_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create task_execution_results table."""

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS task_execution_results (
            result_id           TEXT PRIMARY KEY,
            task_id             TEXT NOT NULL,
            specialist_agent_id TEXT NOT NULL,
            output_text         TEXT NOT NULL,
            tools_used          TEXT NOT NULL DEFAULT '',
            execution_status    TEXT NOT NULL,
            trace_id            TEXT NOT NULL,
            created_at          TIMESTAMPTZ NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_task_execution_results_task_id
        ON task_execution_results (task_id)
        """
    )


def downgrade() -> None:
    """Drop task_execution_results table."""

    op.execute("DROP TABLE IF EXISTS task_execution_results")
