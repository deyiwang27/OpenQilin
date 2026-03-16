"""Create audit_events table for immutable audit trail.

Revision ID: 20260315_0004
Revises: 20260315_0003
Create Date: 2026-03-15
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260315_0004"
down_revision: Union[str, None] = "20260315_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create audit_events table for AUD-001 immutable audit trail."""

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_events (
            event_id        TEXT PRIMARY KEY,
            event_type      TEXT NOT NULL,
            trace_id        TEXT NOT NULL,
            task_id         TEXT,
            principal_id    TEXT,
            principal_role  TEXT,
            action          TEXT,
            target          TEXT,
            decision        TEXT,
            rule_ids        JSONB NOT NULL DEFAULT '[]',
            payload         JSONB NOT NULL DEFAULT '{}',
            created_at      TIMESTAMPTZ NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_audit_events_trace_id
        ON audit_events (trace_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_audit_events_created_at
        ON audit_events (created_at)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_audit_events_task_id
        ON audit_events (task_id)
        """
    )


def downgrade() -> None:
    """Drop audit_events table."""

    op.execute("DROP TABLE IF EXISTS audit_events")
