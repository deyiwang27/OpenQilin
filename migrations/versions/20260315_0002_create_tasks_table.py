"""Create tasks table for runtime state persistence.

Revision ID: 20260315_0002
Revises: 20260311_0001
Create Date: 2026-03-15
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260315_0002"
down_revision: Union[str, None] = "20260311_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create tasks table for runtime state persistence."""

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            task_id         TEXT PRIMARY KEY,
            request_id      TEXT NOT NULL,
            trace_id        TEXT NOT NULL,
            principal_id    TEXT NOT NULL,
            principal_role  TEXT NOT NULL,
            trust_domain    TEXT NOT NULL,
            connector       TEXT NOT NULL,
            command         TEXT NOT NULL,
            target          TEXT NOT NULL,
            args            JSONB NOT NULL DEFAULT '[]',
            metadata        JSONB NOT NULL DEFAULT '[]',
            project_id      TEXT,
            idempotency_key TEXT NOT NULL,
            status          TEXT NOT NULL,
            created_at      TIMESTAMPTZ NOT NULL,
            outcome_source      TEXT,
            outcome_error_code  TEXT,
            outcome_message     TEXT,
            outcome_details     JSONB,
            dispatch_target     TEXT,
            dispatch_id         TEXT
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_tasks_principal_idempotency
        ON tasks (principal_id, idempotency_key)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_tasks_status
        ON tasks (status)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_tasks_created_at
        ON tasks (created_at)
        """
    )


def downgrade() -> None:
    """Drop tasks table."""

    op.execute("DROP TABLE IF EXISTS tasks")
