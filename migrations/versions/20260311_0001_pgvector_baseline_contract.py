"""Enable pgvector extension and baseline embedding schema contract.

Revision ID: 20260311_0001
Revises:
Create Date: 2026-03-11
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260311_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply pgvector extension and extension-dependent embedding table."""

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS knowledge_embedding (
            chunk_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            embedding vector(1536) NOT NULL,
            embedding_model TEXT NOT NULL,
            source_ref TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_knowledge_embedding_project_id
        ON knowledge_embedding (project_id)
        """
    )


def downgrade() -> None:
    """Revert extension-dependent baseline table."""

    op.execute("DROP TABLE IF EXISTS knowledge_embedding")
