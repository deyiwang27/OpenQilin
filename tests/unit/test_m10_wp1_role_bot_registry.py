from __future__ import annotations

import pytest

from openqilin.discord_runtime.role_bot_registry import (
    RoleBotRegistryError,
    build_role_bot_registry,
)
from openqilin.shared_kernel.config import RuntimeSettings


def test_m10_wp1_role_bot_registry_supports_legacy_role_to_token_map() -> None:
    settings = RuntimeSettings(
        discord_role_bot_tokens_json='{"ceo":"ceo-token","auditor":"auditor-token"}',
        discord_multi_bot_enabled=False,
    )

    registry = build_role_bot_registry(settings)

    ceo_identity = registry.identities_by_role["ceo"]
    assert ceo_identity.bot_id == "ceo"
    assert ceo_identity.token == "ceo-token"
    assert ceo_identity.status == "active"
    assert ceo_identity.guild_allowlist == ()


def test_m10_wp1_role_bot_registry_supports_rich_identity_entries() -> None:
    settings = RuntimeSettings(
        discord_role_bot_tokens_json=(
            '{"ceo":{"token":"ceo-token","bot_id":"ceo_core","guild_allowlist":["1","2"]}}'
        ),
        discord_multi_bot_enabled=False,
    )

    registry = build_role_bot_registry(settings)

    ceo_identity = registry.identities_by_role["ceo"]
    assert ceo_identity.bot_id == "ceo_core"
    assert ceo_identity.guild_allowlist == ("1", "2")
    assert ceo_identity.status == "active"


def test_m10_wp1_role_bot_registry_rejects_invalid_json_shape() -> None:
    settings = RuntimeSettings(discord_role_bot_tokens_json='["ceo"]')

    with pytest.raises(RoleBotRegistryError) as error:
        build_role_bot_registry(settings)

    assert error.value.code == "discord_role_bot_json_invalid"


def test_m10_wp1_role_bot_registry_rejects_duplicate_tokens() -> None:
    settings = RuntimeSettings(
        discord_role_bot_tokens_json='{"ceo":"shared","auditor":"shared"}',
        discord_multi_bot_enabled=False,
    )

    with pytest.raises(RoleBotRegistryError) as error:
        build_role_bot_registry(settings)

    assert error.value.code == "discord_role_bot_token_duplicate"


def test_m10_wp1_role_bot_registry_rejects_duplicate_bot_ids() -> None:
    settings = RuntimeSettings(
        discord_role_bot_tokens_json=(
            '{"ceo":{"token":"ceo-token","bot_id":"exec"},'
            '"auditor":{"token":"auditor-token","bot_id":"exec"}}'
        ),
        discord_multi_bot_enabled=False,
    )

    with pytest.raises(RoleBotRegistryError) as error:
        build_role_bot_registry(settings)

    assert error.value.code == "discord_role_bot_id_duplicate"


def test_m10_wp1_role_bot_registry_requires_active_roles_in_multi_bot_mode() -> None:
    settings = RuntimeSettings(
        discord_multi_bot_enabled=True,
        discord_required_role_bots_csv="ceo,auditor",
        discord_role_bot_tokens_json=(
            '{"ceo":{"token":"ceo-token","status":"active"},'
            '"auditor":{"token":"auditor-token","status":"disabled"}}'
        ),
    )

    with pytest.raises(RoleBotRegistryError) as error:
        build_role_bot_registry(settings)

    assert error.value.code == "discord_role_bot_required_missing"


def test_m10_wp1_role_bot_registry_uses_single_bot_fallback_when_disabled() -> None:
    settings = RuntimeSettings(
        discord_multi_bot_enabled=False,
        discord_role_bot_tokens_json="{}",
        discord_bot_token="single-token",
    )

    registry = build_role_bot_registry(settings)

    runtime_identity = registry.identities_by_role["runtime_agent"]
    assert runtime_identity.token == "single-token"
    assert runtime_identity.bot_id == "runtime_agent"
