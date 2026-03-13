from __future__ import annotations

from pathlib import Path

from openqilin.data_access.repositories.identity_channels import (
    InMemoryIdentityChannelRepository,
)


def test_identity_channel_repository_claim_status_and_persistence(tmp_path: Path) -> None:
    snapshot = tmp_path / "system_root" / "runtime" / "identity_channel_mappings.json"
    repository = InMemoryIdentityChannelRepository(snapshot_path=snapshot)

    claimed = repository.claim_mapping(
        connector="discord",
        actor_external_id="owner_001",
        guild_id="guild_001",
        channel_id="channel_001",
        channel_type="text",
    )
    assert claimed.status == "pending"

    verified = repository.set_mapping_status(
        connector="discord",
        actor_external_id="owner_001",
        guild_id="guild_001",
        channel_id="channel_001",
        channel_type="text",
        status="verified",
    )
    assert verified.status == "verified"

    reloaded = InMemoryIdentityChannelRepository(snapshot_path=snapshot)
    restored = reloaded.get_mapping(
        connector="discord",
        actor_external_id="owner_001",
        guild_id="guild_001",
        channel_id="channel_001",
        channel_type="text",
    )
    assert restored is not None
    assert restored.status == "verified"
