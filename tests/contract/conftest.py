"""Contract test conftest: seed verified Discord identity mappings for all test actors.

When build_runtime_services() is fail-closed (M13-WP9), the principal resolver requires
a verified identity_channels row for every external actor.  This fixture runs once per
session and upserts the rows so every contract test starts with a ready-to-use DB.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text

# (actor_external_id, principal_role) for every actor used across contract tests.
_TEST_ACTORS: tuple[tuple[str, str], ...] = (
    ("owner_contract_accept", "owner"),
    ("owner_contract_block", "owner"),
    ("owner_contract_specialist_block", "owner"),
    ("owner_contract_msg_accept", "owner"),
    ("owner_contract_msg_deny", "owner"),
    ("owner_contract_query_1", "owner"),
    ("owner_contract_query_2", "owner"),
    ("owner_callback_contract", "owner"),
)


@pytest.fixture(scope="session", autouse=True)
def seed_test_identities() -> None:
    """Upsert verified Discord identity mappings for all contract test actors."""
    db_url = os.getenv("OPENQILIN_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not db_url:
        return

    engine = create_engine(db_url, future=True)
    now = datetime.now(tz=UTC)
    try:
        with engine.connect() as conn:
            for actor_id, role in _TEST_ACTORS:
                conn.execute(
                    text(
                        """
                        INSERT INTO identity_channels
                            (mapping_id, connector, actor_external_id,
                             guild_id, channel_id, channel_type,
                             status, principal_role, created_at, updated_at)
                        VALUES
                            (:mapping_id, 'discord', :actor_id,
                             'test-guild', 'test-channel', 'text',
                             'verified', :role, :now, :now)
                        ON CONFLICT (connector, actor_external_id, guild_id, channel_id, channel_type)
                        DO UPDATE SET status = 'verified', principal_role = :role, updated_at = :now
                        """
                    ),
                    {
                        "mapping_id": str(uuid4()),
                        "actor_id": actor_id,
                        "role": role,
                        "now": now,
                    },
                )
            conn.commit()
    finally:
        engine.dispose()
