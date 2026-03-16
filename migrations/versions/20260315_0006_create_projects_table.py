"""Create projects table for governance project lifecycle persistence.

Revision ID: 20260315_0006
Revises: 20260315_0005
Create Date: 2026-03-15
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260315_0006"
down_revision: Union[str, None] = "20260315_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create projects table for governance project lifecycle persistence."""

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS projects (
            project_id                              TEXT PRIMARY KEY,
            name                                    TEXT NOT NULL,
            objective                               TEXT NOT NULL,
            status                                  TEXT NOT NULL,
            metadata                                JSONB NOT NULL DEFAULT '{}',
            transitions                             JSONB NOT NULL DEFAULT '[]',
            proposal_messages                       JSONB NOT NULL DEFAULT '[]',
            proposal_approvals                      JSONB NOT NULL DEFAULT '[]',
            completion_report                       JSONB,
            completion_approvals                    JSONB NOT NULL DEFAULT '[]',
            completion_owner_notified_at            TIMESTAMPTZ,
            completion_owner_notification_trace_id  TEXT,
            initialization                          JSONB,
            workforce_bindings                      JSONB NOT NULL DEFAULT '[]',
            created_at                              TIMESTAMPTZ NOT NULL,
            updated_at                              TIMESTAMPTZ NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_projects_status
        ON projects (status)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_projects_created_at
        ON projects (created_at)
        """
    )


def downgrade() -> None:
    """Drop projects table."""

    op.execute("DROP TABLE IF EXISTS projects")
