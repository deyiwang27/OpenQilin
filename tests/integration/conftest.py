"""Integration test conftest: seed verified Discord identity mappings for all test actors.

When build_runtime_services() is fail-closed (M13-WP9), the principal resolver requires
a verified identity_channels row for every external actor.  This fixture runs once per
session and upserts the rows so every integration test starts with a ready-to-use DB.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text

# (actor_external_id, principal_role) for every actor used across integration tests.
_TEST_ACTORS: tuple[tuple[str, str], ...] = (
    ("owner_987", "owner"),
    ("owner_llm_integ_001", "owner"),
    ("owner_communication_integ_001", "owner"),
    ("owner_communication_integ_002", "owner"),
    ("owner_integ_001", "owner"),
    ("owner_integ_replay_blocked", "owner"),
    ("owner_policy_error_integration", "owner"),
    ("owner_budget_error_integration", "owner"),
    ("owner_dispatch_reject_integration", "owner"),
    ("owner_llm_runtime_error_integration", "owner"),
    ("owner_llm_grounding_missing_integration", "owner"),
    ("owner_llm_grounding_citation_integration", "owner"),
    ("owner_wp2_ack", "owner"),
    ("owner_wp2_nack", "owner"),
    ("owner_wp3_retry_ack", "owner"),
    ("owner_wp3_retry_exhausted", "owner"),
    ("owner_wp3_replay", "owner"),
    ("owner_wp4_dlq", "owner"),
    ("owner_wp4_dlq_replay", "owner"),
    ("owner_cb_int_001", "owner"),
    ("owner_cb_int_002", "owner"),
    ("owner_m13_wp1_e2e_001", "owner"),
    ("owner_m13_wp1_e2e_002", "owner"),
    ("owner_m13_wp1_e2e_003", "owner"),
    ("owner_m13_wp1_e2e_004", "owner"),
    ("owner_m13_wp1_e2e_005", "owner"),
    ("owner_m13_wp2_loop_001", "owner"),
    ("owner_m13_wp2_loop_002a", "owner"),
    ("owner_m13_wp2_loop_002b", "owner"),
    # Conformance test actors
    ("owner_m2_conformance_001", "owner"),
    ("owner_m2_conformance_002", "owner"),
    ("owner_m2_conformance_query_001", "owner"),
    ("owner_m3_conformance_cb", "owner"),
    ("owner_m3_conformance_dlq", "owner"),
    ("owner_m10_tool_write_ok", "ceo"),
    ("owner_m10_tool_write_raw_denied", "owner"),
    ("owner_m10_tool_read_denied", "owner"),
    ("owner_query_integration_001", "owner"),
    ("owner_m7_wp6", "owner"),
    ("cwo_m7_wp6", "cwo"),
    ("pm_m7_wp6", "project_manager"),
    ("ceo_m7_wp6", "ceo"),
)


@pytest.fixture(scope="session", autouse=True)
def seed_test_identities() -> None:
    """Upsert verified Discord identity mappings for all integration test actors."""
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
